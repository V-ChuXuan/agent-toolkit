# library skeleton

Use for a package with a manifest but no executable entry point. Write Chinese
`README.md` first using `../classification.md`; use the English headings below
for `README.en.md`, keeping the same order.

Start with the [shared centred masthead](../header-footer.md#opening). Its core
sentence names the API surface and the problem it solves. Then choose the body
sections below.

## Why this exists

The library the reader might use instead, and the concrete difference. No
adjectives without a number behind them.

## Install

```bash
<package manager command>
```

## Quick Start

```python
<the shortest complete example>
```

Show what the example returns, copied from a real run.

## Usage

| Name | Signature | Returns |
|---|---|---|
| | | |

Cover the public surface only. Internal modules stay undocumented here.

## Configuration

Options passed to the main entry point, with defaults read from the code. Drop
this section when the package has no options.

## Limitations

Unsupported runtimes, size limits, behaviours a reader would assume but not get.

## Development

```bash
<install dependencies>
<run the tests>
```

Finish with the [shared closing](../header-footer.md#closing): License,
supported Credits, and the optional Star line.
