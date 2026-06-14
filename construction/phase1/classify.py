"""
Phase 1 heuristic mechanism-class pre-classifier for Thai orthographic errors.

Given a (wrong, correct) pair, diff at TCC level and infer which of the 6
EditingBench mechanism classes the error belongs to. This is a *suggester*
with a confidence score + flag for manual review -- NOT the Phase-6 ThERRANT
scorer. Low-confidence / multi-mechanism / unclassifiable rows are flagged so
they surface as taxonomy-gap signal at Check-in 1.

Classes (subtask2/plan.md s4):
  1 tone-mark      2 consonant-pair   3 karan (native)
  4 vowel/sara     5 cluster/metathesis   6 loanword transliteration
  0 = unclassifiable / multi-class -> flag for review

Loanword-absorption rule (s3d): if etymology == 'loan'/'proper-noun', the
class is forced to 6 regardless of mechanism; the true mechanism is recorded
in also_hits.
"""
import unicodedata
from difflib import SequenceMatcher

try:
    from pythainlp.tokenize import tcc
    _HAS_TCC = True
except Exception:  # pragma: no cover - pythainlp always present in this env
    _HAS_TCC = False

# --- Thai Unicode mark sets -------------------------------------------------
TONE_MARKS = set("่้๊๋")      # ่ ้ ๊ ๋
MAITAIKHU = "็"                                # ็ (short-vowel mark; class 1 per taxonomy table)
THANTHAKHAT = "์"                              # ์ การันต์ (silent marker)
PHINTHU = "ฺ"                                  # ฺ
TONE_LIKE = TONE_MARKS | {MAITAIKHU}

# Above/below/leading/trailing vowel signs + the standalone vowels
VOWEL_SIGNS = set("ะัาำิีึื"
                  "ุูเแโใไๅํ")
#  ะ ั า ำ ิ ี ึ ื ุ ู เ แ โ ใ ไ ฯ-ish ํ(nikhahit)
LONG_SHORT_PAIRS = [("ิ", "ี"), ("ึ", "ื"), ("ุ", "ู")]  # ิ/ี ึ/ื ุ/ู

CONSONANTS = set(chr(c) for c in range(0x0e01, 0x0e2f))  # ก..ฮ (incl ฤ ฦ region handled below)
CONSONANTS |= set("ฤฦ")  # ฤ ฦ

# Consonant confusion groups: Indic-etymology homophones only (Check-in 1
# decision -- faithful to the locked class-2 definition). Each group pairs an
# Indic-origin letter (ฆ ฌ ฎ ฏ ฐ ฑ ฒ ณ ธ ภ ศ ษ ฬ) with its modern-sound
# siblings. Pure non-Indic homophones (ฝ/ฟ, ห/ฮ) are NOT here -> they stay
# in class 5.
CONFUSION_GROUPS = [
    set("ขคฆ"),       # kʰ  (ฆ Indic)
    set("ฉชฌ"),       # tɕʰ (ฌ Indic)
    set("ฎฏ"),            # retroflex stops (locked)
    set("ฐฑฒถทธ"),  # tʰ  (locked ฑ/ท, ท/ธ)
    set("ณน"),            # n   (ณ Indic; locked)
    set("บป"),            # final stop (locked)
    set("ศษส"),       # s   (locked)
    set("พภ"),            # pʰ  (ภ Indic)
    set("ญย"),            # j   (ญ Indic)
    set("ฬล"),            # l   (ฬ Indic)
]


def normalize(s: str) -> str:
    """NFC compose (sara-am stays composed per Q2.4); strip spaces."""
    return unicodedata.normalize("NFC", s).strip()


def char_class(ch: str) -> str:
    if ch in TONE_LIKE:
        return "tone"
    if ch == THANTHAKHAT:
        return "karan"
    if ch in VOWEL_SIGNS:
        return "vowel"
    if ch in CONSONANTS:
        return "consonant"
    return "other"


def _changed_chars(wrong: str, correct: str):
    """Return (removed, added) character multisets across the diff."""
    sm = SequenceMatcher(None, wrong, correct, autojunk=False)
    removed, added = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            removed.extend(wrong[i1:i2])
        if tag in ("replace", "insert"):
            added.extend(correct[j1:j2])
    return removed, added


def _is_confusion_pair(removed_cons, added_cons) -> bool:
    for r in removed_cons:
        for a in added_cons:
            if r == a:
                continue
            for g in CONFUSION_GROUPS:
                if r in g and a in g:
                    return True
    return False


def _is_reorder(wrong: str, correct: str) -> bool:
    return wrong != correct and sorted(wrong) == sorted(correct)


def _is_gemination(removed, added) -> bool:
    # one side has a doubled consonant the other lacks (e.g. ต -> ตต)
    rc = [c for c in removed if c in CONSONANTS]
    ac = [c for c in added if c in CONSONANTS]
    return (len(ac) - len(rc)) != 0 and bool(set(rc) & set(ac))


def _karan_cluster_sig(s: str):
    """Signature of the consonant(s) immediately preceding each ์.
    Differing signatures => a การันต์-cluster change (e.g. ต์ vs ตร์,
    ล์ vs ฟ์). Captured as class 3 (silent-marker cluster) per s4."""
    sigs = []
    for i, ch in enumerate(s):
        if ch == THANTHAKHAT:
            # the single consonant the silent marker sits on
            sigs.append(s[i - 1] if i > 0 and s[i - 1] in CONSONANTS else "")
    return sigs


