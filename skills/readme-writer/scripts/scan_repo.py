#!/usr/bin/env python3
"""Read-only repository scanner for the readme-writer skill.

Prints a JSON fact sheet to stdout. Two hard rules:

- Secret files are listed by path and never opened.
- Environment variables are collected as NAMES only, never values.

Usage:
    python scan_repo.py [repo]        # repo defaults to the current directory
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "out", "target",
    "__pycache__", ".venv", "venv", ".next", ".nuxt", ".cache", "coverage",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
    # Vendored runtimes and dependency drawers that ship inside some projects
    # (for example a portable Python or Perl kept under .tools/).
    ".tools", "third_party", "3rdparty", "bower_components", ".pnpm-store", "Pods",
}
SKIP_DIR_SUFFIXES = (".egg-info", ".dist-info")
SECRET_NAME_RE = re.compile(
    r"^(\.env(\..+)?|.+\.(pem|key|p12|pfx|jks)|credentials.*|.+\.secret)$",
    re.IGNORECASE,
)
LOCK_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "uv.lock", "Cargo.lock", "composer.lock", "Gemfile.lock", "go.sum",
}
BOOTSTRAP_FILES = (
    "install.sh", "bootstrap.sh", "bootstrap.ps1", "setup.sh",
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
)
CONFIG_SUFFIXES = (".toml", ".yaml", ".yml", ".ini", ".cfg")
README_RE = re.compile(r"^readme(\.[a-z]{2}(-[a-z0-9]+)?)?\.(md|markdown|rst|txt)$", re.IGNORECASE)

ENV_CODE_PATTERNS = (
    re.compile(r"process\.env\.([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"process\.env\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]"),
    re.compile(r"os\.environ(?:\.get)?[\[(]\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"),
    re.compile(r"getenv\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"),
    re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)"),
)
SHELL_VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(:-[^}]*)?\}")
ENV_EXAMPLE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=")
SCAN_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".rb", ".go", ".rs",
                 ".sh", ".bash", ".zsh", ".ps1", ".yml", ".yaml"}
# `${NAME}` is an environment variable in a shell script and a template
# literal in TypeScript, so the shell source is restricted by file type.
SHELL_SUFFIXES = {".sh", ".bash", ".zsh", ".ps1", ".yml", ".yaml"}
SHELL_NAMES = {"Dockerfile", "Makefile"}

CJK_RE = re.compile(r"[㐀-䶿一-鿿぀-ヿ가-힯]")
MAX_TREE_LINES = 200
MAX_TREE_DEPTH = 4
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 1500
ENTRYPOINT_CANDIDATES = ("main.py", "cli.py", "__main__.py", "index.js", "index.ts",
                         "main.go", "main.rs")
MAX_ENTRYPOINT_DEPTH = 3


def is_vendored_dir(name: str) -> bool:
    """Directories that are not project source: build, vendor, hidden tool and packaging."""
    return name in SKIP_DIRS or name.startswith(".") or name.endswith(SKIP_DIR_SUFFIXES)


def iter_files(root: Path, *, max_files: int = 50_000) -> list[Path]:
    """Every regular file under root, skipping build and vendor directories."""
    found: list[Path] = []
    stack = [root]
    while stack and len(found) < max_files:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.name.endswith(SKIP_DIR_SUFFIXES):
                    stack.append(entry)
            elif entry.is_file():
                found.append(entry)
    return found


def read_text(path: Path, *, limit: int = MAX_FILE_BYTES) -> str:
    """Decoded text, or an empty string when unreadable or not text."""
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def parse_toml(path: Path) -> dict:
    if tomllib is None:
        return {}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, ValueError):
        return {}


def find_manifest(root: Path, files: list[Path], name: str) -> Path | None:
    """The shallowest file called name, so the repository root manifest wins."""
    matches = [path for path in files if path.name == name]
    if not matches:
        return None
    return min(matches, key=lambda path: (len(path.relative_to(root).parts), path.as_posix()))


def scan_manifests(root: Path, files: list[Path]) -> list[dict]:
    """Key fields from each recognised package manifest.

    The shallowest one per kind is the repository manifest. A monorepo has more,
    and a per-package README needs them, so nested manifests are reported too,
    capped and marked with `root: false`.
    """
    manifests: list[dict] = []

    npm_manifest = find_manifest(root, files, "package.json")
    if npm_manifest is not None:
        data = json.loads(read_text(npm_manifest) or "{}")
        if isinstance(data, dict):
            manifests.append({
                "kind": "npm", "path": npm_manifest.relative_to(root).as_posix(),
                "name": data.get("name"), "version": data.get("version"),
                "description": data.get("description"), "license": data.get("license"),
                "bin": data.get("bin"), "scripts": sorted((data.get("scripts") or {}).keys()),
                "engines": data.get("engines"), "workspaces": data.get("workspaces"),
            })

    for toml_name, kind in (("pyproject.toml", "python"), ("Cargo.toml", "rust")):
        toml_manifest = find_manifest(root, files, toml_name)
        if toml_manifest is None:
            continue
        data = parse_toml(toml_manifest)
        table = data.get("project") or data.get("package") or {}
        if not isinstance(table, dict):
            continue
        manifests.append({
            "kind": kind, "path": toml_manifest.relative_to(root).as_posix(),
            "name": table.get("name"), "version": table.get("version"),
            "description": table.get("description"),
            "license": table.get("license") if isinstance(table.get("license"), str) else None,
            "requires_python": table.get("requires-python"),
            "scripts": sorted((table.get("scripts") or {}).keys()),
            "bin": sorted(table.get("bin") or []) if isinstance(table.get("bin"), list) else None,
            "bins": sorted((data.get("bin") or {}).keys()) if kind == "rust" else None,
        })

    go_manifest = find_manifest(root, files, "go.mod")
    if go_manifest is not None:
        text = read_text(go_manifest)
        module = re.search(r"^module\s+(\S+)", text, re.MULTILINE)
        goversion = re.search(r"^go\s+(\S+)", text, re.MULTILINE)
        manifests.append({
            "kind": "go", "path": go_manifest.relative_to(root).as_posix(),
            "name": module.group(1) if module else None,
            "go": goversion.group(1) if goversion else None,
        })
    for manifest in manifests:
        # A nested manifest may belong to a fixture or a package, not the repo.
        manifest["root"] = Path(manifest["path"]).parent == Path(".")
    manifests.extend(scan_workspace_packages(root, files, manifests))
    return manifests


MAX_WORKSPACE_PACKAGES = 40
WORKSPACE_MANIFEST_NAMES = ("package.json", "pyproject.toml", "Cargo.toml")


def scan_workspace_packages(
    root: Path, files: list[Path], root_manifests: list[dict]
) -> list[dict]:
    """Nested package manifests, so a per-package README has facts to cite.

    Only the fields a README states are kept: name, version, description,
    licence and whether the package declares a command. Capped, because a
    monorepo with 400 packages does not fit in one fact sheet.
    """
    known = {manifest["path"] for manifest in root_manifests}
    packages: list[dict] = []
    for path in sorted(files):
        if path.name not in WORKSPACE_MANIFEST_NAMES:
            continue
        relative = path.relative_to(root)
        if len(relative.parts) < 2 or relative.as_posix() in known:
            continue
        data: dict = {}
        if path.name.endswith(".json"):
            try:
                data = json.loads(read_text(path) or "{}")
            except ValueError:
                data = {}
        else:
            data = parse_toml(path)
            data = data.get("project") or data.get("package") or {}
        if not isinstance(data, dict) or not data.get("name"):
            continue
        packages.append({
            "kind": "npm" if path.name.endswith(".json") else path.stem.split(".")[0],
            "path": relative.as_posix(),
            "directory": relative.parent.as_posix(),
            "name": data.get("name"),
            "version": data.get("version"),
            "description": data.get("description"),
            "license": data.get("license") if isinstance(data.get("license"), str) else None,
            "has_bin": bool(data.get("bin")),
            "root": False,
            "nested": True,
        })
    return packages[:MAX_WORKSPACE_PACKAGES]


def scan_skill_files(root: Path, files: list[Path]) -> list[str]:
    """`SKILL.md` paths: the signal that separates a skill bundle from a library."""
    found = [
        path.relative_to(root).as_posix()
        for path in files
        if path.name == "SKILL.md"
    ]
    return sorted(found)[:50]


def scan_entrypoints(root: Path, manifests: list[dict]) -> list[str]:
    """Executable entry points: manifest bins, Python console scripts, and shallow well-known files.

    npm ``scripts`` are development commands rather than entry points, so they are
    reported as manifest facts and never promoted here.
    """
    found: list[str] = []
    for manifest in manifests:
        for key in ("bin", "bins"):
            value = manifest.get(key)
            if isinstance(value, dict):
                found.extend(value.keys())
            elif isinstance(value, list):
                found.extend(value)
        # [project.scripts] names are console entry points; npm "scripts" are
        # commands run during development, so only the Python manifest is read.
        if manifest.get("kind") == "python":
            found.extend(manifest.get("scripts") or [])
    for candidate in ENTRYPOINT_CANDIDATES:
        for path in root.rglob(candidate):
            parts = path.relative_to(root).parts
            if len(parts) > MAX_ENTRYPOINT_DEPTH:
                continue
            if any(is_vendored_dir(part) for part in parts[:-1]):
                continue
            found.append(path.relative_to(root).as_posix())
    if not found and not manifests:
        # A repository whose whole content is one script: that script is the entry.
        scripts = [
            path
            for path in root.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".sh", ".bash", ".py", ".rb", ".js"}
            and path.name not in BOOTSTRAP_FILES
            and not path.name.startswith(".")
        ]
        if len(scripts) == 1:
            found.append(scripts[0].name)
    return sorted(set(found))


def scan_bootstrap(root: Path) -> list[dict]:
    """Presence and a short preview of install and container files."""
    previews: list[dict] = []
    for name in BOOTSTRAP_FILES:
        path = root / name
        if path.is_file():
            previews.append({
                "path": name,
                "lines": len(read_text(path).splitlines()),
                "preview": read_text(path).splitlines()[:20],
            })
    return previews


def scan_license(root: Path) -> dict:
    """SPDX guess from licence file names, then from the licence text itself.

    Repositories that ship one file per licence (``LICENSE-MIT`` plus
    ``LICENSE-APACHE``) report both, joined with ``OR``.
    """
    found: list[tuple[str, str | None]] = []
    for path in sorted(root.glob("LICENSE*")) + sorted(root.glob("COPYING*")):
        text = read_text(path, limit=20_000)
        if not text:
            continue
        found.append((path.name, infer_license(path.name, text)))
    if not found:
        return {"file": None, "spdx": None, "first_line": None}
    ids = sorted({spdx for _, spdx in found if spdx})
    first_text = read_text(root / found[0][0], limit=20_000)
    first_lines = first_text.splitlines()
    return {
        "file": ", ".join(name for name, _ in found),
        "spdx": " OR ".join(ids) if ids else None,
        "first_line": first_lines[0] if first_lines else None,
    }


LICENSE_FILE_TOKENS = (
    ("agpl", "AGPL-3.0"), ("lgpl", "LGPL-3.0"), ("apache", "Apache-2.0"),
    ("bsd-3", "BSD-3-Clause"), ("bsd-2", "BSD-2-Clause"), ("mpl", "MPL-2.0"),
    ("unlicense", "Unlicense"), ("isc", "ISC"), ("mit", "MIT"), ("gpl", "GPL-3.0"),
)
LICENSE_TEXT_HINTS = (
    ("Apache-2.0", ("apache license", "version 2.0")),
    ("AGPL-3.0", ("gnu affero general public license",)),
    ("LGPL-3.0", ("gnu lesser general public license",)),
    ("GPL-3.0", ("gnu general public license", "version 3")),
    ("MPL-2.0", ("mozilla public license",)),
    ("Unlicense", ("this is free and unencumbered software",)),
    ("MIT", ("permission is hereby granted, free of charge",)),
    ("MIT", ("mit license",)),
    ("BSD-3-Clause", ("redistribution and use in source and binary forms",)),
    ("ISC", ("isc license",)),
)


def infer_license(name: str, text: str) -> str | None:
    lowered = name.lower()
    for token, spdx in LICENSE_FILE_TOKENS:
        if token in lowered:
            return spdx
    head = " ".join(text.split())[:1200].lower()
    for spdx, hints in LICENSE_TEXT_HINTS:
        if all(hint in head for hint in hints):
            return spdx
    return None


def scan_env_signals(root: Path, files: list[Path]) -> dict:
    """Environment variable NAMES from code, shell scripts and .env.example."""
    code: set[str] = set()
    shell: set[str] = set()
    example: set[str] = set()

    for path in files:
        name = path.name
        suffix = path.suffix.lower()
        if name.startswith(".env"):
            if name.endswith((".example", ".sample", ".template")):
                for line in read_text(path, limit=100_000).splitlines():
                    match = ENV_EXAMPLE_RE.match(line)
                    if match:
                        example.add(match.group(1))
            continue
        if suffix not in SCAN_SUFFIXES:
            continue
        text = read_text(path, limit=200_000)
        if not text:
            continue
        for pattern in ENV_CODE_PATTERNS:
            code.update(pattern.findall(text))
        if suffix in SHELL_SUFFIXES or name in SHELL_NAMES:
            shell.update(var for var, _ in SHELL_VAR_RE.findall(text))
        if name in ("docker-compose.yml", "docker-compose.yaml"):
            shell.update(re.findall(r"^\s{4,}([A-Z][A-Z0-9_]{2,}):", text, re.MULTILINE))

    return {
        "code": sorted(code - shell),
        "shell": sorted(shell - code),
        "env_example": sorted(example),
        "all": sorted(code | shell | example),
    }


def scan_configs(root: Path, files: list[Path]) -> list[str]:
    """Configuration files worth citing, excluding lock files."""
    return sorted(
        path.relative_to(root).as_posix()
        for path in files
        if path.suffix.lower() in CONFIG_SUFFIXES and path.name not in LOCK_FILES
    )


def build_tree(root: Path, files: list[Path]) -> dict:
    """Depth- and line-limited directory listing.

    Both limits lose files, so both are reported: a tree that quietly shows 200
    of 217 files while claiming nothing was cut is worse than a short tree.
    """
    lines: list[str] = []
    too_deep = 0
    for path in sorted(files):
        relative = path.relative_to(root)
        if len(relative.parts) > MAX_TREE_DEPTH:
            too_deep += 1
            continue
        lines.append(relative.as_posix())
    return {
        "lines": lines[:MAX_TREE_LINES],
        "truncated": max(0, len(lines) - MAX_TREE_LINES),
        "skipped_by_depth": too_deep,
        "total_files": len(files),
        "max_depth": MAX_TREE_DEPTH,
    }


def scan_existing_readme(root: Path, files: list[Path]) -> dict | None:
    """Path, size and heading list of an existing README."""
    for path in files:
        if path.parent != root or not README_RE.match(path.name):
            continue
        text = read_text(path)
        if not text:
            continue
        headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE)
        return {
            "path": path.relative_to(root).as_posix(),
            "lines": len(text.splitlines()),
            "first_lines": text.splitlines()[:5],
            "section_headers": headings,
        }
    return None


def scan_language_signal(root: Path, existing: dict | None) -> dict:
    """CJK ratio over the repository's own prose.

    Only the existing README and recent commit subjects count: sweeping in
    unrelated markdown lets one large English document drown the signal.
    """
    samples: list[str] = []
    sources: list[str] = []
    if existing:
        samples.append(read_text(root / existing["path"], limit=200_000))
        sources.append(existing["path"])
    subjects = git_output(root, "log", "-20", "--pretty=%s")
    if subjects:
        samples.append(subjects)
        sources.append("git log -20")
    stripped = re.sub(r"\s", "", "\n".join(samples))
    return {
        "cjk_ratio": round(len(CJK_RE.findall(stripped)) / len(stripped), 4) if stripped else 0.0,
        "sampled_chars": len(stripped),
        "sources": sources,
    }


def scan_monorepo(root: Path, manifests: list[dict]) -> dict:
    """Signals that the repository holds several packages."""
    markers = [name for name in ("pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json")
               if (root / name).is_file()]
    directories = [name for name in ("packages", "apps", "services") if (root / name).is_dir()]
    workspaces = next((m.get("workspaces") for m in manifests if m.get("workspaces")), None)
    return {"markers": markers, "directories": directories, "workspaces": workspaces}


def scan_secret_files(root: Path, files: list[Path]) -> list[str]:
    """Paths of secret-bearing files. These are never opened."""
    return sorted(
        path.relative_to(root).as_posix()
        for path in files
        if SECRET_NAME_RE.match(path.name) and path.name != ".env.example"
    )


def git_output(root: Path, *args: str) -> str:
    """stdout of a git command, or an empty string when unavailable."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def scan_git(root: Path) -> dict:
    """Remote, branch and head. `is_repo` separates 'no remote' from 'no git'."""
    inside = git_output(root, "rev-parse", "--is-inside-work-tree")
    return {
        "is_repo": inside == "true",
        "remote": git_output(root, "remote", "get-url", "origin"),
        "branch": git_output(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": git_output(root, "rev-parse", "--short", "HEAD"),
    }


def scan(repo: str) -> dict:
    root = Path(repo).resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")

    files = iter_files(root)
    manifests = scan_manifests(root, files)
    existing = scan_existing_readme(root, files)

    return {
        "root": root.as_posix(),
        "empty": not files,
        "size_warning": {
            "file_count": len(files),
            "batched": len(files) > MAX_FILES,
            "note": "work one top-level folder at a time" if len(files) > MAX_FILES else None,
        },
        "git": scan_git(root),
        "manifests": manifests,
        "skill_files": scan_skill_files(root, files),
        "entrypoints": scan_entrypoints(root, manifests),
        "bootstrap": scan_bootstrap(root),
        "license": scan_license(root),
        "env_signals": scan_env_signals(root, files),
        "config_files": scan_configs(root, files)[:60],
        "tree": build_tree(root, files),
        "existing_readme": existing,
        "language_signal": scan_language_signal(root, existing),
        "monorepo_signal": scan_monorepo(root, manifests),
        "secret_files": scan_secret_files(root, files),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a repository into a JSON fact sheet.")
    parser.add_argument("repo", nargs="?", default=".", help="repository path (default: .)")
    args = parser.parse_args(argv)
    json.dump(scan(args.repo), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
