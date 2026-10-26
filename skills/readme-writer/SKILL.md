---
name: readme-writer
description: "Use when explicitly asked to write, rewrite, trim, audit, or format a README, or format a similar Markdown project document. Content modes use project evidence and check links, commands and bilingual drift; Format preserves content and language. Replaces readme-authoring and readme-beautifier."
disable-model-invocation: true
user-invocable: true
---

# README Writer

Produce a README a first-time visitor can act on without opening the code. Every
claim comes from inspected project material, an attributed source, or the user;
nothing is invented to fill a section. This skill supplies the procedure and
the checkers, not a template to paste. It is invoked deliberately, not inferred from a passing
mention of "README".

Boundary: this skill covers README content and formatting. Format also handles
similar Markdown project documents, without rewriting their prose. General
articles, design documents, and API specifications are outside content modes.

Content modes default to Chinese first: `README.md` (Chinese landing page) and
`README.en.md` (English). An explicit user language scope overrides this default.
Format touches only the selected existing file; Audit writes nothing.

References to the retired `readme-authoring` mean this skill's content modes;
references to `readme-beautifier`, including those in other skills, mean Format.
These are migration names, not additional skills to load.

## Locate the helpers

Resolve `<skill-dir>` to the absolute directory containing this loaded
`SKILL.md`, including when it was loaded through a global link. Replace the
quoted placeholders in commands below with actual paths; `<repo>` is the target
repository and `<temp-dir>` is a safe temporary directory. Never resolve helper
paths against the target repository or assume it contains `.agents/skills/`.

## Step 1 — Route the task

Use the request to select the mode; clarify only when content and formatting
intent remain materially ambiguous. Format takes its own short path and skips
Steps 2–8, including classification, bilingual generation, trimming and evidence
execution. Audit uses inspection and reports findings without writing.

| Task | When | Path |
|---|---|---|
| New | no README, or a full rewrite | facts → draft → check → preview → write |
| Update | behaviour changed and the README is stale | read the README and `git log -p -- README.md`, mark every claim as still true / outdated / unprovable, edit in place |
| Trim | over 350 lines or the user says it is too long | count lines per section, move reference material into `docs/`, leave one summary line and a deep link |
| Audit | the user wants a review | facts, checker, report. **Read-only: do not edit any file unless asked** |
| Format | content is accepted; layout, headings, spacing, lists or code fences need cleanup | read [formatting rules](references/formatting.md), preserve meaning and language, format the selected file, check links and report |

Editing means changing the existing paragraph. Do not append an "update notes"
section at the end.

## Step 2 — Scan

```bash
python "<skill-dir>/scripts/scan_repo.py" "<repo>"
```

The scanner is read-only. It never reads secret files and reports environment
variable names only. It prints JSON with manifests, entry points, bootstrap
files, licence, environment signals, config files, the tree, the existing README
headings, the language signal, monorepo signals, secret file paths, and a size
warning.

- No readable content or metadata: report the missing evidence rather than
  inventing a project. A documentation, data, model, or binary-distribution
  repository can still have a useful README when its actual sources support it.
- More than 1500 files: work one top-level directory at a time, from
  `size_warning`; do not sample.
- Monorepo: ask for root README, per-package READMEs, or both.

If the scanner crashes on a manifest, fall back to reading that manifest by hand
and say which file failed.

## Step 3 — Classify

First identify what the repository delivers, its primary reader, that reader's
first task, and the main cost of a failed or mistaken use. Read the actual entry,
manifests, config examples, tests, licence, and relevant data/model documentation.
Distinguish the released product from its source repository and route other
readers to their own documentation.

Read `references/classification.md`. Use a matching class and its matrix when
helpful; data, model, plugin, template and documentation repositories need not
fit one of the five code-oriented templates. Use [the pattern notes](references/readme-patterns.md)
for those cases or when the audience and first path remain unclear. There is no
required section count.
When the repository has a README already,
compare its headings with the matrix and treat headings outside the matrix as
candidates to preserve; ask during the preview instead of deleting them.

How each enabled section is built — masthead layers, install conventions,
badges, media, numbers, and the closing — is in `references/section-conventions.md`.

## Step 4 — Draft

Answer the primary reader's questions in the first screen: what it is, why it is
useful, where to start, and what result to expect. Installation and terminal
output apply only when they fit that repository; a navigation destination,
interface, generated file, model response or research result can be the first
success. Put long references behind links.

