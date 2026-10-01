"""Apply the consensus-audit drops to T2/T3: remove items whose gold is a residual
SOURCE typo (cross-model consensus, after variant-reconciliation + shared-miss/punct
exclusion). Loanword-variant + register items are KEPT (reconciled in variants.py);
the one register item that can't be reconciled (พวกเขา gluing) is in the drop set so it
never penalises a model. Backs up originals, rewrites data/items_<tier>.jsonl, and emits
a fresh sample file at the post-audit n. Run: PYTHONUTF8=1 python viz/apply_audit_drops.py"""
import json, sys, glob, os, shutil
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDIT = HERE.parent
sys.path.insert(0, str(EDIT))
from inject import normalize
from variants import reconcile_variants

PUNCT = set(' \t“”"\'`.,!?()[]{}:;…-–—/')
def is_punct(s): return s != "" and all(c in PUNCT for c in s)

def drop_ids(resdir, split, n):
    p0 = EDIT / resdir
    items = {json.loads(l)["id"]: json.loads(l)
             for l in (p0 / f"_sample_{split}_{n}.jsonl").open(encoding="utf-8")}
    runs = {}
    for p in glob.glob(str(p0 / "*.jsonl")):
        if os.path.basename(p).startswith("_"):
            continue
        rows = {r["id"]: (r.get("output") or "")
                for r in (json.loads(x) for x in open(p, encoding="utf-8"))}
        if len(rows) >= len(items):
            runs[os.path.basename(p)[:-6]] = rows
    full = list(runs)
    drops = []
    for iid, it in items.items():
        goldn = normalize(it["text_correct"]); wrongn = normalize(it["text_wrong"])
        votes = Counter()
        for m in full:
            o = runs[m].get(iid, "")
            rec = normalize(reconcile_variants(o, it["text_correct"])) if o else wrongn
            votes[rec] += 1
        nongold = sorted(((v, k) for k, v in votes.items() if k != goldn), reverse=True)
        if not nongold:
            continue
        cnt, val = nongold[0]; gv = votes.get(goldn, 0)
        if not (cnt >= 3 and cnt >= gv):
            continue
        if val == wrongn:                      # shared miss -> gold OK, keep
            continue
        if _lev(wrongn, val) + _lev(val, goldn) == _lev(wrongn, goldn):  # partial fix toward gold -> keep
            continue
        if all(is_punct(g) or is_punct(c) for g, c in _blocks(goldn, val)):  # punct over-edit -> keep
            continue
        drops.append(iid)
    return set(drops), len(items)

def _lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def _blocks(a, b):
    import difflib
    return [(a[i1:i2], b[j1:j2]) for tag, i1, i2, j1, j2
            in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if tag != "equal"]

def apply_tier(resdir, split, n, data_name):
    drops, total = drop_ids(resdir, split, n)
    newn = total - len(drops)
    # data file
    data_path = EDIT / "data" / data_name
    if data_path.exists():
        shutil.copy(data_path, data_path.with_suffix(data_path.suffix + ".bak_pre_audit2"))
        kept = [l for l in data_path.open(encoding="utf-8")
                if json.loads(l)["id"] not in drops]
        data_path.write_text("".join(kept), encoding="utf-8")
    # fresh sample at post-audit n (keep original sample untouched as the pre-audit record)
    src = EDIT / resdir / f"_sample_{split}_{n}.jsonl"
    keepers = [l for l in src.open(encoding="utf-8") if json.loads(l)["id"] not in drops]
    (EDIT / resdir / f"_sample_{split}_{newn}.jsonl").write_text("".join(keepers), encoding="utf-8")
    print(f"{split}: dropped {len(drops)} / {total} -> n={newn}  (sample _sample_{split}_{newn}.jsonl, data {data_name})")
    print("   dropped:", " ".join(sorted(drops)))
    return newn

n3 = apply_tier("results_t3", "t3", 150, "items_t3.jsonl")
n2 = apply_tier("results_t2", "t2", 250, "items_t2.jsonl")
print(f"\nRE-SCORE:\n  python score_runs.py --split t3 --n {n3} --results results_t3 --report sample-run-results-t3.md")
print(f"  python score_runs.py --split t2 --n {n2} --results results_t2 --report sample-run-results-t2.md")
