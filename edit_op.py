"""
Phase 2 · Step 2 — edit_op tagger (the keyboard-slip dimension, orthogonal to
mechanism_class; Phase-1 verdict §4). Describes how the WRONG form differs from
the CORRECT one as an edit operation:

  substitution  — char(s) replaced in place
  insertion     — wrong has extra char(s) the correct form lacks
  deletion      — wrong is missing char(s) the correct form has
  transposition — same characters, reordered (metathesis)
  mixed         — more than one operation type

Reuses classify.normalize. Direction is correct -> wrong (the error).
"""
from difflib import SequenceMatcher

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))   # classify.py lives at the repo root
from classify import normalize


def edit_op(wrong: str, correct: str) -> str:
    w, c = normalize(wrong), normalize(correct)
    if w == c:
        return "none"
    if sorted(w) == sorted(c):
        return "transposition"
    tags = set()
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, c, w, autojunk=False).get_opcodes():
        if tag != "equal":
            tags.add(tag)
    if tags == {"replace"}:
        return "substitution"
    if tags == {"insert"}:
        return "insertion"   # wrong has extra chars vs correct
    if tags == {"delete"}:
        return "deletion"    # wrong is missing chars vs correct
    return "mixed"


if __name__ == "__main__":
    tests = [
        ("กระทั้ง", "กระทั่ง", "substitution"),   # ้ -> ่ in place
        ("สังเกตุ", "สังเกต", "insertion"),         # wrong has extra ุ
        ("ภาพยนต์", "ภาพยนตร์", "deletion"),       # wrong missing ร
        ("ศรีษะ", "ศีรษะ", "transposition"),        # ร/ี reordered
        ("กิติมศักดิ์", "กิตติมศักดิ์", "deletion"),  # missing ต
    ]
    ok = 0
    for w, c, exp in tests:
        got = edit_op(w, c)
        flag = "OK" if got == exp else "**"
        ok += got == exp
        print(f"  {flag} {w} -> {c}: {got} (exp {exp})")
    print(f"{ok}/{len(tests)} expected")
