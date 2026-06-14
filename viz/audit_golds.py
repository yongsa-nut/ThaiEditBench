"""Audit a model's 'wrong' items to find likely-defective GOLDS.

For each item the focus model did not get exactly right, categorise per gold edit
(missed / fixed-differently / over-edit) and — the key signal — count how many of
the *fully-run* models converge on the focus model's output vs on the gold. When
several strong models agree on a correction that differs from the gold, the gold is
the likely culprit (e.g. syn-001875: source dropped เข้า → gold "ความใจ" is broken,
6/8 models restore "ความเข้าใจ" and get penalised).

  PYTHONUTF8=1 python viz/audit_golds.py --model gpt55-high --n 819
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDIT = HERE.parent
sys.path.insert(0, str(EDIT))
from grader import align_edits                       # noqa: E402
from inject import normalize                         # noqa: E402
from variants import reconcile_variants               # noqa: E402

RESULTS = EDIT / "results"


def diff_span(a: str, b: str) -> tuple[str, str]:
    """The minimal differing middle of two strings (common prefix/suffix stripped)."""
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    ja, jb = len(a), len(b)
    while ja > i and jb > i and a[ja - 1] == b[jb - 1]:
        ja -= 1
        jb -= 1
    return a[i:ja], b[i:jb]


def load_jsonl(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def complete_models(n):
    """Models whose results/<alias>.jsonl covers all n sample ids (skip partial/blocked)."""
    out = {}
    for p in RESULTS.glob("*.jsonl"):
        if p.name.startswith("_"):
            continue
        rows = {r["id"]: (r.get("output") or "") for r in load_jsonl(p)}
        out[p.stem] = rows
    return out


def per_edit(item, output):
    """Per gold edit: ('fixed'|'diff'|'miss', gold_repl, sys_repl|None) + over-edit count."""
    gold = align_edits(item["text_wrong"], item["text_correct"])
    sysd = align_edits(item["text_wrong"], output or item["text_wrong"])
    sysmap = {(e.start, e.end): e.repl for e in sysd}
    gold_spans = Counter((e.start, e.end) for e in gold)
    rows = []
    for e in gold:
        if (e.start, e.end) in sysmap:
            sr = sysmap[(e.start, e.end)]
            rows.append(("fixed" if sr == e.repl else "diff", e.repl, sr))
        else:
            rows.append(("miss", e.repl, None))
    over = [e.repl for e in sysd if (e.start, e.end) not in gold_spans]
    return rows, over


def consensus_audit(items, runs, full, min_agree, out_path):
    """Flag golds where >= min_agree full models CONVERGE on the same output != gold
    (variant-reconciled). The strongest gold-defect signal: many independent models
    agreeing on a different answer. (Some hits are systematic over-normalisation like
    มั้ย→ไหม, not gold bugs — the gold→consensus diff makes that easy to judge.)"""
    suspects = []
    for iid, it in items.items():
        goldn = normalize(it["text_correct"])
        votes, who = Counter(), {}
        for m in full:
            o = runs[m].get(iid, "")
            rec = normalize(reconcile_variants(o, it["text_correct"])) if o else normalize(it["text_wrong"])
            votes[rec] += 1
            who.setdefault(rec, []).append(m)
        nongold = sorted(((v, k) for k, v in votes.items() if k != goldn), reverse=True)
        if not nongold:
            continue
        cnt, val = nongold[0]
        gv = votes.get(goldn, 0)
        if cnt >= min_agree and cnt >= gv:
            gpart, cpart = diff_span(goldn, val)
            suspects.append((iid, it, gpart, cpart, cnt, gv, who[val]))
    suspects.sort(key=lambda r: (-(r[4] - r[5]), -r[4]))

    # bucket: punctuation/whitespace-only diffs = model OVER-EDIT (gold fine);
    # Thai-text diffs where models converge = likely residual SOURCE TYPO in gold.
    PUNCT = set(' \t“”\"\'`.,!?()[]{}:;…-–—/')
    def is_punct(s):
        return s != "" and all(c in PUNCT for c in s)
    defects, overedits = [], []
    for r in suspects:
        gp, cp = r[2], r[3]
        (overedits if (is_punct(gp) or is_punct(cp)) else defects).append(r)

    def block(rows):
        out = []
        for iid, it, gp, cp, cnt, gv, ms in rows:
            out.append(f"### {iid}  ({it.get('source_doc','?')})  — {cnt} models vs {gv} gold")
            out.append(f"- gold `{gp or '∅'}`  →  consensus `{cp or '∅'}`")
            out.append(f"- gold sentence: `{it['text_correct']}`")
        return out or ["_none_"]

    lines = [f"# Gold audit — cross-model consensus ({len(full)} full models)", "",
             f"Models: {', '.join(sorted(full))}", "",
             f"Flagged where ≥{min_agree} models agree on the SAME output ≠ gold (variant-reconciled).", "",
             f"- **{len(defects)} LIKELY GOLD DEFECTS** — Thai-text disagreement; the gold itself likely "
             "carries a residual source typo (e.g. กฏหมาย, คววม). Review/fix or drop.",
             f"- {len(overedits)} model over-edits (punctuation/quote stripping) — **gold is fine**, model "
             "broke the no-punctuation rule.", "",
             "_A few text diffs can still be model errors (e.g. a model mis-ordering a valid word) — "
             "skim before bulk-fixing._", "",
             "## LIKELY GOLD DEFECTS (review)", ""]
    lines += block(defects)
    lines += ["", "## Model over-edits (gold OK)", ""] + block(overedits)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"consensus audit (≥{min_agree}): {len(defects)} likely gold defects · "
          f"{len(overedits)} model over-edits -> {out_path.name}\n")
    print("LIKELY GOLD DEFECTS:")
    for iid, it, gp, cp, cnt, gv, ms in defects:
        print(f"  {iid}  [{cnt}v{gv}]  gold {gp!r} -> {cp!r}")


def main():
    global RESULTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt55-high")
    ap.add_argument("--split", default="test_public")
    ap.add_argument("--n", type=int, default=819)
    ap.add_argument("--results", default=None, help="results dir (e.g. results_t2 for the paragraph tier)")
    ap.add_argument("--consensus", action="store_true", help="cross-model consensus mode (no focus model)")
    ap.add_argument("--min-agree", type=int, default=3, help="consensus: min models agreeing on a non-gold output")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if args.results:
        RESULTS = EDIT / args.results

    items = {it["id"]: it for it in load_jsonl(RESULTS / f"_sample_{args.split}_{args.n}.jsonl")}
    runs = complete_models(args.n)
    full = [m for m, rows in runs.items() if len(rows) >= len(items)]

    if args.consensus:
        consensus_audit(items, runs, full, args.min_agree,
                        args.out or HERE / "suspect-golds-all.md")
        return
    args.out = args.out or HERE / "suspect-golds.md"
    if args.model not in full:
        raise SystemExit(f"{args.model} is not fully run ({len(runs.get(args.model, {}))}/{len(items)})")
    focus = runs[args.model]

    suspects, overfix, miss, over_only, ws = [], [], [], [], []
    for iid, it in items.items():
        out = focus.get(iid, "")
        if normalize(out) == normalize(it["text_correct"]):
            continue                                  # got it exactly right
        rows, over = per_edit(it, out)
        # whitespace/punct-only difference?
        if normalize(out.replace(" ", "")) == normalize(it["text_correct"].replace(" ", "")):
            ws.append((iid, it, out)); continue
        # cross-model consensus on this item
        agree_focus = sum(1 for m in full if normalize(runs[m].get(iid, "")) == normalize(out))
        agree_gold = sum(1 for m in full if normalize(runs[m].get(iid, "")) == normalize(it["text_correct"]))
        rec = (iid, it, out, rows, over, agree_focus, agree_gold)
        has_diff = any(r[0] == "diff" for r in rows)
        if has_diff and agree_focus >= agree_gold and agree_focus >= 2:
            suspects.append(rec)                      # several models back the focus output ≠ gold
        elif has_diff:
            overfix.append(rec)                       # focus changed it differently, little support
        elif over:
            over_only.append(rec)
        else:
            miss.append(rec)                          # focus left the error in place

    suspects.sort(key=lambda r: (-(r[5] - r[6]), -r[5]))

    def fmt(rec, show_consensus=True):
        iid, it, out, rows, over, af, ag = rec
        ls = [f"### {iid}  ({it.get('source_doc','?')}, {it.get('register','')})"]
        ls.append(f"- wrong  : `{it['text_wrong']}`")
        ls.append(f"- GOLD   : `{it['text_correct']}`")
        ls.append(f"- {args.model:<11}: `{out or '(empty)'}`")
        for st, gr, sr in rows:
            if st == "fixed":
                continue
            if st == "diff":
                ls.append(f"  - edit: gold says **{gr}**, model says **{sr}**")
            else:
                ls.append(f"  - edit: **missed** (gold wants {gr})")
        if over:
            ls.append(f"  - over-edits: {', '.join(over)}")
        if show_consensus:
            ls.append(f"  - consensus (of {len(full)} full models): **{af}** match model · {ag} match gold")
        return "\n".join(ls)

    out_lines = [f"# Gold audit via {args.model} misses ({args.split}, n={args.n})", "",
                 f"Full models used for consensus ({len(full)}): {', '.join(sorted(full))}", "",
                 f"- **{len(suspects)}** SUSPECT GOLDS (model's fix backed by ≥2 models, ≥ gold's support)",
                 f"- {len(overfix)} different-fix, low support (likely model over-fix/guess)",
                 f"- {len(miss)} genuine misses (model left the error)",
                 f"- {len(over_only)} over-edit only", f"- {len(ws)} whitespace/punct-only", "",
                 "## SUSPECT GOLDS (review these — model likely more correct than gold)", ""]
    out_lines += [fmt(r) for r in suspects] or ["_none_"]
    out_lines += ["", "## Different-fix, low support (likely genuine model error)", ""]
    out_lines += [fmt(r) for r in overfix] or ["_none_"]
    out_lines += ["", "## Genuine misses (model left the error — gold presumed OK)", ""]
    out_lines += [fmt(r, show_consensus=False) for r in miss] or ["_none_"]
    if over_only:
        out_lines += ["", "## Over-edit only", ""] + [fmt(r) for r in over_only]
    if ws:
        out_lines += ["", "## Whitespace/punct-only", ""]
        out_lines += [f"- {iid}: `{out}`  (gold `{it['text_correct']}`)" for iid, it, out in ws]
    args.out.write_text("\n".join(out_lines), encoding="utf-8")

    print(f"{args.model}: {len(suspects)} suspect golds · {len(overfix)} low-support diffs · "
          f"{len(miss)} misses · {len(over_only)} over-only · {len(ws)} whitespace  -> {args.out.name}")
    print("\nTOP SUSPECT GOLDS (model backed by ≥2 models, differs from gold):")
    for r in suspects[:15]:
        iid, it, out, rows, over, af, ag = r
        diffs = "; ".join(f"{gr}→{sr}" for st, gr, sr in rows if st == "diff")
        print(f"  {iid}  [{af} vs {ag}]  gold:{diffs.split('→')[0] if diffs else ''}  | {diffs}")


if __name__ == "__main__":
    main()
