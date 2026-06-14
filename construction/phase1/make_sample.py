"""
Build the ~50-item stratified Check-in 1 sample from error-corpus-inventory.jsonl.

Stratifies across the 6 mechanism classes x etymology and deliberately
oversamples edge cases (class 0, real-word candidates, needs-filtering,
multi-mechanism flags) so the user can rule on taxonomy gaps. Deterministic
(seed=42). Writes a Markdown table to phase1/data/sample.md.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
INV = HERE.parent / "error-corpus-inventory.jsonl"
OUT = HERE / "data" / "sample.md"
random.seed(42)


def row_md(r):
    flags = []
    if r["context_dependent"]:
        flags.append("ctx-dep→v2")
    if not r["clean_v1"]:
        flags.append(r["filter_reason"].split()[0])
    if r["flag"]:
        flags.append(r["flag"])
    also = "+".join(map(str, r["also_hits"])) if r["also_hits"] else ""
    return (f"| {r['wrong']} | {r['correct']} | {r['mechanism_class']} "
            f"| {r['etymology']} | {also} | {'; '.join(flags)} | {r['mechanism_detail'][:38]} |")


def pick(rows, pred, n):
    cand = [r for r in rows if pred(r)]
    random.shuffle(cand)
    return cand[:n]


def main():
    rows = [json.loads(l) for l in INV.read_text(encoding="utf-8").splitlines()]
    chosen, seen = [], set()

    def add(items):
        for r in items:
            if r["wrong"] not in seen:
                seen.add(r["wrong"]); chosen.append(r)

    # ~6 per class from v1 (clean & not context-dep), balancing native/loan
    for k in [1, 2, 3, 4, 5, 6]:
        add(pick(rows, lambda r, k=k: r["clean_v1"] and not r["context_dependent"]
                 and r["mechanism_class"] == k and r["etymology"] != "native", 2))
        add(pick(rows, lambda r, k=k: r["clean_v1"] and not r["context_dependent"]
                 and r["mechanism_class"] == k and r["etymology"] == "native", 4))
    # all class 0
    add(pick(rows, lambda r: r["mechanism_class"] == 0, 8))
    # curated context-dependent (-> v2)
    add(pick(rows, lambda r: r["context_dependent"], 8))
    # needs-filtering contamination examples
    add(pick(rows, lambda r: not r["clean_v1"], 5))

    header = ("| wrong | correct | cls | etym | also | flags | mechanism |\n"
              "|---|---|:--:|---|:--:|---|---|")
    lines = [header] + [row_md(r) for r in chosen]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sample size: {len(chosen)} -> {OUT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
