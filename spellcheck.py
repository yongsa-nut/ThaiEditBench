"""Strict clean-sentence filter for dataset construction (the Phase-3 lesson).

The original pool used `clean_ratio >= 0.85`, which let residual SOURCE typos
(กฏหมาย, คววม, สำคัฐ, ขัอความ, นำ้ …) ride into golds. This module is the strict
gate: a sentence is clean only if EVERY all-Thai token is in the lexicon
(thai_words ∪ thai_orst_words ∪ confusion-set correct forms).

Known limitation: a typo that fragments into valid tokens (สุดทาย → สุด+ทาย) is
NOT caught by any dictionary check — the cross-model consensus audit
(viz/audit_golds.py --consensus) remains the post-run safety net for those.
"""
from __future__ import annotations

import re

from pythainlp.corpus import thai_words, thai_orst_words
from pythainlp.tokenize import word_tokenize

from inject import load_confusion_set

LEX = set(thai_words()) | set(thai_orst_words())
LEX |= {r["correct"] for r in load_confusion_set()}     # valid forms, incl. loanwords
_THAI_WORD = re.compile(r"^[฀-๿]+$")

# Recurrent source typos that FRAGMENT into in-lexicon tokens (so the dict gate misses
# them) — seeded from confirmed T1+T2 consensus-audit defects. Distinctive multi-char
# strings that don't occur inside correct words, so substring rejection is safe. Grows
# as the audit finds more. (The cross-model consensus audit remains the final net.)
KNOWN_TYPOS = (
    "กฏหมาย", "คววม", "สุดทาย", "ขัอความ", "นำ้", "คุลม", "ยุทธ์ศาสตร์", "บุเบกษา",
    "สถานะภาพ", "มันใจ", "ต้างมี", "คุ้มคลั่ง", "อัชญลี", "เปล๊า", "จันทรโอชา",
    "ทั้งสิน", "ปฏิเศษ", "ลักษร", "ทำแผลทั่ง", "ชั่งโมง",
)


def unknown_thai_tokens(s: str) -> list[str]:
    """All-Thai tokens (any length) not in the lexicon — i.e. typos or proper nouns."""
    return [t for t in word_tokenize(s, engine="newmm")
            if _THAI_WORD.match(t) and t not in LEX]


def is_clean(s: str) -> bool:
    """Strict: no out-of-lexicon Thai token AND no known fragmentable typo substring."""
    if any(t in s for t in KNOWN_TYPOS):
        return False
    return not unknown_thai_tokens(s)


if __name__ == "__main__":
    typos = ["ทำผิดกฏหมาย", "ระบบที่มีคววมซับซ้อน", "บทบาทสำคัฐ", "การใช้ขัอความ", "สถานการณ์นำ้"]
    clean = ["ระบบนี้มีความซับซ้อนสูงมาก", "เขาทำงานอย่างตั้งใจและรอบคอบเสมอ"]
    print("typos (expect unknown tokens flagged):")
    for s in typos:
        print(f"  is_clean={is_clean(s)!s:5} unknown={unknown_thai_tokens(s)}  {s}")
    print("clean (expect is_clean=True):")
    for s in clean:
        print(f"  is_clean={is_clean(s)!s:5} unknown={unknown_thai_tokens(s)}  {s}")
