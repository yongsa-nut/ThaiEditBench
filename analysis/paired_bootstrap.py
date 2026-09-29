"""Paired item-level bootstrap for the pairwise comparisons quoted in paper Section 5.1.

Run from the repo root:  PYTHONUTF8=1 python analysis/paired_bootstrap.py
"""
import sys, json, random
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from grader import align_edits, score_correction          # noqa: E402
from variants import reconcile_variants                   # noqa: E402

_GOLD_CACHE: dict[str, dict] = {}
_MODEL_CACHE: dict[tuple, dict] = {}


def gold_for(split_file: str) -> dict:
    if split_file not in _GOLD_CACHE:
        items = [json.loads(l) for l in (REPO / "data" / split_file).open(encoding="utf-8")]
        _GOLD_CACHE[split_file] = {
            it["id"]: (it, align_edits(it["text_wrong"], it["text_correct"])) for it in items
        }
    return _GOLD_CACHE[split_file]


def counts_for(model: str, results_dir: str, split_file: str) -> dict:
    key = (model, results_dir, split_file)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    ibi = gold_for(split_file)
    outs = {}
    for line in (REPO / results_dir / f"{model}.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        outs[r["id"]] = r
    per = {}
    for iid, (it, gold) in ibi.items():
        if iid not in outs:
            continue
        out = outs[iid].get("output") or ""
        sys_text = reconcile_variants(out, it["text_correct"]) if out else it["text_wrong"]
        sysd = align_edits(it["text_wrong"], sys_text)
        per[iid] = score_correction(gold, sysd)
    _MODEL_CACHE[key] = per
    return per


def f1(counts) -> float:
    tp = sum(c.tp for c in counts)
    ns = sum(c.n_sys for c in counts)
    ng = sum(c.n_gold for c in counts)
    p = tp / ns if ns else 0.0
    r = tp / ng if ng else 0.0
    return 2 * p * r / (p + r) if (p + r) else 0.0


def paired(mA, mB, results_dir, split_file, nboot=10000, seed=20260712):
    A = counts_for(mA, results_dir, split_file)
    B = counts_for(mB, results_dir, split_file)
    ids = sorted(set(A) & set(B))
    n = len(ids)
    fa, fb = f1([A[i] for i in ids]), f1([B[i] for i in ids])
    obs = fa - fb
    rng = random.Random(seed)
    deltas = []
    for _ in range(nboot):
        s = [ids[rng.randrange(n)] for _ in range(n)]
        deltas.append(f1([A[i] for i in s]) - f1([B[i] for i in s]))
    deltas.sort()
    lo, hi = deltas[int(0.025 * nboot)], deltas[int(0.975 * nboot) - 1]
    p = 2 * min(sum(d <= 0 for d in deltas), sum(d >= 0 for d in deltas)) / nboot
    return fa, fb, obs, lo, hi, min(p, 1.0), n


COMPS = [
    ("T3",   "results_t3",   "items_t3.jsonl",          "gemma-4-31b", "gpt55-med"),
    ("T3",   "results_t3",   "items_t3.jsonl",          "gemma-4-31b", "gpt55-high"),
    ("T3",   "results_t3",   "items_t3.jsonl",          "gemma-4-31b", "opus-4.7"),
    ("T3",   "results_t3",   "items_t3.jsonl",          "gemma-4-31b", "gpt54-mini"),
    ("T3",   "results_t3",   "items_t3.jsonl",          "gemma-4-31b", "typhoon25"),
    ("T1",   "results",      "items_test_public.jsonl", "gpt55-high",  "gpt55-med"),
    ("T1",   "results",      "items_test_public.jsonl", "gpt55-high",  "opus-4.7"),
    ("T1",   "results",      "items_test_public.jsonl", "gpt55-high",  "gemma-4-31b"),
    ("T1",   "results",      "items_test_public.jsonl", "gemma-4-31b", "typhoon-s"),
    ("WIKI", "results_wiki", "items_wiki.jsonl",        "gemma-4-31b", "gpt54-mini"),
    ("WIKI", "results_wiki", "items_wiki.jsonl",        "gemma-4-31b", "gpt55-high"),
]

if __name__ == "__main__":
    print(f"{'tier':5s} {'A vs B':42s} {'F1(A)':>6s} {'F1(B)':>6s} {'delta':>7s}  {'95% CI':>17s} {'p':>7s}  n")
    for tier, rd, sf, a, b in COMPS:
        fa, fb, obs, lo, hi, p, n = paired(a, b, rd, sf)
        sig = "*" if p < 0.05 else " "
        print(f"{tier:5s} {a + ' vs ' + b:42s} {fa:6.3f} {fb:6.3f} {obs:+7.3f}  [{lo:+.3f},{hi:+.3f}] {p:7.4f}{sig} {n}")
