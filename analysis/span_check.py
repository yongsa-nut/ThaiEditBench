"""Exact-span check for the outcome decomposition (paper Section 5.2).

A gold edit counts as miscorrected only when a system edit has exactly its TCC span. This splits the
missed edits into untouched ones and ones overlapped by a system edit with a different span.

Run from the repo root:  PYTHONUTF8=1 python analysis/span_check.py
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import error_analysis as EA
from grader import align_edits

def overlaps(g, s):
    gs, ge, ss, se = g.start, g.end, s.start, s.end
    if gs == ge and ss == se:
        return gs == ss
    if gs == ge:
        return ss <= gs <= se
    if ss == se:
        return gs <= ss <= ge
    return ss < ge and se > gs

res = {}
for label, subdir, split, expected in EA.TIERS:
    items = {it["id"]: it for it in (json.loads(l) for l in (EA.DATA / f"items_{split}.jsonl").open(encoding="utf-8"))}
    pooled = Counter()
    per_model = {}
    for rp in sorted((REPO / subdir).glob("*.jsonl")):
        if rp.name.startswith("_"): continue
        outs = EA.load_outputs(rp)
        c = Counter()
        for iid, it in items.items():
            if iid not in outs: continue
            out = outs[iid].get("output") or ""
            sys_text = EA.reconcile_variants(out, it["text_correct"]) if out else it["text_wrong"]
            outcomes, over, gold = EA.classify_item(it, sys_text)
            sysd = align_edits(it["text_wrong"], sys_text)
            for (cl, kind, _), ge in zip(outcomes, gold):
                if kind == "missed":
                    kind = "missed_touched" if any(overlaps(ge, s) for s in sysd) else "missed_untouched"
                c[kind] += 1
        n = sum(c.values())
        per_model[rp.stem] = {k: round(v / n, 4) for k, v in c.items()} | {"n": n}
        pooled += c
    n = sum(pooled.values())
    res[label] = {"pooled": {k: round(v / n, 4) for k, v in pooled.items()} | {"n": n}, "per_model": per_model}
    print(label, res[label]["pooled"])
    worst = sorted(per_model.items(), key=lambda kv: -kv[1].get("missed_touched", 0))[:5]
    for a, m in worst:
        print("   ", a, m)
out_dir = Path(__file__).resolve().parent / "out"
out_dir.mkdir(exist_ok=True)
json.dump(res, open(out_dir / "span_check.json", "w"), indent=1)
