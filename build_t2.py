"""Build a MULTI-SENTENCE tier of EditingBench (paragraph T2 / page T3).

Composes passages from K spell-filtered sentences of ONE source article, then injects
SPARSE errors (1..max-errors per passage) into a subset — the rest are clean
distractors. The point: measure PRECISION over long clean context (over-editing), not
just recall. Records per-sentence spans (char + TCC) + `has_error` so score_runs.py
computes clean-sentence fidelity. Gold invariant (apply edits ⇒ text_correct) asserted.

  PYTHONUTF8=1 python build_t2.py --sents 5  --max-errors 2 --n 150 --split t2 --tier paragraph --out data/items_t2.jsonl
  PYTHONUTF8=1 python build_t2.py --sents 15 --max-errors 3 --n 70  --split t3 --tier page --gaps --out data/items_t3.jsonl

Contiguity: default requires K *contiguous* clean sentences (tight coherence, T2).
`--gaps` collects clean sentences in document order allowing filtered gaps — needed for
long pages (15 strictly-contiguous strictly-clean sentences are rare).
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from pythainlp.tokenize import sent_tokenize

from inject import (load_confusion_set, inject, apply_edits, normalize,
                    tcc_segments, tcc_span_for_char_range)
from spellcheck import is_clean

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CACHE = DATA / "clean_cache"
SEED = 20260524
THAI = re.compile(r"[฀-๿]")
JOIN = " "
SOURCES = [("thaigov", "gov", "CC0"), ("thaisum", "news", "MIT"),
           ("wikipedia", "encyclopedic", "CC BY-SA")]


def usable(s: str) -> str | None:
    s = s.strip()
    if not (40 <= len(s) <= 180):
        return None
    if "http" in s or "\n" in s or "|" in s:
        return None
    if len(THAI.findall(s)) / max(len(s), 1) < 0.6:
        return None
    return s if is_clean(s) else None


def windows_from_article(text: str, seen: set, k: int, contiguous: bool) -> list[list[str]]:
    """Non-overlapping windows of k clean (globally-unique) sentences from one article.
    contiguous: k must be an unbroken run. else: clean sentences in document order,
    filtered gaps allowed."""
    out: list[list[str]] = []
    if contiguous:
        run: list[str] = []
        for raw in sent_tokenize(text):
            s = usable(raw)
            if s is None or normalize(s) in seen:
                run = []
                continue
            run.append(s)
            if len(run) == k:
                out.append(run[:])
                seen.update(normalize(x) for x in run)
                run = []
    else:
        clean = []
        for raw in sent_tokenize(text):
            s = usable(raw)
            if s is None or normalize(s) in seen:
                continue
            clean.append(s)
        for i in range(0, len(clean) - k + 1, k):
            w = clean[i:i + k]
            out.append(w)
            seen.update(normalize(x) for x in w)
    return out


def inject_balanced(sentence, by_class, class_count, rng):
    """Inject ONE error, preferring the least-used class that has a site here."""
    for cid in sorted(by_class, key=lambda c: (class_count[c], c)):
        item = inject(sentence, by_class[cid], n=1, rng=rng)
        if item:
            class_count[cid] += 1
            return item
    return None


def build_passage(window, by_class, class_count, rng, max_errors):
    weights = [0.6 ** i for i in range(max_errors)]
    n_err = rng.choices(range(1, max_errors + 1), weights=weights)[0]
    idxs = list(range(len(window)))
    rng.shuffle(idxs)
    injections = {}
    for idx in idxs:
        if len(injections) >= n_err:
            break
        item = inject_balanced(window[idx], by_class, class_count, rng)
        if item:
            injections[idx] = item
    if not injections:
        return None

    parts_w, parts_c, sent_spans, agg_edits = [], [], [], []
    cur = 0
    for idx, sent in enumerate(window):
        if idx > 0:
            parts_w.append(JOIN)
            parts_c.append(JOIN)
            cur += len(JOIN)
        inj = injections.get(idx)
        w = inj["text_wrong"] if inj else normalize(sent)
        c = inj["text_correct"] if inj else normalize(sent)
        start = cur
        parts_w.append(w)
        parts_c.append(c)
        cur += len(w)
        sent_spans.append({"char_start": start, "char_end": cur, "has_error": bool(inj)})
        if inj:
            for e in inj["edits"]:
                agg_edits.append({**e, "char_start": e["char_start"] + start,
                                  "char_end": e["char_end"] + start})
    text_wrong = "".join(parts_w)
    text_correct = "".join(parts_c)

    segs = tcc_segments(text_wrong)
    for e in agg_edits:
        ts, te = tcc_span_for_char_range(segs, e["char_start"], e["char_end"])
        if ts is None:
            return None
        e["tcc_start"], e["tcc_end"] = ts, te
    for sp in sent_spans:
        ts, te = tcc_span_for_char_range(segs, sp["char_start"], sp["char_end"])
        sp["tcc_start"], sp["tcc_end"] = ts, te

    if apply_edits(text_wrong, agg_edits) != text_correct:
        return None
    return text_wrong, text_correct, agg_edits, sent_spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150, help="target passages")
    ap.add_argument("--sents", type=int, default=5, help="sentences per passage")
    ap.add_argument("--max-errors", type=int, default=2)
    ap.add_argument("--split", default="t2")
    ap.add_argument("--tier", default="paragraph")
    ap.add_argument("--gaps", action="store_true", help="allow filtered gaps within an article (for long pages)")
    ap.add_argument("--out", type=Path, default=DATA / "items_t2.jsonl")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--append-to", type=Path, default=None,
                    help="grow an EXISTING tier file to --n total: keep its items + ids "
                         "verbatim (so already-collected runs stay valid), seed dedup from "
                         "them, number new ids after the max. --out defaults to this path.")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    contiguous = not args.gaps

    recs = load_confusion_set()
    by_class = defaultdict(list)
    for r in recs:
        by_class[r["class_id"]].append(r)
    class_count = Counter()

    # append mode: preserve existing items + ids; dedup new passages against them.
    existing, existing_correct, start_idx = [], set(), 0
    if args.append_to and args.append_to.exists():
        existing = [json.loads(l) for l in args.append_to.open(encoding="utf-8")]
        existing_correct = {it["text_correct"] for it in existing}
        nums = [int(it["id"].rsplit("-", 1)[-1]) for it in existing
                if it["id"].rsplit("-", 1)[-1].isdigit()]
        start_idx = max(nums) if nums else 0
        if args.out == DATA / "items_t2.jsonl":
            args.out = args.append_to
        print(f"  append mode: {len(existing)} existing items (ids up to {start_idx}) kept; "
              f"generating up to {args.n - len(existing)} new")

    pools, seen = {}, set()
    # seed sentence-dedup from existing items' recoverable clean sentences
    for it in existing:
        for sp in it.get("sentences", []):
            if not sp.get("has_error"):
                seen.add(normalize(it["text_wrong"][sp["char_start"]:sp["char_end"]]))
    for name, register, lic in SOURCES:
        rows = [json.loads(l) for l in (CACHE / f"{name}.jsonl").open(encoding="utf-8")]
        rng.shuffle(rows)
        wins, target = [], 3 * args.n // len(SOURCES) + 10
        for r in rows:
            wins += [(w, register, f"{name}#{r.get('article','?')}", lic)
                     for w in windows_from_article(r["text"], seen, args.sents, contiguous)]
            if len(wins) >= target:
                break
        rng.shuffle(wins)
        pools[name] = wins
        print(f"  {name:12} {len(wins)} candidate windows")

    items, idx = [], start_idx
    target_new = args.n - len(existing)
    order = [n for n, _, _ in SOURCES]
    cursors = {n: 0 for n in order}
    while len(items) < target_new and any(cursors[n] < len(pools[n]) for n in order):
        for n in order:
            if len(items) >= target_new or cursors[n] >= len(pools[n]):
                continue
            window, register, doc, lic = pools[n][cursors[n]]
            cursors[n] += 1
            built = build_passage(window, by_class, class_count, rng, args.max_errors)
            if not built:
                continue
            tw, tc, edits, spans = built
            if tc in existing_correct:                 # dedup vs existing (append mode)
                continue
            idx += 1
            items.append({
                "id": f"{args.split}-{idx:06d}", "tier": args.tier, "source_track": "synthetic",
                "register": register, "source_doc": doc, "lang": "th",
                "text_wrong": tw, "text_correct": tc, "edits": edits,
                "n_errors": len(edits), "n_sentences": args.sents, "sentences": spans,
                "density": args.tier, "gold_source": "construction", "verified": False,
                "license": lic, "split": args.split,
            })

    out_items = existing + items
    with args.out.open("w", encoding="utf-8") as f:
        for it in out_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    cc = Counter(e["class"] for it in out_items for e in it["edits"])
    nd = Counter(it["n_errors"] for it in out_items)
    sl = sum(len(it["text_wrong"]) for it in out_items) / max(len(out_items), 1)
    new_note = f" (+{len(items)} new, kept {len(existing)})" if existing else ""
    print(f"\nwrote {len(out_items)} {args.tier}s{new_note} ({args.sents} sents) -> {args.out.name}")
    print(f"  errors/passage: {dict(sorted(nd.items()))} | class dist: {dict(sorted(cc.items()))}")
    print(f"  mean length {sl:.0f} chars | registers: {dict(Counter(it['register'] for it in out_items))}")


if __name__ == "__main__":
    main()
