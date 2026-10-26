# Agent Toolkit

## Purpose

Share reusable Agent prompts, Skills, MCP integrations, Hooks and working patterns.
Publish portable assets extracted from personal practice; keep personal profiles,
credentials and runtime installation state outside this repository.

## Code Map and Stack

- `skills/readme-writer/`: Markdown Skill, references and standard-library Python helpers.
- `hooks/session-title/`: standard-library Python core/tests; Codex adapter and Pi TypeScript adapter.
- `prompts/`, `mcp/`, `patterns/`, `experiments/`: asset categories; empty categories are documented as such.
- No shared service, database, web application or dependency installation is required.
- Python 3.11+ is the project baseline. Host integrations have their own prerequisites.

## Development Workflow

Inspect callers and tests before changing an asset. Use focused regression tests
for behavior changes and documentation checks for content changes. Native subagents
may implement bounded slices; the main agent owns integration and publication.
Do not run or rewrite the installed copies while preparing shareable source assets.

Understand the affected flow before editing, reuse existing patterns, keep changes
surgical and define observable acceptance. Resolve facts by inspection; ask for
material product decisions. Preserve unrelated edits and existing error handling.

## Complexity Budget

- Do not silently expand scope for theoretical robustness.
- Before adding complexity for a speculative race condition or security edge
  case, explain the concrete failure mode, evidence of likelihood (or uncertainty),
  and implementation/maintenance cost; obtain user buy-in.
- If the extra protection is unnecessary for the agreed scope, omit it and
  continue the requested work.
- This does not waive required input validation, access control, data-integrity
  safeguards, or fixes for demonstrated failures.

## Commit Attribution

- Preserve the project's commit convention. For Conventional Commits, use
  `type(scope): [AI] description` when AI materially authored or modified content
  included in the commit.
- Drafting only the commit message does not require the marker.
- The marker records AI involvement, not review or verification status.
- Do not invent tool/model attribution or co-author identities.
- Commit attribution does not grant permission to commit or push.

## Frontend Consistency

- This project currently has no UI. If one is explicitly requested, read the
  enclosing workspace `DESIGN.md` when available and follow any project-specific
  design rules. A standalone checkout must not require a maintainer's local path.
- Reuse existing components, design tokens, and approved dependencies. Prefer
  mature libraries over custom implementations of complex behavior.
- Prefer UI components whose source can be inspected and adapted locally;
  preserve accessibility and upstream license requirements.
- Keep one coherent design language. Do not add overlapping libraries without
  a concrete gap and approval.

### Reference Stack — Examples for React Projects

- UI components and visual style: shadcn/ui with Nova styling.
- Icons: Lucide.
- Animation: Motion.
- Resizable panel layouts: react-resizable-panels.
- Drag and drop: dnd-kit.
- Shared client state: Zustand.

Use these examples as a starting point when the project has no established
choice. Follow the existing project stack first; do not automatically install
every example or migrate existing code to match this list. Use native layout
and local component state when sufficient. Before adopting a library, check
compatibility with the project's framework and installed versions.

## Verification

Run from the repository root, without services or credentials:

```sh
python -B -X utf8 skills/readme-writer/scripts/selftest.py
python -B -X utf8 -m unittest discover -s hooks/session-title -p "test_*.py" -q
python -B -X utf8 skills/readme-writer/scripts/check_readme.py README.md
```

Review public files for machine paths, personal profiles, secrets, broken relative
links and license notices. A passing Python test suite does not prove host UI
renaming, Pi/OMP compatibility or live model behavior. Report those limits.

Run the smallest relevant checks and report observed results and gaps.

## Domain and Data Constraints

- Preserve safety gates and input/output behavior when removing personal examples.
- Fixtures must be self-contained; tests cannot depend on an enclosing workspace.
- Do not include session histories, personal project aliases, account secrets or
  real user data. Generic example values and detector fixtures are allowed.
- Repository assets are the maintenance source once explicitly adopted. Existing
  `.codex`/`.agents` installation copies and global discovery links are separate;
  copying an asset does not change those installations or keep copies in sync.
- Every asset records purpose, trigger, inputs, outputs, dependencies, validation,
  status and version. Preserve upstream attribution and license notices.
- Status is `draft`, `experimental`, `stable` or `retired`; do not imply that an
  unimplemented category or untested integration is available.

## Workspace Integration

- When inside a managed workspace, project rules own development methods,
  technical constraints and verification; the enclosing workspace rules govern
  shared resources, cross-project operations and safety.
- In a Trellis-managed workspace, root Trellis alone owns task lifecycle,
  execution permission and owned paths. Keep task records there; never initialize
  project-local `.trellis/` or copy its managed block. Resolve the enclosing root
  before calling its scripts by absolute path. Standalone users run the checks
  above directly; Trellis is not an asset runtime dependency.
- Before writes, confirm this project, applicable nested instructions, execution
  directory and task scope. A command workdir does not relocate a session or prove
  that instructions reloaded. Verify actual host state separately.
- Keep runtime state project-local where the host supports it; ignore .omx/ in Git.
  Preserve user pauses, host permissions and external/destructive authorization.

## Project Authorization

No automatic commits or publication by default. Require explicit session
authorization for commits, push, release, deployment, paid/production calls and
destructive user-data changes. Preserve installed host configuration unless
the user explicitly requests an installation change.
