#!/usr/bin/env python3
"""Read-only README checker for the readme-writer skill.

Errors exit 1. Warnings exit 0 unless --strict.

Checks that parse links, HTML and headings run on prose only, so an example
inside a fenced code block is not mistaken for the real thing. Two checks run
on the whole document instead, because a fenced block is exactly where a
copy-pasted local path or a leftover marker hides:

- machine-local absolute paths
- placeholder markers, after HTML comments are removed

That last exception matters: `<!-- TODO: ... -->` is this skill's sanctioned
"fact I could not verify" marker, so it must not fail the checker. Bare `TODO`
in visible text, `{{name}}` and `[Project Name]` still do.

Usage:
    python check_readme.py README.md [--pair README.zh-CN.md]
                         [--max-lines 350] [--strict]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMG_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)(?:\s[^<>]*?)?(/?)>")

VOID_TAGS = {"img", "br", "hr", "input", "meta", "link", "source", "area", "base", "col"}
CHECKED_TAGS = {
    "a", "b", "blockquote", "code", "dd", "details", "div", "dl", "dt", "em", "h1", "h2",
    "h3", "h4", "h5", "h6", "i", "kbd", "li", "ol", "p", "pre", "s", "span", "strong",
    "sub", "summary", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}

LOCAL_PATH_RES = (
    re.compile(r"(?:^|[\s(\"'`])/(?:Users|home|root|Volumes|mnt)/"),
    re.compile(r"\b[A-Za-z]:\\"),
    re.compile(r"\bfile://"),
)
PLACEHOLDER_RES = (
    re.compile(r"\b(?:TODO|TBD|FIXME|XXX)\b"),
    re.compile(r"\{\{[^}\n]{1,60}\}\}"),
    re.compile(r"\[(?:Project|Your|Repo|Company)\s+Name\]", re.IGNORECASE),
)
INFLATED_RE = re.compile(
    r"blazingly\s+fast|world-class|seamless(?:ly)?|revolutioniz\w*|cutting-edge|"
    r"state-of-the-art|game-chang\w*|effortless\w*|empowering|unleash\w*|"
    r"a testament to|say goodbye to|let'?s dive in|in today'?s fast-paced|"
    r"赋能|矩阵|全链路|极致体验|无缝|颠覆",
    re.IGNORECASE,
)
LICENSE_BADGE_RE = re.compile(
    r"(?:img\.shields\.io|badgen\.net|badge\.fury\.io)[^\s)\"']*licen[cs]e|"
    r"!\[[^\]]*licen[cs]e[^\]]*\]",
    re.IGNORECASE,
)
LICENSE_REF_RE = re.compile(r"(?i)(?:see|under|见|遵循)\s+`?(?:the\s+)?LICEN[CS]E\b")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)*")
URL_RE = re.compile(r"https?://\S+")
TELL_RES = (
    (re.compile(r"\bnot just\b[^\n.]{0,80}?\bbut\b", re.IGNORECASE), "staged contrast `not just ... but ...`"),
    (re.compile(r"^\s*(?:Certainly[!,]|Great question\b|Sure thing\b)", re.IGNORECASE), "chat residue"),
)
LANGUAGE_README_RE = re.compile(r"^readme\.[a-z]{2}(?:-[a-z0-9]+)?\.md$", re.IGNORECASE)
FLAG_RE = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")

DEFAULT_TAXONOMY = Path(__file__).resolve().parent.parent / "references" / "classification.md"


def read(path: Path) -> str:
    """Decoded text, refusing to guess at a broken encoding.

    `errors="ignore"` would drop the undecodable bytes and then report a clean
    file, which is worse than failing: a GBK README would pass the checker with
    its headings gone. A BOM is stripped because editors add it silently.
    """
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise SystemExit(f"cannot read {path}: {error}") from error
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise SystemExit(
            f"{path} is not valid UTF-8 ({error.reason} at byte {error.start}); "
            "re-save it as UTF-8 before checking"
        ) from error
    return text


def prose_lines(text: str) -> list[str]:
    """Lines with fenced blocks and inline code removed, numbering preserved."""
    out: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if fence is None:
            if match:
                marker = match.group(1)
                fence = (marker[0], len(marker))
                out.append("")
                continue
            out.append(INLINE_CODE_RE.sub("", line))
        else:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1]:
                fence = None
            out.append("")
    return out


def fenced_lines(text: str) -> list[str]:
    """Non-empty content lines from inside fenced blocks."""
    out: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if fence is None:
            if match:
                marker = match.group(1)
                fence = (marker[0], len(marker))
        else:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1]:
                fence = None
            elif line.strip():
                out.append(line.strip())
    return out


def slugify(heading: str) -> str:
    """GitHub's heading-to-anchor rule."""
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return text.replace(" ", "-")


