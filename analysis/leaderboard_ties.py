"""Per-tier correction F1, 95% item-bootstrap CIs, and paired-bootstrap ties with the column best
(paper Table 1 underlines and the CI table in Appendix D). Also scores the unaudited natural set.

Run from the repo root:  PYTHONUTF8=1 python analysis/leaderboard_ties.py
"""
import sys, json, random
import numpy as np
from collections import Counter
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from grader import align_edits, score_correction, score_detection
from variants import reconcile_variants
import error_analysis as EA

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "leaderboard_ties.json"
TIERS = [("T1", "results", "items_test_public.jsonl"), ("T2", "results_t2", "items_t2.jsonl"),
         ("T3", "results_t3", "items_t3.jsonl"), ("WIKI", "results_wiki", "items_wiki.jsonl")]
NBOOT = 10000

def load(rd, sf):
    items = [json.loads(l) for l in (REPO / "data" / sf).open(encoding="utf-8")]
    models = {}
    for rp in sorted((REPO / rd).glob("*.jsonl")):
        if rp.name.startswith("_"): continue
        outs = {}
        for line in rp.open(encoding="utf-8"):
            try:
                r = json.loads(line); outs[r["id"]] = r
            except Exception: pass
        models[rp.stem] = outs
    return items, models

def f1(tp, ns, ng):
    p = tp / ns if ns else 0.0; r = tp / ng if ng else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0

res = {}
for tier, rd, sf in TIERS:
    items, models = load(rd, sf)
    gold = {it["id"]: align_edits(it["text_wrong"], it["text_correct"]) for it in items}
    ids = [it["id"] for it in items]
    per = {}
    for m, outs in models.items():
        cc, dc, oc = [], [], Counter()
        for it in items:
            iid = it["id"]
            out = (outs.get(iid) or {}).get("output") or ""
            sys_text = reconcile_variants(out, it["text_correct"]) if out else it["text_wrong"]
            sysd = align_edits(it["text_wrong"], sys_text)
            cc.append(score_correction(gold[iid], sysd)); dc.append(score_detection(gold[iid], sysd))
            if tier == "WIKI" and it.get("edits"):
                outcomes, _, _ = EA.classify_item(it, sys_text)
                for (_c, k, _r) in outcomes: oc[k] += 1
        per[m] = {"cc": cc, "dc": dc, "oc": oc, "cov": sum(1 for i in ids if i in outs)}
    n = len(ids)
    rng = np.random.default_rng(20260929)
    samples = rng.integers(0, n, size=(NBOOT, n))
    def boot_f1s(cc):
        tp = np.array([c.tp for c in cc])[samples].sum(1); ns = np.array([c.n_sys for c in cc])[samples].sum(1)
        ng = np.array([c.n_gold for c in cc])[samples].sum(1)
        p = np.where(ns > 0, tp / np.maximum(ns, 1), 0.0); r = np.where(ng > 0, tp / np.maximum(ng, 1), 0.0)
        return np.where(p + r > 0, 2 * p * r / np.maximum(p + r, 1e-12), 0.0)
    boots, point = {}, {}
    for m, d in per.items():
        cc = d["cc"]
        point[m] = f1(sum(c.tp for c in cc), sum(c.n_sys for c in cc), sum(c.n_gold for c in cc))
        boots[m] = boot_f1s(cc)
    best = max(point, key=point.get)
    table = {}
    for m in per:
        lo, hi = float(np.quantile(boots[m], .025)), float(np.quantile(boots[m], .975))
        dc = per[m]["dc"]
        det = f1(sum(c.tp for c in dc), sum(c.n_sys for c in dc), sum(c.n_gold for c in dc))
        if m == best:
            p = None
        else:
            deltas = boots[best] - boots[m]
            p = float(min(1.0, 2 * min((deltas <= 0).sum(), (deltas >= 0).sum()) / NBOOT))
        oc = per[m]["oc"]; tot = sum(oc.values())
        table[m] = {"corr_f1": round(point[m], 4), "ci": [round(lo, 4), round(hi, 4)], "det_f1": round(det, 4),
                    "p_vs_best": p, "tied_with_best": (p is None or p >= 0.05), "coverage": per[m]["cov"],
                    "decomp": {k: round(v / tot, 4) for k, v in oc.items()} if tot else None}
    res[tier] = {"n_items": n, "gold_edits": sum(len(g) for g in gold.values()), "best": best, "models": table}
    print(tier, "n", n, "gold_edits", res[tier]["gold_edits"], "best", best, flush=True)
    for m, t in sorted(table.items(), key=lambda kv: -kv[1]["corr_f1"]):
        print(f"   {m:18s} {t['corr_f1']:.3f} [{t['ci'][0]:.3f},{t['ci'][1]:.3f}] det {t['det_f1']:.3f} p={t['p_vs_best']} tie={t['tied_with_best']} cov={t['coverage']} {t['decomp'] or ''}", flush=True)
    json.dump(res, OUT.open("w"), indent=1)
