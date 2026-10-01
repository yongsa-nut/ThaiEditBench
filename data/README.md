# ThaiEditBench data

Character-level Thai orthographic error-correction items. One JSON object per
line; each is a test item with an erroneous `text_wrong`, a gold `text_correct`,
and a typed list of `edits`. The full record contract — every field, the edit
object, and the construction invariants — is in
[`../docs/schema.md`](../docs/schema.md).

## Files

### Evaluation splits and length tiers

| file | items | what |
|---|--:|---|
| `items_train.jsonl` | 249 | synthetic; for tuning prompts/baselines |
| `items_dev.jsonl` | 606 | synthetic; development |
| `items_test_public.jsonl` | 774 | **T1 sentence tier**, public |
| `items_test_private.jsonl` | 868 | held-out: synthetic + 40 Wikipedia-mined; lowest memorization risk |
| `items_t2.jsonl` | 224 | **T2 paragraph tier** (multi-sentence) |
| `items_t3.jsonl` | 122 | **T3 page tier** (page-length) |

The public test / T2 / T3 tiers were trimmed by the same automatic cross-model
consensus audit (mainly residual source typos and non-standard source spellings;
45 / 26 / 28 items dropped respectively; reports in `../viz/audit-review-t1.md`
and `../viz/audit-review-t2t3.md`). The audit method is described in the paper's
Appendix B, and the tooling lives in [`../viz/`](../viz/) (`audit_golds.py`,
`apply_audit_drops.py`).

### Construction inputs and intermediates

| file | what |
|---|---|
| `confusion-set.jsonl` | 1,044 canonical wrong→correct pairs × 6 classes (with etymology + edit-op tags) |
| `synthetic_pool.jsonl` | full synthetic backbone before splitting (gold exact by construction) |
| `wiki_filtered_pairs.jsonl` | RID-gated clean pairs mined from cleanup-bot edit history |
| `wiki_items.jsonl` | curated, class-balanced mined ship set (~40) |
| `wiki_items_all.jsonl` | full mined sentence-level set (103) |
| `items_wiki.jsonl` | the same 103 items under the name the harness uses (`--split wiki`); the paper's natural-error set is the 87 left after the consensus audit (`analysis/natural_eval.py`) |
| `memorization.json` | per-source verbatim-recall scores used to route low-memorization text to the held-out test split |
| `excluded.jsonl` | items removed during construction/audit, with reasons |

Not shipped (regenerable, or licensed): `data/raw/` (licensed raw inputs — e.g.
VISTEC, cleanup-bot dumps), `data/clean_cache/` (cached HuggingFace pulls),
`data/wiki_raw_pairs.jsonl` (large mining intermediate). See
[`../construction/README.md`](../construction/README.md) to reproduce them.

## The six-class mechanism taxonomy

| class | name | mechanism |
|---|---|---|
| 1 | tone mark | wrong/missing/spurious tone mark (วรรณยุกต์) |
| 2 | consonant pair | homophonous consonant confusion (ส/ศ/ษ, ค/ฆ, …) |
| 3 | ตัวการันต์ | silenced-consonant marker (การันต์) errors |
| 4 | vowel | vowel-form confusion (incl. short/long, สระ placement) |
| 5 | cluster / metathesis | consonant-cluster or character-order errors |
| 6 | loanword transliteration | inconsistent transliteration of contemporary loanwords |

An **etymology tag** (`native` / `loan` / `proper-noun`) accompanies each edit;
the **loanword-absorption rule** restricts class 6 to *contemporary* foreign
loans (long-integrated borrowings are treated as native). Details and worked
examples: [`../docs/confusion-set.md`](../docs/confusion-set.md) and
[`../docs/taxonomy.html`](../docs/taxonomy.html).

## Provenance & licensing

Items derive from permissive-redistribution corpora only: **thaisum** (news, MIT),
**Thai Wikipedia** (encyclopedic, CC BY-SA, dated snapshot), **Royal Gazette /
Constitution** and **thaigov** (legal/gov, CC0/public domain). Mined items are
from Thai Wikipedia (CC BY-SA). The dataset is released under **CC BY-SA 4.0**
(inheriting share-alike from Wikipedia). Each item also carries its own
source-`license` field. The academic register is a documented gap (no permissive
source). Catalog: [`../docs/corpus-catalog.md`](../docs/corpus-catalog.md).