def headings_of(lines: list[str]) -> list[str]:
    return [m.group(2) for line in lines if (m := HEADING_RE.match(line))]


def load_heading_map(path: Path | None) -> dict[str, str]:
    """Read the English/Chinese heading table from classification.md.

    The table sits between `<!-- heading-map:start -->` and
    `<!-- heading-map:end -->` so unrelated two-column tables are ignored. An
    unreadable or missing taxonomy degrades to the language-independent checks
    only, so the checker still works when copied alone.
    """
    if path is None or not path.is_file():
        return {}
    mapping: dict[str, str] = {}
    inside = False
    for line in read(path).splitlines():
        stripped = line.strip()
        if stripped == "<!-- heading-map:start -->":
            inside = True
            continue
        if stripped == "<!-- heading-map:end -->":
            break
        if not inside or not stripped.startswith("|"):
            continue
        cells = [cell.strip().strip("`* ") for cell in stripped.strip("|").split("|")]
        if len(cells) != 2:
            continue
        english, chinese = cells
        if not english or not chinese:
            continue
        if set(english) <= {"-", ":", " "} or set(chinese) <= {"-", ":", " "}:
            continue
        if chinese.lower() in {"中文", "chinese"}:
            continue
        mapping[chinese.lower()] = english.lower()
    return mapping


def canonical_headings(lines: list[str], mapping: dict[str, str]) -> list[str]:
    """H2 headings only, lowered and translated to the canonical English name.

    H3 and deeper carry details whose wording legitimately differs between the
    two languages, so only section-level headings are compared for alignment.
    """
    out: list[str] = []
    for line in lines:
        match = HEADING_RE.match(line)
        if not match or len(match.group(1)) != 2:
            continue
        key = re.sub(r"[`*]", "", match.group(2)).strip().lower()
        out.append(mapping.get(key, key))
    return out


def check_local_paths(raw_lines: list[str], findings: list[tuple[str, int, str]]) -> None:
    """Machine-local paths, including inside fenced blocks.

    Inline code is excluded: a path written as `` `C:\\Users\\...` `` is usually
    documentation about the rule, not a copied path.
    """
    for number, line in enumerate(raw_lines, 1):
        scannable = INLINE_CODE_RE.sub("", line)
        for pattern in LOCAL_PATH_RES:
            if match := pattern.search(scannable):
                findings.append(("error", number, f"machine-local path `{match.group(0).strip()}`"))


def strip_html_comments(lines: list[str]) -> list[str]:
    """Blank HTML comments while preserving the line count."""
    text = "\n".join(lines)
    blanked = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)
    return blanked.split("\n")


def check_placeholders(prose: list[str], findings: list[tuple[str, int, str]]) -> None:
    for number, line in enumerate(strip_html_comments(prose), 1):
        line = URL_RE.sub("", line)
        for pattern in PLACEHOLDER_RES:
            for match in pattern.finditer(line):
                # `[TODO.md](...)` is a file link, not a leftover marker.
                if re.match(r"\.(md|markdown|txt|rst|py|js|ts)\b", line[match.end():]):
                    continue
                findings.append(("error", number, f"leftover placeholder `{match.group(0)}`"))


def check_html(prose: list[str], findings: list[tuple[str, int, str]]) -> None:
    stack: list[tuple[str, int]] = []
    for number, line in enumerate(prose, 1):
        for closing, name, self_closing in TAG_RE.findall(line):
            tag = name.lower()
            if tag in VOID_TAGS or self_closing:
                continue
            if tag not in CHECKED_TAGS:
                continue
            if not closing:
                stack.append((tag, number))
            elif stack and stack[-1][0] == tag:
                stack.pop()
            else:
                findings.append(("error", number, f"unmatched closing tag `</{tag}>`"))
    for tag, number in stack:
        findings.append(("error", number, f"unclosed HTML tag `<{tag}>`"))


