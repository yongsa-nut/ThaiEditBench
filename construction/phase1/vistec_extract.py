"""
Source 3: VISTEC-TP-TH-2021 (49,997 Twitter sentences; mrpeerat/OSKut mirror).

Misspellings are tagged inline: <msp value="CORRECT">WRONG</msp>.
VISTEC's tags do NOT carry Nakwijit's intentional/unintentional label, so we
apply a HEURISTIC proxy for the inverted 3-question filter (true separation
needs annotation -> Phase 5). Buckets:
  - spacing      : space / ไม้ยมก (ๆ) spacing differences        (§2 deferred)
  - multiword    : multi-token value                             (§2 deferred)
  - truncation   : wrong is a shortening of correct (โทร/โทรศัพท์) -> Nakwijit "simplified" (drop)
  - context_dep  : curated real-word confusion                   (-> v2)
  - ortho        : single-word character-level error             (V1 KEEP -> classify)

For the ortho bucket we tally the class distribution and isolate
**keyboard-slip candidates** (the 7th-class watch): single-consonant
substitutions that fall to class 5's non-pair fallback, or doubled-letter
insertions -- i.e. errors with no class 1-4 linguistic pattern.

Output: phase1/data/vistec_pairs.jsonl  (+ printed stats)
"""
import json
import re
from collections import Counter
from pathlib import Path

from classify import classify, normalize, CONSONANTS, CONFUSION_GROUPS, char_class
from realword_pairs import is_context_dependent

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA / "vistec_pairs.jsonl"
MSP = re.compile(r'<msp value="([^"]*)">(.*?)</msp>')
TAG = re.compile(r"</?(?:ne|ab|compound)>")


_RUN = re.compile(r"(.)\1+")


def _collapse(s: str) -> str:
    return _RUN.sub(r"\1", s)


def bucket(wrong: str, correct: str) -> str:
    if " " in wrong or " " in correct or "ๆ" in (wrong + correct):
        return "spacing"
    # intentional elongation/repetition (Nakwijit semantic, Q1=YES) -> drop:
    # the two are equal once runs of repeated chars are collapsed
    if _collapse(wrong) == _collapse(correct):
        return "repetition"
    if len(wrong) < len(correct) and (correct.startswith(wrong) or
                                       len(correct) - len(wrong) >= 3):
        return "truncation"
    if is_context_dependent(wrong, correct):
        return "context_dep"
    return "ortho"


def is_keyboard_slip_candidate(wrong: str, correct: str, res: dict) -> bool:
    """A single-consonant non-pair substitution (class-5 fallback) or a
    doubled-letter indel -- an error with no class 1-4 linguistic pattern."""
    if res["primary_class"] not in (5, 0):
        return False
    from difflib import SequenceMatcher
    rem, add = [], []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, wrong, correct).get_opcodes():
        if tag in ("replace", "delete"):
            rem += list(wrong[i1:i2])
        if tag in ("replace", "insert"):
            add += list(correct[j1:j2])
    # doubled letter
    if sorted(rem) != sorted(add) and len(rem) + len(add) <= 2:
        only = rem + add
        if all(ch in CONSONANTS for ch in only):
            in_pair = any(any(ch in g for g in CONFUSION_GROUPS) for ch in only)
            return not in_pair
    return False


def main():
    pairs = Counter()  # (wrong,correct) -> frequency
    for name in ("train", "test"):
        text = (DATA / f"vistec_{name}.txt").read_text(encoding="utf-8")
        for correct, wrong in MSP.findall(text):
            w = normalize(TAG.sub("", wrong))
            c = normalize(TAG.sub("", correct))
            if w and c and w != c:
                pairs[(w, c)] += 1

    rows, bcount = [], Counter()
    cls_dist = Counter()
    kbd = []
    for (w, c), freq in pairs.items():
        b = bucket(w, c)
        bcount[b] += 1
        rec = dict(source="vistec", wrong=w, correct=c, freq=freq, vistec_bucket=b)
        if b == "ortho":
            res = classify(w, c, etymology="native")
            rec.update(mechanism_class=res["primary_class"], also_hits=res["also_hits"],
                       confidence=res["confidence"], flag=res["flag"],
                       mechanism_detail=res["mechanism_detail"])
            cls_dist[res["primary_class"]] += 1
            if is_keyboard_slip_candidate(w, c, res):
                rec["keyboard_slip_candidate"] = True
                kbd.append((w, c, freq))
        rows.append(rec)

    rows.sort(key=lambda r: -r["freq"])
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total_tagged = sum(pairs.values())
    print(f"VISTEC <msp> tags: {total_tagged} total, {len(pairs)} unique (wrong,correct)")
    print("buckets:", dict(bcount))
    print(f"\northo bucket class distribution ({sum(cls_dist.values())} unique):")
    for k in [1, 2, 3, 4, 5, 0]:
        if cls_dist[k]:
            print(f"  class {k}: {cls_dist[k]}")
    print(f"\nKEYBOARD-SLIP candidates (7th-class watch): {len(kbd)} unique")
    for w, c, fr in sorted(kbd, key=lambda x: -x[2])[:25]:
        print(f"  {w} -> {c}   (freq {fr})")


if __name__ == "__main__":
    main()
