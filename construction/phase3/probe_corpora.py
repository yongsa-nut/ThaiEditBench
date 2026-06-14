"""
Phase 3 · live corpus probes for the clean-corpus catalog.

Probes each ELIGIBLE (permissive-redistribution + formal) Thai text corpus to
back the catalog rows with real numbers, instead of trusting dataset cards:

  - size           : total rows (HF dataset-viewer /size)
  - text field     : auto-detected from the first record
  - cleanliness    : % of Thai-script word tokens (newmm) found in the offline
                     RID/Thai lexicon (thai_words ∪ thai_orst_words). A relative
                     ORTHOGRAPHIC-NOISE proxy: clean formal prose lands high
                     (proper nouns / inflections are the honest OOV floor);
                     social/web-crawl lands lower.
  - segmentability : pythainlp sent_tokenize stats on a sampled passage
                     (Thai has no sentence terminator, so we must verify it).

We use the HF **dataset-viewer API** (datasets-server) rather than the
`datasets` loader: it returns JSON rows over HTTP, sidestepping the
"Dataset scripts no longer supported" failure (datasets 4.x) and any full
download. Samples are written to phase3/data/<name>_sample.txt for eyeballing.

Run: PYTHONUTF8=1 python phase3/probe_corpora.py
"""
import json
import re
import sys
import time
from pathlib import Path

import requests
from pythainlp.tokenize import word_tokenize, sent_tokenize
from pythainlp.corpus import thai_words, thai_orst_words

HERE = Path(__file__).resolve().parent
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)
VIEWER = "https://datasets-server.huggingface.co"
UA = "ThaiEditBench-research/0.1 (academic; anonymous@example.com)"
S = requests.Session(); S.headers["User-Agent"] = UA

LEX = set(thai_words()) | set(thai_orst_words())
THAI = re.compile(r"[฀-๿]")
THAI_WORD = re.compile(r"^[฀-๿]+$")  # pure Thai-script token (no digits/latin/punct)

# Eligible injection-pool candidates (HF IDs verified 2026-05-23). `field` is a
# hint; the probe auto-detects if absent/wrong. `prefer_split` picks a split.
CANDIDATES = [
    {"name": "thai_wikipedia_v3", "id": "pythainlp/thai-wiki-dataset-v3",
     "register": "encyclopedic", "license": "CC BY-SA 3.0", "field": "text"},
    {"name": "wikimedia_wikipedia_th", "id": "wikimedia/wikipedia",
     "config": "20231101.th", "register": "encyclopedic",
     "license": "CC BY-SA 4.0/3.0", "field": "text"},
    {"name": "thaisum", "id": "pythainlp/thaisum",
     "register": "news", "license": "MIT", "field": "body"},
    {"name": "thaigov_v2", "id": "pythainlp/thaigov-v2-corpus-22032023",
     "register": "gov-formal-news", "license": "CC0-1.0", "field": None},
    {"name": "thai_constitution", "id": "pythainlp/thai-constitution-corpus",
     "register": "legal-formal", "license": "CC0-1.0", "field": None},
    {"name": "thai_law", "id": "pythainlp/thai-law-dataset",
     "register": "legal-formal", "license": "CC0-1.0", "field": None},
]

# Reference-only (kept OUT of the injection pool) — probe register for comparison.
REFERENCE = [
    {"name": "prachathai67k_REF_NC", "id": "PyThaiNLP/prachathai67k",
     "register": "news", "license": "CC BY-NC (excluded)", "field": "body_text"},
]


def get_json(url, params=None, tries=3):
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:  # noqa
            last = repr(e)
        time.sleep(2 * (k + 1))
    return {"_error": last}


def viewer_size(ds):
    j = get_json(f"{VIEWER}/size", {"dataset": ds})
    if "_error" in j:
        return None, j["_error"]
    try:
        return j["size"]["dataset"]["num_rows"], None
    except Exception:
        return None, "no size field"


def viewer_first_config_split(ds, want_config=None):
    j = get_json(f"{VIEWER}/splits", {"dataset": ds})
    if "_error" in j:
        return None, None, j["_error"]
    splits = j.get("splits", [])
    if not splits:
        return None, None, "no splits"
    # prefer the requested config + a 'train' split
    cand = [s for s in splits if want_config is None or s.get("config") == want_config]
    cand = cand or splits
    train = [s for s in cand if s.get("split") == "train"] or cand
    pick = train[0]
    return pick["config"], pick["split"], None