def check_links(
    prose: list[str],
    path: Path,
    findings: list[tuple[str, int, str]],
    anchor_cache: dict[Path, set[str]],
) -> None:
    """Dead anchors and links to files that do not exist."""
    own_anchors = {slugify(h) for h in headings_of(prose)}
    for number, line in enumerate(prose, 1):
        targets = LINK_RE.findall(line) + IMG_RE.findall(line)
        for target in targets:
            if target.startswith(("#", "mailto:", "tel:", "data:")) or "://" in target:
                if target.startswith("#"):
                    _check_anchor(target[1:], own_anchors, number, findings)
                continue
            file_part, _, fragment = target.partition("#")
            if not file_part:
                continue
            if file_part.startswith("/"):
                continue  # reported by check_local_paths
            resolved = (path.parent / file_part).resolve()
            if not resolved.exists():
                findings.append(("error", number, f"link target does not exist: `{file_part}`"))
                continue
            if fragment and resolved.suffix.lower() in {".md", ".markdown"}:
                if resolved not in anchor_cache:
                    anchor_cache[resolved] = {
                        slugify(h) for h in headings_of(prose_lines(read(resolved)))
                    }
                _check_anchor(fragment, anchor_cache[resolved], number, findings, file_part)


def _check_anchor(
    anchor: str,
    known: set[str],
    number: int,
    findings: list[tuple[str, int, str]],
    where: str = "",
) -> None:
    if anchor not in known:
        suffix = f" in `{where}`" if where else ""
        findings.append(("error", number, f"dead anchor `#{anchor}`{suffix}"))


def check_license_badge(
    raw_lines: list[str], path: Path, findings: list[tuple[str, int, str]]
) -> None:
    for number, line in enumerate(raw_lines, 1):
        if not LICENSE_BADGE_RE.search(line):
            continue
        root = path.parent
        # A glob generator is always truthy, so each match must be materialised
        # before any() can answer whether a licence file exists.
        has_license_file = any(
            any(root.glob(name)) for name in ("LICENSE*", "COPYING*", "LICENCE*")
        )
        if not has_license_file:
            findings.append(("error", number, "license badge but no LICENSE file in the repository"))
        break


def check_license_reference(
    prose: list[str], path: Path, findings: list[tuple[str, int, str]]
) -> None:
    """A sentence pointing at LICENSE is a claim that the file exists."""
    root = path.parent
    for number, line in enumerate(prose, 1):
        if not LICENSE_REF_RE.search(line):
            continue
        exists = any(
            any(root.glob(name)) for name in ("LICENSE*", "COPYING*", "LICENCE*")
        )
        if not exists:
            findings.append(("error", number,
                             "the README points at LICENSE but no licence file exists"))
        return


def unfenced_lines(text: str) -> list[str]:
    """Lines with fenced blocks blanked, inline code kept.

    A licence reference usually sits in a code span (`LICENSE`), which
    `prose_lines` strips, so this variant exists for checks that need it.
    """
    out: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if fence is None:
            if match:
                marker = match.group(1)
                fence = (marker[0], len(marker))
                out.append("")
                continue
            out.append(line)
        else:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1]:
                fence = None
            out.append("")
    return out


def check_tells(prose: list[str], findings: list[tuple[str, int, str]]) -> None:
    """Mechanical AI tells that a regex can decide without judgement."""
    for number, line in enumerate(prose, 1):
        for pattern, label in TELL_RES:
            if pattern.search(line):
                findings.append(("warning", number, label))


def check_length(prose: list[str], max_lines: int, findings: list[tuple[str, int, str]]) -> None:
    total = len(prose)
    if total > max_lines:
        findings.append(("warning", total, f"{total} lines exceeds --max-lines {max_lines}"))


def check_inflated(prose: list[str], findings: list[tuple[str, int, str]]) -> None:
    for number, line in enumerate(prose, 1):
        if match := INFLATED_RE.search(line):
            findings.append(("warning", number, f"inflated wording `{match.group(0)}`"))


