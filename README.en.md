<div align="center">

# Agent Toolkit

**Reusable Agent assets drawn from personal development practice.**

For developers using Agents: Prompts, Skills, MCP tools, Hooks and working patterns.

[Browse assets](#asset-index) · [Usage](#usage) · [简体中文](README.md) · [English](README.en.md)

</div>

## Quick Start

Choose an asset by the problem you want to solve, then read its guide. Keep a Skill's complete directory. Check host capabilities before connecting a Hook.

### Asset index

| Asset | Problem addressed | When to use | Status | Version |
| --- | --- | --- | --- | --- |
| [README Writer](skills/readme-writer/README.md) | Write, update, trim, audit and format READMEs using project evidence | An explicit request to handle a README or similar Markdown project document | `experimental` | `0.1.0` |
| [Session Title](hooks/session-title/README.md) | Prepare a single session-naming request for a host | A host supports Hooks or extensions and can confirm its current title state | `experimental` | `0.1.0` |

`experimental` means runnable content exists, but you still need to validate it against your host and tasks. Passing Python checks does not guarantee model output quality or automatic host renaming.

For README work, have your Agent read [README Writer's SKILL.md](skills/readme-writer/SKILL.md), then follow its mode, evidence, preview and writing procedure.

For session naming, start with [Session Title's host integration](hooks/session-title/README.md#宿主接入). It prepares the request; actual renaming still requires native host capabilities.

## Usage

### Directory

| Directory | Contents | Available now |
| --- | --- | --- |
| [skills/](skills/README.md) | Work skills entered through `SKILL.md`, with scripts and references | README Writer |
| [hooks/](hooks/README.md) | Event-triggered scripts and host adapters | Session Title |
| [prompts/](prompts/README.md) | Standalone task prompts and input/output contracts | No assets yet |
| [mcp/](mcp/README.md) | MCP tools, services or shareable integration guides | No assets yet |
| [patterns/](patterns/README.md) | Reusable working methods, decision steps and validation | No assets yet |
| [experiments/](experiments/README.md) | Trials and observations not yet developed into formal assets | No assets yet |

Use the index's problem and context columns to find an asset, then read its README. A Skill's detailed behavior lives in `SKILL.md`; a Hook's host requirements live in its integration guide.

### Adoption

There is no unified installer. Copy a complete asset directory or let your host reference it, following the asset's instructions. Discovery rules, permissions and host versions vary.

- **Skills**: read `SKILL.md` and keep `references/` and `scripts/`. README Writer requires explicit invocation; merely mentioning README does not activate it.
- **Hooks**: read the inputs, outputs and host limitations before connecting them. Preserve a way to restore the existing configuration.
- **Prompts, MCP and Patterns**: there is no installable content yet. Future assets will have their own guides.

Repository files are the maintenance source. Files installed under `.codex/hooks`, `.codex/skills`, `.agents/skills` or global directories are installation or adaptation copies. **Copying does not change an existing entry point or establish automatic synchronization.** Review differences and run asset validation before updating an installed copy.

## Participate

### Lifecycle

| Status | Meaning | Adoption guidance |
| --- | --- | --- |
| `draft` | Purpose or interface is being worked out; validation is incomplete | Read as a draft |
| `experimental` | An implementation or reproducible procedure exists; contracts may change | Try in a controlled setting |
| `stable` | Contracts, dependencies and validation are documented, with reuse evidence | Follow the guide and verify your environment |
| `retired` | No longer recommended; reasons and alternatives are retained | Consult for history or migration |

Changing status updates the asset guide and index. It does not install, uninstall or delete files. Assets maintain their own versions. Document compatibility and migration when inputs, outputs or integration methods change.

### Adding an asset

1. Choose the category and name the asset after a concrete problem. Check the index for overlap.
2. Extract the reusable method. Replace personal project names, fixed paths, account information and private data with inputs or explicit examples.
3. Use `skills/<name>/SKILL.md` for a Skill and a dedicated README for other assets. Preserve required scripts, references and attribution.
4. Complete the fields below, run the smallest relevant validation and add an index entry. State what remains unverified.

| Field | Minimum content |
| --- | --- |
| Purpose | The concrete problem it solves |
| Trigger | When to use it and when to skip |
| Input | What the user, host or files must provide |
| Output | Files, text, behavior and side effects |
| Dependencies | Runtime, host capabilities, permissions and external services |
| Validation | Runnable commands or reproducible steps |
| Status | `draft`, `experimental`, `stable` or `retired` |
| Version | Current version and relevant compatibility notes |

Do not publish session histories, real credentials, personal configuration or runtime caches. Use placeholders for example keys. Preserve sources and licenses for referenced or adapted material.

## Development

### Validation

Python helpers use the standard library. The project baseline is Python 3.11+. Run from the repository root:

```sh
python -B -X utf8 skills/readme-writer/scripts/selftest.py
python -B -X utf8 -m unittest discover -s hooks/session-title -p "test_*.py" -q
python -B -X utf8 skills/readme-writer/scripts/check_readme.py README.md --pair README.en.md
```

Self-checks and unit tests cover script rules, inputs, outputs and controlled fixtures. The documentation checker covers structure and links, not the truth of claims. Real hosts, model quality and external services need separate validation as described in the asset guide.

The commands above were run in an isolated temporary copy on Windows with Python 3.15.0. Self-checks and unit tests passed; bilingual documentation checks reported no errors or warnings. This does not establish runtime support on other Python versions or operating systems.

## Limitations

Both available assets are `experimental`. Model output quality, automatic Codex Desktop renaming and current Pi/OMP compatibility were not verified in this run. A Hook cannot supply native capabilities that its host lacks.

The repository does not yet provide a unified installer, automatic synchronization or a ready-to-run MCP service. Prompts, MCP, Patterns and Experiments currently contain directory guides only.

## License

Original contributions use the [MIT License](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for sources and upstream licenses of adapted material.

## Credits

- [QingYunA/readme-skill](https://github.com/QingYunA/readme-skill): README workflow, review conventions and writing guidance.
- [NewTurn2017/readme-writer](https://github.com/NewTurn2017/readme-writer): classification, templates and evidence inventory structure.
- [RichardLitt/standard-readme](https://github.com/RichardLitt/standard-readme): section naming and ordering guidance.

<p align="center"><sub>If these assets help you, a ⭐ can help others find them.</sub></p>
