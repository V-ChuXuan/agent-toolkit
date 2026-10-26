# Section conventions

How each section is built, once the matrix says it is enabled. These are the
conventions a reader can feel but rarely names, and the ones a rewrite most often
drops.

## Masthead

Use the centred layout in [the shared example](header-footer.md), with generous
space between these layers. Drop any layer the repository cannot fill.

1. Existing logo, with descriptive alt text and a repository-relative path.
   Around 120–180 px often works; choose a size that suits the asset rather
   than imposing an icon-size limit.
2. Project name as the single `#` heading, optionally with its Chinese name.
3. One bold sentence stating the core use and concrete value.
4. A short supporting description of the main workflow, audience, or runtime.
   A measured number belongs here only when it helps and has evidence.
5. Factual badges in one or two compact rows: release, build status, runtime,
   supported platforms, or licence. Use a consistent style.
6. Real entry points such as Download, Docs, Examples, Community, and the
   language switch. Keep the row short; omit nonexistent destinations.

Close the centred container before the body, which stays left-aligned. Do not
add sponsors, decorative media, or channels to imitate a reference project's
masthead. Markdown inside an HTML container needs blank lines around it; keep
those boundaries from the example.

The first 50 words state what the tool is, what makes it different, and for
whom. No history, no motivation, no thanks in the masthead.

## Install

- Prerequisites first: runtime, minimum version, and whether a separate install
  step exists at all. Take the version from the manifest, not from memory.
- One subsection per installation method, the recommended one first, marked
  `(recommended)`. Rare or manual paths collapse into `<details>`.
- For agent-facing tools, the first method is a one-line prompt that tells the
  agent to read `INSTALL.md` and follow it; installation details live in that
  file so the README survives install-logic changes.
- End the section by pointing at the next step.
- When recommending an optional feature, state four things: default state, why
  it is recommended, its cost, and a paste-ready command.

## Badges

A badge earns its place by answering a decision: is this maintained, does it run
on my runtime, is it published. A build badge must point to an actual workflow;
a licence badge must match the actual licence file and may coexist with the
footer's licence sentence. Do not add a line-count badge or a static "passing"
badge without a status source. Use one style across all badges.

## Closing

Follow License → Credits → a short Star invitation, as in
[WeChatBridge](https://github.com/freestylefly/WeChatBridge). Use
[the shared example](header-footer.md), with these conditions:

- License is one sentence naming the actual licence and linking to its file.
  If none is declared, say so; do not assign one or create a file for the layout.
- Credits names verified sources or contributors and says what each supplied,
  such as a base project or a dependency's role. Link to the real source. Omit
  this section when there is nobody or nothing supported to acknowledge.
- For a public GitHub project, finish with one friendly, centred, small-text
  sentence inviting a Star. A single ⭐ is enough. Use the README's language;
  omit the invitation for private or non-GitHub deliverables.
- Do not copy a reference project's names, licence, contributors, badge states,
  metrics, or sponsors. Do not add a heading or another feature list after the
  closing sentence.

## Demo and media

- If a before/after image exists, it goes first, directly under the masthead: it
  answers "what is this" and "why use it" at once.
- Then two or three questions the reader would actually type, then a short video.
  On GitHub, upload the MP4 in an issue comment and use the generated
  `user-attachments` URL; GitHub plays it inline.
- Screenshots go under `docs/` and are referenced by relative path, with alt text
  stating what the screen shows. Provide a dark and a light variant with
  `<picture>` when the UI has both.
- A repository that gets cloned to install (skill, plugin, template) keeps video,
  GIFs and benchmark corpora outside git: attachment links for media, release
  downloads for corpora.

## Numbers

- Every number carries its conditions: sample, runs, model or hardware, setup.
- Every number has a data file and one command that reproduces it.
- A number is expanded once. Other places cite it with a link.
- After re-measuring, search every copy — README, the other language, `docs/`,
  the site — for the old value and change all of them.
- A small sample is written as a sentence ("about 18× fewer tokens in a small
  test, [details](bench/README.md)"), not as a headline table.
- Unfavourable numbers get one honest sentence explaining why, then a link.

## Honest limits

State what the project does not do, including the comparison the reader expects:
"Its diagram tools go further than ours" is stronger than silence. When something
was not measured, write "not measured" rather than implying it was.

## Update mode

Read the existing README and, in a git repository, `git log -p -- README.md`.
Mark every claim still true, outdated, or unprovable. Edit in place: no update
notes section at the end. At delivery, list the claims that were dropped as
outdated and the claims that could not be verified.
