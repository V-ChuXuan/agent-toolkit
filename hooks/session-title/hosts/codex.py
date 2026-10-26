#!/usr/bin/env python3
"""Codex UserPromptSubmit adapter for the shared session-title core."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from typing import Any

import session_title

MAX_HOOK_BYTES = 64 * 1024
CODEX_PROBE_TIMEOUT = 5.0


@dataclass(frozen=True)
class TitleProbe:
    known: bool
    title: str | None = None


def _read_event() -> dict[str, Any]:
    try:
        raw = getattr(sys.stdin, "buffer", sys.stdin).read(MAX_HOOK_BYTES + 1)
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if len(raw) > MAX_HOOK_BYTES:
            return {}
        value = json.loads(raw.decode("utf-8"))
        return value if isinstance(value, dict) else {}
    except (UnicodeError, json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}


def _codex_command() -> list[str] | None:
    override = os.environ.get("CODEX_EXECUTABLE")
    candidates = [override] if override else []
    if os.name == "nt":
        candidates.extend(("codex.exe", "codex.cmd", "codex"))
    else:
        candidates.append("codex")

    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate:
            continue
        path = Path(candidate).expanduser()
        if not path.is_file():
            found = shutil.which(candidate)
            if not found:
                continue
            path = Path(found)
        suffix = path.suffix.casefold()
        if suffix in {".cmd", ".bat"}:
            return ["cmd.exe", "/d", "/s", "/c", str(path)]
        if suffix == ".ps1":
            return [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(path),
            ]
        return [str(path)]
    return None


def _send(process: subprocess.Popen[str], value: dict[str, Any]) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _read_until(process: subprocess.Popen[str], request_id: int, deadline: float) -> dict[str, Any] | None:
    assert process.stdout is not None
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if not line:
            return None
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("id") == request_id:
            return value
    return None


def _read_thread_title(session_id: str, cwd: Path, timeout: float = CODEX_PROBE_TIMEOUT) -> TitleProbe:
    command = _codex_command()
    if command is None:
        return TitleProbe(False)

    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(
            [*command, "app-server", "--stdio"],
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
    except (OSError, TypeError, ValueError):
        return TitleProbe(False)

    timer = threading.Timer(timeout, process.kill)
    timer.daemon = True
    timer.start()
    deadline = time.monotonic() + timeout
    try:
        _send(
            process,
            {
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "session-title-hook", "version": "0.1"}},
            },
        )
        initialized = _read_until(process, 1, deadline)
        if not initialized or not isinstance(initialized.get("result"), dict):
            return TitleProbe(False)

        _send(process, {"method": "initialized"})
        _send(
            process,
            {
                "id": 2,
                "method": "thread/read",
                "params": {"threadId": session_id, "includeTurns": False},
            },
        )
        response = _read_until(process, 2, deadline)
        if not response:
            return TitleProbe(False)
        error = response.get("error")
        if isinstance(error, dict):
            if (
                error.get("code") == -32600
                and error.get("message") == f"thread not loaded: {session_id}"
            ):
                return TitleProbe(True, None)
            return TitleProbe(False)
        if error is not None:
            return TitleProbe(False)
        thread = response.get("result", {}).get("thread")
        if not isinstance(thread, dict):
            return TitleProbe(False)
        name = thread.get("name")
        if name is None or name == "":
            return TitleProbe(True, None)
        if isinstance(name, str):
            return TitleProbe(True, name)
        return TitleProbe(False)
    except (BrokenPipeError, OSError, TypeError, ValueError):
        return TitleProbe(False)
    finally:
        timer.cancel()
        for stream in (process.stdin, process.stdout, process.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        try:
            process.terminate()
            process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass


def _additional_context(result: dict[str, Any]) -> str:
    context = result.get("context", {})
    domain_terms = context.get("domain_terms", [])
    terms = ", ".join(domain_terms) if isinstance(domain_terms, list) else ""
    lines = [
        "<session-title-task>",
        f"Scope kind: {context.get('kind_hint', '')}",
        f"Scope object: {context.get('object_hint', '')}",
        f"Relative path: {context.get('relative_path', '')}",
        f"Format: {context.get('format', '模块名 | 持续目标')}",
        f"Target chars: {context.get('target_chars', 24)}",
        f"Soft max chars: {context.get('soft_max_chars', 24)}",
    ]
    if terms:
        lines.append(f"Domain terms: {terms}")
    lines.extend((str(result.get("instruction", "")), "</session-title-task>"))
    return "\n".join(line for line in lines if line)


def main() -> int:
    try:
        event = _read_event()
        hook_event = event.get("hook_event_name")
        if hook_event not in (None, "UserPromptSubmit", "userPromptSubmit"):
            return 0
        session_id = event.get("session_id")
        cwd_value = event.get("cwd")
        prompt = event.get("prompt")
        if not isinstance(session_id, str) or not session_id:
            return 0
        if not isinstance(cwd_value, str) or not cwd_value:
            return 0
        if not isinstance(prompt, str):
            return 0
        cwd = Path(cwd_value).expanduser().resolve(strict=False)

        if session_title.request_status("codex", cwd, session_id) != "absent":
            return 0
        probe = _read_thread_title(session_id, cwd)
        if not probe.known:
            return 0
        result = session_title.prepare(
            {
                "host": "codex",
                "session_id": session_id,
                "cwd": str(cwd),
                "prompt": prompt,
                "current_title": probe.title,
            }
        )
        if result.get("action") != "request_title":
            return 0
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": _additional_context(result),
                    }
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
