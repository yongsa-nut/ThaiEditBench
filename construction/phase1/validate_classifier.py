"""
Validate phase1/classify.py against the hand-labeled botfix gold set.

For class-6 (loanword) gold entries we pass etymology='loan' (the gold cat 6
*is* the loanword bucket); for the rest we pass 'native'. Reports overall
agreement on primary_class and a confusion matrix, plus the disagreements so
they can be inspected before trusting the classifier on unlabeled sources.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

from classify import classify

HERE = Path(__file__).resolve().parent
GOLD = HERE / "data" / "botfix_gold.jsonl"


def main():
    rows = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines()]
    n = correct = 0
    confusion = defaultdict(Counter)
    disagree = []
    for r in rows:
        gold = r["gold_class"]
        if gold == 0:
            continue  # uncertain gold -- excluded from agreement calc
        etym = "loan" if gold == 6 else "native"
        pred = classify(r["wrong"], r["correct"], etymology=etym)["primary_class"]
        n += 1
        confusion[gold][pred] += 1
        if pred == gold:
            correct += 1
        else:
            disagree.append((r["wrong"], r["correct"], gold, pred,
                             classify(r["wrong"], r["correct"], etym)["mechanism_detail"]))
    print(f"agreement (excl. gold class 0): {correct}/{n} = {correct/n:.1%}\n")
    print("confusion matrix (rows=gold, cols=pred):")
    classes = [1, 2, 3, 4, 5, 6, 0]
    print("      " + "".join(f"{c:>5}" for c in classes))
    for g in [1, 2, 3, 4, 5, 6]:
        print(f"gold{g} " + "".join(f"{confusion[g][c]:>5}" for c in classes))
    print(f"\n{len(disagree)} disagreements:")
    for w, c, g, p, d in disagree:
        print(f"  {w} -> {c}  gold={g} pred={p}  [{d}]")


if __name__ == "__main__":
    main()
