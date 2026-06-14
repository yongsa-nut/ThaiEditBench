"""Bake the EditingBench model-error visualization (single self-contained HTML).

Reads the run sample + every results/<alias>.jsonl and, **using the same
`grader.align_edits` the scorer uses**, computes per-item per-model verdicts
(each gold edit fixed / detected-not-fixed / missed, plus the model's spurious
over-edits) with char offsets for highlighting. Bakes it all into `viz.html`.

Faithfulness: gold and system edits are both derived by aligning `text_wrong`
against their target, so they live in one TCC coordinate system and the
fixed/missed verdicts match `score_runs.py`'s correction/detection counts exactly.

  PYTHONUTF8=1 python build_viz.py                       # split test_public, n=819, all run files
  PYTHONUTF8=1 python build_viz.py --n 16 --models gpt55-med typhoon25
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDIT = HERE.parent
sys.path.insert(0, str(EDIT))                       # grader.py / inject.py live one level up

from grader import align_edits                       # noqa: E402
from inject import normalize, tcc_segments           # noqa: E402
from variants import reconcile_variants               # noqa: E402

RESULTS = EDIT / "results"
TEMPLATE = HERE / "viz.html"
# Matches the BAKED assignment line whether it's the pristine placeholder
# (`const BAKED = null; ...`) or a previous bake (`const BAKED = {…};`) — so the
# single viz.html is its own re-bakeable template (json.dumps emits one line).
BAKED_RE = re.compile(r"^const BAKED = .*$", re.M)


# ---------------------------------------------------------------- geometry ---
def char_offsets(segs: list[str]) -> list[int]:
    """offs[i] = char start of TCC index i (offs[len] = total length)."""
    offs = [0]
    for s in segs:
        offs.append(offs[-1] + len(s))
    return offs


def class_of(item: dict, tcc_start: int, tcc_end: int) -> tuple[int, str]:
    """Mechanism class of a derived edit via TCC-span containment in the stored
    edits (mirrors grader.per_class_recall.class_of)."""
    for s in item["edits"]:
        if s["tcc_start"] <= tcc_start and tcc_end <= s["tcc_end"]:
            return s["class"], s.get("class_name", "")
        if tcc_start == tcc_end and s["tcc_start"] <= tcc_start <= s["tcc_end"]:
            return s["class"], s.get("class_name", "")
    return 0, ""


def gold_minimal(item: dict) -> tuple[list, list, list[int]]:
    """Minimal gold edits (the units the grader scores) with src char spans + class.
    Returns (gold_edits, gold_min_records, offs)."""
    wrong_n = normalize(item["text_wrong"])
    segs = tcc_segments(wrong_n)
    offs = char_offsets(segs)
    gold = align_edits(item["text_wrong"], item["text_correct"])
    recs = []
    for e in gold:
        cls, cname = class_of(item, e.start, e.end)
        recs.append({
            "src_cstart": offs[e.start], "src_cend": offs[e.end],
            "src_text": "".join(segs[e.start:e.end]), "correct": e.repl,
            "class": cls, "class_name": cname,
        })
    return gold, recs, offs


def analyze(item: dict, gold, offs: list[int], output: str) -> dict:
    """Verdict of one model output against the gold edits, in grader terms.

    statuses[i] ∈ fixed|detected|missed aligned to `gold`; out_marks paint the
    (normalized) model-output string: green=fixed, orange=over-edit, red=missed.
    """
    # accept standard spelling variants (สิทธิ~สิทธิ์); empty = no-op (recall 0)
    sys_text = reconcile_variants(output, item["text_correct"]) if output else item["text_wrong"]
    out_n = normalize(sys_text)
    sysd = align_edits(item["text_wrong"], sys_text)

    cor_pool = Counter((e.start, e.end, e.repl) for e in sysd)
    det_pool = Counter((e.start, e.end) for e in sysd)

    statuses = []
    for e in gold:
        ck, dk = (e.start, e.end, e.repl), (e.start, e.end)
        fixed = cor_pool.get(ck, 0) > 0
        if fixed:
            cor_pool[ck] -= 1
        det = det_pool.get(dk, 0) > 0
        if det:
            det_pool[dk] -= 1
        statuses.append("fixed" if fixed else ("detected" if det else "missed"))

    # output-side spans: delta-remap of sys edits over the (normalized) wrong string.
    fixed_keys = Counter((e.start, e.end, e.repl) for e in gold)
    out_marks, delta = [], 0
    for e in sorted(sysd, key=lambda x: x.start):
        out_start = offs[e.start] + delta
        out_end = out_start + len(e.repl)
        delta += len(e.repl) - (offs[e.end] - offs[e.start])
        key = (e.start, e.end, e.repl)
        is_fixed = fixed_keys.get(key, 0) > 0
        if is_fixed:
            fixed_keys[key] -= 1
        out_marks.append([out_start, out_end, "fixed" if is_fixed else "over"])

    # missed gold edits still sit (unchanged) in the output → mark red at their
    # remapped output position (shift by the deltas of sys edits that precede them).
    for e, st in zip(gold, statuses):
        if st != "missed":
            continue
        d = 0
        for s in sorted(sysd, key=lambda x: x.start):
            if s.start >= e.end:
                break
            if s.end <= e.start:
                d += len(s.repl) - (offs[s.end] - offs[s.start])
        ms = offs[e.start] + d
        out_marks.append([ms, ms + (offs[e.end] - offs[e.start]), "missed"])

    out_marks.sort()
    return {"output": out_n, "exact": out_n == normalize(item["text_correct"]),
            "statuses": statuses, "out_marks": out_marks}


# --------------------------------------------------------------- left panel ---
def correct_marks(item: dict) -> list:
    """Remap stored edit spans onto text_correct (delta-aware; mirrors annotate.html
    correctRanges)."""
    order = sorted(item["edits"], key=lambda e: e["char_start"])
    delta, marks = 0, []
    for e in order:
        s = e["char_start"] + delta
        en = s + len(e["correct"])
        marks.append([s, en, e["class"]])
        delta += len(e["correct"]) - (e["char_end"] - e["char_start"])
    return sorted(marks)


def wrong_marks(item: dict) -> list:
    out = []
    for e in item["edits"]:
        out.append([e["char_start"], e["char_end"], e["class"], e.get("class_name", "")])
    return sorted(out)


# ------------------------------------------------------------------- build ---
def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def build(split: str, n: int, models: list[str] | None):
    sample = RESULTS / f"_sample_{split}_{n}.jsonl"
    if not sample.exists():
        raise SystemExit(f"no sample {sample.name} — run run_editing.py for this split/n first")
    items_raw = load_jsonl(sample)

    run_files = {p.stem: p for p in RESULTS.glob("*.jsonl") if not p.name.startswith("_")}
    aliases = [m for m in (models or sorted(run_files)) if m in run_files]
    if not aliases:
        raise SystemExit("no matching results/<alias>.jsonl files to visualize")
    outputs_by_model = {a: {r["id"]: r for r in load_jsonl(run_files[a])} for a in aliases}

    items, outputs = [], {a: {} for a in aliases}
    for it in items_raw:
        gold, gmin, offs = gold_minimal(it)
        items.append({
            "id": it["id"], "register": it.get("register", ""),
            "density": it.get("density", ""), "n_errors": it.get("n_errors", len(it["edits"])),
            "text_wrong": it["text_wrong"], "text_correct": it["text_correct"],
            "wrong_marks": wrong_marks(it), "correct_marks": correct_marks(it),
            "edits": [{"wrong": e["wrong"], "correct": e["correct"],
                       "class": e["class"], "class_name": e.get("class_name", "")}
                      for e in it["edits"]],
            "gold_min": gmin,
        })
        for a in aliases:
            rec = outputs_by_model[a].get(it["id"])
            if rec is None:
                continue
            outputs[a][it["id"]] = analyze(it, gold, offs, rec.get("output") or "")

    baked = {"split": split, "n": n, "models": aliases, "items": items, "outputs": outputs}
    return baked, aliases


def main():
    global RESULTS
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="test_public")
    ap.add_argument("--n", type=int, default=819)
    ap.add_argument("--models", nargs="+", default=None, help="default: every results/<alias>.jsonl")
    ap.add_argument("--results", default="results", help="results dir (e.g. results_t2 / results_t3 for the paragraph/page tiers)")
    ap.add_argument("--out", type=Path, default=HERE / "viz.html")
    args = ap.parse_args()
    RESULTS = EDIT / args.results

    baked, aliases = build(args.split, args.n, args.models)
    tpl = TEMPLATE.read_text(encoding="utf-8")
    if not BAKED_RE.search(tpl):
        raise SystemExit("viz.html has no `const BAKED = …;` line to replace")
    js = json.dumps(baked, ensure_ascii=False).replace("</", "<\\/")
    # function replacement: avoids re backslash/group interpretation in the JSON payload
    html = BAKED_RE.sub(lambda _m: f"const BAKED = {js};", tpl, count=1)
    args.out.write_text(html, encoding="utf-8")
    n_pairs = sum(len(outputs) for outputs in baked["outputs"].values())
    print(f"baked {len(baked['items'])} items × {len(aliases)} models "
          f"({n_pairs} graded outputs) -> {args.out}")
    print(f"  models: {', '.join(aliases)}")


if __name__ == "__main__":
    main()
