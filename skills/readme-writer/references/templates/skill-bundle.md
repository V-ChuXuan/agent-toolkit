# skill-bundle skeleton

Use for a repository that installs one or more agent skills. Write Chinese
`README.md` first using `../classification.md`; use the English headings below
for `README.en.md`, keeping the same order.

Start with the [shared centred masthead](../header-footer.md#opening). Its core
sentence says which agent it plugs into and what the agent can do afterwards.
Then choose the body sections below.

## Why this exists

The task the agent fails at without this skill, described concretely.

## Install

```bash
<install command, idempotent>
```

Give the destination directory and the files it receives. State the prerequisite:
agent version, runtime, any CLI the skill shells out to.

## Usage

Trigger with `<phrase>` or `<phrase>`. One worked example: what the user says,
what the agent does, what comes back.

## Configuration

| Variable | Default | Read by |
|---|---|---|
| | | |

Only real variables. A skill with no configuration drops this section.

## Limitations

What the skill will not do, which inputs it rejects, and where its output is not
trustworthy without a human check.

## Development

```bash
<install dependencies>
<run the smoke test>
```

Finish with the [shared closing](../header-footer.md#closing): License,
supported Credits, and the optional Star line.
