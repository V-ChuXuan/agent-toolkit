# Anti-AI prose rules

Two failure modes, in the order they usually appear:

1. Marketing filler — `seamlessly`, `revolutionize`, emoji on every bullet.
2. Concept inflation — a normal mechanism dressed up as a "matrix", a "system",
   a "guard", a "full-chain pipeline". It reads as expertise and carries no fact.

Both are detectable in a draft, and the second one is worse: it survives a casual
review because it sounds technical.

## Banned wording

Replace rather than soften. The right-hand column is what a maintainer would
actually write.

| Banned | Write instead |
|---|---|
| seamlessly, seamless | say what the two parts hand to each other, or delete |
| blazingly fast | the measured number and what it was measured on |
| world-class, cutting-edge, state-of-the-art, game-changing | delete; if it matters, cite the benchmark |
| revolutionize, empower, unleash | the verb the user performs: install, export, paste |
| effortless, intuitive, user-friendly | the number of steps, or the one command |
| robust, secure, enterprise-grade | the mechanism: sandbox, signed releases, bounded retries |
| "a testament to", "say goodbye to", "let's dive in", "in today's fast-paced" | delete the sentence and start with the fact |
| 赋能, 无缝, 颠覆, 极致体验 | 具体动作和数字 |
| 全链路 | 点名从哪一步到哪一步 |
| 矩阵, 体系, 守护 | 说清楚它到底拦住什么、什么时候触发 |

The checker's `INFLATED_RE` covers the machine-detectable subset of this table:
`seamlessly`, `blazingly fast`, `world-class`, `revolutionize*`, `cutting-edge`,
`state-of-the-art`, `game-chang*`, `effortless*`, `empowering`, `unleash*`,
`a testament to`, `say goodbye to`, `let's dive in`, `in today's fast-paced`,
`赋能`, `矩阵`, `全链路`, `极致体验`, `无缝`, `颠覆`. Change one list and you
change the other in the same edit. Words like `体系` and `守护` stay out of the
regex on purpose: `守护进程` and `文件体系` are ordinary technical terms, and a
false positive trains people to ignore the checker.

## Sentence shape

- One clause per sentence. Chinese under about 25 characters, English under about
  20 words. If a sentence needs a comma to survive, split it.
- The subject is a person or a concrete thing: you drop a file, the script reads
  it, the server returns a page. Not "支持…", not "is designed to…".
- Name the mechanism, not the benefit it is supposed to produce. "Retries three
  times with a 2 s backoff" beats "robust error handling".
- No exclamation marks. No emoji per bullet; a consistent emoji on H2 headings
  and a single ⭐ in the closing Star invitation are allowed.

## Feature bullets

Use one shape throughout:

```
- **Phrase naming the feature:** the mechanism or the measured result, at most
  two sentences. Name the file or command that proves it when it is not obvious.
```

Examples:

- `- **Offline by default:** the index is built from local files; no network call
  happens after install.`
- `- **Bounded retries:** a failed fetch retries three times with a 2 s backoff,
  then fails the run instead of hanging.`

Not:

- `- **Powerful and flexible:** designed to meet all your needs.`
- `- **高性能:** 采用多级缓存矩阵，全链路优化。`

## Claims that need evidence

A sentence with an adjective but no number, file, or command behind it is a
finding. Either attach the evidence or cut the adjective. Comparisons need the
conditions: sample size, hardware, model, and the command that produced the
number.

## Mechanical tells

These need no judgement. Two are checked by `scripts/check_readme.py` as
warnings; the rest are a read-through list because a regex would misfire.

- **`not just X, but Y`**: a staged contrast that delays the point. State Y.
- **Chat residue**: "Great question", "Certainly!", "Sure thing" — none of these
  belong in a document.
- **Em dash chains**: a dash every other sentence is a tic, not punctuation.
- **Heading echo**: a one-line paragraph that repeats its own heading.
- **Same opener three times**: three consecutive sentences starting with the same
  content word.

## Body length

For a small tool, 400 to 900 words is enough; 1,800 is the ceiling. Length above
that usually means reference material that belongs in `docs/`.

## Self-test before delivery

1. Would I say this sentence to a colleague in review? If not, rewrite it.
2. Does every number have a source I can point at?
3. Could the same sentence describe a different project? If yes, it is filler.
4. Read the first paragraph aloud. Does it answer "what is this" before anything
   else?