def _karan_involved(w: str, c: str) -> bool:
    if THANTHAKHAT in (w + c) and (w.count(THANTHAKHAT) != c.count(THANTHAKHAT)):
        return True
    return _karan_cluster_sig(w) != _karan_cluster_sig(c)


def _rr_an_alternation(w: str, c: str) -> bool:
    # รร <-> ัน structural alternation (บรรได <-> บันได)
    return (("รร" in w) and ("ัน" in c)) or (("ัน" in w) and ("รร" in c))


def _syllable_indel(removed, added) -> bool:
    """A contiguous vowel+consonant chunk inserted or deleted (spurious /
    missing syllable, e.g. เยอรมันนี -> เยอรมนี drops ัน)."""
    for chunk in (removed, added):
        has_v = any(char_class(ch) == "vowel" for ch in chunk)
        has_c = any(ch in CONSONANTS for ch in chunk)
        if has_v and has_c and len(chunk) >= 2:
            return True
    return False


def classify(wrong: str, correct: str, etymology: str = "native") -> dict:
    """Return {primary_class, also_hits, confidence, flag, mechanism_detail}."""
    w, c = normalize(wrong), normalize(correct)
    if w == c:
        return dict(primary_class=0, also_hits=[], confidence=0.0,
                    flag="identical", mechanism_detail="wrong == correct after NFC")

    removed, added = _changed_chars(w, c)
    changed = removed + added

    cons_removed = [ch for ch in removed if ch in CONSONANTS]
    cons_added = [ch for ch in added if ch in CONSONANTS]
    cons_changed = bool(cons_removed or cons_added)

    # mechanism signals (a pair may trip several)
    sig = {}
    sig[3] = _karan_involved(w, c)                                  # การันต์ / silent-marker cluster
    sig[5] = (_is_reorder(w, c) or _rr_an_alternation(w, c)
              or _is_gemination(removed, added) or _syllable_indel(removed, added))
    sig[2] = cons_changed and _is_confusion_pair(cons_removed, cons_added)
    sig[1] = any(char_class(ch) == "tone" for ch in changed)        # tone marks incl ็
    sig[4] = any(char_class(ch) == "vowel" for ch in changed)       # vowel/sara
    sig["cons5"] = cons_changed and not sig[2]                       # non-pair consonant -> cluster

    labels = {1: "tone-mark change", 2: "consonant-pair confusion",
              3: "การันต์ / silent-marker cluster change", 4: "vowel/sara change",
              5: "cluster/metathesis/gemination/syllable change",
              "cons5": "non-pair consonant change (cluster)"}
    detail = [labels[k] for k in (3, 5, 2, 1, 4, "cons5") if sig.get(k)]

    # Priority for the PRIMARY class (taxonomy intent): a consonant-pair swap
    # (incl. one sitting under a ์) is class 2; then การันต์ cluster, then
    # structural metathesis, tone, vowel; fallback = non-pair consonant.
    order = [2, 3, 5, 1, 4]
    hits = [k for k in order if sig.get(k)]
    if not hits and sig["cons5"]:
        hits = [5]

    # Loanword absorption: force class 6, keep true mechanism in also_hits
    if etymology in ("loan", "proper-noun"):
        return dict(primary_class=6, also_hits=hits,
                    confidence=0.9 if hits else 0.5,
                    flag=None if hits else "loan-no-mechanism",
                    mechanism_detail="; ".join(detail) or "loanword transliteration")

    if not hits:
        return dict(primary_class=0, also_hits=[], confidence=0.0,
                    flag="unclassifiable", mechanism_detail="no Thai-mark change detected")

    primary = hits[0]
    also = hits[1:]
    # confidence: single clean mechanism = high; multi = lower + flag
    if len(hits) == 1:
        conf, flag = 0.9, None
    elif len(hits) == 2:
        conf, flag = 0.6, "multi-mechanism"
    else:
        conf, flag = 0.4, "multi-mechanism"
    return dict(primary_class=primary, also_hits=also, confidence=conf,
                flag=flag, mechanism_detail="; ".join(detail))


# --- Nakwijit 3-question filter (thesis s3.6) -------------------------------
# Keep only UNINTENTIONAL errors from social-media corpora (Sources 3 & 4).
#   Q1 conveys additional meaning/emotion?  YES -> semantic   (drop)
#   Q2 needs more/less effort to type?      YES -> simplified (drop)
#   Q3 outside commonly-known misspellings? NO  -> commonly-known misspelling (keep)
#                                           YES + Q1=NO + Q2=NO -> typo (keep)
# Inverted keep-rule: NOT q1_semantic AND NOT q2_simplified.
def is_unintentional(q1_semantic: bool, q2_simplified: bool) -> bool:
    return (not q1_semantic) and (not q2_simplified)


if __name__ == "__main__":
    # quick smoke
    for w, c, e in [("กระทั้ง", "กระทั่ง", "native"),
                    ("กฏ", "กฎ", "native"),
                    ("โครงการณ์", "โครงการ", "native"),
                    ("สังเกตุ", "สังเกต", "native"),
                    ("ศรีษะ", "ศีรษะ", "native"),
                    ("นิวยอร์ค", "นิวยอร์ก", "loan")]:
        print(w, "->", c, classify(w, c, e))
