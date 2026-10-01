"""Error-analysis breakdown for EditingBench — beyond the leaderboard.

Dissects *how* models fail, not just how much. Reuses the grader's exact
`align_edits` + matching + `variants.reconcile_variants`, so every number here is
consistent with `score_runs.py`. Reproducible by construction: it reads the
CANONICAL post-audit items (`data/items_<split>.jsonl`) and grades whatever
`<results_dir>/<alias>.jsonl` outputs exist — so re-running after more models /
the T3 tier finish just folds them in. Partial runs are reported with coverage.

For each gold edit a model faces it assigns one outcome —
  fixed         right span + right replacement   (correction TP)
  wrong_corr    right span, wrong replacement     (detection TP, correction FN)
  missed        span never touched                (detection FN)
— plus over_edit = a system edit at a span with no gold edit (spurious; the
over-editing / precision signal that dominates the long-context tiers).

Sections per tier: coverage+headline · failure decomposition (missed vs
miscorrected vs over-edit) · per-class outcome split · cross-model item hardness
(universally-missed items = paper hard-cases AND gold-audit candidates) ·
over-edit catalogue · register effect · miscorrection examples per class.

  PYTHONUTF8=1 python error_analysis.py                 # all tiers that have data
  PYTHONUTF8=1 python error_analysis.py --tiers T1 T2   # subset
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from grader import align_edits, score_sentence_accuracy
from inject import normalize, tcc_segments
from variants import reconcile_variants

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CLASS_NAME = {0: "(unmapped)", 1: "tone", 2: "consonant", 3: "การันต์",
              4: "vowel", 5: "cluster", 6: "loanword"}

# (label, results subdir, split, expected n) — mirrors build_leaderboard.TIERS.
# Re-run picks up whatever exists; T3 folds in automatically once it has data.
TIERS = [("T1", "results", "test_public", 774),
         ("T2", "results_t2", "t2", 224),
         ("T3", "results_t3", "t3", 122)]


def span_text(wrong: str, start: int, end: int) -> str:
    """Source TCCs covered by a TCC-index span (for human-readable edits)."""
    segs = tcc_segments(normalize(wrong))
    return "".join(segs[start:end]) if end > start else "∅"


def class_map(stored: list[dict]):
    def class_of(e):
        for s in stored:
            if s["tcc_start"] <= e.start and e.end <= s["tcc_end"]:
                return s["class"]
            if e.start == e.end and s["tcc_start"] <= e.start <= s["tcc_end"]:
                return s["class"]
        return 0
    return class_of


def classify_item(it: dict, sys_text: str):
    """Per gold edit: (class, outcome, model_repl). Plus over-edits [(src,repl)]."""
    wrong, correct = it["text_wrong"], it["text_correct"]
    gold = align_edits(wrong, correct)
    sysd = align_edits(wrong, sys_text)
    class_of = class_map(it["edits"])

    corr_avail = Counter((e.start, e.end, e.repl) for e in sysd)
    det_avail = Counter((e.start, e.end) for e in sysd)
    sys_by_span = defaultdict(list)
    for e in sysd:
        sys_by_span[(e.start, e.end)].append(e.repl)

    outcomes = []
    matched_span = Counter()
    for e in gold:
        c = class_of(e)
        kc, kd = (e.start, e.end, e.repl), (e.start, e.end)
        if corr_avail[kc] > 0:
            corr_avail[kc] -= 1
            det_avail[kd] -= 1
            matched_span[kd] += 1
            outcomes.append((c, "fixed", e.repl))
        elif det_avail[kd] > 0:
            det_avail[kd] -= 1
            matched_span[kd] += 1
            repl = sys_by_span[kd][min(matched_span[kd] - 1, len(sys_by_span[kd]) - 1)]
            outcomes.append((c, "wrong_corr", repl))
        else:
            outcomes.append((c, "missed", None))

    gold_spans = Counter((e.start, e.end) for e in gold)
    used = Counter()
    over = []
    for e in sysd:
        sp = (e.start, e.end)
        if gold_spans[sp] - used[sp] > 0:
            used[sp] += 1
        else:
            over.append((span_text(wrong, e.start, e.end), e.repl))
    return outcomes, over, gold


def load_outputs(run_path: Path):
    out = {}
    for line in run_path.open(encoding="utf-8"):
        try:
            r = json.loads(line)
            out[r["id"]] = r
        except Exception:                               # noqa
            pass
    return out


def analyse_tier(label, subdir, split, expected):
    items_path = DATA / f"items_{split}.jsonl"
    res_dir = HERE / subdir
    if not items_path.exists() or not res_dir.exists():
        return None
    items = {it["id"]: it for it in (json.loads(l) for l in items_path.open(encoding="utf-8"))}
    runs = sorted(p for p in res_dir.glob("*.jsonl") if not p.name.startswith("_"))
    if not runs:
        return None

    models = {}
    item_correct = defaultdict(set)                     # id -> {models that got it sentence-exact}
    for rp in runs:
        alias = rp.stem
        outputs = load_outputs(rp)
        graded = [iid for iid in items if iid in outputs]
        if not graded:
            continue
        # per-model accumulators
        oc = Counter()                                  # outcome counts over gold edits
        per_class = defaultdict(Counter)                # class -> outcome counts
        over_n = 0
        clean_tcc = 0                                   # clean (non-error) TCCs over graded items
        over_cat = Counter()                            # 'src→repl' -> count
        miscorr = defaultdict(list)                     # class -> [(src, gold, model)]
        by_register = defaultdict(lambda: [0, 0])       # register -> [edits_fixed, edits_total]
        n_err = 0
        for iid in graded:
            it = items[iid]
            r = outputs[iid]
            n_err += bool(r.get("error"))
            out = r.get("output") or ""
            sys_text = reconcile_variants(out, it["text_correct"]) if out else it["text_wrong"]
            outcomes, over, gold = classify_item(it, sys_text)
            # clean TCCs = total source TCCs minus those covered by a gold error span
            # (the denominator for an exposure-normalized over-edit rate).
            n_tcc = len(tcc_segments(normalize(it["text_wrong"])))
            err_tcc = sum(e.end - e.start for e in gold)
            clean_tcc += max(n_tcc - err_tcc, 0)
            if score_sentence_accuracy([it["text_correct"]], sys_text):
                item_correct[iid].add(alias)
            reg = it.get("register", "?")
            for (c, kind, mrepl), ge in zip(outcomes, gold):
                oc[kind] += 1
                per_class[c][kind] += 1
                by_register[reg][1] += 1
                if kind == "fixed":
                    by_register[reg][0] += 1
                elif kind == "wrong_corr" and len(miscorr[c]) < 40:
                    miscorr[c].append((span_text(it["text_wrong"], ge.start, ge.end),
                                       ge.repl, mrepl))
            over_n += len(over)
            for src, repl in over:
                over_cat[f"{src or '∅'}→{repl or '∅'}"] += 1
        models[alias] = {
            "graded": len(graded), "coverage": len(graded) / expected if expected else 0,
            "n_errors": n_err, "outcomes": dict(oc),
            "gold_edits": sum(oc.values()),
            "over_edits": over_n,
            "clean_tcc": clean_tcc,
            "per_class": {c: dict(v) for c, v in per_class.items()},
            "over_cat": over_cat.most_common(20),
            "miscorr": {c: v for c, v in miscorr.items()},
            "by_register": {k: v for k, v in by_register.items()},
        }
    return {"label": label, "split": split, "expected": expected,
            "n_items": len(items), "models": models,
            "item_hardness": {iid: len(ms) for iid, ms in item_correct.items()},
            "items": items}


def rate(d, k):
    tot = sum(d.values())
    return d.get(k, 0) / tot if tot else 0.0


def fmt_tier(t) -> list[str]:
    L = [f"## {t['label']} — {t['split']} ({t['n_items']} items)", ""]
    ms = t["models"]
    order = sorted(ms, key=lambda a: -rate(ms[a]["outcomes"], "fixed"))

    # A. coverage + failure decomposition
    L += ["### Failure decomposition (share of gold edits)", "",
          "`fixed` = correct · `wrong_corr` = right site, wrong fix · `missed` = site untouched · "
          "`over/100` = spurious edits per 100 items (over-editing).", "",
          "| model | cov | gold edits | fixed | wrong_corr | missed | over/100 |",
          "|---|--:|--:|--:|--:|--:|--:|"]
    for a in order:
        m = ms[a]
        oc = m["outcomes"]
        cov = f"{m['coverage']*100:.0f}%"
        ov100 = 100 * m["over_edits"] / m["graded"] if m["graded"] else 0
        L.append(f"| {a} | {cov} | {m['gold_edits']} | {rate(oc,'fixed'):.3f} | "
                 f"{rate(oc,'wrong_corr'):.3f} | {rate(oc,'missed'):.3f} | {ov100:.1f} |")

    # B. per-class outcome (aggregated across models): which classes are hard, and WHY
    L += ["", "### Per-class difficulty (pooled across all models)", "",
          "Splits each class's failures into *detection* (missed) vs *correction* "
          "(wrong_corr) — the diagnostic axis.", "",
          "| class | gold edits | fixed | wrong_corr | missed |",
          "|---|--:|--:|--:|--:|"]
    pooled = defaultdict(Counter)
    for a in ms:
        for c, oc in ms[a]["per_class"].items():
            for k, v in oc.items():
                pooled[c][k] += v
    for c in sorted(pooled):
        oc = pooled[c]
        tot = sum(oc.values())
        L.append(f"| {c} {CLASS_NAME.get(c,'?')} | {tot} | {rate(oc,'fixed'):.3f} | "
                 f"{rate(oc,'wrong_corr'):.3f} | {rate(oc,'missed'):.3f} |")

    # C. cross-model item hardness
    hard = t["item_hardness"]
    nmodels = len(order)
    hist = Counter(hard.values())
    L += ["", f"### Item hardness ({nmodels} models scored)", "",
          "How many models got each item *sentence-exact*. 0 = universally missed "
          "(intrinsically hard **or** suspect gold → audit); high = easy.", "",
          "| #models correct | items |", "|---:|---:|"]
    for k in range(nmodels + 1):
        if hist.get(k):
            L.append(f"| {k}/{nmodels} | {hist[k]} |")
    universal = [iid for iid, c in hard.items() if c == 0]
    if universal:
        L += ["", f"**Universally-missed ({len(universal)}) — first 20 (gold edits shown):**", ""]
        for iid in universal[:20]:
            it = t["items"][iid]
            eds = "; ".join(f"{e['wrong']}→{e['correct']} (c{e['class']})" for e in it["edits"])
            L.append(f"- `{iid}` [{it.get('register','?')}]: {eds}")

    # D. over-edit catalogue (pooled)
    pooled_over = Counter()
    for a in ms:
        for k, v in ms[a]["over_cat"]:
            pooled_over[k] += v
    if pooled_over:
        L += ["", "### Top spurious over-edits (pooled `src→repl`)", ""]
        L += ["| src→repl | count |", "|---|--:|"]
        for k, v in pooled_over.most_common(15):
            L.append(f"| {k} | {v} |")

    # E. register effect (pooled fixed-rate)
    reg = defaultdict(lambda: [0, 0])
    for a in ms:
        for r, (f, tot) in ms[a]["by_register"].items():
            reg[r][0] += f
            reg[r][1] += tot
    if reg:
        L += ["", "### Register effect (pooled correction recall)", "",
              "| register | fixed/total | recall |", "|---|--:|--:|"]
        for r in sorted(reg):
            f, tot = reg[r]
            L.append(f"| {r} | {f}/{tot} | {f/tot:.3f} |" if tot else f"| {r} | 0/0 | — |")

    # F. miscorrection examples per class (pooled, deduped)
    L += ["", "### Miscorrection examples (right site, wrong fix) — `src · gold · model`", ""]
    pooled_mis = defaultdict(Counter)
    for a in ms:
        for c, exs in ms[a]["miscorr"].items():
            for src, gold, mod in exs:
                pooled_mis[c][f"{src} · {gold} · {mod or '∅'}"] += 1
    for c in sorted(pooled_mis):
        top = pooled_mis[c].most_common(6)
        if top:
            L.append(f"**class {c} {CLASS_NAME.get(c,'?')}:** " +
                     " | ".join(f"{k} ×{v}" for k, v in top))
    L.append("")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", nargs="+", default=None,
                    help="subset of tier labels (default: all with data)")
    ap.add_argument("--out", type=Path, default=HERE / "ERROR-ANALYSIS.md")
    ap.add_argument("--json", type=Path, default=HERE / "error_analysis.json")
    args = ap.parse_args()

    want = set(args.tiers) if args.tiers else None
    out_lines = ["# EditingBench — Error Analysis", "",
                 "Reproducible (`error_analysis.py`); reads canonical post-audit items + "
                 "available model runs. Coverage <100% = run still in progress.", ""]
    dump = {}
    for label, subdir, split, expected in TIERS:
        if want and label not in want:
            continue
        t = analyse_tier(label, subdir, split, expected)
        if not t:
            print(f"{label}: no data (skipped)")
            continue
        cov = ", ".join(f"{a} {m['coverage']*100:.0f}%" for a, m in t["models"].items())
        print(f"{label}: {len(t['models'])} models, {cov}")
        out_lines += fmt_tier(t)
        dump[label] = {a: {k: v for k, v in m.items() if k not in ("miscorr",)}
                       for a, m in t["models"].items()}

    args.out.write_text("\n".join(out_lines), encoding="utf-8")
    args.json.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n-> {args.out.relative_to(HERE)}  +  {args.json.relative_to(HERE)}")


if __name__ == "__main__":
    main()
