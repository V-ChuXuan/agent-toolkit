from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("session_title.py")
SPEC = importlib.util.spec_from_file_location("session_title", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def profile_data(name: str = "test-profile", language: str = "zh-CN") -> dict:
    return {
        "version": 1,
        "name": name,
        "language": language,
        "kind_rules": [
            {"prefix": "projects/docs", "kind": "资料", "object": "docs"},
            {"prefix": "projects", "kind": "项目", "object_depth": 1},
            {"prefix": "notes/reference", "kind": "笔记", "object": "参考"},
        ],
        "aliases": {"demo-project": "示例项目"},
        "domain_terms": ["Hook", "会话标题"],
        "exclude": [".tmp"],
    }


def write_profile(root: Path, data: dict | str | None = None) -> Path:
    path = root / MODULE.PROFILE_FILE
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data or profile_data(), ensure_ascii=False), encoding="utf-8")
    return path


def payload(
    cwd: Path,
    prompt: str,
    session_id: str = "session-1",
    current_title: str | None = None,
    **extra,
) -> dict:
    return {
        "host": "codex",
        "session_id": session_id,
        "cwd": str(cwd),
        "prompt": prompt,
        "current_title": current_title,
        **extra,
    }


def run_cli(data: dict | bytes, state_root: Path, *args: str, env_extra: dict | None = None):
    env = os.environ.copy()
    env["SESSION_TITLE_STATE_ROOT"] = str(state_root)
    env.pop("SESSION_TITLE_PROFILE", None)
    if env_extra:
        env.update(env_extra)
    raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), *args],
        input=raw,
        capture_output=True,
        env=env,
    )


