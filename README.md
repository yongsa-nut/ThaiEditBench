# ThaiEditBench

A mechanism-typed, length-stratified benchmark for **Thai character-level
orthographic error correction**.

Thai is written without word boundaries and layers tone marks, silenced
consonants (ตัวการันต์), and heavy loanword transliteration onto a Brahmic
script, producing orthographic error mechanisms unlike those targeted by English
GEC or Chinese spelling check. ThaiEditBench provides:

1. a principled **six-class mechanism taxonomy** plus an etymology tag;
2. **three length tiers** — sentence / paragraph / page — that isolate robustness
   to long, mostly-clean context;
3. **contamination-robust construction** — errors are *injected* into novel clean
   text and *mined* from Thai-Wikipedia cleanup-bot history, screened by a
   memorization probe. Gold corrections are exact by construction, and a blind
   two-annotator study measures how reliably the mechanism labels can be applied
   (Krippendorff's α = 0.75).

Grading is at **Thai Character Cluster (TCC)** level with ERRANT-style span
matching (detection / correction F1, plus per-mechanism span-F0.5, word-level
GLEU, and a clean-sentence *fidelity* signal). The accompanying paper evaluates
16 models and reports three findings: (1) under the benchmark's conditions,
models that locate an error almost always fix it correctly, so what separates
them is *detection*; (2) the evaluated Thai-specialized models do not lead the
strongest general models; and (3) long, mostly-correct context exposes
**over-edit accumulation** and clean-text fidelity failures that sentence-level
evaluation hides. On real errors mined from Wikipedia edit history, the model
ranking transfers (Spearman ρ = 0.92 with the sentence tier).

**Paper:** Nutchanon Yongsatianchot, Piyalitt Ittichaiwong, and Kanyakorn
Veerakanjana. *ThaiEditBench: A Mechanism-Typed, Length-Stratified Benchmark for
Thai Orthographic Error Correction.* AACL-IJCNLP 2026. PDF and LaTeX sources:
[`paper/`](paper/).

```bibtex
@inproceedings{yongsatianchot-etal-2026-thaieditbench,
  title     = {{ThaiEditBench}: A Mechanism-Typed, Length-Stratified Benchmark for
               {Thai} Orthographic Error Correction},
  author    = {Yongsatianchot, Nutchanon and Ittichaiwong, Piyalitt and
               Veerakanjana, Kanyakorn},
  booktitle = {Proceedings of AACL-IJCNLP 2026},
  year      = {2026}
}
```

## Repository layout

```
.
├── grader.py            TCC-level detection/correction F1, sentence accuracy, GLEU, bootstrap CI
├── therrant.py          ThERRANT — ERRANT-style edit-typer for the 6 orthographic classes
├── score_runs.py        grade model run files → summary + per-class recall + ChERRANT span-F0.5
├── run_editing.py        model harness (Typhoon / OpenAI / Anthropic / OpenRouter / gateway; resume-safe)
├── error_analysis.py    per-tier failure decomposition (detection vs over-edit, by class/register)
├── inject.py            core error injection (whole-token-run match + TCC gold spans)
├── inject_dataset.py    pull + normalize + filter + stratified inject → synthetic pool
├── mine_wiki.py         harvest typo fixes from a Wikipedia cleanup bot's edit history
├── filter_diffs.py      RID-gate + classify + rebuild + curate mined pairs
├── build_dataset.py     dedup + class-balanced, memorization-routed split
├── build_t2.py          assemble the paragraph (T2) and page (T3) tiers
├── classify.py          6-class orthographic mechanism classifier
├── edit_op.py           edit-operation tagger (sub / ins / del / transpose)
├── variants.py spellcheck.py memorization_probe.py   supporting utilities
├── test_*.py            unit tests (grader / inject / therrant)
│
├── data/                dataset splits, length tiers, confusion set   → see data/README.md
├── results/             16-model run outputs — T1 (sentence) tier
├── results_t2/          16-model run outputs — T2 (paragraph) tier
├── results_t3/          16-model run outputs — T3 (page) tier
├── results_wiki/        16-model run outputs — natural errors mined from Wikipedia
├── results_prompt_en/   prompt ablation: English instruction (T1, two models)
├── results_prompt_fewshot/  prompt ablation: Thai instruction + 2 examples (T1, two models)
├── analysis/            ties, CIs, natural-error audit, span check, paired tests  → see below
├── viz/                 leaderboard, error-visualizer, gold-audit tooling
├── annotation/          blind label study: sheets, both raters' labels, Krippendorff α scorer
├── construction/        dataset-construction provenance scripts (phases 1–3)   → see construction/README.md
├── docs/                schema, taxonomy, corpus catalog, harness details
└── paper/               the paper: PDF, LuaLaTeX sources, figure
```

## Install

Python ≥ 3.10.

```bash
pip install -r requirements.txt
```

Core grading/construction needs only `pythainlp`, `requests`, and `matplotlib`.
The model harness additionally needs `openai` and/or `anthropic` (lazy-imported,
only when you actually run models).

## Quickstart

**Run the tests** (no network, no keys):

```bash
PYTHONUTF8=1 python test_grader.py
PYTHONUTF8=1 python test_inject.py
PYTHONUTF8=1 python test_therrant.py
```

**Grade the shipped model runs** (re-derives every number in the paper):

```bash
PYTHONUTF8=1 python score_runs.py --split test_public --n 819                       # T1 sentence
PYTHONUTF8=1 python score_runs.py --split t2 --n 223 --results results_t2           # T2 paragraph
PYTHONUTF8=1 python score_runs.py --split t3 --n 124 --results results_t3           # T3 page
PYTHONUTF8=1 python error_analysis.py                                               # failure decomposition
```

**Natural errors, ties, and checks behind the paper's tables** (no network, no keys):

```bash
PYTHONUTF8=1 python score_runs.py --split wiki --n 103 --results results_wiki --report results_wiki/report.md   # natural set, all items
PYTHONUTF8=1 python analysis/natural_eval.py      # consensus audit (103 -> 79) + natural results (Sec. 5.5, App. F)
PYTHONUTF8=1 python analysis/leaderboard_ties.py  # CIs and paired ties with the column best (Table 1, App. D)
PYTHONUTF8=1 python analysis/paired_bootstrap.py  # pairwise comparisons quoted in Sec. 5.1
PYTHONUTF8=1 python analysis/span_check.py        # exact-span check on the outcome decomposition (Sec. 5.2)
PYTHONUTF8=1 python annotation/score_annotation.py --labels annotation/labels_ann1.json \
    annotation/labels_ann2.json --alpha-set annotation/alpha_set_blind.jsonl   # label study (Sec. 3.7, App. E)
```

Precomputed outputs are in `analysis/out/`.

**Rebuild the leaderboard and the degradation figure:**

```bash
PYTHONUTF8=1 python viz/build_leaderboard.py     # → viz/leaderboard.html
PYTHONUTF8=1 python viz/plot_degradation.py      # → paper/fig1-degradation.{png,pdf}
```

**Evaluate a new model.** Copy `.env.example` to `.env`, fill in the keys for the
providers you want, then:

```bash
PYTHONUTF8=1 python run_editing.py --models gpt55-med --split test_public --n 819
PYTHONUTF8=1 python score_runs.py  --split test_public --n 819
```

Run `python run_editing.py --help` for the full model registry and flags
(`--workers` for parallelism, `--results` to isolate a tier, `--smoke` for a
16-item triage pass).

## The dataset

| split / tier | file | items | what |
|---|---|--:|---|
| train | `data/items_train.jsonl` | 249 | synthetic |
| dev | `data/items_dev.jsonl` | 606 | synthetic |
| **test (public, T1)** | `data/items_test_public.jsonl` | 795 | sentence tier |
| held-out test | `data/items_test_private.jsonl` | 868 | synthetic + 40 mined; lowest memorization; not evaluated in the paper |
| **natural errors** | `data/items_wiki.jsonl` | 103 | real errors mined from Wikipedia; 79 after the consensus audit |
| **T2 paragraph** | `data/items_t2.jsonl` | 223 | multi-sentence |
| **T3 page** | `data/items_t3.jsonl` | 124 | page-length |

Item schema, the six-class taxonomy, the loanword-absorption rule, and full
provenance/licensing are documented in [`data/README.md`](data/README.md) and
[`docs/`](docs/). Construction is reproducible from the scripts in
[`construction/`](construction/) (some steps require licensed raw inputs that are
not redistributed — see that README).

## The paper

The camera-ready PDF is [`paper/acl_paper.pdf`](paper/acl_paper.pdf); the LuaLaTeX
sources are in [`paper/`](paper/) (see its README to compile).

## License

- **Code** — MIT (see [`LICENSE`](LICENSE)).
- **Data** — CC BY-SA 4.0. Items derive from permissive-redistribution sources
  (thaisum, MIT; Thai Wikipedia, CC BY-SA; Royal Gazette / Constitution and
  thaigov, CC0/public domain) and inherit the share-alike term from Wikipedia.
  Per-source provenance is in [`data/README.md`](data/README.md).
