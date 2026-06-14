"""
Phase 4c — merge synthetic + mined pools into the final EditingBench splits.

Steps (plan.md §8):
  1. load synthetic_pool.jsonl (+ wiki_items.jsonl if present)
  2. cross-corpus dedup vs VISTEC-TP-TH-2021 / Wisesight (sentence level) + drop
     exact (wrong,correct) duplicates
  3. group by text_correct so a clean sentence never spans two splits (no leakage)
  4. memorization-aware + embargo routing: low-memorization / mined / dated-wiki
     groups preferred for test_private; well-memorized encyclopedic/legal kept out
  5. stratify across class x etymology x density; assign dev / test_public /
     test_private (~1000 each) / train (remainder), class-balanced
  6. write data/items_{train,dev,test_public,test_private}.jsonl

Run:  PYTHONUTF8=1 python build_dataset.py
"""
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
# Raw bot-history / VISTEC inputs are licensed and not redistributed; drop them
# under data/raw/ to re-run the mining step (see construction/README.md).
PHASE1_DATA = DATA / "raw"

SYN = DATA / "synthetic_pool.jsonl"
MINED = DATA / "wiki_items.jsonl"
MEMO = DATA / "memorization.json"
SEED = 20260524
# Fractions of each class's groups (per-class slicing keeps every split balanced).
# test_private is largest + low-memorization (the blind leaderboard); train = remainder.
FRAC = {"test_private": 0.34, "test_public": 0.32, "dev": 0.24}     # train ~= 0.10


def norm_sent(s):
    return re.sub(r"\s+", "", s)


def load_items():
    items = []
    for line in SYN.open(encoding="utf-8"):
        items.append(json.loads(line))
    if MINED.exists():
        for line in MINED.open(encoding="utf-8"):
            items.append(json.loads(line))
    return items


def external_sentences():
    """Normalized sentence set from VISTEC/Wisesight for cross-corpus dedup."""
    ext = set()
    for p in PHASE1_DATA.glob("*.txt"):
        try:
            for line in p.open(encoding="utf-8"):
                line = line.strip()
                if line:
                    ext.add(norm_sent(line))
        except Exception:                                # noqa
            pass
    return ext


def memo_risk():
    """source-name -> memorization risk (mean_lcp_ratio); default 0.5 if absent."""
    if not MEMO.exists():
        return {}
    j = json.loads(MEMO.read_text(encoding="utf-8"))
    return {k: v.get("mean_lcp_ratio", 0.0) for k, v in j.get("per_source", {}).items()}


def source_name(item):
    doc = item.get("source_doc", "")
    if doc.startswith("thaisum"):
        return "thaisum"
    if doc.startswith("thwiki") or "wiki" in doc:
        return "wikipedia"
    if doc.startswith("thaigov"):
        return "thaigov"
    if doc.startswith("constitution"):
        return "constitution"
    return "other"


def primary_class(item):
    return item["edits"][0]["class"] if item["edits"] else 0


def main():
    rng = random.Random(SEED)
    items = load_items()
    print(f"loaded {len(items)} items (synthetic + mined)")

    # 2. dedup
    ext = external_sentences()
    seen_pairs, kept, drop_ext, drop_dup = set(), [], 0, 0
    for it in items:
        if norm_sent(it["text_correct"]) in ext:
            drop_ext += 1
            continue
        key = (it["text_wrong"], it["text_correct"])
        if key in seen_pairs:
            drop_dup += 1
            continue
        seen_pairs.add(key)
        kept.append(it)
    print(f"  dedup: dropped {drop_ext} vs VISTEC/Wisesight, {drop_dup} exact dups "
          f"-> {len(kept)} items")

    # 3. group by clean sentence (a sentence never spans two splits)
    groups = defaultdict(list)
    for it in kept:
        groups[it["text_correct"]].append(it)
    glist = list(groups.values())
    print(f"  {len(glist)} distinct clean sentences (groups)")

    # 4. routing key: low risk first (mined=most novel -> risk 0; else source risk)
    risk = memo_risk()
    def grisk(g):
        it = g[0]
        if it["source_track"] == "mined":
            return 0.0
        return risk.get(source_name(it), 0.5)

    # 5. CLASS-BALANCED assignment by PROPORTIONAL slicing. Bucket groups by dominant
    #    class; sort each class by risk (low first). Slice each class by fraction so
    #    every split is class-balanced regardless of class size: the LOW-risk slice of
    #    each class -> test_private (least-memorized + gets the mined groups, risk 0),
    #    then test_public, dev; the high-risk remainder -> train.
    assign = {"train": [], "dev": [], "test_public": [], "test_private": []}
    by_class = defaultdict(list)
    for g in glist:
        by_class[primary_class(g[0])].append(g)
    classes = sorted(by_class)
    for c in classes:
        rng.shuffle(by_class[c])
        by_class[c].sort(key=grisk)             # low risk first
        n = len(by_class[c])
        i_priv = int(round(n * FRAC["test_private"]))
        i_pub = i_priv + int(round(n * FRAC["test_public"]))
        i_dev = i_pub + int(round(n * FRAC["dev"]))
        assign["test_private"] += by_class[c][:i_priv]
        assign["test_public"] += by_class[c][i_priv:i_pub]
        assign["dev"] += by_class[c][i_pub:i_dev]
        assign["train"] += by_class[c][i_dev:]

    # 6. flatten + stamp split, write
    out_counts = {}
    for split, grps in assign.items():
        rows = []
        for g in grps:
            for it in g:
                it["split"] = split
                rows.append(it)
        rng.shuffle(rows)
        path = DATA / f"items_{split}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for it in rows:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        out_counts[split] = len(rows)

    # report
    print("\nsplit sizes:", out_counts)
    for split, grps in assign.items():
        cls = Counter(primary_class(it) for g in grps for it in g)
        den = Counter(it["density"] for g in grps for it in g)
        trk = Counter(it["source_track"] for g in grps for it in g)
        print(f"  {split:13s} class={dict(sorted(cls.items()))} density={dict(den)} track={dict(trk)}")

    # leakage checks
    sent_split = defaultdict(set)
    for split, grps in assign.items():
        for g in grps:
            sent_split[g[0]["text_correct"]].add(split)
    leaked = sum(len(v) > 1 for v in sent_split.values())
    print(f"\nleakage check: {leaked} sentences span >1 split (must be 0)")
    print(f"test_private memorization risk (mean): "
          f"{sum(grisk(g) for g in assign['test_private'])/max(len(assign['test_private']),1):.3f}")
    print(f"train memorization risk (mean): "
          f"{sum(grisk(g) for g in assign['train'])/max(len(assign['train']),1):.3f}")


if __name__ == "__main__":
    main()
