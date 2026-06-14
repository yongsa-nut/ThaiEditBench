"""
Source 7: Thai Deaf Corpus (Supachan/ThaiDeafCorpus, 22,718 sentence rows).
Format per line: wrong|||correct_ref1|||correct_ref2...

These are mostly sentence-level GRAMMAR / word-order / word-choice edits
(sign-language transfer) -- the plan says to filter those OUT and keep only
character-level orthographic substitutions. We tokenize (newmm), align
wrong vs the first correct ref, and keep only 1-token<->1-token 'replace'
ops whose two tokens are a small character-level edit (orthographic), i.e.
the same word misspelled -- not a different word.

Output: phase1/data/deaf_pairs.jsonl  (+ stats)
"""
import json
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from pythainlp.tokenize import word_tokenize
from classify import classify, normalize, CONSONANTS

HERE = Path(__file__).resolve().parent
SRC = HERE / "data" / "thai_deaf_corpus.txt"
OUT = HERE / "data" / "deaf_pairs.jsonl"


def char_edit_distance(a: str, b: str) -> int:
    # Levenshtein on code points (cheap; pairs are short)
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (a[i-1] != b[j-1]))
            prev = cur
    return dp[n]


def orthographic_subs(wrong: str, correct: str):
    """1-token<->1-token replacements that are small char-level edits."""
    wt = word_tokenize(wrong, engine="newmm")
    ct = word_tokenize(correct, engine="newmm")
    out = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, wt, ct).get_opcodes():
        if tag == "replace" and (i2 - i1) == 1 and (j2 - j1) == 1:
            w, c = normalize(wt[i1]), normalize(ct[j1])
            if w == c or " " in w + c:
                continue
            d = char_edit_distance(w, c)
            # same-word misspelling: small edit, similar length, shares most chars
            if d <= 2 and abs(len(w) - len(c)) <= 2 and min(len(w), len(c)) >= 2 \
                    and any(ch in CONSONANTS for ch in w):
                out.append((w, c))
    return out


def main():
    pairs = Counter()
    n_lines = 0
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if "|||" not in line:
            continue
        n_lines += 1
        parts = [p for p in line.split("|||") if p.strip()]
        if len(parts) < 2:
            continue
        wrong, correct = parts[0], parts[1]
        for pr in orthographic_subs(wrong, correct):
            pairs[pr] += 1
    rows, cls = [], Counter()
    for (w, c), f in pairs.items():
        res = classify(w, c, etymology="native")
        cls[res["primary_class"]] += 1
        rows.append(dict(source="deaf", wrong=w, correct=c, freq=f,
                         mechanism_class=res["primary_class"], flag=res["flag"],
                         mechanism_detail=res["mechanism_detail"]))
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"scanned {n_lines} sentence rows -> {len(rows)} unique char-level "
          f"orthographic pairs (rest are grammar/word-order, filtered out)")
    print("class distribution:", {k: cls[k] for k in sorted(cls)})
    for r in sorted(rows, key=lambda x: -x["freq"])[:20]:
        print(f"  {r['wrong']} -> {r['correct']}  cls={r['mechanism_class']} (freq {r['freq']})")


if __name__ == "__main__":
    main()
