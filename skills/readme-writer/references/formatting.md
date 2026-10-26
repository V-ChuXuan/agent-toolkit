# Format mode

Use when the user accepts the content and wants a README or similar Markdown
project document tidied. This is the former `readme-beautifier` capability.
Read only the selected file and its relevant link targets; skip repository
scanning, content classification, runtime verification and bilingual generation.

## Preserve the content

- Keep the filename, language, facts, qualifications and author's tone. Do not
  translate, add a sibling README, rewrite prose, add claims or remove content.
- Preserve command and configuration text and every code example's behavior.
  Formatting must not strip shell syntax or change significant whitespace.
- Keep reasonable section order and the existing choices about logos, badges,
  navigation, a TOC and Chinese/English spacing. Do not impose the content modes'
  centred opening, footer, chapter matrix or length target.
- Do not add an introduction, empty-section explanation, badge, TOC, Credits,
  licence or Star invitation to fill a perceived gap. Report missing content
  separately; an empty section is not permission to invent or delete its text.

## Small formatting pass

1. Read the whole selected file and identify actual formatting problems.
2. Fix inconsistent heading levels, list markers and indentation, table layout,
   code fences, paragraph spacing and trailing whitespace where safe. Tag a
   code fence only when its language or output type is known. Keep one final
   newline; preserve meaningful hard line breaks and code whitespace.
3. Prefer heading-level corrections that keep heading text and anchors stable.
   If a heading text must change, repair its selected-file TOC and local anchor
   callers. Inspect known inbound references; if repair would require changing
   an unselected document, keep the heading text and report that limitation.
4. Compare before and after for lost or added information, changed commands and
   broken links/HTML. The existing `check_readme.py` can compare structural
   findings before and after using its absolute skill path. It may auto-detect
   another language file; report those differences, never edit that sibling as
   part of Format. Existing content warnings are findings, not a mandate to
   rewrite, trim or translate.

Apply an already-authorized local formatting request to the selected file and
summarize the concrete fixes. If the user supplied pasted text, return the
formatted text. If the file is already clean, say so without manufacturing a
change. For a review-only request, report formatting findings without writing.

Content accuracy questions use Audit; a requested content rewrite uses New or
Update. A formatting pass must not silently switch to either mode.
