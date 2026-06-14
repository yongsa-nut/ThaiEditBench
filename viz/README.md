# EditingBench — Model Error Viewer

A zero-install single-HTML viewer to inspect, error-by-error, how each model's Thai
spelling corrections compare to the gold answer. Left panel = ground truth; right
panel = a chosen model (dropdown), with a **compare-all** toggle that shows every
model's verdict for the current item.

```
build_viz.py   bake the run sample + every results/<alias>.jsonl into viz.html
viz.html       the viewer (vanilla JS, opens offline; items baked in)
```

## Build

```powershell
# from the editing/ directory
PYTHONUTF8=1 python viz/build_viz.py                       # split test_public, n=819, all run files
PYTHONUTF8=1 python viz/build_viz.py --n 16 --models gpt55-med typhoon25
#   --split test_public  --n 819  --models <a b …>(default: every results/*.jsonl)  --out viz/viz.html
```

The baker reads `results/_sample_<split>_<n>.jsonl` (the exact items models saw) plus
each `results/<alias>.jsonl`, then **derives every verdict with the same
`grader.align_edits` the scorer uses** — so the highlights are grading-consistent, not
a separate heuristic. Open `viz/viz.html` in any browser (no server, no network).

## What you see

**Left — ground truth**
- *input (errors):* `text_wrong` with each error span marked **yellow**.
- *gold correction:* `text_correct` with each corrected token marked **green**.
- a `wrong → correct (class)` chip per stored error.

**Right — model output** (dropdown to swap models)
- the model's output, highlighted: **green** = matches the gold correction (fixed),
  **red** = a gold edit left unfixed (error still present), **orange** = an over-edit
  (a change the model made that the gold did not).
- a verdict list, one row per *minimal scored edit*: `✓ fixed` / `◐ detected (wrong
  fix)` / `✗ missed`, with its mechanism class. An `exact ✓ / not exact` badge.

**Compare all** (toggle or press `c`) — a table of every model's exact-match flag and
per-error ✓/◐/✗ row for the current item, so you can scan disagreement at a glance.

**Filters** — by mechanism class (1–6), density (single/multi), free-text search, and
**"only items this model got wrong"** (hides items the selected model nailed) — the
fast path to the model's actual failures.

Keys: `←`/`→` prev/next item · `c` compare-all.

## Faithfulness

Verdicts are computed exactly like `score_runs.py`: gold and system edits are both
derived by aligning `text_wrong` against their target (`align_edits`), so they share
one TCC coordinate system. `✓ fixed` count == correction true-positives and
`✓+◐` == detection true-positives for that item (verified against the grader). The
mechanism class shown is the stored class of the edit that contains the derived span.

## Re-baking

Re-run `build_viz.py` after new model runs land in `results/`. The viewer is regenerated
in place; just refresh the browser. Models with no run file for the current split/n are
omitted; items a model has no output for show "no run for this model on this item".
