"""
Phase 4a — filter mined Wikipedia diffs into clean sentence-level items.

Input : data/wiki_raw_pairs.jsonl  (from mine_wiki.py)
Filters (plan.md §6a):
  - both sides single Thai token, len<=30, TCC edit-distance <= 5
  - RID GATE: wrong NOT in lexicon, correct IN lexicon  (kills garbage like the
    pilot's มีการนำ->ป้องกันไม่; LEX = thai_words ∪ thai_orst_words)
  - classify via phase1/classify.classify(); drop class-0 / identical
  - dedup by normalized wrong form; tag confusion-set overlap (novel = bonus)
Then rebuild a sentence-level item from the corrected context line, reusing the
SAME inject() geometry so mined items share the schema + TCC gold spans. Gold is
'annotated' (provisional) — the mined correction needs the Phase-5 human pass.

Output: data/wiki_filtered_pairs.jsonl  (the clean word pairs + class)
        data/wiki_items.jsonl           (sentence-level items, schema.md)
Run:  PYTHONUTF8=1 python filter_diffs.py
"""
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pythainlp.tokenize import tcc, sent_tokenize
from pythainlp.corpus import thai_words, thai_orst_words

from inject import normalize, inject, apply_edits, tcc_segments, CLASS_NAME

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
sys.path.insert(0, str(HERE))                          # classify.py / edit_op.py live at the repo root
from classify import classify                          # noqa: E402
from edit_op import edit_op                            # noqa: E402

RAW = DATA / "wiki_raw_pairs.jsonl"
FILTERED = DATA / "wiki_filtered_pairs.jsonl"
ITEMS = DATA / "wiki_items.jsonl"            # curated subset (consumed by build_dataset)
ITEMS_ALL = DATA / "wiki_items_all.jsonl"    # full yield (appendix / scale-up)
CURATE_TARGET = 40                           # class-balanced high-confidence ship count
MIN_CORRECT_LEN = 3                          # drop <=2-char correct forms (diff fragments)

LEX = set(thai_words()) | set(thai_orst_words())
SEED = 20260524


def tcc_editdist(a, b):
    """Levenshtein at TCC granularity (plan.md §6a edit-distance <=5)."""
    x, y = tcc.segment(a), tcc.segment(b)
    m, n = len(x), len(y)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1,
                        prev + (x[i - 1] != y[j - 1]))
            prev = cur
    return dp[n]


def load_confusion_correct():
    s = set()
    for line in (HERE / "data" / "confusion-set.jsonl").open(encoding="utf-8"):
        s.add(normalize(json.loads(line)["correct"]))
    return s


def repair(s):
    """Same surface repair as the synthetic track: compose decomposed sara-am and
    fix เเ. A pair that is *only* an encoding variation collapses to identical here
    and is not a spelling-mechanism error -> dropped."""
    return s.replace("ํา", "ำ").replace("เเ", "แ")


RESID_MARKUP = set("|{}[]=")                            # markup that survives = non-prose


def strip_wiki(line):
    """Remove templates / refs / links / html so a clean prose sentence can be
    recovered from a Wikipedia diff line (keeping link display text)."""
    line = re.sub(r"<[^>]+>", " ", line)
    line = re.sub(r"\{\{[^{}]*\}\}", " ", line)
    line = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", line)   # [[a|b]] -> b
    line = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", line)      # [url text] -> text
    line = re.sub(r"https?://\S+", " ", line)
    line = re.sub(r"'{2,}", "", line)                              # bold/italic ''' ''
    return line


def passes(w, c):
    """Single Thai token-ish, len bound, edit-distance, RID gate, not encoding-only."""
    if " " in w or " " in c or w == c:
        return False
    if repair(w) == repair(c):                          # encoding-only variation
        return False
    if max(len(w), len(c)) > 30:
        return False
    if min(len(w), len(c)) < 2:                          # drop 1-char fragments (คศ->ค) from
        return False                                     # misaligned multi-change diff lines
    if w[0] != c[0] and w[-1] != c[-1]:                  # a genuine typo shares a prefix OR
        return False                                     # suffix; unrelated del/ins misalignments
    if tcc_editdist(w, c) > 5:                           # (นเรียะคุ->อัง) share neither
        return False
    return (w not in LEX) and (c in LEX)               # RID gate