def check_pair(
    prose: list[str],
    pair_prose: list[str],
    pair_name: str,
    findings: list[tuple[str, int, str]],
    heading_map: dict[str, str] | None = None,
) -> None:
    """Bilingual drift, using only language-independent signals."""
    left_levels = [len(m.group(1)) for line in prose if (m := HEADING_RE.match(line))]
    right_levels = [len(m.group(1)) for line in pair_prose if (m := HEADING_RE.match(line))]
    if len(left_levels) != len(right_levels):
        findings.append(("warning", 1,
                         f"section count differs: this file {len(left_levels)}, "
                         f"{pair_name} {len(right_levels)}"))
    elif left_levels != right_levels:
        findings.append(("warning", 1, f"section heading levels differ from {pair_name}"))

    if heading_map:
        canonical = set(heading_map.values())
        left_all = canonical_headings(prose, heading_map)
        right_all = canonical_headings(pair_prose, heading_map)
        left_titles = [title for title in left_all if title in canonical]
        right_titles = [title for title in right_all if title in canonical]
        missing = [title for title in right_titles if title not in left_titles]
        extra = [title for title in left_titles if title not in right_titles]
        unmapped = sorted({title for title in left_all + right_all if title not in canonical})
        if unmapped:
            # An unlisted heading may be a translation of a mapped one, so an
            # absence claim would be a guess. Report the map gap once instead.
            findings.append(("warning", 1,
                             f"sections outside the heading map: {', '.join(unmapped[:4])}"))
        else:
            if missing:
                findings.append(("warning", 1,
                                 f"sections absent from this file: {', '.join(missing[:4])}"))
            if extra:
                findings.append(("warning", 1,
                                 f"sections absent from {pair_name}: {', '.join(extra[:4])}"))
            if not missing and not extra and left_titles != right_titles:
                findings.append(("warning", 1, f"section order differs from {pair_name}"))

    numbers = numbers_in(prose)
    pair_numbers = numbers_in(pair_prose)
    if numbers != pair_numbers:
        only_left = sorted(set(numbers) - set(pair_numbers))
        only_right = sorted(set(pair_numbers) - set(numbers))
        findings.append(("warning", 1,
                         f"numbers differ from {pair_name}: only here {only_left or 'none'}, "
                         f"only there {only_right or 'none'}"))

    if heading_map:
        check_pair_blocks(prose, pair_prose, pair_name, heading_map, findings)


def section_blocks(prose: list[str], heading_map: dict[str, str]) -> dict[str, int]:
    """Paragraph count per H2 section, keyed by the canonical heading.

    A paragraph is a run of non-empty lines; headings are not counted, fenced
    code is already blanked by `prose_lines`, and list items count as one run
    per list because they are not separated by a blank line.
    """
    counts: dict[str, int] = {}
    current: str | None = None
    in_block = False
    for line in prose:
        heading = HEADING_RE.match(line)
        if heading:
            current = (heading_map.get(heading.group(2).strip().lower(),
                                       heading.group(2).strip().lower())
                       if len(heading.group(1)) == 2 else None)
            in_block = False
            continue
        if current is None:
            continue
        if line.strip():
            if not in_block:
                counts[current] = counts.get(current, 0) + 1
                in_block = True
        else:
            in_block = False
    return counts


MIN_BLOCK_SWING = 2
BLOCK_RATIO = 0.5


def check_pair_blocks(
    prose: list[str],
    pair_prose: list[str],
    pair_name: str,
    heading_map: dict[str, str],
    findings: list[tuple[str, int, str]],
) -> None:
    """A section with far fewer paragraphs than its counterpart lost content.

    Translation may merge a sentence or two, so a difference of one paragraph
    is ignored; a gap of two or more together with a ratio outside 0.5–2.0 is
    reported. Fenced code is excluded, because code parity has its own check.
    """
    left = section_blocks(prose, heading_map)
    right = section_blocks(pair_prose, heading_map)
    for heading, left_count in left.items():
        right_count = right.get(heading)
        if right_count is None or left_count == right_count:
            continue
        if abs(left_count - right_count) < MIN_BLOCK_SWING:
            continue
        smaller, larger = sorted((left_count, right_count))
        if larger and smaller / larger >= BLOCK_RATIO:
            continue
        findings.append(("warning", 1,
                         f"section `{heading}` has {left_count} paragraphs here "
                         f"and {right_count} in {pair_name}"))


