"""Natural-error evaluation (paper Section 5.5 and Appendix F).

Applies the cross-model consensus audit (k >= 3) to the 103 mined items, then scores all 16 systems
on the audited set and on all items: correction F1 with CIs, paired ties, outcome decomposition,
and rank correlation with T1. The dropped item ids are listed in the output JSON.

Run from the repo root:  PYTHONUTF8=1 python analysis/natural_eval.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import error_analysis as EA  # noqa: E402
from grader import align_edits, score_correction, score_detection  # noqa: E402
from inject import normalize  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "natural_eval.json"
K, NBOOT = 3, 10000
INVIS = "\u200b\u200c\u200d\ufeff"
strip = lambda t: re.sub(r"[\s\.,;:!?\"'()\-\u2013\u2014" + INVIS + "]", "", t)


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


items = [json.loads(l) for l in (REPO / "data" / "items_wiki.jsonl").open(encoding="utf-8")]
runs = {rp.stem: EA.load_outputs(rp) for rp in sorted((REPO / "results_wiki").glob("*.jsonl"))
        if not rp.name.startswith("_")}


def sys_text(m, it):
    r = runs[m].get(it["id"]) or {}
    out = r.get("output") or ""
    return EA.reconcile_variants(out, it["text_correct"]) if out else it["text_wrong"]


dropped, reasons = [], Counter()
for it in items:
    g, w = normalize(it["text_correct"]), normalize(it["text_wrong"])
    c = Counter(normalize(sys_text(m, it)) for m in runs)
    c.pop(g, None)
    if not c:
        continue
    cons, n = c.most_common(1)[0]
    if n < K or cons == w or strip(cons) == strip(g):
        continue
    if lev(w, cons) + lev(cons, g) == lev(w, g):
        reasons["keep_partial_fix"] += 1
        continue
    ge = {(e.start, e.end) for e in align_edits(w, g)}
    ce = align_edits(w, cons)
    extra_unmarked = any((e.start, e.end) not in ge for e in ce)
    reasons["drop_extra_unmarked_fix" if extra_unmarked else "drop_different_fix_at_gold_span"] += 1
    dropped.append(it["id"])

kept = [it for it in items if it["id"] not in set(dropped)]
print("dropped", len(dropped), dict(reasons), "kept", len(kept))


def f1(tp, ns, ng):
    p = tp / ns if ns else 0.0
    r = tp / ng if ng else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


def evaluate(subset, tag):
    n = len(subset)
    gold = {it["id"]: align_edits(it["text_wrong"], it["text_correct"]) for it in subset}
    rng = np.random.default_rng(20260929)
    samples = rng.integers(0, n, size=(NBOOT, n))
    per = {}
    for m in runs:
        cc, dc, oc = [], [], Counter()
        for it in subset:
            st = sys_text(m, it)
            sysd = align_edits(it["text_wrong"], st)
            cc.append(score_correction(gold[it["id"]], sysd))
            dc.append(score_detection(gold[it["id"]], sysd))
            outcomes, _o, _g = EA.classify_item(it, st)
            for (_c, k, _r) in outcomes:
                oc[k] += 1
        tp, ns, ng = (np.array([getattr(c, a) for c in cc]) for a in ("tp", "n_sys", "n_gold"))
        T, NS, NG = tp[samples].sum(1), ns[samples].sum(1), ng[samples].sum(1)
        P = np.where(NS > 0, T / np.maximum(NS, 1), 0.0)
        R = np.where(NG > 0, T / np.maximum(NG, 1), 0.0)
        boot = np.where(P + R > 0, 2 * P * R / np.maximum(P + R, 1e-12), 0.0)
        tot = sum(oc.values())
        per[m] = {"f1": f1(tp.sum(), ns.sum(), ng.sum()), "boot": boot,
                  "det": f1(sum(c.tp for c in dc), sum(c.n_sys for c in dc), sum(c.n_gold for c in dc)),
                  "decomp": {k: oc[k] / tot for k in ("fixed", "wrong_corr", "missed")}}
    best = max(per, key=lambda m: per[m]["f1"])
    res = {}
    for m, d in per.items():
        if m == best:
            p = None
        else:
            dl = per[best]["boot"] - d["boot"]
            p = float(min(1.0, 2 * min((dl <= 0).sum(), (dl >= 0).sum()) / NBOOT))
        res[m] = {"f1": round(d["f1"], 4), "ci": [round(float(np.quantile(d["boot"], .025)), 4),
                                                  round(float(np.quantile(d["boot"], .975)), 4)],
                  "det": round(d["det"], 4), "p_vs_best": p, "tied": p is None or p >= 0.05,
                  "decomp": {k: round(v, 4) for k, v in d["decomp"].items()}}
    t1 = {Path(f).stem: json.load(open(f, encoding="utf-8"))["correction"]["F1"]
          for f in (REPO / "results").glob("*.json")}
    from scipy.stats import pearsonr, spearmanr
    ks = sorted(res)
    rho = spearmanr([t1[k] for k in ks], [per[k]["f1"] for k in ks]).statistic
    r = pearsonr([t1[k] for k in ks], [per[k]["f1"] for k in ks]).statistic
    pooled = {k: round(float(np.mean([res[m]["decomp"][k] for m in res])), 4) for k in ("fixed", "wrong_corr", "missed")}
    summary = {"n_items": n, "gold_edits": sum(len(v) for v in gold.values()), "best": best,
               "mean_f1": round(float(np.mean([per[m]["f1"] for m in per])), 4), "spearman_t1": round(float(rho), 4),
               "pearson_t1": round(float(r), 4), "pooled_decomp": pooled,
               "max_wrong_corr": max(res[m]["decomp"]["wrong_corr"] for m in res), "models": res}
    print(f"\n[{tag}] n={n} best={best} mean={summary['mean_f1']} rho={summary['spearman_t1']} r={summary['pearson_t1']} pooled={pooled} maxwc={summary['max_wrong_corr']}")
    for m, v in sorted(res.items(), key=lambda kv: -kv[1]["f1"]):
        print(f"   {m:18s} {v['f1']:.3f} [{v['ci'][0]:.3f},{v['ci'][1]:.3f}] det {v['det']:.3f} p={v['p_vs_best']} tie={v['tied']} {v['decomp']}")
    return summary


out = {"dropped": dropped, "reasons": dict(reasons),
       "audited": evaluate(kept, "audited"), "all": evaluate(items, "all")}
json.dump(out, OUT.open("w"), indent=1)
