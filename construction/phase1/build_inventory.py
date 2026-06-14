"""
Assemble the Phase-1 error-corpus inventory from the harvested sources.

Inputs (Sources 1 & 2, the RID-sourced seed):
  data/wiktionary_pairs.jsonl   (Source 1, scraped)
  data/botfix_gold.jsonl        (Source 2, hand-classified in typo-classification.html)

For each (wrong, correct) pair:
  - NFC normalize (Q2.4)
  - mechanism_class: trust botfix gold label; else heuristic classify()
  - etymology: heuristic (native / loan / proper-noun)
  - context_dependent: True if the WRONG form is itself a valid Thai word
    (real-word confusion -> route to v2, NOT v1)
  - rid_citation: dictionary.orst.go.th lemma (these lists are RID-backed)
  - dedup across sources by normalized wrong form

Output: error-corpus-inventory.jsonl  (+ printed stats)
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from classify import classify, normalize
from realword_pairs import is_context_dependent
from pythainlp.corpus import thai_words

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE.parent / "error-corpus-inventory.jsonl"   # final deliverable location

THAI_DICT = set(thai_words())   # informational only (in_lexicon); not used to route v2

FOREIGN_LANG = ["อังกฤษ", "ฝรั่งเศส", "ญี่ปุ่น", "จีน", "เยอรมัน", "อิตาลี",
                "สเปน", "โปรตุเกส", "ดัตช์", "ฮอลันดา", "รัสเซีย", "เกาหลี",
                "ละติน", "ลาติน", "กรีก", "อาหรับ", "มลายู"]
PROPER_KW = ["วิสามานยนาม", "ชื่อประเทศ", "ชื่อเมือง", "ยี่ห้อ", "ชื่อบุคคล",
             "ชื่อเฉพาะ", "ชื่อจังหวัด"]
CLASS_NAME = {1: "tone_mark", 2: "consonant_pair", 3: "karan_native",
              4: "vowel", 5: "cluster_metathesis", 6: "loanword_translit",
              0: "UNCLASSIFIED"}


def guess_etymology(correct: str, note: str) -> str:
    if any(k in note for k in PROPER_KW):
        return "proper-noun"
    if re.search(r"[A-Za-z]", note) or any(k in note for k in FOREIGN_LANG):
        return "loan"
    return "native"   # incl. Pali/Sanskrit/Khmer-integrated (taxonomy: native)


def rid_cite(correct: str) -> str:
    return f"https://dictionary.orst.go.th/ (lemma: {correct})"


def cleanliness(w: str, c: str):
    """Is this a clean v1 candidate (single-token, character-level, same word)?
    Returns (clean_v1: bool, reason: str). Non-clean items are kept in the
    inventory but excluded from the v1 class distribution and flagged."""
    if " " in w or " " in c:
        return False, "multi-token/spacing (deferred §2)"
    if any(ch in (w + c) for ch in "()（）"):
        return False, "parse-artifact/parenthesis"
    if w.endswith("-") or c.endswith("-") or w.startswith("-") or c.startswith("-"):
        return False, "fragment (dash)"
    if abs(len(w) - len(c)) >= 4:
        return False, "large length diff (likely whole-word/phrase)"
    return True, ""


def load_wiktionary():
    rows = []
    for line in (DATA / "wiktionary_pairs.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows.append(dict(source="wiktionary", wrong=r["wrong"], correct=r["correct"],
                         note=r.get("note", ""), gold_class=None,
                         correct_alts=r.get("correct_alts", [])))
    return rows


def load_botfix():
    rows = []
    for line in (DATA / "botfix_gold.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows.append(dict(source="botfix", wrong=r["wrong"], correct=r["correct"],
                         note=r.get("mechanism", ""), gold_class=r["gold_class"],
                         correct_alts=[]))
    return rows


def build():
    raw = load_botfix() + load_wiktionary()   # botfix first => its gold wins on dedup
    seen = {}
    out = []
    for r in raw:
        w = normalize(r["wrong"])
        c = normalize(r["correct"])
        if w == c or not w or not c:
            continue
        if w in seen:
            seen[w]["sources"] = sorted(set(seen[w]["sources"] + [r["source"]]))
            continue
        etym = guess_etymology(c, r["note"])
        # mechanism: trust botfix gold; else heuristic
        if r["gold_class"] is not None:
            mech = r["gold_class"]
            if mech == 6:
                etym = "loan"
            conf, flag, detail = 1.0, None, "botfix hand-label"
            also = []
        else:
            res = classify(w, c, etymology=etym)
            mech = res["primary_class"]
            also = res["also_hits"]
            conf, flag, detail = res["confidence"], res["flag"], res["mechanism_detail"]
        # context_dependent (-> v2) from the CURATED real-word list (Check-in 1
        # decision). in_lexicon kept only as an informational signal.
        ctx = is_context_dependent(w, c)
        clean_v1, reason = cleanliness(w, c)
        rec = dict(source=r["source"], sources=[r["source"]], wrong=w, correct=c,
                   correct_alts=r["correct_alts"],
                   mechanism_class=mech, mechanism_name=CLASS_NAME[mech],
                   also_hits=also, etymology=etym,
                   context_dependent=ctx, in_lexicon=(w in THAI_DICT),
                   clean_v1=clean_v1, filter_reason=reason,
                   confidence=conf, flag=flag, mechanism_detail=detail,
                   note=r["note"], rid_citation=rid_cite(c))
        seen[w] = rec
        out.append(rec)

    with OUT.open("w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- stats ----
    print(f"TOTAL unique pairs: {len(out)}  -> {OUT.name}")
    by_src = Counter(s for rec in out for s in rec["sources"])
    print("by source (incl. dedup overlap):", dict(by_src))
    clean = [r for r in out if r["clean_v1"]]
    v1 = [r for r in clean if not r["context_dependent"]]   # v1 = clean & not real-word
    print(f"\nclean_v1: {len(clean)}   needs-filtering: {len(out)-len(clean)}"
          f"   v1 (clean & not context-dep): {len(v1)}")
    print("  filter reasons:", dict(Counter(r["filter_reason"] for r in out if not r["clean_v1"])))
    print("\nmechanism x etymology (v1 set):")
    grid = defaultdict(Counter)
    for rec in v1:
        grid[rec["mechanism_class"]][rec["etymology"]] += 1
    print(f"{'class':<22}{'native':>8}{'loan':>8}{'proper':>8}{'total':>8}")
    for k in [1, 2, 3, 4, 5, 6, 0]:
        n = grid[k]["native"]; l = grid[k]["loan"]; p = grid[k]["proper-noun"]
        if n + l + p == 0:
            continue
        print(f"{k} {CLASS_NAME[k]:<20}{n:>8}{l:>8}{p:>8}{n+l+p:>8}")
    ctx = sum(1 for r in out if r["context_dependent"])
    flagged = sum(1 for r in v1 if r["flag"])
    unclass = sum(1 for r in v1 if r["mechanism_class"] == 0)
    print(f"\ncontext_dependent (curated, -> v2): {ctx}")
    print(f"flagged for review (multi/low-conf): {flagged}")
    print(f"UNCLASSIFIED (class 0) within v1: {unclass}")


if __name__ == "__main__":
    build()
