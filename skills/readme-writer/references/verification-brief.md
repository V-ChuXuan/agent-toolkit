# Independent README review brief

Hand this to a subagent that did not write the README, with read-only access.
Its job is to find what is wrong, not to approve the text. Use it for a new
README or a change touching more than about a third of the file.

Replace the angle-bracket fields before sending.

---

```text
You are reviewing a README that someone else wrote. Your job is to find what is
wrong, not to approve it.

Repository: <repo path>
README files: <actual selected files, normally Chinese README.md and English README.en.md>
Documents they link to: <docs/ paths>

Rules:
- Read only. Do not edit, create, commit, push, install or deploy anything.
- You may run the project's own tests, linters and --help commands.
- For every claim, find the file that proves it. No proof means it is a finding.

Check in this order:

1. Unsupported claims. Features, limits, commands, defaults, supported platforms.
   Point at the code (file:line). For a default value, read the code that uses
   the value, not a comment or .env.example.
2. Numbers. Every measured number carries its conditions (sample, runs, model or
   hardware, setup) and the command or data file that produced it. The same
   number must not differ between the two README files or the linked docs.
3. Commands. Every install and usage command exists and works in the order given.
   A command that was not run must carry the "Not run while writing this README"
   line and a reason.
   Check the invocation literally: `python -m tool` from a checkout is not an
   installed `tool`. If the README says a command "was run" or "is available",
   verify the executable resolves (`where`, `command -v`, `pip show`); report the
   claim as false when only the module form works.
   Check order and direction claims (first/last/biggest/smallest/ascending) by
   running the command on a small sample and reading the output.
   Reconcile the flag table against `--help`: every documented flag must exist,
   and every existing flag must be documented or deliberately left out.
4. Badges. Version, runtime and licence badges match the manifest and files.
5. Omissions. User-visible commands, settings and hard limits that neither the
   README nor the linked docs mention.
6. Overstatement. Adjectives and comparisons with no measurement behind them.
7. Promises the code does not keep. Report these as code findings, not as README
   edits.

Report every finding as: severity (blocker / high / medium / low), README file
and line, the exact quoted text, what the code or file says (file:line), and the
corrected sentence.

Then list what you checked and found accurate, and what you suspect but could not
prove (with what would settle it).

End with: would you block publishing this README, and on which items.

Write the report in Chinese. Keep technical terms, command names, identifiers and
file paths in English.
```

---

## After the report

1. Fix every blocker and high finding. Fix medium findings when the change is
   small; otherwise list them for the user.
2. Code findings ("the code does not do what the README claims") do not get
   edited into the README. Report them separately.
3. Resolve `<skill-dir>` to the absolute directory containing the loaded
   `SKILL.md`, then run `python "<skill-dir>/scripts/check_readme.py" "<repo>/README.md" --pair "<repo>/README.en.md"`
   for the actual files in scope; omit `--pair` for a single-file request.
4. For a large rewrite, send the changed sections back to the same reviewer once.
5. At delivery, say which findings changed the text.
