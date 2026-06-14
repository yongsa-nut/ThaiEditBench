"""
Phase 6 — ThERRANT validation (subtask2/plan.md §9).

Validation target: automatic class labels match the dataset's class labels at
>= 85% agreement (ERRANT English floor). We don't yet have human class labels
(that's Phase 5), so we validate against the construction/stored gold classes:
this tests that ThERRANT's span-extraction + word-expansion + classify pipeline
recovers the same mechanism class the dataset carries.

Matching: each ThERRANT edit is mapped to the stored gold edit whose TCC span
contains it; classes compared. Reports overall + per-class agreement + the main
confusions, and asserts >= 0.85 overall.

Run:  PYTHONUTF8=1 python test_therrant.py [--split dev]
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from therrant import annotate, load_loan_lexicon
from inject import CLASS_NAME

HERE = Path(__file__).resolve().parent


def unit_cases(loan):
    # span recovery + typing on hand cases
    a = annotate("นักวิทยาศาสตร์สังเกตุปรากฏการณ์", "นักวิทยาศาสตร์สังเกตปรากฏการณ์", loan)
    assert len(a) == 1 and a[0].klass == 4, a          # vowel (native)
    a = annotate("ออกกฏหมายใหม่", "ออกกฎหมายใหม่", loan)
    assert len(a) == 1 and a[0].klass == 2, a          # consonant-pair ฏ/ฎ (native, not loan)
    a = annotate("ฝรั่งเศษเป็นประเทศ", "ฝรั่งเศสเป็นประเทศ", loan)
    assert len(a) == 1 and a[0].klass == 6, a          # loanword absorption (ฝรั่งเศส ∈ loan lex)
    a = annotate("เขาใช้คอมพิวเตอร์ใหม่", "เขาใช้คอมพิวเตอร์ใหม่", loan)
    assert a == [], a                                  # no error -> no edits
    print("  ok: unit cases (vowel native / consonant-pair native / loanword absorption / no-op)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    args = ap.parse_args()
    loan = load_loan_lexicon()
    unit_cases(loan)

    items = [json.loads(l) for l in (HERE / "data" / f"items_{args.split}.jsonl").open(encoding="utf-8")]
    n_match, n_agree = 0, 0
    n_gold, n_unmatched = 0, 0
    per_class = defaultdict(lambda: [0, 0])            # gold class -> [agree, total-matched]
    confusion = Counter()                              # (gold_class, therrant_class)

    for it in items:
        ann = annotate(it["text_wrong"], it["text_correct"], loan)
        stored = it["edits"]
        n_gold += len(stored)
        for s in stored:
            # ThERRANT edit contained in this stored edit's span
            cand = [a for a in ann if s["tcc_start"] <= a.tcc_start and a.tcc_end <= s["tcc_end"]]
            if not cand:
                n_unmatched += 1
                continue
            tk = cand[0].klass
            n_match += 1
            per_class[s["class"]][1] += 1
            confusion[(s["class"], tk)] += 1
            if tk == s["class"]:
                n_agree += 1
                per_class[s["class"]][0] += 1

    overall = n_agree / n_match if n_match else 0.0
    print(f"\nsplit={args.split}  items={len(items)}  gold_edits={n_gold}  "
          f"matched={n_match}  unmatched(span-miss)={n_unmatched}")
    print(f"overall class agreement: {overall:.3f}  (target >= 0.85)")
    print("per-class agreement (gold class -> matched recall):")
    for c in sorted(per_class):
        ok, tot = per_class[c]
        print(f"  {c} {CLASS_NAME.get(c,'?'):16s}: {ok/tot:.3f}  (n={tot})")
    # top off-diagonal confusions
    off = {k: v for k, v in confusion.items() if k[0] != k[1]}
    if off:
        print("top confusions (gold->therrant):",
              ", ".join(f"{g}->{t}:{n}" for (g, t), n in
                        sorted(off.items(), key=lambda kv: -kv[1])[:6]))
    span_recall = n_match / n_gold if n_gold else 0.0
    print(f"span recovery: {span_recall:.3f} of gold edits matched by a ThERRANT span")
    assert overall >= 0.85, f"class agreement {overall:.3f} < 0.85"
    print("\nThERRANT VALIDATION PASSED (>= 0.85)")


if __name__ == "__main__":
    main()
