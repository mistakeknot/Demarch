---
artifact_type: solution
stage: compound
category: data-pipelines
tags: [derived-data, overlay, corrections, ocr, extraction, provenance, build-time]
---

# Repairs to derived data live in an overlay, never in the artifact

Solved 2026-08-19 in `bridger` (`data/corrections.json`, applied by
`kublai/build_embed.corrected_domains`) repairing OCR rot in a 308-domain
catalog extracted from scanned source texts.

## The trap: hand-editing extractor output

The extracted catalog had glued words ("mysteriof"), two-column OCR
interleaves, truncated clauses, and citation fragments. The obvious fix —
edit the catalog JSON — is a time bomb: the next extractor run silently
resurrects every defect, and until then nobody can tell hand-repairs from
extractor output, so the extractor can never be trusted or improved against
its own artifact. The failure is worse when the extractor is currently
un-runnable (missing fixture): the artifact quietly becomes source, and the
day the input reappears, a rebuild destroys months of invisible repairs.

## The pattern: a reviewable overlay applied at consumption time

- All repairs land in one hand-reviewed overlay file
  (`data/corrections.json`): per-record field replacements, `null` to remove
  a field, with a `_doc` header stating the rule and citing repair sources.
- Every consumer reads through one function
  (`corrected_domains()` = load artifact → merge secondary sources →
  apply overlay → normalize) so there is exactly one definition of
  "the catalog as shipped."
- The artifact itself stays byte-identical to extractor output. Re-extraction
  is always safe; the overlay re-applies on top.
- Repairs cite their evidence (the recovered ARAS sentence, the de Vries
  entry) so an overlay diff is reviewable as a claim, not a whim.

## Bonus rule discovered the same day

Mechanical normalizations that encode a *rule* (slash spacing in titles)
belong in the apply function as code, not as N overlay entries — the overlay
is for content judgments, code is for conventions.

## Prevention

- If you find yourself editing a generated file, stop and build the overlay
  channel first; it is ~40 lines.
- The overlay applies at pack/build time, not via a one-shot migration
  script — one-shots drift from reality the first time upstream changes.

Related: [`2026-08-19-ratchet-baseline-lint-adoption.md`](2026-08-19-ratchet-baseline-lint-adoption.md)
— the gate that finds what the overlay then fixes.
