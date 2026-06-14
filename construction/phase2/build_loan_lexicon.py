"""
Phase 2 · Step 1 — etymology resolver (the loanword-lexicon pass deferred from
Phase 1). Rather than download whole category memberships, we batch-query the
Wiktionary categories of OUR correct forms (prop=categories, 50 titles/req) and
decide etymology from the "ศัพท์ภาษาไทยที่ยืมมาจากภาษา{LANG}" (borrowed-from-LANG)
categories.

Taxonomy split (subtask2/plan.md §5): loan = contemporary FOREIGN origins
(English/French/Japanese/Chinese/…). The Indic-classical + Mon-Khmer + Tai
substrate (Pali/Sanskrit/Khmer/Mon/คำเมือง/ลาว/อีสาน/…) is NATIVE-integrated and
is NOT loan. A transliteration heuristic covers forms with no Wiktionary entry.

Output: phase2/data/etymology_map.jsonl  (correct -> etymology, origin, source)
"""
import json
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
INV = HERE.parent / "error-corpus-inventory.jsonl"
OUT = HERE / "data" / "etymology_map.jsonl"
API = "https://th.wiktionary.org/w/api.php"
UA = "ThaiEditBench-research/0.1 (academic; anonymous@example.com)"
S = requests.Session(); S.headers["User-Agent"] = UA

BORROW_PREFIX = "ศัพท์ภาษาไทยที่ยืมมาจากภาษา"
# Origins treated as NATIVE (not class-6 loan). Two groups:
#  (a) Indic-classical + Mon-Khmer + Tai substrate (taxonomy §5: native-integrated)
#  (b) OLD fully-naturalized loans (Check-in decision): the taxonomy reserves
#      'loan' for *contemporary* foreign langs; pre-modern integrated loans
#      (Tamil/Persian/Burmese/Malay/Portuguese/Hindi/Arabic…) behave native
#      orthographically (กะปิ, กะหรี่, กะละแม, สบู่, อะไหล่) -> mechanism class.
NATIVE_ROOTS = [  # (a) substrate
    "บาลี", "สันสกฤต", "เขมร", "มอญ", "คำเมือง", "อีสาน", "ลาว", "ปักษ์ใต้",
    "ไทลื้อ", "ไทใหญ่", "เขิน", "จ้วง", "ร่วม", "กูย", "ชอง", "เลอเวือะ",
    "กะเหรี่ยง", "จาม",
    # (b) old-integrated loans -> native
    "ทมิฬ", "เปอร์เซีย", "พม่า", "มาเลเซีย", "มลายู", "ชวา", "โปรตุเกส",
    "ฮินดี", "อาหรับ", "เบงกอล", "เนปาล", "คุชราต",
]
THANTHAKHAT = "์"
INDIC_KARAN_OK = set("รนลยวคชญฑฒณธภศษส")  # consonants that legit take ์ in native S/P words


def origin_of(cat: str):
    """If cat is a borrowed-from-language category, return (lang, is_loan)."""
    if not cat.startswith(BORROW_PREFIX):
        return None
    lang = cat[len(BORROW_PREFIX):]
    is_native = any(root in lang for root in NATIVE_ROOTS)
    return lang, (not is_native)


def fetch_categories(titles):
    """Batched prop=categories. Returns {title: [category,...]}."""
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        p = {"action": "query", "prop": "categories", "titles": "|".join(batch),
             "cllimit": "500", "format": "json", "formatversion": "2"}
        cont = {}
        while True:
            pp = dict(p); pp.update(cont)
            r = S.get(API, params=pp, timeout=30).json()
            for pg in r.get("query", {}).get("pages", []):
                cats = [c["title"].replace("หมวดหมู่:", "")
                        for c in pg.get("categories", [])]
                out.setdefault(pg["title"], []).extend(cats)
            if "continue" in r:
                cont = r["continue"]
            else:
                break
        sys.stderr.write(f"  fetched {min(i+50,len(titles))}/{len(titles)}\n")
    return out


def heuristic_loan(correct: str, note: str) -> bool:
    """Fallback for forms with no Wiktionary categories: transliteration cues."""
    if re.search(r"[A-Za-z]", note):
        return True
    # การันต์ on a consonant that doesn't take silent-marker in native S/P words
    for i, ch in enumerate(correct):
        if ch == THANTHAKHAT and i > 0 and correct[i-1] not in INDIC_KARAN_OK:
            return True
    return False


def main():
    rows = [json.loads(l) for l in INV.read_text(encoding="utf-8").splitlines()]
    forms = sorted({r["correct"] for r in rows})
    note_by_form = {r["correct"]: r.get("note", "") for r in rows}
    cats = fetch_categories(forms)

    out = []
    n_loan_wikt = 0
    for f in forms:
        origins = [origin_of(c) for c in cats.get(f, [])]
        origins = [o for o in origins if o]
        loan_langs = [lang for lang, is_loan in origins if is_loan]
        native_langs = [lang for lang, is_loan in origins if not is_loan]
        # Wiktionary categories ONLY -- the transliteration/note heuristic was
        # dropped (it read English mechanism-descriptions in `note` and
        # mislabeled native words like กระทั่ง/คำนวณ as loan). Authoritative only.
        if loan_langs:
            etym, origin, src = "loan", loan_langs[0], "wiktionary-category"
            n_loan_wikt += 1
        elif native_langs:
            etym, origin, src = "native", native_langs[0], "wiktionary-category"
        else:
            etym, origin, src = "native", "", "default"
        out.append(dict(correct=f, etymology=etym, origin=origin,
                        etym_source=src, wikt_categories=cats.get(f, [])))

    with OUT.open("w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"resolved {len(out)} correct forms -> {OUT.name}")
    print(f"  loan (Wiktionary category): {n_loan_wikt}   native: {len(out)-n_loan_wikt}")


if __name__ == "__main__":
    main()
