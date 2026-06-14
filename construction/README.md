# Dataset-construction provenance

These are the upstream scripts that built the confusion set, the clean-corpus
catalog, and the error-corpus inventory. They are included for transparency and
reproducibility; the **shipped dataset** (`../data/`) is the product, and the
day-to-day construction/grading code lives at the repository root.

The two taxonomy modules used at construction time — `phase1/classify.py`
(6-class mechanism classifier) and `phase2/edit_op.py` (edit-operation tagger) —
are mirrored at the repository root, where the runtime grader/injector import
them. The copies are identical; the root copies are canonical for the harness.

```
phase1/   error-corpus inventory + the mechanism classifier
  classify.py            6-class orthographic classifier (also at repo root)
  build_inventory.py     assemble the tagged error-pair inventory
  validate_classifier.py classifier validation
  scrape_wiktionary.py   borrowed-terms categories → loanword evidence
  realword_pairs.py vistec_extract.py deaf_extract.py extract_botfix_html.py
  make_html.py make_sample.py wiki_pilot.py

phase2/   confusion set + loan lexicon
  edit_op.py             edit-operation tagger (also at repo root)
  build_confusion_set.py assemble the 1,044-pair confusion set
  build_loan_lexicon.py  class-6 loanword lexicon (etymology oracle)
  confusion_stats.py     coverage / balance stats

phase3/   clean-corpus catalog
  probe_corpora.py       live-probe candidate corpora for cleanliness/licensing
```

## Running them

Several steps require **licensed or large raw inputs that are not
redistributed** (e.g. the VISTEC corpus, the Wikipedia cleanup-bot history
dumps). Place such inputs under `../data/raw/` to re-run those steps. Steps that
only call public APIs (Wikipedia, Wiktionary, the HuggingFace dataset-viewer)
run as-is; they send a descriptive `User-Agent` (anonymized in this release —
set your own contact before any heavy crawling).

The end-to-end construction pipeline (root-level scripts, after the confusion set
and clean corpus exist) is documented in [`../docs/HARNESS.md`](../docs/HARNESS.md).
