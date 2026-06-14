"""
Phase 4b — build the synthetic injection pool (the EditingBench backbone).

Pipeline:  pull clean text per register  ->  NFC-normalize + repair the two
Phase-3 surface variations  ->  sentence-segment + length/Thai/cleanliness filter
->  stratified injection (6 class x etymology x density) via inject.py  ->
data/synthetic_pool.jsonl.

Clean sources (permissive-only, from corpus-catalog.md):
  news        thaisum                (MIT)     field 'body'
  encyclopedic wikimedia/wikipedia    (CC BY-SA) cfg 20231101.th  field 'text'  [dated -> embargo]
  legal       thai-constitution-corpus (CC0)    field 'txt'
  gov         thaigov-v2-corpus      (CC0)     field 'context'

Run:  PYTHONUTF8=1 python inject_dataset.py            (uses cache if present)
      PYTHONUTF8=1 python inject_dataset.py --refresh  (re-pull from HF)
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import requests
from pythainlp.tokenize import sent_tokenize, word_tokenize
from pythainlp.corpus import thai_words, thai_orst_words

from inject import (load_confusion_set, group_by_correct, find_sites, inject,
                    apply_edits, tcc_segments, token_spans)

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CACHE = DATA / "clean_cache"
DATA.mkdir(exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

VIEWER = "https://datasets-server.huggingface.co"
UA = "ThaiEditBench-research/0.1 (academic; anonymous@example.com)"
S = requests.Session(); S.headers["User-Agent"] = UA

LEX = set(thai_words()) | set(thai_orst_words())
THAI = re.compile(r"[฀-๿]")
THAI_WORD = re.compile(r"^[฀-๿]+$")
SEED = 20260524

# (name, register, hf id, config, field, rows_to_pull, license, max_sentences)
# max_sentences caps each register so giant legal docs don't dominate / stall the
# CPU-bound indexing; per-document text is also capped (DOC_CHAR_CAP).
SOURCES = [
    ("thaisum", "news", "pythainlp/thaisum", None, "body", 2500, "MIT", 9000),
    ("wikipedia", "encyclopedic", "wikimedia/wikipedia", "20231101.th", "text", 1500, "CC BY-SA", 8000),
    ("constitution", "legal", "pythainlp/thai-constitution-corpus", None, "txt", 20, "CC0", 900),
    ("thaigov", "gov", "pythainlp/thaigov-v2-corpus-22032023", None, "context", 1500, "CC0", 5000),
]
DOC_CHAR_CAP = 12000        # process only the first N chars of any one document

# Per-class single-error targets (native unless noted). Loanword(6)=loan; a few
# proper-noun seeds exist but are too sparse for a balanced cell -> best-effort.
SINGLE_TARGET = {1: 380, 2: 380, 3: 380, 4: 380, 5: 380, 6: 320}
MULTI_TARGET = 600          # n=2, mixed-class density bucket
MAX_USES_PER_SENTENCE = 3   # variety cap


# --- surface normalization --------------------------------------------------

def repair(text):
    """NFC + repair the two Phase-3 surface variations so the injected error is
    the ONLY deviation from RID-correct orthography (Q2.4)."""
    import unicodedata
    text = unicodedata.normalize("NFC", text)
    text = text.replace("ํา", "ำ")   # nikhahit+sara-aa -> sara-am ำ
    text = text.replace("เเ", "แ")   # เเ -> แ
    return text


# --- HF dataset-viewer paged pull -------------------------------------------

def get_json(url, params, tries=4):
    last = None
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=45)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:150]}"
        except Exception as e:                       # noqa
            last = repr(e)
        time.sleep(2 * (k + 1))
    raise RuntimeError(f"viewer fail {url} {params}: {last}")


def first_config_split(ds, want_config):
    j = get_json(f"{VIEWER}/splits", {"dataset": ds})
    splits = j.get("splits", [])
    cand = [s for s in splits if want_config is None or s.get("config") == want_config] or splits
    train = [s for s in cand if s.get("split") == "train"] or cand
    return train[0]["config"], train[0]["split"]


def pull_rows(ds, config, split, field, n_rows):
    """Page through /rows in 100-row windows; yield (field_text, row_index, extras)."""
    out = []
    for offset in range(0, n_rows, 100):
        length = min(100, n_rows - offset)
        j = get_json(f"{VIEWER}/rows", {"dataset": ds, "config": config,
                                        "split": split, "offset": offset, "length": length})
        rows = j.get("rows", [])
        if not rows:
            break
        for r in rows:
            row = r["row"]
            txt = row.get(field) or ""
            if isinstance(txt, str) and txt:
                # capture an article id for wiki (for 4c disjoint partition)
                art = row.get("id") or row.get("title") or ""
                out.append((txt, r.get("row_idx", offset), str(art)))
        time.sleep(0.15)
    return out


def cache_source(name, ds, config_hint, field, n_rows):
    path = CACHE / f"{name}.jsonl"
    if path.exists():
        return path
    config, split = first_config_split(ds, config_hint)
    rows = pull_rows(ds, config, split, field, n_rows)
    with path.open("w", encoding="utf-8") as f:
        for txt, idx, art in rows:
            f.write(json.dumps({"text": txt, "row": idx, "article": art},
                               ensure_ascii=False) + "\n")
    print(f"  pulled {len(rows)} rows -> {path.name}")
    return path


# --- sentence pool ----------------------------------------------------------

def clean_ratio(toks):
    thai = [t for t in toks if THAI_WORD.match(t)]
    if not thai:
        return 0.0
    return sum(t in LEX for t in thai) / len(thai)


def usable_sentences(text, register, doc_id):
    """Segment + filter one document into clean sentence-level stimuli.

    Tokenizes each kept sentence ONCE and caches the (token, start, end) spans on
    the record so index_pool / injection reuse them instead of re-tokenizing.
    """
    text = repair(text)[:DOC_CHAR_CAP]
    out = []
    for raw in sent_tokenize(text):
        s = raw.strip()
        if not (40 <= len(s) <= 180):
            continue
        if "http" in s or "\n" in s or "|" in s:
            continue
        thai_chars = len(THAI.findall(s))
        if thai_chars / max(len(s), 1) < 0.6:        # drop English/number-heavy lines
            continue
        spans = token_spans(s)                       # tokenize once
        if not spans:
            continue
        if clean_ratio([t for (t, _a, _b) in spans]) < 0.85:   # start from clean text
            continue
        out.append({"text": s, "register": register, "source_doc": doc_id, "spans": spans})
    return out


def build_sentence_pool(refresh):
    pool = []
    print("Building clean sentence pool:")
    for name, register, ds, cfg, field, n_rows, lic, max_sents in SOURCES:
        path = CACHE / f"{name}.jsonl"
        if refresh and path.exists():
            path.unlink()
        cache_source(name, ds, cfg, field, n_rows)
        n0, added = len(pool), 0
        for line in path.open(encoding="utf-8"):
            if added >= max_sents:
                break
            rec = json.loads(line)
            if name == "wikipedia":
                doc = f"thwiki:article_id={rec['article']}"
            elif name == "thaisum":
                doc = f"thaisum#{rec['row']}"
            elif name == "thaigov":
                doc = f"thaigov#{rec['row']}"
            else:
                doc = f"constitution#{rec['row']}"
            for s in usable_sentences(rec["text"], register, doc):
                s["license"] = lic
                pool.append(s)
                added += 1
                if added >= max_sents:
                    break
        print(f"  {name}: +{len(pool)-n0} usable sentences ({register})")
    print(f"  TOTAL usable sentences: {len(pool)}")
    return pool


# --- stratified injection ---------------------------------------------------

def index_pool(pool, by_correct):
    """Attach to each sentence the set of correct-forms it can host (token-run)."""
    for s in pool:
        sites = find_sites(s["text"], by_correct, spans=s.get("spans"))
        s["forms"] = sorted({f for (_a, _b, f) in sites})
        s["nsites"] = len(sites)
    return pool


def make_item(idx, item_core, sent, density):
    return {
        "id": f"syn-{idx:06d}",
        "source_track": "synthetic",
        "register": sent["register"],
        "source_doc": sent["source_doc"],
        "lang": "th",
        "text_wrong": item_core["text_wrong"],
        "text_correct": item_core["text_correct"],
        "edits": item_core["edits"],
        "n_errors": len(item_core["edits"]),
        "density": density,
        "gold_source": "construction",
        "verified": False,
        "license": sent["license"],
        "split": "unassigned",          # 4c assigns
    }


def generate(pool, recs, rng):
    by_correct = group_by_correct(recs)
    forms_by_class = {}                 # (class_id) -> set(correct forms)
    pairs_by_class = {}                 # class_id -> [records]
    for r in recs:
        pairs_by_class.setdefault(r["class_id"], []).append(r)
        forms_by_class.setdefault(r["class_id"], set()).add(r["correct"])
    index_pool(pool, by_correct)
    uses = {id(s): 0 for s in pool}
    items, idx = [], 0
    counts = {c: 0 for c in SINGLE_TARGET}

    # ---- single-error, per class ----
    for cid, target in SINGLE_TARGET.items():
        cforms = forms_by_class[cid]
        hosts = [s for s in pool if cforms & set(s["forms"])]
        rng.shuffle(hosts)
        made, guard = 0, 0
        while made < target and guard < target * 40:
            guard += 1
            if not hosts:
                break
            sent = hosts[rng.randrange(len(hosts))]
            if uses[id(sent)] >= MAX_USES_PER_SENTENCE:
                continue
            core = inject(sent["text"], pairs_by_class[cid], n=1, rng=rng)
            if core is None:
                continue
            items.append(make_item(idx, core, sent, "single")); idx += 1
            uses[id(sent)] += 1; made += 1; counts[cid] += 1
        print(f"  class {cid}: {made} single-error items "
              f"(from {len(hosts)} candidate sentences)")

    # ---- multi-error (n=2, mixed class) ----
    multi_hosts = [s for s in pool if s["nsites"] >= 2]
    rng.shuffle(multi_hosts)
    made, guard = 0, 0
    while made < MULTI_TARGET and guard < MULTI_TARGET * 40 and multi_hosts:
        guard += 1
        sent = multi_hosts[rng.randrange(len(multi_hosts))]
        if uses[id(sent)] >= MAX_USES_PER_SENTENCE:
            continue
        core = inject(sent["text"], recs, n=2, rng=rng)
        if core is None or len(core["edits"]) < 2:
            continue
        items.append(make_item(idx, core, sent, "multi")); idx += 1
        uses[id(sent)] += 1; made += 1
    print(f"  multi-error: {made} items (n=2)")
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-pull from HF viewer")
    args = ap.parse_args()
    rng = random.Random(SEED)
    recs = load_confusion_set()
    pool = build_sentence_pool(args.refresh)
    print("Generating synthetic items:")
    items = generate(pool, recs, rng)

    # validate the gold invariant on the whole pool before writing
    bad = 0
    for it in items:
        if apply_edits(it["text_wrong"], it["edits"]) != it["text_correct"]:
            bad += 1
        for ed in it["edits"]:
            if "".join(tcc_segments(it["text_wrong"])[ed["tcc_start"]:ed["tcc_end"]]) != ed["wrong"]:
                bad += 1
    assert bad == 0, f"{bad} items failed the gold invariant"

    out = DATA / "synthetic_pool.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"\nwrote {len(items)} items -> {out.name}  (gold invariant: all pass)")

    # quick distribution report
    from collections import Counter
    by_cls = Counter(e["class"] for it in items for e in it["edits"])
    by_reg = Counter(it["register"] for it in items)
    by_den = Counter(it["density"] for it in items)
    print("  errors per class:", dict(sorted(by_cls.items())))
    print("  items per register:", dict(by_reg))
    print("  density:", dict(by_den))


if __name__ == "__main__":
    main()