Match each key claim to its evidence: behavior verified in this session,
implementation/configuration inspected, or an attributed source statement.
Read [evidence and reader routing](references/evidence-and-routing.md) when
assigning those levels or separating multiple readers. Source files and directory
trees do not prove runtime success. Stop verification before deployment,
publication, paid calls, production writes, notifications or real sensitive data.

Length target: about 300 lines. Above 350 the trim path applies. Build the
centred masthead and the closing from [the shared example](references/header-footer.md):
existing logo, name, core use, short detail, factual badges, and real navigation;
then License, optional Credits, and a short Star invitation. Keep the body
left-aligned. Follow `references/section-conventions.md` for the conditions and
the install section. Do not invent assets, links, contributors, or a licence
to fill the layout.

Facts rule, applied line by line:

- Every install and usage command exists in the repository (manifest scripts,
  `Makefile`, `--help` output, install script).
- **Name the invocation you actually ran.** `python -m tool` from a checkout is
  not the same as an installed `tool`. Before writing "the command was run",
  confirm the executable resolves (`where`/`command -v`/`pip show`); if only the
  module form works, say so and do not claim the installed command works.
- Every default value is read from the code that uses it, never from a comment
  or `.env.example`.
- Every version, runtime and licence claim comes from inspected manifests,
  licence files, model/data cards or release evidence; attribute unverified
  source statements instead of presenting them as current runtime facts.
- Every measured number comes with its conditions and the command or data file
  that produced it.
- **Order and direction are measured, not inferred.** For any claim containing
  first/last/biggest/smallest/ascending/reverse, run the command on a sample and
  read the resulting order. An option name is not evidence of its behaviour.
- **An API claim is exercised.** Import the package and call the function or
  method you name, at the level you claim: a module export and an instance
  method are different facts, and reading `__init__.py` does not tell them apart.
- **Every flag in `--help` is accounted for.** Document it, or say why it is
  omitted. A table that silently drops `--verbose` and `--version` reads as
  complete and is not.
- **A limitation you keep must keep its qualifier.** If the old text said
  "skipped (but not their arguments or body)", the new text cannot say "skipped";
  trimming a clause turns a true sentence into a false one.
- Every external link is a URL that was opened or copied from the repository; do
  not assemble an address from a pattern.
- No source, no sentence. Ask the user for what only they know (measured
  numbers, motivation, screenshots, comparisons). If there is no answer, leave
  `<!-- TODO: what is missing -->` and list it at delivery.

Show only commands that were run. Run them in a scratch copy, never in the
repository. Trim whitespace from output and nothing else. A command that cannot
run here, or must not run because it deploys, publishes, pushes, deletes or
spends money, is shown without output followed by one line:
`Not run while writing this README: needs <reason>.`

Secrets rule: write variable names from `.env.example` or the code, never
values. Never open `.env`, `*.key`, `*.pem` or `credentials*`. Redact
`sk-…`, `ghp_/gho_/ghs_…`, `AKIA…`, `AIza…` and JWT-shaped strings as
`[REDACTED]` and tell the user where they were.

Content modes write both languages in this step unless the user specified a
narrower language scope. Format preserves the selected file's language and
never creates a translation. Use the canonical headings from
`references/classification.md` so the two files pair up. Draft the Chinese landing
page first by default; use `language_signal` to understand the existing material,
not to override an explicit language choice. Numbers, commands,
variable names, paths and badge URLs are copied verbatim; prose is written
natively, not translated sentence by sentence.

## Step 5 — Check

```bash
python "<skill-dir>/scripts/check_readme.py" "<repo>/README.md" --pair "<repo>/README.en.md"
python "<skill-dir>/scripts/check_readme.py" "<repo>/README.md" --previous "<temp-dir>/README.md.bak"
python -m tool --help > "<temp-dir>/help.txt"
python "<skill-dir>/scripts/check_readme.py" "<repo>/README.md" --help-text "<temp-dir>/help.txt"
python -m tool ... > "<temp-dir>/run.txt"
python "<skill-dir>/scripts/check_readme.py" "<repo>/README.md" --transcript "<temp-dir>/run.txt" --transcript "<temp-dir>/help.txt"
```

The checker can find one other language file automatically beside `README.md`;
use explicit `--pair` when compatibility language pages also exist. The second
is for a rewrite: every H2 in the old file must still leave a trace, so a trim
cannot quietly drop a section instead of moving it. It also compares sections
that kept their heading: if the body lost more than half its text and the
section links nowhere, the content was deleted rather than relocated. The third
catches a flag the tool documents and the README silently omits. The last one is the honesty check:
every fenced block tagged `text`, `console` or `output` must appear verbatim in
a captured run, so a plausible-looking output block that was never printed is
reported. Whitespace may differ; words may not.

