# webapp skeleton

Use for a served application. Write Chinese `README.md` first using
`../classification.md`; use the English headings below for `README.en.md`,
keeping the same order.

Start with the [shared centred masthead](../header-footer.md#opening). Its core
sentence says what the user does in the app and what they get back. Then choose
the body sections below.

## Demo

A screenshot or a short recording of the main screen, committed under `docs/` and
referenced by relative path. Alt text states what the screen shows.

## Why this exists

The product it replaces and the difference the reader cares about. Keep it to one
short paragraph.

## Install

```bash
<install dependencies>
```

State the runtime version from the manifest and the database or service the app
expects.

## Quick Start

```bash
<start the development server>
```

Give the local URL and the account, if any, created by a seed script.

## Features

- **<feature name>:** the mechanism, in at most two sentences.

## Configuration

| Variable | Default | Read by |
|---|---|---|
| | | |

Names only, from `.env.example` or the code. Never print a value.

## Architecture

Optional. Describe only what a contributor needs to change the code: the
top-level modules and the direction of their imports.

## Limitations

What it does not handle yet, and what a reader would wrongly assume it does.

Finish with the [shared closing](../header-footer.md#closing): License,
supported Credits, and the optional Star line.
