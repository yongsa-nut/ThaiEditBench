"""
Phase 2 · Step 3 — build the canonical confusion-set.jsonl from the Phase-1
inventory (clean v1 only), applying the authoritative etymology + loanword-
absorption + edit_op + RID verification.

Pipeline per pair:
  1. keep clean_v1 AND NOT context_dependent (the v1 set)
  2. override etymology from phase2/data/etymology_map.jsonl
  3. loanword-absorption: loan -> class 6 (old class -> also_hits);
     a pair previously absorbed but now native -> recompute true mechanism
  4. add edit_op
  5. RID-verify correct ∈ thai_orst_words (flag misses; don't drop)
  6. canonical schema; dedup by normalized wrong; sort by class

Prints CHECK-IN stats (class-6 movement, RID misses). Writes confusion-set.jsonl.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "phase1"))
from classify import classify, normalize
from edit_op import edit_op
from pythainlp.corpus import thai_orst_words

HERE = Path(__file__).resolve().parent
INV = HERE.parent / "error-corpus-inventory.jsonl"
EMAP = HERE / "data" / "etymology_map.jsonl"
OUT = HERE.parent / "confusion-set.jsonl"
CLASS_NAME = {1: "tone_mark", 2: "consonant_pair", 3: "karan_native",
              4: "vowel", 5: "cluster_metathesis", 6: "loanword_translit",
              0: "unclassified"}
RID = set(thai_orst_words())


def main():
    inv = [json.loads(l) for l in INV.read_text(encoding="utf-8").splitlines()]
    emap = {json.loads(l)["correct"]: json.loads(l)
            for l in EMAP.read_text(encoding="utf-8").splitlines()}

    v1 = [r for r in inv if r["clean_v1"] and not r["context_dependent"]]
    before = Counter(r["mechanism_class"] for r in v1)

    out, seen = [], set()
    moved_to_6, moved_out_6, excluded_0 = 0, 0, 0
    rid_miss = []
    etym_src = Counter()
    for r in v1:
        w, c = normalize(r["wrong"]), normalize(r["correct"])
        if w in seen:
            continue
        seen.add(w)
        # etymology: Wiktionary category is authoritative; otherwise preserve
        # the botfix HAND-LABELED loans (class-6 gold); else default native
        # (Phase-1 note-based loan guesses are dropped as unreliable). Keep
        # Phase-1 proper-noun tags.
        em = emap.get(c, {})
        em_etym = em.get("etymology") if em.get("etym_source") == "wiktionary-category" else None
        is_botfix6 = ("botfix" in r["sources"]) and r["mechanism_class"] == 6
        if em_etym == "loan" or is_botfix6:
            etym = "loan"
        elif em_etym == "native":
            etym = "native"
        else:
            etym = "proper-noun" if r["etymology"] == "proper-noun" else "native"
        etym_src[em.get("etym_source", "default") if em_etym else
                 ("botfix-gold" if is_botfix6 else "default")] += 1
        cls = r["mechanism_class"]
        also = list(r["also_hits"])
        # loanword-absorption applies to LOANWORDS only (§3d). Native Thai /
        # Sanskrit-derived proper nouns (นภดล, องคุลิมาล) keep their mechanism.
        if etym == "loan":
            if cls != 6:
                also = sorted(set(also + [cls]) - {6})
                cls = 6
                moved_to_6 += 1
        else:  # native or proper-noun
            if cls == 6:                      # previously absorbed -> recompute true mechanism
                res = classify(w, c, etymology="native")
                cls, also = res["primary_class"], res["also_hits"]
                moved_out_6 += 1
        if cls == 0:                          # unclassified edge cases (abbrev/
            excluded_0 += 1                   # symbol/mixed) -> not a mechanism;
            continue                          # kept in inventory, out of confusion set
        if c not in RID:
            rid_miss.append((w, c))
        out.append(dict(
            **{"class": CLASS_NAME[cls]},
            class_id=cls, wrong=w, correct=c,
            correct_alts=r.get("correct_alts", []),
            etymology=etym, origin=em.get("origin", ""),
            edit_op=edit_op(w, c), also_hits=also,
            mechanism_detail=r["mechanism_detail"],
            sources=r["sources"], rid_entry=r["rid_citation"],
            rid_verified=(c in RID), license="CC BY-SA"))

    out.sort(key=lambda r: (r["class_id"], r["wrong"]))
    with OUT.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    after = Counter(r["class_id"] for r in out)
    print(f"=== confusion-set.jsonl: {len(out)} pairs "
          f"({excluded_0} class-0 edge cases excluded) ===\n")
    print(f"{'class':<22}{'before':>8}{'after':>8}{'Δ':>6}")
    for k in [1, 2, 3, 4, 5, 6, 0]:
        print(f"{k} {CLASS_NAME[k]:<20}{before.get(k,0):>8}{after.get(k,0):>8}"
              f"{after.get(k,0)-before.get(k,0):>+6}")
    print(f"\nETYMOLOGY RE-TAG: {moved_to_6} pairs absorbed INTO class 6; "
          f"{moved_out_6} moved OUT of 6 to mechanism")
    print(f"class 6: {before.get(6,0)} (floor) -> {after.get(6,0)}")
    print("etymology source:", dict(etym_src))
    print(f"\nedit_op:", dict(Counter(r['edit_op'] for r in out)))
    print(f"\nRID-verify (thai_orst_words): {len(out)-len(rid_miss)}/{len(out)} "
          f"= {(len(out)-len(rid_miss))/len(out):.1%} verified; {len(rid_miss)} misses")
    print("  sample misses:", [c for _, c in rid_miss[:15]])


if __name__ == "__main__":
    main()