Open `<!-- TODO -->` markers are counted and reported: they are allowed, but the
delivery message has to name them.

Errors mean the file is not ready: dead anchors, missing relative files,
machine-local paths, leftover placeholders, broken HTML, a licence badge with no
`LICENSE` file. Warnings cover length, inflated wording, bilingual drift (section
set, order, numbers, code lines, and a section whose paragraph count diverges
between the two files), sections
outside the heading map, sections the old README had that this one lost, flags
missing from the flag table, output that no run produced, and open TODOs.
`--strict` turns warnings into failure. Fix every error and every warning that
is not deliberate, then run it again.

Running the checker is not evidence that the text is true. In this order:
re-read the draft against Step 4, then simulate the reader on a fresh machine —
follow the README from a clean checkout and stop at the first step that cannot be
completed from the text alone. Fix the step before that blocker, not the blocker.
A README that starts with a command the reader cannot run has failed the
simulation even with zero checker findings.

Before claiming the readme is done, run the skill's own self-test once if you
edited a rule:

```bash
python "<skill-dir>/scripts/selftest.py"
```

Wording for the two cases the checker cannot see:

- A command that was run: say what came back (`4 tests passed`, `HTTP 200`).
- A command that was not run: `Not run while writing this README: needs <reason>.`
  A command whose output would change the machine (installers, migrations) or
  that needs a secret, a GUI or another OS belongs in this category.

## Step 6 — Preview before writing

Show a summary first: class, enabled sections, sections preserved from the old
README, TODO list, and which commands were not run. Write only after the user
confirms. If they ask for the full text, show it.

## Step 7 — Write

- Existing README: copy to `README.md.bak` before overwriting.
- Write both content language files in the same pass unless the user requested
  a narrower language scope. Format follows its selected-file path instead.
- Report the class, the two paths, the backup path, the TODO count and, for an
  update, the claims dropped as outdated — in two or three lines.

Never commit, push, tag, publish, or open a pull request from this skill. The
repository's own release process owns those actions.

## Step 8 — Independent review, large changes only

A new README, or a change touching more than about a third of the text, gets a
second pass: hand `references/verification-brief.md` to a subagent that did not
write the file, with read-only access, and fix what it reports as blocker or
high. Routine edits skip this step.

If the reviewer still reports blockers after two rounds, stop and give the user
the findings instead of shipping a third draft.

## Rules that never bend

1. No claim without inspected project evidence, an attributed source, or the
   user's answer; wording must reflect its evidence level.
2. Content-mode command claims need evidence that they run or an explicit
   "not run" line. Format preserves accepted commands without executing them.
3. No secret value, ever.
4. Content modes default to both languages with identical facts; preserve an
   explicit narrower scope. Format keeps the existing file and language only.
5. Content modes preview before writing and back up before overwriting; Format
   follows its selected-file formatting path.
6. No commit, push, release, or deployment.

## Stop and ask

For content modes, stop rather than guessing when the repository has no usable
evidence, the primary reader or scope remains materially ambiguous, the only
fact that makes the README useful is missing and the user has not answered, or
writing would overwrite a README the user has not seen. Format does not need a
code-project classification or new facts; preserve its accepted content.

## Files here

- `references/formatting.md` — selected-file formatting without content changes
- `references/evidence-and-routing.md` — evidence levels and reader entry points
- `references/readme-patterns.md` — reader-first patterns beyond the code templates
- `references/classification.md` — classes, section matrix, bilingual heading map
- `references/section-conventions.md` — masthead, install, badges, media, numbers, closing, update ledger
- `references/header-footer.md` — shared centred masthead and License → Credits → Star example
- `references/anti-ai-slop.md` — banned wording, with replacements
- `references/verification-brief.md` — read-only review prompt for Step 8
- `references/templates/` — one skeleton per class
- `scripts/scan_repo.py` — read-only fact sheet
- `scripts/check_readme.py` — exit 1 on errors; auto-pairs the other language, and `--previous` catches a dropped section
- `scripts/selftest.py` — exercises every rule; run after editing a rule

Adapted in structure and rules from `QingYunA/readme-skill` (MIT) and
`NewTurn2017/readme-writer` (MIT), with command-evidence and section-budget
rules from `rishabhrawat35/github-readme-writer` (no licence: rules only, no
code) and section naming from `RichardLitt/standard-readme` (MIT).