def numbers_in(prose: list[str]) -> list[str]:
    """Numbers that carry a fact, ignoring URLs, inline code and list markers."""
    text = "\n".join(prose)
    text = URL_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s", "", text)
    return sorted(NUMBER_RE.findall(text))


def check_pair_commands(raw: str, pair_raw: str, pair_name: str,
                        findings: list[tuple[str, int, str]]) -> None:
    """Commands, variable names and paths must be byte-identical across languages."""
    left = set(fenced_lines(raw))
    right = set(fenced_lines(pair_raw))
    missing = sorted(left - right)
    if missing:
        preview = ", ".join(f"`{line}`" for line in missing[:3])
        findings.append(("warning", 1, f"code lines absent from {pair_name}: {preview}"))


def fenced_blocks(text: str) -> list[tuple[str, str, int]]:
    """(language, content, start line) for each fenced block."""
    blocks: list[tuple[str, str, int]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = FENCE_RE.match(lines[index])
        if not match:
            index += 1
            continue
        marker = match.group(1)
        language = lines[index].strip()[len(marker):].strip().lower()
        start = index + 2
        body: list[str] = []
        index += 1
        while index < len(lines):
            closing = FENCE_RE.match(lines[index])
            if closing and closing.group(1)[0] == marker[0] and len(closing.group(1)) >= len(marker):
                break
            body.append(lines[index])
            index += 1
        blocks.append((language, "\n".join(body), start))
        index += 1
    return blocks


OUTPUT_LANGUAGES = {"text", "console", "output"}


def normalize_output(text: str) -> str:
    return " ".join(text.split())


def check_transcript(
    raw: str,
    transcripts: list[tuple[str, str]],
    findings: list[tuple[str, int, str]],
) -> None:
    """Every quoted output block must appear in at least one supplied run log.

    Only blocks tagged `text`, `console` or `output` are checked: a bash or
    python block is code, not a transcript. Whitespace is normalised, because
    copy-paste reflows it; words are not.
    """
    if not transcripts:
        return
    haystacks = [(name, normalize_output(text)) for text, name in transcripts]
    names = ", ".join(name for name, _ in haystacks)
    for language, content, line in fenced_blocks(raw):
        if language not in OUTPUT_LANGUAGES:
            continue
        needle = normalize_output(content)
        if len(needle) < 8:
            continue
        if not any(needle in haystack for _, haystack in haystacks):
            preview = needle[:60] + ("…" if len(needle) > 60 else "")
            findings.append(("warning", line,
                             f"output block not found in {names}: {preview}"))


TODO_RE = re.compile(r"<!--\s*TODO\b", re.IGNORECASE)


def check_open_todos(raw: str, findings: list[tuple[str, int, str]]) -> None:
    """Count the sanctioned `<!-- TODO -->` markers so delivery can list them."""
    markers = [(number, _) for number, line in enumerate(raw.splitlines(), 1)
               for _ in TODO_RE.findall(line)]
    if markers:
        first = markers[0][0]
        word = "marker" if len(markers) == 1 else "markers"
        findings.append(("warning", first, f"{len(markers)} open TODO {word}"))


def run(
    path: Path,
    pair: Path | None,
    max_lines: int,
    heading_map: dict[str, str] | None = None,
    previous: Path | None = None,
    help_text: tuple[str, str] | None = None,
    transcript: list[tuple[str, str]] | None = None,
) -> list[tuple[str, int, str]]:
    raw = read(path)
    prose = prose_lines(raw)
    raw_lines = raw.splitlines()
    findings: list[tuple[str, int, str]] = []

    check_local_paths(raw_lines, findings)
    check_placeholders(prose, findings)
    check_html(prose, findings)
    check_links(prose, path, findings, {})
    check_license_badge(raw_lines, path, findings)
    check_license_reference(unfenced_lines(raw), path, findings)
    check_length(prose, max_lines, findings)
    check_inflated(prose, findings)
    check_tells(prose, findings)
    check_open_todos(raw, findings)

    if pair is not None:
        pair_raw = read(pair)
        check_pair(prose, prose_lines(pair_raw), pair.name, findings, heading_map)
        check_pair_commands(raw, pair_raw, pair.name, findings)
    if previous is not None:
        check_trim(prose, prose_lines(read(previous)), previous.name, findings)
    if help_text is not None:
        text, name = help_text
        check_help_coverage(raw_lines, text, name, findings)
    if transcript is not None:
        check_transcript(raw, transcript, findings)
    return findings


def check_trim(
    prose: list[str],
    previous_prose: list[str],
    previous_name: str,
    findings: list[tuple[str, int, str]],
) -> None:
    """A rewrite must not silently drop a section the old file had.

    Moving a section to `docs/` is allowed, but the README has to keep a
    summary line and a link, so the old heading's words must still appear
    somewhere in the new text. The H1 is skipped: a title may legitimately be
    rewritten.

    A language switch makes heading text incomparable: a Chinese README turned
    into an English one would report every section as dropped. In that case the
    check says so once instead of guessing.
    """
    body = "\n".join(prose).lower()
    old_body = "\n".join(previous_prose)
    if language_flipped(body, old_body):
        findings.append(("warning", 1,
                         f"{previous_name} looks like another language; sections not compared"))
        return
    dropped = [
        heading
        for level, heading in headings_with_levels(previous_prose)
        if level > 1 and not heading_traced(heading, body)
    ]
    if dropped:
        preview = ", ".join(dropped[:4])
        more = "" if len(dropped) <= 4 else f" (+{len(dropped) - 4} more)"
        findings.append(("warning", 1,
                         f"sections in {previous_name} with no trace here: {preview}{more}"))
    check_shrunken_sections(prose, previous_prose, findings)


MIN_SECTION_CHARS = 200
SHRINK_RATIO = 0.5


def sections_by_heading(lines: list[str]) -> dict[str, str]:
    """Body text per H2, keyed by the lower-cased heading."""
    sections: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            if current is not None:
                sections[current] = "\n".join(body)
            current = match.group(2).strip().lower() if len(match.group(1)) == 2 else None
            body = []
        elif current is not None:
            body.append(line)
    if current is not None:
        sections[current] = "\n".join(body)
    return sections


def check_shrunken_sections(
    prose: list[str],
    previous_prose: list[str],
    findings: list[tuple[str, int, str]],
) -> None:
    """A kept section that lost most of its text must link where it went.

    The heading check above sees "the section is still there". This one sees
    "the section is there but 80% of its content vanished", which is how a
    qualifier or a whole paragraph disappears while a heading survives.
    A link in the section body counts as relocation to `docs/`; no link means
    the content was simply dropped.
    """
    previous = sections_by_heading(previous_prose)
    for heading, body in sections_by_heading(prose).items():
        old_body = previous.get(heading)
        if not old_body:
            continue
        old_chars = len(re.sub(r"\s+", "", old_body))
        new_chars = len(re.sub(r"\s+", "", body))
        if old_chars < MIN_SECTION_CHARS or new_chars >= old_chars * SHRINK_RATIO:
            continue
        if "](" in body:
            continue
        findings.append(("warning", 1,
                         f"section `{heading}` kept {new_chars} of {old_chars} characters "
                         "and links nowhere"))


CJK_RE = re.compile(r"[\u3400-\u9fff]")


def language_flipped(new_text: str, old_text: str) -> bool:
    """True when one text is mostly CJK and the other mostly is not."""
    if not new_text or not old_text:
        return False

    def ratio(text: str) -> float:
        letters = sum(1 for ch in text if ch.isalpha())
        return len(CJK_RE.findall(text)) / letters if letters else 0.0

    new_ratio, old_ratio = ratio(new_text), ratio(old_text)
    return (new_ratio < 0.02 and old_ratio > 0.10) or (old_ratio < 0.02 and new_ratio > 0.10)


def headings_with_levels(lines: list[str]) -> list[tuple[int, str]]:
    return [(len(m.group(1)), m.group(2)) for line in lines if (m := HEADING_RE.match(line))]


def heading_traced(heading: str, body: str) -> bool:
    """True when the heading, or a recognisable part of it, appears in the body.

    An old heading is traced through any of:
    - the whole heading,
    - the longest shared run of two or three words (`Vulture - Find dead code`
      via `find dead code`),
    - a single long word in either direction (`Installation` via `install`).

    The point is to catch a section that vanished, not to police renaming.
    """
    cleaned = re.sub(r"[`*_]", "", heading).lower().strip()
    if not cleaned or cleaned in body:
        return True
    words = [word for word in re.split(r"[^a-z0-9\u4e00-\u9fff]+", cleaned) if word]
    if not words:
        return True
    if len(words) >= 2:
        for size in (3, 2):
            for start in range(len(words) - size + 1):
                run = " ".join(words[start:start + size])
                if len(run) > 6 and run in body:
                    return True
    body_words = set(re.findall(r"[a-z0-9\u4e00-\u9fff]+", body))
    for word in words:
        if len(word) < 5:
            continue
        if any(candidate.startswith(word) or word.startswith(candidate)
               for candidate in body_words if len(candidate) >= 5):
            return True
    return False


def check_help_coverage(
    raw_lines: list[str],
    help_text: str,
    help_name: str,
    findings: list[tuple[str, int, str]],
) -> None:
    """Every long flag the tool's `--help` prints must be mentioned somewhere.

    One direction only: a README may legitimately mention a flag from another
    tool, but it must not omit one of its own.
    """
    compact = "\n".join(raw_lines)
    help_flags = {flag for flag in FLAG_RE.findall(help_text) if flag != "--help"}
    undocumented = sorted(flag for flag in help_flags if flag not in compact)
    if undocumented:
        preview = ", ".join(f"`{flag}`" for flag in undocumented[:6])
        more = "" if len(undocumented) <= 6 else f" (+{len(undocumented) - 6} more)"
        findings.append(("warning", 1,
                         f"flags in {help_name} with no mention here: {preview}{more}"))


def auto_pair(path: Path) -> Path | None:
    """The one sibling README in another language, if there is exactly one."""
    if not (path.name.lower() == "readme.md" or LANGUAGE_README_RE.fullmatch(path.name)):
        return None
    siblings = [
        candidate
        for candidate in path.parent.glob("README.*.md")
        if candidate.resolve() != path.resolve()
        and LANGUAGE_README_RE.fullmatch(candidate.name)
    ]
    return siblings[0] if len(siblings) == 1 else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a README for structural and factual defects.")
    parser.add_argument("readme", help="path to the README to check")
    parser.add_argument("--pair", help="the other language's README, for drift checks")
    parser.add_argument("--max-lines", type=int, default=350, help="line budget (default: 350)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument(
        "--taxonomy",
        help="classification.md holding the English/Chinese heading table "
             "(default: the skill's references/classification.md)",
    )
    parser.add_argument(
        "--previous",
        help="the README this one replaces; every old section must leave a trace",
    )
    parser.add_argument(
        "--help-text",
        help="a file holding the tool's `--help` output; every long flag in it "
             "must be mentioned in the README",
    )
    parser.add_argument(
        "--transcript",
        action="append",
        help="a file holding real run output (repeatable); every ```text block "
             "in the README must appear in one of them",
    )
    args = parser.parse_args(argv)

    path = Path(args.readme)
    if not path.is_file():
        raise SystemExit(f"not a file: {path}")
    pair = Path(args.pair) if args.pair else auto_pair(path)
    if pair is not None and not pair.is_file():
        raise SystemExit(f"not a file: {pair}")
    previous = Path(args.previous) if args.previous else None
    if previous is not None and not previous.is_file():
        raise SystemExit(f"not a file: {previous}")
    help_source = None
    if args.help_text:
        help_path = Path(args.help_text)
        if not help_path.is_file():
            raise SystemExit(f"not a file: {help_path}")
        help_source = (read(help_path), help_path.name)
    transcript_source = None
    if args.transcript:
        transcript_source = []
        for name in args.transcript:
            transcript_path = Path(name)
            if not transcript_path.is_file():
                raise SystemExit(f"not a file: {transcript_path}")
            transcript_source.append((read(transcript_path), transcript_path.name))

    findings = run(path, pair, args.max_lines, load_heading_map(
        Path(args.taxonomy) if args.taxonomy else DEFAULT_TAXONOMY
    ) if pair is not None else {}, previous, help_source, transcript_source)
    for severity, line, message in sorted(findings, key=lambda f: (f[1], f[0])):
        print(f"{path}:{line}: {severity}: {message}")

    errors = sum(1 for severity, _, _ in findings if severity == "error")
    warnings = len(findings) - errors
    print(f"---- {errors} error(s), {warnings} warning(s)")
    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
