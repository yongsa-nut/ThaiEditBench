"""
Extract the hand-classified entries from subtask2/typo-classification.html.

This file is the บอตแก้คำผิด list (Source 2) already classified into the 6
mechanism classes and user-approved (2026-04-16). It serves two purposes:
  (1) harvested Source-2 data for the inventory, and
  (2) the gold-label set for validating phase1/classify.py.

Outputs phase1/data/botfix_gold.jsonl with fields:
  wrong, correct, gold_class (1-6, 0=uncertain), mechanism, variants
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE.parent / "typo-classification.html"
OUT = HERE / "data" / "botfix_gold.jsonl"

# Each entry line looks like:
#   { wrong: "กระทั้ง", correct: "กระทั่ง", cat: 1, mechanism: "...", variants: "" },
ENTRY_RE = re.compile(
    r'\{\s*wrong:\s*"([^"]*)",\s*correct:\s*"([^"]*)",\s*cat:\s*(\d+),'
    r'\s*mechanism:\s*"([^"]*)",\s*variants:\s*"([^"]*)"\s*\}'
)


def main():
    text = HTML.read_text(encoding="utf-8")
    rows = []
    for m in ENTRY_RE.finditer(text):
        wrong, correct, cat, mech, variants = m.groups()
        rows.append(dict(wrong=wrong, correct=correct, gold_class=int(cat),
                         mechanism=mech, variants=variants))
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"extracted {len(rows)} entries -> {OUT}")
    # class distribution
    from collections import Counter
    dist = Counter(r["gold_class"] for r in rows)
    for k in sorted(dist):
        print(f"  class {k}: {dist[k]}")


if __name__ == "__main__":
    main()
