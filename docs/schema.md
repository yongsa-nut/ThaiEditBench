# ThaiEditBench Item Schema (v1)

The contract for every dataset record in `data/items_*.jsonl`. One JSON object
per line = one **sentence-level** test item. This is the interface the Phase-7
TCC grader and the Phase-8 model harness consume — keep it stable.

```json
{
  "id": "syn-000123",
  "source_track": "synthetic",
  "register": "news",
  "source_doc": "thaisum#12345",
  "lang": "th",
  "text_wrong":   "นักวิทยาศาสตร์สังเกตุปรากฏการณ์ทางธรรมชาติ",
  "text_correct": "นักวิทยาศาสตร์สังเกตปรากฏการณ์ทางธรรมชาติ",
  "edits": [
    {
      "tcc_start": 7, "tcc_end": 11,
      "char_start": 14, "char_end": 21,
      "wrong": "สังเกตุ", "correct": "สังเกต",
      "class": 4, "class_name": "vowel",
      "etymology": "native", "edit_op": "insertion"
    }
  ],
  "n_errors": 1,
  "density": "single",
  "gold_source": "construction",
  "verified": false,
  "license": "MIT",
  "split": "train"
}
```

## Fields

| field | type | meaning |
|---|---|---|
| `id` | str | stable id; prefix `syn-` (synthetic) / `wik-` (mined) |
| `source_track` | enum | `synthetic` \| `mined` |
| `register` | enum | `news` \| `encyclopedic` \| `legal` \| `gov` |
| `source_doc` | str | provenance: `thaisum#<row>`, `thwiki:rev/<to>←<from> (article_id=<id>)`, … |
| `lang` | str | `th` (v1 is Thai-script only) |
| `text_wrong` | str | **model input** — the sentence containing the error(s). NFC-normalized |
| `text_correct` | str | gold corrected sentence. NFC-normalized |
| `edits` | list | one object per error (see below). Empty list ⇒ no-error item (none in v1) |
| `n_errors` | int | `len(edits)` |
| `density` | enum | `single` (1 error) \| `multi` (≥2) |
| `gold_source` | enum | `construction` (synthetic, gold is exact) \| `annotated` (mined, gold from human pass) |
| `verified` | bool | set true after Phase-5 spot-verify (synthetic) / 3-annotator pass (mined) |
| `license` | enum | inherited from source: `MIT` \| `CC BY-SA` \| `CC0` \| `PD` |
| `split` | enum | `train` \| `dev` \| `test_public` \| `test_private` |

## Edit object

| field | type | meaning |
|---|---|---|
| `tcc_start`, `tcc_end` | int | **half-open TCC-index span** in `text_wrong` (`pythainlp.tokenize.tcc`). The primary grading unit (§7) |
| `char_start`, `char_end` | int | half-open Unicode-char span in `text_wrong` (convenience / reconstruction) |
| `wrong` | str | the erroneous surface form occupying the span |
| `correct` | str | the gold replacement |
| `class` | int 1–6 | mechanism class (§4): 1 tone · 2 consonant-pair · 3 การันต์ · 4 vowel · 5 cluster · 6 loanword |
| `class_name` | str | human-readable class name |
| `etymology` | enum | `native` \| `loan` \| `proper-noun` (§5) |
| `edit_op` | enum | `substitution` \| `insertion` \| `deletion` \| `transposition` \| `mixed` |

## Invariants (enforced by `test_inject.py`)

1. **Round-trip:** `apply_edits(text_wrong, edits) == text_correct`.
2. **TCC alignment:** `"".join(tcc_segments(text_wrong)[e.tcc_start:e.tcc_end]) == e.wrong` for every edit.
3. **Char alignment:** `text_wrong[e.char_start:e.char_end] == e.wrong`.
4. **Non-overlap:** edits within an item are disjoint and ascending.
5. **Boundary-safe origin:** every synthetic error replaces a whole newmm token-run
   (never a substring inside a word), so short forms (`ก็`, `นะ`) never corrupt
   embedding words.

## Notes

- v1 is **context-independent** (RID-verifiable): every `wrong` form is wrong out of
  context. Context-dependent confusions were routed to v2 in Phase 1.
- `text_correct` is the NFC-normalized clean source sentence with the two Phase-3
  surface variations repaired (`◌ํ+า → ำ`, `เเ → แ`) so the injected error is the
  *only* deviation from RID-correct orthography.