class SessionTitleCoreTests(unittest.TestCase):
    def test_profile_uses_longest_component_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            profile = MODULE.load_profile(root / "projects" / "demo-project")
            self.assertEqual(profile.name, "test-profile")
            self.assertEqual(profile.language, "zh-CN")
            cases = {
                "projects/demo-project/src": ("项目", "示例项目"),
                "projects/docs/api": ("资料", "docs"),
                "projects/docs-other/api": ("项目", "docs-other"),
                "projects-other/demo": ("工作区", "工作区"),
                "notes/reference/articles": ("笔记", "参考"),
                "notes/other-topic": ("工作区", "工作区"),
            }
            for relative, expected in cases.items():
                context = MODULE._profile_context(profile, root / relative)
                self.assertIsNotNone(context, relative)
                self.assertEqual((context.kind_hint, context.object_hint), expected, relative)
            self.assertEqual(
                MODULE._profile_context(profile, root / "PROJECTS" / "DEMO-PROJECT").object_hint,
                "示例项目",
            )
            self.assertIsNone(MODULE._profile_context(profile, root / ".tmp" / "probe"))

    def test_nearest_profile_and_environment_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            write_profile(root, profile_data("nearby"))
            self.assertEqual(MODULE.load_profile(nested).name, "nearby")

            override_root = root / "override"
            override_root.mkdir()
            override = write_profile(override_root, profile_data("override"))
            with patch.dict(os.environ, {"SESSION_TITLE_PROFILE": str(override)}):
                self.assertEqual(MODULE.load_profile(nested).name, "override")
            with patch.dict(os.environ, {"SESSION_TITLE_PROFILE": str(root / "missing.json")}):
                with self.assertRaises(MODULE.ProfileError):
                    MODULE.load_profile(nested)

    def test_invalid_profiles_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in (
                "{bad",
                {"version": 2, "name": "x", "language": "auto"},
                {**profile_data(), "kind_rules": [{"prefix": "../x", "kind": "项目", "object_depth": 1}]},
                {**profile_data(), "kind_rules": [{"prefix": "x", "kind": "项目", "object_depth": True}]},
            ):
                write_profile(root, value)
                with self.assertRaises(MODULE.ProfileError):
                    MODULE.load_profile(root)

    def test_generic_git_and_temporary_fallbacks(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "shared-project"
            child = repo / "src" / "tests"
            child.mkdir(parents=True)
            (repo / ".git").mkdir()
            (repo / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
            profile = MODULE.load_profile(child)
            self.assertTrue(profile.generic)
            context = MODULE._profile_context(profile, child)
            self.assertEqual((context.kind_hint, context.object_hint), ("项目", "shared-project"))

            temp_child = Path(tempfile.gettempdir()) / "session-title-random-probe"
            profile = MODULE._generic_profile(temp_child)
            context = MODULE._profile_context(profile, temp_child)
            self.assertEqual((context.kind_hint, context.object_hint), ("临时", "临时"))

    def test_gate_matrix_and_state_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            cwd = root / "projects" / "demo-project"
            cwd.mkdir(parents=True)
            state = root / "state"
            expected = {
                "": "empty_prompt",
                "继续": "continuation",
                "好的！": "continuation",
                "批准实施": "continuation",
                "ok": "continuation",
                "https://example.com/path": "url_only",
                "请整理 token=secret-value 项目": "sensitive_input",
                "帮我看看": "ambiguous_task",
                "分析一下": "ambiguous_task",
                "继续开发": "ambiguous_task",
                "检查一下是不是误判": "ambiguous_task",
                "再检查一下": "ambiguous_followup",
                "这个怎么样": "ambiguous_followup",
                "还有什么优化空间吗": "ambiguous_followup",
            }
            for prompt, reason in expected.items():
                with patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}):
                    result = MODULE.prepare(payload(cwd, prompt, session_id=f"gate-{len(prompt)}"))
                self.assertEqual(result, {"version": 1, "action": "skip", "reason": reason}, prompt)
            self.assertFalse(state.exists())

            excluded = root / ".tmp" / "probe"
            excluded.mkdir(parents=True)
            with patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}):
                result = MODULE.prepare(payload(excluded, "实现会话标题 Hook"))
            self.assertEqual(result["action"], "skip")
            self.assertEqual(result["reason"], "path_excluded")
            self.assertFalse(state.exists())

    def test_prepare_returns_model_context_without_prompt_or_final_title(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            cwd = root / "projects" / "demo-project"
            cwd.mkdir(parents=True)
            state = root / "state"
            prompt = "实现一个不会和用户抢标题的会话命名 Hook"
            with patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}):
                first = MODULE.prepare(payload(cwd, prompt))
                replay = MODULE.prepare(payload(cwd, prompt))
            self.assertEqual(first["action"], "request_title")
            self.assertEqual(first["context"]["kind_hint"], "项目")
            self.assertEqual(first["context"]["object_hint"], "示例项目")
            self.assertEqual(first["context"]["language"], "zh-CN")
            self.assertEqual(first["context"]["format"], "模块名 | 持续目标")
            for expected in (
                "先完成用户首个实质任务，在发送最终答复前才调用宿主原生标题工具改名一次",
                "优先写具体对象、行为、错误现象或决策",
                "后续追问不再改名",
                "不要向用户展示标题建议或解释改名要求",
                "无原生工具时正常完成，不伪造改名",
            ):
                self.assertIn(expected, first["instruction"])
            encoded = json.dumps(first, ensure_ascii=False)
            self.assertNotIn(prompt, encoded)
            self.assertNotIn("session-1", encoded)
            self.assertNotIn(str(cwd), first.get("instruction", ""))
            self.assertNotIn("final_title", first)
            self.assertEqual(replay, {"version": 1, "action": "skip", "reason": "already_requested"})

            files = list(state.rglob("*.json"))
            self.assertEqual(len(files), 1)
            persisted = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(
                set(persisted),
                {"version", "host", "profile", "phase", "claimed_at"},
            )
            self.assertNotIn(prompt, files[0].read_text(encoding="utf-8"))
            self.assertNotIn(str(cwd), files[0].read_text(encoding="utf-8"))

    def test_manual_title_skips_without_claim_and_unknown_state_is_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            cwd = root / "projects" / "demo-project"
            cwd.mkdir(parents=True)
            state = root / "state"
            with patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}):
                manual = MODULE.prepare(payload(cwd, "实现会话标题 Hook", current_title="用户自己的标题"))
                unknown = MODULE.prepare(payload(cwd, "实现会话标题 Hook", current_title=1))
            self.assertEqual(manual["reason"], "manual_title")
            self.assertEqual(unknown["reason"], "title_state_unknown")
            self.assertFalse(state.exists())

    def test_missing_current_title_is_unknown_and_does_not_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            cwd = root / "projects" / "demo-project"
            cwd.mkdir(parents=True)
            state = root / "state"
            missing = payload(cwd, "实现会话标题 Hook", session_id="missing-title")
            missing.pop("current_title")
            with patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}):
                result = MODULE.prepare(missing)
            self.assertEqual(result, {"version": 1, "action": "skip", "reason": "title_state_unknown"})
            self.assertFalse(state.exists())

    def test_empty_current_title_means_confirmed_no_title(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            cwd = root / "projects" / "demo-project"
            cwd.mkdir(parents=True)
            state = root / "state"
            with patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}):
                result = MODULE.prepare(
                    payload(cwd, "实现会话标题 Hook", session_id="empty-title", current_title="")
                )
            self.assertEqual(result["action"], "request_title")
            self.assertEqual(len(list(state.rglob("*.json"))), 1)

    def test_concurrent_processes_claim_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            cwd = root / "projects" / "demo-project"
            cwd.mkdir(parents=True)
            state = root / "state"
            data = payload(cwd, "修复登录问题", session_id="concurrent")
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: run_cli(data, state, "prepare"), range(8)))
            self.assertTrue(all(result.returncode == 0 for result in results))
            parsed = [json.loads(result.stdout) for result in results]
            self.assertEqual(sum(item.get("action") == "request_title" for item in parsed), 1)
            self.assertEqual(sum(item.get("reason") == "already_requested" for item in parsed), 7)
            self.assertEqual(len(list(state.rglob("*.json"))), 1)

    def test_state_failure_ttl_and_partition_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            cwd = root / "projects" / "demo-project"
            cwd.mkdir(parents=True)
            blocked = root / "blocked-state"
            blocked.write_text("occupied", encoding="utf-8")
            with patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(blocked)}):
                result = MODULE.prepare(payload(cwd, "实现会话标题 Hook"))
            self.assertEqual(result["reason"], "state_error")

            state = root / "state"
            now = time.time()
            with patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}):
                profile = MODULE.load_profile(cwd)
                stale_path = MODULE._state_path("codex", profile, "stale")
                stale_path.parent.mkdir(parents=True)
                stale_path.write_text("{}", encoding="utf-8")
                old = now - MODULE.STATE_TTL_SECONDS - 10
                os.utime(stale_path, (old, old))
                first = MODULE.prepare(payload(cwd, "实现会话标题 Hook", session_id="fresh"), now=now)
                self.assertEqual(first["action"], "request_title")
                self.assertFalse(stale_path.exists())

                same_profile_other_host = MODULE.prepare(
                    {**payload(cwd, "实现会话标题 Hook", session_id="fresh"), "host": "pi"},
                    now=now + 1,
                )
                self.assertEqual(same_profile_other_host["action"], "request_title")

    def test_validate_title_contract(self):
        valid = MODULE.validate_title("Hook | 收紧会话标题")
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["reason"], "ok")
        self.assertNotIn("warning", valid)

        recommended = MODULE.validate_title("会话标题 Hook | 收紧标题状态与指令")
        self.assertTrue(recommended["valid"])
        self.assertEqual(recommended["reason"], "ok")
        self.assertNotIn("warning", recommended)

        long_name = "LongRepositoryNameWithImportantSuffix"
        soft = MODULE.validate_title(f"实现·{long_name} | 通用会话标题 Hook")
        self.assertTrue(soft["valid"])
        self.assertEqual(soft["warning"], "soft_max_exceeded")

        invalid = {
            "": "empty",
            "实现·对象": "separator",
            "a | b | c": "separator",
            "a|b": "separator",
            "·对象 | 任务": "left_parts",
            "意图· | 任务": "left_parts",
            "意图·对象 | <tag>": "control_or_tag",
            "意图·对象 | api_key=secret-value": "sensitive_input",
            "意图·对象 | https://example.com": "contains_url",
            "意图·对象 | 第一行\n第二行": "multiline",
            "继续": "separator",
            "x" * (MODULE.MAX_TITLE_CHARS + 1) + " | y": "too_long",
        }
        for title, reason in invalid.items():
            result = MODULE.validate_title(title)
            self.assertFalse(result["valid"], title)
            self.assertEqual(result["reason"], reason, title)

    def test_cli_default_json_and_text_debug(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_profile(root)
            cwd = root / "projects" / "demo-project"
            cwd.mkdir(parents=True)
            data = payload(cwd, "实现会话标题 Hook", session_id="cli")
            state = root / "state"
            json_result = run_cli(data, state, "prepare")
            self.assertEqual(json_result.returncode, 0)
            parsed = json.loads(json_result.stdout)
            self.assertEqual(parsed["action"], "request_title")
            self.assertEqual(json_result.stderr, b"")

            text_result = run_cli(
                payload(cwd, "实现会话标题 Hook", session_id="cli-text"),
                root / "state-text",
                "--format",
                "text",
                "prepare",
            )
            self.assertEqual(text_result.returncode, 0)
            self.assertIn(b"request_title:", text_result.stdout)
            self.assertNotIn(b"session-", text_result.stdout)
            self.assertEqual(text_result.stderr, b"")

    def test_bad_inputs_exit_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            for raw in (b"{bad", b"\xff", b"[]", b"{}"):
                result = run_cli(raw, state, "prepare")
                self.assertEqual(result.returncode, 0)
                self.assertIn(json.loads(result.stdout)["action"], {"skip"})
                self.assertEqual(result.stderr, b"")
            oversized = b"x" * (MODULE.MAX_INPUT_BYTES + 1)
            result = run_cli(oversized, state, "prepare")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["action"], "skip")


if __name__ == "__main__":
    unittest.main()
