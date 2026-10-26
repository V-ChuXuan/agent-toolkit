#!/usr/bin/env python3
"""Host-neutral session-title preparation and validation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any

MAX_INPUT_BYTES = 64 * 1024
MAX_FIELD_CHARS = 8 * 1024
MAX_TITLE_CHARS = 80
TARGET_TITLE_CHARS = 24
SOFT_MAX_TITLE_CHARS = 24
STATE_TTL_SECONDS = 30 * 24 * 60 * 60
PROFILE_FILE = ".session-title.json"
URL_ONLY = re.compile(r"(?:(?:https?://|www\.)[^\s<>]+)", re.IGNORECASE)
SECRET = re.compile(
    r"(?i)(?:"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    r"|sk-[A-Za-z0-9_-]{8,}"
    r"|(?:api[_ -]?key|access[_ -]?key|auth[_ -]?token|token|secret|password|passwd)"
    r"\s*[:=]\s*\S+"
    r"|bearer\s+[A-Za-z0-9._~-]{8,}"
    r")"
)
CONTINUATION = re.compile(
    r"^(?:(?:请|麻烦)?(?:继续|接着|往下|开始|开工|执行)(?:吧|任务)?"
    r"|(?:好的?|可以|行|批准(?:实施|开始)?|没问题)"
    r"|嗯+"
    r"|ok(?:ay)?"
    r"|status"
    r"|/status)"
    r"[\s!！。．,.，？?~～]*$",
    re.IGNORECASE,
)
ACTION_ONLY = re.compile(
    r"^(?:"
    r"(?:请|帮我|麻烦)?\s*"
    r"(?:检查|确认|判断|核验|分析|处理|查看|看看|看一下|看下|实现|修复|开发|"
    r"整理|调研|研究|设计|规划|阅读|打开|查阅|搜索|查找)(?:一下|下|一番)?"
    r"|(?:检查|确认|判断)(?:一下|下)?是不是(?:误判|异常|有问题)"
    r"|继续(?:开发|处理|做|工作|任务)?"
    r"|开发(?:一下|下)?"
    r")[\s!！。．,.，？?~～]*$",
    re.IGNORECASE,
)
AMBIGUOUS_FOLLOWUP = re.compile(
    r"^(?:"
    r"(?:我(?:觉得|感觉))?(?:可能|好像|似乎)?(?:还是|仍然)?"
    r"(?:不行|不对|不太对|不够好|有问题)"
    r"[，,、\s]*(?:你)?(?:再|继续)?(?:审查|检查|看看|分析|确认|判断|处理)?(?:一下|下)?"
    r"|(?:那|然后|现在)?(?:再|继续)?(?:审查|检查|看看|分析|确认|判断|处理)(?:一下|下)?"
    r"|(?:这个|这样|它|上述)(?:怎么样|可以吗|行吗|对吗|好用吗)"
    r"|(?:现在|目前)(?:呢|怎么样)"
    r"|还有什么优化空间(?:吗)?"
    r")[\s!！。．,.，？?~～]*$",
    re.IGNORECASE,
)
CONTROL_OR_TAG = re.compile(r"[\x00-\x1f\x7f<>]")
SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")
GENERIC_DIR_NAMES = {
    "",
    "workspace",
    "workspaces",
    "new-chat",
    "tmp",
    "temp",
    "src",
    "app",
    "repo",
    "project",
    "projects",
}


class ProfileError(ValueError):
    """The selected profile cannot be used safely."""


@dataclass(frozen=True)
class Profile:
    name: str
    language: str
    root: Path
    source: str | None
    kind_rules: tuple[dict[str, Any], ...]
    aliases: dict[str, str]
    domain_terms: tuple[str, ...]
    exclude: tuple[tuple[str, ...], ...]
    generic: bool = False


@dataclass(frozen=True)
class PathContext:
    relative_path: str
    kind_hint: str
    object_hint: str


def _safe_path(value: Any, base: Path | None = None) -> Path | None:
    if not isinstance(value, str) or not value or len(value) > MAX_FIELD_CHARS:
        return None
    try:
        path = Path(value).expanduser()
        if not path.is_absolute() and base is not None:
            path = base / path
        return path.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None


def _read_input() -> dict[str, Any]:
    try:
        raw = getattr(sys.stdin, "buffer", sys.stdin).read(MAX_INPUT_BYTES + 1)
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if len(raw) > MAX_INPUT_BYTES:
            return {}
        value = json.loads(raw.decode("utf-8"))
        return value if isinstance(value, dict) else {}
    except (UnicodeError, json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}


def _skip(reason: str) -> dict[str, Any]:
    return {"version": 1, "action": "skip", "reason": reason}


def _clean_text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    value = "".join(ch for ch in value if not (ord(ch) < 32 or ord(ch) == 127))
    return re.sub(r"\s+", " ", value).strip()[:limit].rstrip()


def _normalized_parts(value: str) -> tuple[str, ...]:
    parts: list[str] = []
    for part in value.replace("\\", "/").split("/"):
        part = part.strip()
        if not part or part == ".":
            continue
        if part == ".." or re.match(r"^[A-Za-z]:$", part):
            raise ProfileError("unsafe path component")
        parts.append(part)
    return tuple(parts)


def _casefold_parts(parts: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(part.casefold() for part in parts)


def _starts_with(parts: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    return len(parts) >= len(prefix) and _casefold_parts(parts[: len(prefix)]) == _casefold_parts(prefix)


def _relative_parts(path: Path, root: Path) -> tuple[str, ...] | None:
    try:
        relative = path.relative_to(root)
    except ValueError:
        try:
            common = Path(os.path.commonpath((str(path), str(root))))
        except (OSError, ValueError):
            return None
        if os.path.normcase(str(common)) != os.path.normcase(str(root)):
            return None
        try:
            relative = Path(os.path.relpath(path, root))
        except (OSError, ValueError):
            return None
    return tuple(part for part in relative.parts if part not in {"", "."})


def _display_alias(value: str, aliases: dict[str, str]) -> str:
    for key, alias in aliases.items():
        if key.casefold() == value.casefold():
            return alias
    return value


def _parse_profile_file(path: Path) -> Profile:
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ProfileError("profile too large")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError("profile unreadable") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ProfileError("profile version")
    name = _clean_text(data.get("name"), 64)
    language = _clean_text(data.get("language"), 16) or "auto"
    if not name:
        raise ProfileError("profile name")
    if language not in {"auto", "zh-CN", "en"}:
        raise ProfileError("profile language")

    raw_rules = data.get("kind_rules", [])
    if not isinstance(raw_rules, list) or len(raw_rules) > 64:
        raise ProfileError("profile rules")
    kind_rules: list[dict[str, Any]] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ProfileError("profile rule")
        prefix = _normalized_parts(item.get("prefix", ""))
        kind = _clean_text(item.get("kind"), 32)
        object_name = _clean_text(item.get("object"), 80)
        object_depth = item.get("object_depth", 0)
        if not prefix or not kind:
            raise ProfileError("profile rule")
        if not isinstance(object_depth, int) or isinstance(object_depth, bool) or not 0 <= object_depth <= 3:
            raise ProfileError("profile object depth")
        if not object_name and object_depth == 0:
            raise ProfileError("profile rule object")
        kind_rules.append(
            {
                "prefix": prefix,
                "kind": kind,
                "object": object_name,
                "object_depth": object_depth,
            }
        )
    kind_rules.sort(key=lambda rule: len(rule["prefix"]), reverse=True)

    raw_aliases = data.get("aliases", {})
    if not isinstance(raw_aliases, dict) or len(raw_aliases) > 128:
        raise ProfileError("profile aliases")
    aliases: dict[str, str] = {}
    for key, value in raw_aliases.items():
        clean_key = _clean_text(key, 80)
        clean_value = _clean_text(value, 80)
        if not clean_key or not clean_value:
            raise ProfileError("profile alias")
        aliases[clean_key] = clean_value

    raw_terms = data.get("domain_terms", [])
    if not isinstance(raw_terms, list) or len(raw_terms) > 64:
        raise ProfileError("profile terms")
    domain_terms: list[str] = []
    for value in raw_terms:
        term = _clean_text(value, 40)
        if term and term not in domain_terms:
            domain_terms.append(term)

    raw_exclude = data.get("exclude", [])
    if not isinstance(raw_exclude, list) or len(raw_exclude) > 64:
        raise ProfileError("profile exclude")
    exclude: list[tuple[str, ...]] = []
    for value in raw_exclude:
        parts = _normalized_parts(value if isinstance(value, str) else "")
        if parts:
            exclude.append(parts)

    return Profile(
        name=name,
        language=language,
        root=path.parent,
        source=str(path),
        kind_rules=tuple(kind_rules),
        aliases=aliases,
        domain_terms=tuple(domain_terms),
        exclude=tuple(exclude),
    )


def find_git_root(start: Path) -> Path | None:
    current = start
    while True:
        marker = current / ".git"
        try:
            if marker.is_dir() and (marker / "HEAD").is_file():
                return current
            if marker.is_file():
                first_line = marker.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
                if first_line and first_line[0].strip().startswith("gitdir:"):
                    return current
        except OSError:
            pass
        if current == current.parent:
            return None
        current = current.parent


def _generic_profile(cwd: Path) -> Profile:
    git_root = find_git_root(cwd)
    root = git_root or cwd
    return Profile(
        name="generic",
        language="auto",
        root=root,
        source=None,
        kind_rules=(),
        aliases={},
        domain_terms=(),
        exclude=(),
        generic=True,
    )


def load_profile(cwd: Path) -> Profile:
    configured = os.environ.get("SESSION_TITLE_PROFILE")
    if configured:
        path = _safe_path(configured, cwd)
        if path is None or not path.is_file():
            raise ProfileError("profile override missing")
        return _parse_profile_file(path)

    current = cwd
    while True:
        candidate = current / PROFILE_FILE
        try:
            if candidate.is_file():
                return _parse_profile_file(candidate)
        except OSError:
            pass
        if current == current.parent:
            break
        current = current.parent
    return _generic_profile(cwd)


def _profile_context(profile: Profile, cwd: Path) -> PathContext | None:
    relative = _relative_parts(cwd, profile.root)
    if relative is None:
        return None
    if any(_starts_with(relative, prefix) for prefix in profile.exclude):
        return None
    for rule in profile.kind_rules:
        prefix = rule["prefix"]
        if not _starts_with(relative, prefix):
            continue
        object_name = rule["object"]
        if not object_name:
            depth = rule["object_depth"]
            selected = relative[len(prefix) : len(prefix) + depth]
            if len(selected) < depth:
                return None
            object_name = "/".join(_display_alias(part, profile.aliases) for part in selected)
        return PathContext(
            relative_path="/".join(relative),
            kind_hint=rule["kind"],
            object_hint=object_name,
        )

    if not profile.generic:
        return PathContext(
            relative_path="/".join(relative),
            kind_hint="工作区",
            object_hint="工作区",
        )

    git_root = find_git_root(cwd)
    if git_root is not None:
        return PathContext(
            relative_path="/".join(relative),
            kind_hint="项目",
            object_hint=_display_alias(git_root.name, profile.aliases) or "项目",
        )

    temporary = _safe_path(tempfile.gettempdir())
    is_temp = temporary is not None and (
        os.path.normcase(str(cwd)) == os.path.normcase(str(temporary))
        or os.path.normcase(str(cwd)).startswith(os.path.normcase(str(temporary)) + os.sep)
    )
    if is_temp:
        return PathContext(relative_path="/".join(relative), kind_hint="临时", object_hint="临时")
    root_name = _clean_text(profile.root.name, 80)
    if profile.root != cwd or root_name.casefold() not in GENERIC_DIR_NAMES:
        return PathContext(
            relative_path="/".join(relative),
            kind_hint="工作区",
            object_hint=_display_alias(root_name, profile.aliases) or "工作区",
        )
    return PathContext(relative_path="/".join(relative), kind_hint="工作区", object_hint="工作区")


def _request_text(prompt: Any) -> str | None:
    if not isinstance(prompt, str) or not prompt or len(prompt) > MAX_FIELD_CHARS:
        return None
    text = prompt
    if "# My request:" in text:
        text = text.rsplit("# My request:", 1)[1]
        if not text.strip() or text.lstrip().startswith("<image"):
            return None
    elif text.lstrip().startswith("# Files mentioned by the user:"):
        return None
    text = text.strip()
    return text or None


def _gate_reason(prompt: Any) -> str | None:
    text = _request_text(prompt)
    if text is None:
        return "empty_prompt"
    if URL_ONLY.fullmatch(text):
        return "url_only"
    if SECRET.search(text):
        return "sensitive_input"
    normalized = text.strip(" \t\r\n，。；：:、,!?！？~～")
    if CONTINUATION.fullmatch(normalized):
        return "continuation"
    if ACTION_ONLY.fullmatch(normalized):
        return "ambiguous_task"
    if AMBIGUOUS_FOLLOWUP.fullmatch(normalized):
        return "ambiguous_followup"
    return None


def _effective_language(profile: Profile, prompt: str) -> str:
    if profile.language != "auto":
        return profile.language
    return "zh-CN" if re.search(r"[\u3400-\u9fff]", prompt) else "en"


def _state_root() -> Path:
    configured = os.environ.get("SESSION_TITLE_STATE_ROOT")
    if configured:
        return _safe_path(configured) or Path(tempfile.gettempdir()) / "session-title" / "state"
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base = _safe_path(local_app_data)
        if base is not None:
            return base / "session-title" / "state"
    return Path.home() / "AppData" / "Local" / "session-title" / "state"


def _safe_component(value: str) -> str:
    cleaned = SAFE_COMPONENT.sub("-", value).strip("-._")
    return cleaned[:64] or "default"


def _state_path(host: str, profile: Profile, session_id: str) -> Path:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:32]
    return _state_root() / _safe_component(host) / _safe_component(profile.name) / f"{digest}.json"


def request_status(
    host: str,
    cwd: Path,
    session_id: str,
    now: float | None = None,
) -> str:
    """Return requested, absent, or unknown without creating state."""
    if (
        not isinstance(host, str)
        or not re.fullmatch(r"[a-z0-9_-]+", host)
        or not isinstance(cwd, Path)
        or not isinstance(session_id, str)
        or not session_id
    ):
        return "unknown"
    try:
        profile = load_profile(cwd)
    except ProfileError:
        return "unknown"
    path = _state_path(host, profile, session_id)
    try:
        if not path.is_file():
            return "absent"
        current = time.time() if now is None else now
        if current - path.stat().st_mtime > STATE_TTL_SECONDS:
            path.unlink()
            return "absent"
        return "requested"
    except OSError:
        return "unknown"


def _cleanup_expired(directory: Path, now: float) -> None:
    try:
        entries = tuple(directory.glob("*.json"))
    except OSError:
        return
    for path in entries:
        try:
            if now - path.stat().st_mtime > STATE_TTL_SECONDS:
                path.unlink()
        except OSError:
            continue


def _claim(path: Path, host: str, profile: Profile, now: float) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _cleanup_expired(path.parent, now)
    except OSError:
        return "error"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return "exists"
    except OSError:
        return "error"

    payload = {
        "version": 1,
        "host": host,
        "profile": profile.name,
        "phase": "requested",
        "claimed_at": int(now),
    }
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        return "claimed"
    except OSError:
        try:
            path.unlink()
        except OSError:
            pass
        return "error"


def _instruction(language: str) -> str:
    if language == "zh-CN":
        return (
            "先完成用户首个实质任务，在发送最终答复前才调用宿主原生标题工具改名一次。"
            "标题必须单行，主推荐格式为“模块名 | 持续目标”；如宿主已有“意图·对象 | 任务”约定，可兼容该格式。"
            "优先写具体对象、行为、错误现象或决策，不使用“实现”“处理需求”“优化”“问题”等空泛词。"
            "标题目标约 24 个字符，24 个字符是软上限；保留稳定对象名，不复制长路径、URL、XML 或敏感信息。"
            "只依据首个实质任务提炼持续目标，不要用关键词模板拼接。后续追问不再改名。"
            "不要向用户展示标题建议或解释改名要求；无原生工具时正常完成，不伪造改名。"
            "如果当前已有用户自定义标题、工具不可用或写入不安全，不要修改标题，也不要声称写入成功。"
        )
    return (
        "Complete the user's first substantive task first; call the host's native session-title tool exactly once, "
        "immediately before sending the final answer. "
        "Use one line, preferably in the form `module | ongoing goal`; retain `intent·object | task` only as a "
        "compatibility form when the host already uses it. "
        "Prefer concrete objects, actions, observed errors, or decisions; avoid vague words such as implement, "
        "handle requirements, optimize, or issue. "
        f"Aim for {TARGET_TITLE_CHARS} characters or fewer and treat {SOFT_MAX_TITLE_CHARS} as a soft maximum. "
        "Preserve stable repository/object names and omit long paths, URLs, XML, and secrets. "
        "Summarize the ongoing goal from the first substantive task instead of copying a keyword template. "
        "Do not rename the session on later follow-ups. Do not show title suggestions or explain the renaming "
        "requirement to the user. Finish normally without a native tool and never claim a rename that did not happen. "
        "Do not overwrite an existing user title or claim success when writing is unsafe."
    )


def prepare(data: dict[str, Any], now: float | None = None) -> dict[str, Any]:
    host = _clean_text(data.get("host"), 32).casefold()
    session_id = data.get("session_id")
    cwd = _safe_path(data.get("cwd"))
    prompt = data.get("prompt")

    if not host or not re.fullmatch(r"[a-z0-9_-]+", host):
        return _skip("invalid_host")
    if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > MAX_FIELD_CHARS:
        return _skip("invalid_session")
    if cwd is None:
        return _skip("invalid_cwd")
    if not isinstance(prompt, str) or len(prompt) > MAX_FIELD_CHARS:
        return _skip("invalid_prompt")
    # Only an explicit null or empty value means the adapter confirmed no title.
    if "current_title" not in data:
        return _skip("title_state_unknown")
    current_title = data["current_title"]
    if current_title is not None and not isinstance(current_title, str):
        return _skip("title_state_unknown")
    if isinstance(current_title, str) and current_title.strip():
        return _skip("manual_title")

    try:
        profile = load_profile(cwd)
    except ProfileError:
        return _skip("profile_invalid")
    context = _profile_context(profile, cwd)
    if context is None:
        return _skip("path_excluded")

    gate = _gate_reason(prompt)
    if gate:
        return _skip(gate)

    claim_time = time.time() if now is None else now
    claim = _claim(_state_path(host, profile, session_id), host, profile, claim_time)
    if claim == "exists":
        return _skip("already_requested")
    if claim != "claimed":
        return _skip("state_error")

    language = _effective_language(profile, prompt)
    return {
        "version": 1,
        "action": "request_title",
        "reason": "eligible",
        "profile": {
            "name": profile.name,
            "language": profile.language,
            "source": profile.source,
        },
        "context": {
            "cwd": str(cwd),
            "relative_path": context.relative_path,
            "kind_hint": context.kind_hint,
            "object_hint": context.object_hint,
            "language": language,
            "aliases": profile.aliases,
            "domain_terms": list(profile.domain_terms),
            "format": "模块名 | 持续目标",
            "target_chars": TARGET_TITLE_CHARS,
            "soft_max_chars": SOFT_MAX_TITLE_CHARS,
        },
        "instruction": _instruction(language),
    }


def validate_title(title: Any) -> dict[str, Any]:
    if not isinstance(title, str):
        return {"valid": False, "reason": "title_type", "title": "", "chars": 0}
    normalized = title.strip()
    chars = len(normalized)
    result = {"valid": False, "title": normalized, "reason": "", "chars": chars}
    if not normalized:
        result["reason"] = "empty"
        return result
    if "\n" in normalized or "\r" in normalized:
        result["reason"] = "multiline"
        return result
    if chars > MAX_TITLE_CHARS:
        result["reason"] = "too_long"
        return result
    if CONTROL_OR_TAG.search(normalized):
        result["reason"] = "control_or_tag"
        return result
    if SECRET.search(normalized):
        result["reason"] = "sensitive_input"
        return result
    if URL_ONLY.search(normalized):
        result["reason"] = "contains_url"
        return result
    if normalized.count("|") != 1 or normalized.count(" | ") != 1:
        result["reason"] = "separator"
        return result
    left, task = normalized.split(" | ", 1)
    if not left or not task:
        result["reason"] = "empty_part"
        return result
    if left.count("·") > 1:
        result["reason"] = "left_parts"
        return result
    if left.count("·") == 1 and any(not part.strip() for part in left.split("·")):
        result["reason"] = "left_parts"
        return result
    if CONTINUATION.fullmatch(normalized) or ACTION_ONLY.fullmatch(normalized):
        result["reason"] = "not_a_title"
        return result

    result["valid"] = True
    result["reason"] = "ok"
    if chars > SOFT_MAX_TITLE_CHARS:
        result["warning"] = "soft_max_exceeded"
    return result


def _format_text(result: dict[str, Any]) -> str:
    if result.get("action") == "request_title":
        context = result.get("context", {})
        return (
            f"request_title: {context.get('kind_hint', '')}·{context.get('object_hint', '')}"
            f" | {context.get('format', '')}"
        )
    if "valid" in result:
        if result["valid"]:
            return f"valid: {result['title']} ({result['chars']} chars)"
        return f"invalid: {result['reason']}"
    return f"skip: {result.get('reason', 'unknown')}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="session-title")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare", help="read a host event from stdin")
    validate_parser = subparsers.add_parser("validate", help="validate a generated title")
    validate_parser.add_argument("--title")
    args = parser.parse_args(argv)

    if args.command == "prepare":
        result = prepare(_read_input())
    else:
        data = _read_input()
        title = args.title if args.title is not None else data.get("title")
        result = validate_title(title)

    if args.format == "text":
        print(_format_text(result))
    else:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
