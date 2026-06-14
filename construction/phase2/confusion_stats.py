"""Phase 2 · Step 4 — coverage stats for confusion-set.jsonl (for the README)."""
import json
from collections import Counter, defaultdict
from pathlib import Path

CS = Path(__file__).resolve().parent.parent / "confusion-set.jsonl"
rows = [json.loads(l) for l in CS.read_text(encoding="utf-8").splitlines()]
CLASSES = ["tone_mark", "consonant_pair", "karan_native", "vowel",
           "cluster_metathesis", "loanword_translit"]

print(f"TOTAL: {len(rows)} pairs\n")

print("class × etymology:")
g = defaultdict(Counter)
for r in rows:
    g[r["class"]][r["etymology"]] += 1
print(f"{'class':<20}{'native':>8}{'loan':>8}{'proper':>8}{'total':>8}")
for c in CLASSES:
    n, l, p = g[c]["native"], g[c]["loan"], g[c]["proper-noun"]
    print(f"{c:<20}{n:>8}{l:>8}{p:>8}{n+l+p:>8}")

print("\nclass × edit_op:")
ops = ["substitution", "insertion", "deletion", "transposition", "mixed"]
g2 = defaultdict(Counter)
for r in rows:
    g2[r["class"]][r["edit_op"]] += 1
print(f"{'class':<20}" + "".join(f"{o[:5]:>7}" for o in ops))
for c in CLASSES:
    print(f"{c:<20}" + "".join(f"{g2[c][o]:>7}" for o in ops))

print("\nprovenance (source membership):", dict(Counter(s for r in rows for s in r["sources"])))
print("etymology origins (loan):", dict(Counter(r["origin"] for r in rows if r["etymology"] == "loan")))
print("RID-verified:", sum(r["rid_verified"] for r in rows), "/", len(rows))
print("correct_alts present:", sum(1 for r in rows if r["correct_alts"]))
