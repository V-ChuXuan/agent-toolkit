from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


CORE = Path(__file__).parent
sys.path.insert(0, str(CORE))

from hosts import codex as codex_host  # noqa: E402


def write_profile(root: Path) -> None:
    (root / ".session-title.json").write_text(
        json.dumps(
            {
                "version": 1,
                "name": "codex-host-test",
                "language": "zh-CN",
                "kind_rules": [
                    {"prefix": "projects", "kind": "项目", "object": "demo"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def event(cwd: Path) -> dict:
    return {
        "session_id": "thread-1",
        "cwd": str(cwd),
        "prompt": "实现会话标题 Hook",
        "hook_event_name": "UserPromptSubmit",
    }


def run_hook(cwd: Path, state: Path, probe: codex_host.TitleProbe) -> tuple[int, str]:
    stdout = io.StringIO()
    with (
        patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}),
        patch.object(codex_host, "_read_event", return_value=event(cwd)),
        patch.object(codex_host, "_read_thread_title", return_value=probe),
        redirect_stdout(stdout),
    ):
        code = codex_host.main()
    return code, stdout.getvalue()


class CodexHostTests(unittest.TestCase):
    def test_standalone_entrypoint_accepts_invalid_event_from_another_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(
                [sys.executable, "-B", "-X", "utf8", str(CORE.resolve() / "codex_hook.py")],
                input=b"{}",
                capture_output=True,
                cwd=directory,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
            self.assertEqual(result.stdout, b"")
            self.assertEqual(result.stderr, b"")

    def probe_with_fake_server(self, response: dict) -> codex_host.TitleProbe:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "response.json").write_text(
                json.dumps(response),
                encoding="utf-8",
            )
            server = root / "fake_app_server.py"
            server.write_text(
                "\n".join(
                    (
                        "import json, pathlib, sys",
                        "response = json.loads(pathlib.Path(__file__).with_name('response.json').read_text(encoding='utf-8'))",
                        "for line in sys.stdin:",
                        "    request = json.loads(line)",
                        "    request_id = request.get('id')",
                        "    if request_id == 1:",
                        "        print(json.dumps({'id': 1, 'result': {}}), flush=True)",
                        "    elif request_id == 2:",
                        "        print(json.dumps(response), flush=True)",
                    )
                ),
                encoding="utf-8",
            )
            with patch.object(
                codex_host,
                "_codex_command",
                return_value=[sys.executable, str(server)],
            ):
                return codex_host._read_thread_title("thread-1", root, timeout=2)

    def test_empty_title_injects_context_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / "projects" / "demo"
            cwd.mkdir(parents=True)
            write_profile(root)
            state = root / "state"

            first_code, first_stdout = run_hook(
                cwd,
                state,
                codex_host.TitleProbe(True, None),
            )
            second_code, second_stdout = run_hook(
                cwd,
                state,
                codex_host.TitleProbe(True, None),
            )

            self.assertEqual((first_code, second_code), (0, 0))
            self.assertEqual(second_stdout, "")
            output = json.loads(first_stdout)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn("<session-title-task>", context)
            self.assertIn("Scope object: demo", context)
            self.assertIn("发送最终答复前", context)
            self.assertEqual(len(list(state.rglob("*.json"))), 1)

    def test_manual_title_skips_without_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / "projects" / "demo"
            cwd.mkdir(parents=True)
            write_profile(root)
            state = root / "state"

            code, stdout = run_hook(
                cwd,
                state,
                codex_host.TitleProbe(True, "用户标题"),
            )

            self.assertEqual((code, stdout), (0, ""))
            self.assertFalse(state.exists())

    def test_unknown_title_skips_without_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / "projects" / "demo"
            cwd.mkdir(parents=True)
            write_profile(root)
            state = root / "state"

            code, stdout = run_hook(cwd, state, codex_host.TitleProbe(False))

            self.assertEqual((code, stdout), (0, ""))
            self.assertFalse(state.exists())

    def test_prepare_failure_exits_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / "projects" / "demo"
            cwd.mkdir(parents=True)
            write_profile(root)
            state = root / "state"

            with (
                patch.dict(os.environ, {"SESSION_TITLE_STATE_ROOT": str(state)}),
                patch.object(codex_host, "_read_event", return_value=event(cwd)),
                patch.object(
                    codex_host,
                    "_read_thread_title",
                    return_value=codex_host.TitleProbe(True, None),
                ),
                patch.object(codex_host.session_title, "prepare", side_effect=RuntimeError),
                redirect_stdout(io.StringIO()),
            ):
                code = codex_host.main()

            self.assertEqual(code, 0)
            self.assertFalse(state.exists())

    def test_thread_read_parses_confirmed_empty_title(self):
        probe = self.probe_with_fake_server(
            {"id": 2, "result": {"thread": {"name": None}}}
        )
        self.assertEqual(probe, codex_host.TitleProbe(True, None))

    def test_thread_read_maps_unloaded_new_thread_to_empty_title(self):
        probe = self.probe_with_fake_server(
            {
                "id": 2,
                "error": {
                    "code": -32600,
                    "message": "thread not loaded: thread-1",
                },
            }
        )
        self.assertEqual(probe, codex_host.TitleProbe(True, None))

    def test_thread_read_keeps_other_errors_unknown(self):
        probe = self.probe_with_fake_server(
            {
                "id": 2,
                "error": {
                    "code": -32603,
                    "message": "database is locked",
                },
            }
        )
        self.assertEqual(probe, codex_host.TitleProbe(False))


if __name__ == "__main__":
    unittest.main()
