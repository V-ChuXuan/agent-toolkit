#!/usr/bin/env python3
"""Self-test for the readme-writer scripts. Standard library only.

Every rule the checker claims is exercised on a fixture written to a temporary
directory, so a regex change cannot silently disable a check. Run it after any
edit to `check_readme.py` or `scan_repo.py`:

    python -B -X utf8 skills/readme-writer/scripts/selftest.py

Exit code 0 means every case passed.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKER = HERE / "check_readme.py"
SCANNER = HERE / "scan_repo.py"

failures: list[str] = []
passed = 0


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load("readme_writer_check", CHECKER)
scanner = load("readme_writer_scan", SCANNER)


def expect(condition: bool, label: str) -> None:
    global passed
    if condition:
        passed += 1
    else:
        failures.append(label)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def findings_of(path: Path, pair: Path | None = None, max_lines: int = 350,
                previous: Path | None = None):
    return checker.run(path, pair, max_lines,
                       checker.load_heading_map(checker.DEFAULT_TAXONOMY), previous)


def messages(findings) -> str:
    return " | ".join(message for _, _, message in findings)


# ---------------------------------------------------------------- error rules

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    bad = write(root / "bad" / "README.md", "\n".join([
        "# Bad",
        "",
        "[gone](#no-such-heading)",
        "",
        "![image](missing.png)",
        "",
        "Copy from C:\\Users\\someone\\project or /home/someone/project",
        "",
        "TODO: finish this",
        "",
        "<div>unclosed",
        "",
        "[![license](https://img.shields.io/badge/license-MIT-blue.svg)](#license)",
        "",
        "## License",
    ]))
    text = messages(findings_of(bad))
    expect("dead anchor" in text, "error: dead anchor is reported")
    expect("does not exist" in text, "error: missing relative file is reported")
    expect("machine-local path" in text, "error: machine-local path is reported")
    expect("leftover placeholder" in text, "error: visible TODO is reported")
    expect("unclosed HTML tag" in text, "error: unclosed HTML tag is reported")
    expect("no LICENSE file" in text, "error: licence badge without LICENSE is reported")

    # The repository has no LICENSE file, so the badge rule must fire; adding
    # one must silence it. This is the rule that once failed silently.
    write(root / "bad" / "LICENSE", "MIT License\n")
    expect("no LICENSE file" not in messages(findings_of(bad)),
           "error: licence badge passes once LICENSE exists")

    # A sentence pointing at LICENSE claims the file exists.
    claims = write(root / "claims" / "README.md", "\n".join([
        "# T", "", "## License", "", "MIT — see `LICENSE`.", "",
    ]))
    expect("no licence file exists" in messages(findings_of(claims)),
           "error: a LICENSE reference without the file is reported")
    write(root / "claims" / "LICENSE", "MIT License\n\nCopyright (c) 2026 Example\n")
    expect("no licence file exists" not in messages(findings_of(claims)),
           "error: the same reference passes once LICENSE exists")

    # A fenced example must not be treated as the real thing.
    fenced = write(root / "fenced" / "README.md", "\n".join([
        "# Fenced",
        "",
        "```markdown",
        "[gone](#no-such-heading)",
        "TODO: inside an example",
        "```",
        "",
        "## License",
    ]))
    expect(findings_of(fenced) == [], "suppressed: anchors and placeholders inside fences")

    # Inline code documents a rule; it is not a leaked path.
    inline = write(root / "inline" / "README.md", "\n".join([
        "# Inline",
        "",
        "Never write `` `/Users/you/project` `` or `C:\\Users\\you` in a README.",
        "",
        "## License",
    ]))
    expect("machine-local path" not in messages(findings_of(inline)),
           "suppressed: machine-local paths inside inline code")

    # A file link named TODO.md is not a leftover marker.
    todo_link = write(root / "todo" / "README.md", "\n".join([
        "# Links",
        "",
        "- Roadmap: [TODO.md](https://example.com/TODO.md)",
        "",
        "## License",
    ]))
    expect("leftover placeholder" not in messages(findings_of(todo_link)),
           "suppressed: TODO.md link is not a placeholder")

    # An HTML comment is this skill's sanctioned marker: it is not an error,
    # but it is counted so delivery can list it.
    commented = write(root / "commented" / "README.md", "\n".join([
        "# Commented",
        "",
        "<!-- TODO: measured number missing -->",
        "",
        "## License",
    ]))
    commented_text = messages(findings_of(commented))
    expect("leftover placeholder" not in commented_text,
           "suppressed: TODO inside an HTML comment is not an error")
    expect("1 open TODO marker" in commented_text,
           "todos: a sanctioned marker is counted for delivery")

    todos = write(root / "todos" / "README.md", "\n".join([
        "# T", "", "<!-- TODO: one -->", "<!-- TODO: two -->", "", "## License",
    ]))
    expect("2 open TODO markers" in messages(findings_of(todos)),
           "todos: multiple markers are counted once")

# -------------------------------------------------------------- warning rules

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    long_readme = write(root / "README.md", "# Long\n\n" + ("line\n" * 360) + "## License\n")
    expect("exceeds --max-lines" in messages(findings_of(long_readme)),
           "warning: length budget")
    expect("exceeds --max-lines" not in messages(findings_of(long_readme, max_lines=400)),
           "warning: length budget honours --max-lines")

    inflated = write(root / "README.html", "# X\n\nIt is seamlessly blazingly fast.\n")
    expect("inflated wording" in messages(findings_of(inflated)), "warning: inflated wording")

    tells = write(root / "tells.md", "# T\n\nThis is not just fast but cheap.\n\nCertainly! It works.\n")
    told = messages(findings_of(tells))
    expect("staged contrast" in told, "warning: staged not-just-but contrast")
    expect("chat residue" in told, "warning: chat residue")

# ------------------------------------------------------------ bilingual pair

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    en = write(root / "README.md", "\n".join([
        "# Tool", "", "## Install", "", "```bash", "pip install tool", "```", "",
        "## Usage", "", "Total: 12 tests.", "", "## License", "", "MIT",
    ]))
    zh_ok = write(root / "README.zh-CN.md", "\n".join([
        "# Tool", "", "## 安装", "", "```bash", "pip install tool", "```", "",
        "## 用法", "", "共 12 个测试。", "", "## 许可", "", "MIT",
    ]))
    expect(findings_of(en, zh_ok) == [], "pair: aligned headings and numbers pass")

    zh_drift = write(root / "README.drift.md", "\n".join([
        "# Tool", "", "## 安装", "", "```bash", "pip install tool", "```", "",
        "## 许可", "", "MIT",
    ]))
    drift = messages(findings_of(en, zh_drift))
    expect("sections absent" in drift or "section count differs" in drift,
           "pair: a missing section is reported")
    expect("numbers differ" in drift, "pair: a number mismatch is reported")

    # Paragraph parity: a section that lost a body in one language.
    fat_en = write(root / "README.en2.md", "\n".join([
        "# Tool", "", "## Usage", "",
        "First paragraph.", "", "Second paragraph.", "", "Third paragraph.",
        "", "## License", "MIT",
    ]))
    thin_zh = write(root / "README.zh2.md", "\n".join([
        "# 工具", "", "## 用法", "", "只有一段。", "", "## 许可", "MIT",
    ]))
    expect("paragraphs here" in messages(findings_of(fat_en, thin_zh)),
           "pair: a section with far fewer paragraphs is reported")

    close = write(root / "README.zh3.md", "\n".join([
        "# 工具", "", "## 用法", "", "第一段。", "", "第二段。", "", "## 许可", "MIT",
    ]))
    expect("paragraphs here" not in messages(findings_of(fat_en, close)),
           "pair: a one-paragraph difference is tolerated")
    en_noise = write(root / "README.noise.md", "\n".join([
        "# Tool", "", "1. First step", "See https://example.com/a/2 and `F841`.", "", "## License",
    ]))
    zh_noise = write(root / "README.noise-zh.md", "\n".join([
        "# Tool", "", "1. 第一步", "", "## 许可",
    ]))
    expect("numbers differ" not in messages(findings_of(en_noise, zh_noise)),
           "pair: URLs, inline code and list numbers are not counted")

# --------------------------------------------------------- heading map + auto pair

mapping = checker.load_heading_map(checker.DEFAULT_TAXONOMY)
expect(len(mapping) >= 10, "map: heading table loads from classification.md")
expect(mapping.get("安装") == "install", "map: Chinese heading maps to canonical English")

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write(root / "README.md", "# A\n\n## Install\n")
    write(root / "README.zh-CN.md", "# A\n\n## 安装\n")
    expect(checker.auto_pair(root / "README.md") == root / "README.zh-CN.md",
           "auto-pair: sibling language README is found")
    write(root / "README.md.bak", "# old\n")
    expect(checker.auto_pair(root / "README.md.bak") is None,
           "auto-pair: a .bak file never pairs")

# ------------------------------------------------------------------ exit codes

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    good = write(root / "good.md", "# G\n\n## License\n")
    bad = write(root / "bad.md", "# B\n\n[dead](#nope)\n")
    warn = write(root / "warn.md", "# W\n\nseamlessly\n")

    def quiet(argv):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            return checker.main(argv)

    expect(quiet([str(good)]) == 0, "exit: clean file exits 0")
    expect(quiet([str(bad)]) == 1, "exit: error exits 1")
    expect(quiet([str(warn)]) == 0, "exit: warning alone exits 0")
    expect(quiet([str(warn), "--strict"]) == 1, "exit: --strict fails on a warning")

# ------------------------------------------------------------------ encodings

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    crlf = root / "crlf.md"
    crlf.write_bytes("# Title\r\n\r\n## Install\r\n\r\n## License\r\n".encode("utf-8"))
    expect(findings_of(crlf) == [], "encoding: CRLF file checks clean")

    bom = root / "bom.md"
    bom.write_bytes(b"\xef\xbb\xbf" + b"# Title\n\n## License\n")
    expect(checker.headings_of(checker.prose_lines(checker.read(bom))) == ["Title", "License"],
           "encoding: a BOM does not hide the first heading")

    gbk = root / "gbk.md"
    gbk.write_bytes("# 标题\n\n## 安装\n".encode("gbk"))
    try:
        checker.read(gbk)
        failed = True
    except SystemExit as error:
        failed = "not valid UTF-8" in str(error)
    expect(failed, "encoding: a non-UTF-8 file fails loudly instead of decoding to nothing")

# --------------------------------------------------------- help coverage (--help)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    help_text = root / "help.txt"
    help_text.write_text("usage: tool [options]\n\n  --alpha   first\n  --beta    second\n", encoding="utf-8")

    partial = write(root / "partial.md", "# T\n\nUse `--alpha`.\n\n## License\n\nMIT\n")
    covered = write(root / "covered.md", "# T\n\nUse `--alpha` and `--beta`.\n\n## License\n\nMIT\n")

    def with_help(path):
        return checker.run(path, None, 350, {}, None, (checker.read(help_text), help_text.name))

    expect("--beta" in messages(with_help(partial)),
           "help: a flag present in --help but absent from the README is reported")
    expect("with no mention" not in messages(with_help(covered)),
           "help: a flag mentioned in the README passes")

# ------------------------------------------------------- transcripts (--transcript)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    transcript = root / "run.txt"
    transcript.write_text(
        "protocol: MCP\nstatus: ok\nitems: 3\n\nusage: tool [-h] [--alpha]\n",
        encoding="utf-8",
    )
    real = write(root / "real.md", "\n".join([
        "# T", "", "```text", "protocol: MCP", "status: ok", "items: 3", "```",
        "", "## License", "MIT",
    ]))
    fake = write(root / "fake.md", "\n".join([
        "# T", "", "```text", "protocol: MCP", "status: ok", "items: 9", "```",
        "", "## License", "MIT",
    ]))
    code = write(root / "code.md", "\n".join([
        "# T", "", "```bash", "pip install tool", "```", "", "## License", "MIT",
    ]))

    def with_transcript(path):
        return checker.run(path, None, 350, {}, None, None,
                           [(checker.read(transcript), transcript.name)])

    expect("not found" not in messages(with_transcript(real)),
           "transcript: a block copied from the log passes")
    expect("not found" in messages(with_transcript(fake)),
           "transcript: an invented block is reported")
    expect("not found" not in messages(with_transcript(code)),
           "transcript: a bash block is code, not output")

# ------------------------------------------------------- trimmed sections (--previous)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    previous = write(root / "README.prev.md", "# Old\n\n## Install\n\n## Integrations\n\n## Examples\n")
    trimmed = write(root / "README.md", "# New\n\n## Install\n")
    kept = write(root / "README.kept.md", "\n".join([
        "# New", "", "## Install", "",
        "Integrations moved to [docs](docs/integrations.md).", "",
    ]))
    lost = messages(findings_of(trimmed, previous=previous))
    expect("Integrations" in lost, "trim: a section dropped without a link is reported")
    kept_text = messages(findings_of(kept, previous=previous))
    expect("Integrations" not in kept_text, "trim: a section named in a summary line counts")
    expect("Examples" in kept_text, "trim: a section with no trace at all is still reported")

    # Rewriting a Chinese README into English must not report every section.
    zh_old = write(root / "README.zh.bak", "# 工具\n\n## 安装\n\n## 配置\n\n## 许可\n")
    en_new = write(root / "README.en.md", "# Tool\n\n## Install\n\n## License\n")
    flipped = messages(findings_of(en_new, previous=zh_old))
    expect("another language" in flipped, "trim: a language switch is named, not guessed at")
    expect("sections in" not in flipped, "trim: no dropped-section list across languages")

    # A kept heading whose body lost most of its text and links nowhere.
    long_body = "This paragraph explains a behaviour in detail. " * 8
    fat = write(root / "README.fat.md", "# T\n\n## Usage\n\n" + long_body + "\n")
    thin = write(root / "README.thin.md", "# T\n\n## Usage\n\nShort.\n")
    linked = write(root / "README.linked.md",
                   "# T\n\n## Usage\n\nMoved: [usage](docs/usage.md).\n")
    tiny = write(root / "README.tiny.md", "# T\n\n## Usage\n\nOld small line.\n")
    tiny_new = write(root / "README.tiny2.md", "# T\n\n## Usage\n")
    expect("kept" in messages(findings_of(thin, previous=fat)),
           "trim: a section that lost most of its text is reported")
    expect("kept" not in messages(findings_of(linked, previous=fat)),
           "trim: a shrunk section that links elsewhere passes")
    expect("kept" not in messages(findings_of(tiny_new, previous=tiny)),
           "trim: a small section is not judged on size")

# --------------------------------------------------------------- word list sync

slop = (HERE.parent / "references" / "anti-ai-slop.md").read_text(encoding="utf-8")
section = slop.split("The checker's `INFLATED_RE` covers", 1)
expect(len(section) == 2, "sync: anti-ai-slop.md documents INFLATED_RE")
if len(section) == 2:
    block = section[1].split(". Change one list", 1)[0]
    import re as _re
    tokens = _re.findall(r"`([^`]+)`", block)
    probe = {"revolutioniz*": "revolutionize", "game-chang*": "game-changing",
             "effortless*": "effortless", "unleash*": "unleash"}
    unenforced = [
        token for token in tokens
        if not checker.INFLATED_RE.search(probe.get(token, token.replace("*", "")))
    ]
    expect(tokens and not unenforced,
           f"sync: every documented inflated word is enforced (missing: {unenforced})")

# -------------------------------------------------------------------- scanner

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    # A project with a manifest, console script, env signal in three shapes, a
    # skill file and a secret that must be listed but never read.
    proj = root / "project"
    write(proj / "pyproject.toml", "\n".join([
        "[project]",
        'name = "demo"',
        'version = "1.0.0"',
        'license = { file = "LICENSE.txt" }',
        '[project.scripts]',
        'demo = "demo.core:main"',
    ]))
    write(proj / "LICENSE.txt", "MIT License\n")
    write(proj / "demo" / "__init__.py", "")
    write(proj / "demo" / "core.py", 'import os\nKEY = os.environ["DEMO_KEY"]\n')
    write(proj / "run.sh", '#!/bin/sh\necho "${DEMO_HOME:-/tmp}"\n')
    write(proj / ".env.example", "DEMO_TOKEN=changeme\n")
    write(proj / ".env", "DEMO_TOKEN=super-secret-value\n")
    write(proj / ".tools" / "vendor" / "__main__.py", "print('vendored')\n")
    write(proj / "skills" / "demo" / "SKILL.md", "---\nname: demo\n---\n")

    facts = scanner.scan(str(proj))
    env_names = set(facts["env_signals"]["all"])
    expect({"DEMO_KEY", "DEMO_HOME", "DEMO_TOKEN"} <= env_names,
           "scan: env names from code, shell and .env.example")
    expect("super-secret-value" not in json.dumps(facts),
           "scan: secret file content never enters the fact sheet")
    expect(any("demo" in str(entry) for entry in facts["entrypoints"]),
           "scan: console script appears in entry points")
    expect(facts["skill_files"] == ["skills/demo/SKILL.md"], "scan: SKILL.md is reported")
    expect(facts["license"]["spdx"] == "MIT", "scan: licence inferred from file name")
    expect(not any("__main__" in path for path in facts["entrypoints"]),
           "scan: vendored .tools entry point is skipped")

    # A repository that is one script and nothing else.
    scripted = root / "script"
    write(scripted / "wait-for-me.sh", "#!/bin/sh\nexit 0\n")
    expect(scanner.scan(str(scripted))["entrypoints"] == ["wait-for-me.sh"],
           "scan: a single top-level script is the entry point")

    # Tree accounting: files dropped by the depth limit must be counted.
    deep = root / "deep"
    for index in range(3):
        write(deep / "a" / "b" / "c" / "d" / "e" / f"f{index}.txt", "x\n")
    write(deep / "shallow.txt", "x\n")
    tree = scanner.scan(str(deep))["tree"]
    expect(tree["skipped_by_depth"] == 3,
           "scan: files beyond the tree depth are counted, not silently dropped")
    expect(tree["total_files"] == 4, "scan: tree reports the full file count")

    # Monorepo: a per-package README needs the nested package facts.
    mono = root / "mono"
    write(mono / "package.json", '{"name":"root","private":true,"workspaces":["packages/*"]}')
    write(mono / "pnpm-workspace.yaml", "packages:\n  - 'packages/*'\n")
    write(mono / "packages" / "a" / "package.json",
          '{"name":"@scope/a","version":"1.0.0","bin":{"a":"index.js"}}')
    mono_facts = scanner.scan(str(mono))
    nested = [m for m in mono_facts["manifests"] if m.get("nested")]
    expect(len(nested) == 1 and nested[0]["name"] == "@scope/a",
           "scan: a monorepo reports its nested package")
    expect(nested and nested[0]["has_bin"] is True,
           "scan: a nested package records whether it declares a command")
    expect(mono_facts["monorepo_signal"]["markers"], "scan: monorepo markers are detected")

    # Empty repository must say so rather than invent facts.
    empty = root / "empty"
    empty.mkdir()
    expect(scanner.scan(str(empty))["empty"] is True, "scan: empty repository is flagged")

    # Dual licence files.
    dual = root / "dual"
    write(dual / "LICENSE-MIT", "MIT License\n")
    write(dual / "LICENSE-APACHE", "Apache License Version 2.0\n")
    expect("OR" in (scanner.scan(str(dual))["license"]["spdx"] or ""),
           "scan: dual licence files are joined")

# ------------------------------------------------------------------------- CLI

result = subprocess.run([sys.executable, str(SCANNER), "--help"],
                        capture_output=True, text=True)
expect(result.returncode == 0, "cli: scan_repo.py --help exits 0")
result = subprocess.run([sys.executable, str(CHECKER), "--help"],
                        capture_output=True, text=True)
expect(result.returncode == 0, "cli: check_readme.py --help exits 0")

# ---------------------------------------------------------------------- report

print(f"{passed} passed, {len(failures)} failed")
for failure in failures:
    print(f"  FAIL {failure}")
sys.exit(1 if failures else 0)