def main():
    if not RAW.exists():
        print(f"no {RAW.name} — run mine_wiki.py first")
        return
    rng = random.Random(SEED)
    conf_correct = load_confusion_correct()
    # A recurring real typo (ปรากฏ / สังเกต) appears in many articles; each distinct
    # sentence is a genuinely different test item. Keep up to MAX_CTX distinct contexts
    # per wrong-form (dedup identical contexts only) so common typos aren't collapsed to 1.
    MAX_CTX = 2
    ctx_seen, form_n, filtered = defaultdict(set), Counter(), []
    raw_n = 0
    for line in RAW.open(encoding="utf-8"):
        raw_n += 1
        r = json.loads(line)
        w, c = normalize(r["wrong"]), normalize(r["correct"])
        if not passes(w, c):
            continue
        cl_key = re.sub(r"\s+", "", r.get("correct_line", ""))
        if form_n[w] >= MAX_CTX or cl_key in ctx_seen[w]:
            continue
        ctx_seen[w].add(cl_key)
        form_n[w] += 1
        res = classify(w, c, etymology="native")       # etymology unknown -> native default
        if res["primary_class"] == 0:
            continue
        r.update({"wrong": w, "correct": c,
                  "class": res["primary_class"],
                  "class_name": CLASS_NAME[res["primary_class"]],
                  "edit_op": edit_op(w, c),
                  "in_confusion_set": c in conf_correct})
        filtered.append(r)

    with FILTERED.open("w", encoding="utf-8") as f:
        for r in filtered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # rebuild sentence-level items from the corrected context line
    items, idx, no_ctx = [], 0, 0
    for r in filtered:
        line = repair(strip_wiki(normalize(r.get("correct_line", "") or "")))
        if not line or r["correct"] not in line:
            no_ctx += 1
            continue
        # isolate the prose sentence holding the correction; reject if markup survives
        sent = None
        for s in sent_tokenize(line):
            s = re.sub(r"\s+", " ", s).strip(" -*#:!")
            if (r["correct"] in s and 20 <= len(s) <= 200
                    and not (set(s) & RESID_MARKUP)
                    and len(re.findall(r"[฀-๿]", s)) / max(len(s), 1) >= 0.6):
                sent = s
                break
        if sent is None:
            no_ctx += 1
            continue
        pseudo = [{"wrong": r["wrong"], "correct": r["correct"],
                   "class_id": r["class"], "etymology": "native",
                   "edit_op": r["edit_op"]}]
        core = inject(sent, pseudo, n=1, rng=rng)
        if core is None:
            no_ctx += 1
            continue
        items.append({
            "id": f"wik-{idx:06d}", "source_track": "mined",
            "register": "encyclopedic",
            "source_doc": f"thwiki:rev/{r['revid']}←{r['parentid']} ({r['title']})",
            "lang": "th",
            "text_wrong": core["text_wrong"], "text_correct": core["text_correct"],
            "edits": core["edits"], "n_errors": len(core["edits"]),
            "density": "single", "gold_source": "annotated", "verified": False,
            "license": "CC BY-SA", "split": "unassigned",
        })
        idx += 1

    # validate gold invariant
    for it in items:
        assert apply_edits(it["text_wrong"], it["edits"]) == it["text_correct"]

    # full yield -> appendix file
    with ITEMS_ALL.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    # --- CURATE to a class-balanced, high-confidence ship set (~CURATE_TARGET) ---
    # Drop short diff-fragment forms; rank within class by confidence
    # (confusion-set match > longer correct form > recurs in >1 article); fair-share
    # across classes (smallest class first donates its slack to larger ones).
    ctx_count = Counter(it["edits"][0]["wrong"] for it in items)
    def conf_key(it):
        e = it["edits"][0]
        return (e["correct"] in conf_correct, len(e["correct"]), ctx_count[e["wrong"]])
    by_cls = defaultdict(list)
    for it in items:
        if len(it["edits"][0]["correct"]) >= MIN_CORRECT_LEN:
            by_cls[it["edits"][0]["class"]].append(it)
    for c in by_cls:
        by_cls[c].sort(key=conf_key, reverse=True)
    order = sorted(by_cls, key=lambda c: len(by_cls[c]))   # smallest class first
    quota, take = CURATE_TARGET, {}
    for i, c in enumerate(order):
        share = quota // (len(order) - i)
        take[c] = min(share, len(by_cls[c]))
        quota -= take[c]
    curated = [it for c in by_cls for it in by_cls[c][:take[c]]]
    curated.sort(key=lambda it: it["id"])
    with ITEMS.open("w", encoding="utf-8") as f:
        for it in curated:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"raw {raw_n} -> filtered {len(filtered)} clean pairs "
          f"({len(filtered)/max(raw_n,1):.0%}); RID gate + classify applied")
    print(f"  class dist (pairs): {dict(sorted(Counter(r['class'] for r in filtered).items()))}")
    print(f"  novel (not in confusion set): {sum(not r['in_confusion_set'] for r in filtered)}")
    print(f"  sentence-level items: {len(items)} (dropped {no_ctx} w/o usable context) -> {ITEMS_ALL.name}")
    print(f"  CURATED to {len(curated)} (class-balanced, len>={MIN_CORRECT_LEN}, conf-ranked) -> {ITEMS.name}")
    print(f"    curated class dist: {dict(sorted(Counter(it['edits'][0]['class'] for it in curated).items()))}")
    print(f"    curated in-confusion-set: {sum(it['edits'][0]['correct'] in conf_correct for it in curated)} / {len(curated)}")


if __name__ == "__main__":
    main()
