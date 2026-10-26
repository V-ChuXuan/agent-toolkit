# Classification and section activation

Single source of truth for three decisions: which class a repository is, which
sections that class enables, and how the English and Chinese headings pair up.
`scripts/scan_repo.py` supplies the signals; this file decides what they mean.

This guide applies to content modes. Format uses only
[formatting rules](formatting.md), preserving the selected file's language,
sections and current style; it does not apply this matrix or generate a pair.

## Five code-oriented classes

| Class | Signals | Register |
|---|---|---|
| `skill-bundle` | several `SKILL.md` files, or `install.sh` / `bootstrap.sh` linking skills into an agent directory | one-line install, what the agent gains, idempotent setup |
| `cli-tool` | `bin` in `package.json`, `[project.scripts]` in `pyproject.toml`, `[[bin]]` in `Cargo.toml`, `cmd/*/main.go` | first command within the first screen, flag table, real output |
| `library` | manifest without executable entry points, import-level usage, published metadata | install, import example, API table, constraints |
| `webapp` | `next.config.*`, `vite.config.*`, `nuxt.config.*`, `Dockerfile` plus compose, `app/` plus `pages/` | screenshot first, quick start, environment table, deployment |
| `script` | one entry file, no or minimal manifest, examples over API | what it does, how to run it, licence line |

Choose the class by what the primary reader will do, using scanner signals as
evidence rather than a fixed precedence. Do not force a documentation, data,
model, plugin, integration or template repository into `script` just because it
has no manifest. Read the relevant [pattern notes](readme-patterns.md) instead:

- Plugins and integrations: host, supported versions, permissions and one visible
  effect after activation.
- Datasets, models and research: provenance and licence, task and format,
  minimal load/inference/reproduction, evaluation conditions and limitations.
- Templates: generated result, creation path, modification starting point and
  external prerequisites; keep template-maintainer work separate.
- Documentation and resource collections: scope, reliable navigation, common
  lookup/adoption task, version and maintenance entry.

The matrix is a starting point for matching code projects, not a required
structure for every repository.

## Section activation matrix

`●` enabled by default · `○` enabled only when a signal exists · `–` not used.
Select sections that help this repository's reader; there is no minimum count.
Do not add a section just to fill the matrix. Preserve useful existing sections
even when their headings are outside it.

| Section | skill-bundle | cli-tool | library | webapp | script |
|---|:-:|:-:|:-:|:-:|:-:|
| Centred masthead (existing logo, title, core use, badges, navigation) | ● | ● | ● | ● | ● |
| Demo (screenshot, GIF, or ask → get) | ○ | ○ | ○ | ● | – |
| Why this exists (difference from alternatives) | ● | ● | ● | ● | – |
| Install | ● | ● | ● | ● | ● |
| Quick Start | ● | ● | ● | ● | ● |
| Usage | ● | ● | ● | ○ | ● |
| Features | ○ | ● | ● | ● | – |
| Configuration (including environment variables) | ● | ● | ○ | ● | – |
| Architecture (how it works) | ○ | ○ | ○ | ○ | – |
| Limitations (what it does not do) | ● | ● | ● | ● | ○ |
| Development (including verification commands) | ● | ○ | ● | ● | – |
| License | ● | ● | ● | ● | ● |
| Credits (verified sources and contributions) | ○ | ○ | ○ | ○ | ○ |

Finish in this order: License, Credits when supported, then a short centred
Star invitation for a public GitHub project. The invitation has no heading.
See [the shared opening and closing](header-footer.md).

## Signals that are missing

- No licence file: say that no licence is declared. Do not choose a licence,
  create a `LICENSE` file, or add a licence badge as part of styling the README.
  Link to the actual licence file when one exists; never claim a licence the
  repository does not contain.
- No verified source or contribution to acknowledge: omit Credits, rather than
  inventing a dependency, sponsor, contributor, or community.
- No git repository: skip contributors, changelog links and dynamic badges.
- `env_signals` empty: drop the environment table, even where the matrix says
  `●`; keep configuration only when a real config file exists.
- No manifest: omit unsupported package-manager install lines. Classify by the
  deliverable and reader task; a single executable script may use `script`.
- No readable sources or metadata: report the evidence gap. Binary releases can
  be documented from actual release metadata or attributed official sources;
  do not invent behavior or an installation path.
- Monorepo signal: ask whether the root README, one README per package, or both
  are wanted. Never sample a subset of packages silently. `manifests` lists each
  nested package with `nested: true`, its `directory`, and `has_bin`, so the
  per-package facts are already in hand when the user chooses.

## Sections the author added

Compare `existing_readme.section_headers` with this matrix. A heading outside
the matrix that clearly holds real content is a candidate to keep, not noise.
Ask about it during the preview instead of deleting it.

## Language

Content modes default to Chinese first: `README.md` is the Chinese landing page
and `README.en.md` is the English version. An explicit user language scope takes
precedence. Draft Chinese first by default; `language_signal` informs the reading
of existing material without changing the chosen landing language. Format keeps
the selected file and its existing language; Audit creates neither file.

Numbers, commands, variable names, paths and badge URLs are copied verbatim
between the two files. Prose is written natively in each language, not
translated sentence by sentence.

## Bilingual heading map

Use the English heading as the canonical name in `README.en.md` and the Chinese one
in `README.md`. `scripts/check_readme.py --pair` reads this table to report
missing or reordered sections. Only H2 and deeper headings are compared; the H1
is the project name and may stay identical in both files.

<!-- heading-map:start -->
| English | 中文 |
|---|---|
| Why this exists | 为什么做这个 |
| Demo | 演示 |
| Install | 安装 |
| Quick Start | 快速开始 |
| Usage | 用法 |
| Features | 功能 |
| Configuration | 配置 |
| Architecture | 架构 |
| Limitations | 什么时候不该用 |
| Development | 开发 |
| Similar programs | 同类工具 |
| Participate | 参与 |
| Examples | 示例 |
| Credits | 致谢 |
| Community | 社区 |
| License | 许可 |
| License | 许可证 |
<!-- heading-map:end -->

A heading that is not in this table is compared as raw text, so a new section
will report drift until it is added here. That is deliberate: the map is also
the record of which sections were agreed.
