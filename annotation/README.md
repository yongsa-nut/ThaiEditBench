# EditingBench — Phase 5 Annotation Toolchain (Track 1 · Subtask 2)

A zero-install browser tool + sampler/bundler + scorer for the human
**α-calibration** pass. Annotators open one HTML file, confirm/override each spelling
fix, download a `labels_<id>.json`, and email it back; the scorer computes
**Krippendorff's α per mechanism class** and emits a consensus `gold.json`.

```
build_sheets.py     sample the α-set (40 mined + class-balanced synthetic top-up) + bake per-annotator HTML
annotate.html       the tool (vanilla JS, no install, autosave/resume, Export → labels_<id>.json)
score_annotation.py ingest labels → per-class α + consensus gold.json + disagreement report
alpha_set.jsonl     the exact baked set (build output; the scorer reads this)
dist/annotate_<id>.html   one self-contained file per annotator (build output)
gold.json           consensus gold (score output)
```

## The α-set (what gets annotated and why)

- **40 mined items** (real BotKung Wikipedia typo-fixes, `gold_source:"annotated"`) —
  the gold is *uncertain*, so these get the full 3-annotator pass.
- **Class-balanced synthetic top-up** (~80 items) — the mine covers classes 1–4 well
  but **cluster = 5 and loanword = 0**, so we add single-error synthetic items to reach
  **~20 units/class for all 6 classes**. Synthetic gold is construction-exact; labeling
  them with 3 annotators validates the taxonomy + construction with real agreement
  (this replaces a separate single-reviewer spot-verify).

Only single-error items are sampled, so each item contributes cleanly to one class.

## What an annotator does

Per sentence the tool shows the **misspelled input** (yellow span) and the
**gold correction** (green span). For each error, confirm or override:

1. **Real orthographic error?** ✓ ใช่ / ✗ ไม่ใช่ — reject stylistic/factual changes.
2. **Mechanism class (1–6)** — pre-filled with our auto-guess (keys `1`–`6`).
3. **Etymology** — native / loan / proper-noun.
4. **Edit op** — substitution / insertion / deletion / transposition / mixed.

class/etymology/edit_op are **pre-filled**; the annotator just confirms unless they
disagree. Work autosaves to the browser (`localStorage`); they can close and resume.
Keys: `1`–`6` class · `y`/`n` accept · `←`/`→` navigate. **Nothing is uploaded** until
they click **Export labels** → downloads `labels_<id>.json`.

## Run it

```powershell
# 1. Build (one HTML per annotator; 3 annotators all label the SAME set — required for α)
PYTHONUTF8=1 python build_sheets.py --annotators ann1 ann2 ann3
#    options: --per-class 20  --pools test_public dev  --seed 20260524  --out dist

# 2. Email each annotator their one dist/annotate_<id>.html. They Export → labels_<id>.json, email back.

# 3. Drop the returned files here, then score (≥2 required):
PYTHONUTF8=1 python score_annotation.py --labels labels_ann1.json labels_ann2.json labels_ann3.json
#    --threshold 0.70 (default) · --selftest to validate the scorer
```

The scorer prints: headline multiclass α vs the **0.70 gate**, per-class α + agreement,
consensus tier counts, and a disagreement report ordered for the adjudicator
(`adjudicate` → dropped/bad-injection → `majority`, mined first). It writes `gold.json`.

## Reading the output

- **headline α** — the labeling-reliability number to report against ≥0.70.
- **per-class one-vs-rest α** — *prevalence-sensitive* (the balanced 20/class set has
  ~100 negatives per class, so it runs high); read it alongside **agreement** = the
  pairwise class-match rate on items whose construction class is that class.
- **consensus** ∈ `unanimous` / `majority` / `adjudicate` (3-way split → senior
  adjudicator decides) / `dropped_not_error` (mined, ≥2 reject) / `bad_injection`
  (synthetic, ≥2 reject — a construction-quality flag).
- **class_mismatch** (synthetic only) — consensus class ≠ construction class; a
  taxonomy/construction disagreement to review.

## Caveats

- **Loanword (class 6) units are all synthetic** — the BotKung mine has zero loanword
  fixes. Its α validates the *taxonomy*, not the mine's loanword coverage.
- **Class-name string:** the data uses `loanword_translit` for class 6; the tool keys
  on the numeric class (1–6) and displays "ทับศัพท์ / loanword".

## Out of scope

Applying `gold.json` back into `data/items_test_private.jsonl` (a separate apply step
the user runs after adjudication — sets `verified:true`, updates `class` for mined
items). Subtask 1 calibration (separate tool in `prosody/calibration/`). The
production SEA-HELM 8-run × 30-bootstrap model matrix.