def viewer_rows(ds, config, split, length=100):
    j = get_json(f"{VIEWER}/rows",
                 {"dataset": ds, "config": config, "split": split,
                  "offset": 0, "length": length})
    if "_error" in j:
        return None, j["_error"]
    return [r["row"] for r in j.get("rows", [])], None


def detect_field(row, hint):
    if hint and hint in row and isinstance(row[hint], str):
        return hint
    # prefer common text fields, else the longest string value
    for k in ("text", "body", "article", "content", "body_text", "summary"):
        if isinstance(row.get(k), str) and len(row[k]) > 20:
            return k
    strs = [(k, v) for k, v in row.items() if isinstance(v, str)]
    if not strs:
        return None
    return max(strs, key=lambda kv: len(kv[1]))[0]


def cleanliness(text):
    """% of pure-Thai word tokens in the RID/Thai lexicon + sample OOV."""
    toks = word_tokenize(text, engine="newmm")
    thai_toks = [t for t in toks if THAI_WORD.match(t)]
    if not thai_toks:
        return None, 0, []
    in_lex = [t for t in thai_toks if t in LEX]
    oov = [t for t in thai_toks if t not in LEX]
    pct = 100.0 * len(in_lex) / len(thai_toks)
    # most frequent OOV (signal: proper nouns vs garbage)
    from collections import Counter
    top_oov = [w for w, _ in Counter(oov).most_common(15)]
    return pct, len(thai_toks), top_oov


def seg_stats(text):
    """sent_tokenize stats on a passage (cap length to keep it quick)."""
    passage = text[:4000]
    sents = [s for s in sent_tokenize(passage) if s.strip()]
    if not sents:
        return 0, 0
    avg_chars = sum(len(s) for s in sents) / len(sents)
    return len(sents), avg_chars


def probe(c):
    ds = c["id"]
    print(f"\n=== {c['name']}  ({ds})  [{c['register']} · {c['license']}] ===")
    n, err = viewer_size(ds)
    if err:
        print(f"  SIZE: n/a ({err})")
    else:
        print(f"  SIZE: {n:,} rows")
    config, split, err = viewer_first_config_split(ds, c.get("config"))
    if err:
        print(f"  ROWS: FAILED to list splits -> {err}")
        return {"name": c["name"], "id": ds, "status": f"splits-fail: {err}",
                "rows": n}
    rows, err = viewer_rows(ds, config, split, length=100)
    if err or not rows:
        print(f"  ROWS: FAILED ({err}); config={config} split={split}")
        return {"name": c["name"], "id": ds, "status": f"rows-fail: {err}",
                "rows": n, "config": config, "split": split}
    print(f"  fields: {list(rows[0].keys())}  | config={config} split={split}")
    field = detect_field(rows[0], c.get("field"))
    print(f"  text field -> '{field}'")
    blob = "\n".join(str(r.get(field, "")) for r in rows if r.get(field))
    pct, ntok, top_oov = cleanliness(blob)
    nsent, avgc = seg_stats(blob)
    print(f"  CLEANLINESS: {pct:.1f}% in-lexicon  (of {ntok:,} Thai tokens sampled)")
    print(f"  top OOV: {' '.join(top_oov)}")
    print(f"  SEGMENT: {nsent} sents in 4k-char passage, avg {avgc:.0f} chars/sent")
    # write a sample for eyeballing register/cleanliness
    sample_path = OUT / f"{c['name']}_sample.txt"
    with sample_path.open("w", encoding="utf-8") as f:
        for r in rows[:25]:
            t = str(r.get(field, "")).strip().replace("\n", " ")
            f.write(t[:500] + "\n\n")
    return {"name": c["name"], "id": ds, "register": c["register"],
            "license": c["license"], "rows": n, "field": field,
            "cleanliness_pct": round(pct, 1) if pct else None,
            "thai_tokens_sampled": ntok, "sents_in_4k": nsent,
            "avg_chars_per_sent": round(avgc), "top_oov": top_oov,
            "config": config, "split": split, "status": "ok"}


def main():
    results = []
    print("################  ELIGIBLE (injection pool)  ################")
    for c in CANDIDATES:
        results.append(probe(c))
    print("\n################  REFERENCE (excluded, register check)  ################")
    for c in REFERENCE:
        results.append(probe(c))
    (OUT / "probe_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT/'probe_results.json'} + per-corpus *_sample.txt")


if __name__ == "__main__":
    main()
