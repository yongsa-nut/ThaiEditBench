"""Build per-annotator EditingBench annotation sheets (Phase 5).

Selects the α-calibration set and bakes one self-contained HTML file per annotator
(items embedded — no separate JSON, no file-picker, no install). Each annotator opens
their `annotate_<id>.html`, labels, clicks Export, and sends back one
`labels_<id>.json`. Mirrors the prosody calibration bundler.

The α-set = ALL 40 mined items (gold uncertain — real BotKung Wikipedia fixes) +
a class-balanced SYNTHETIC top-up so every mechanism class reaches ~`--per-class`
units (mined covers classes 1-4 well but cluster=5, loanword=0). Synthetic items are
construction-gold; the 3-annotator pass on them validates the taxonomy + construction
with real inter-annotator agreement. Only single-error items are sampled, so each
α-set item contributes cleanly to one class.

The same item set (same order) is baked for every annotator — required so the scorer
can align ratings by `id`. The set is also dumped to `alpha_set.jsonl`, which the
scorer reads to recover each item's provenance + construction class.

  PYTHONUTF8=1 python build_sheets.py --annotators ann1 ann2 ann3
  PYTHONUTF8=1 python build_sheets.py --annotators ann1 ann2 ann3 --per-class 20
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
TEMPLATE = HERE / "annotate.html"
ALPHA_SET = HERE / "alpha_set.jsonl"
SEED = 20260524

# Must match the placeholder lines in annotate.html exactly.
ITEMS_PLACEHOLDER = "const BAKED_ITEMS = null; /* BAKED_ITEMS_PLACEHOLDER */"
NAME_PLACEHOLDER = "const BAKED_NAME  = null; /* BAKED_NAME_PLACEHOLDER */"

RENDER_FIELDS = ("id", "source_track", "register", "text_wrong", "text_correct")
EDIT_FIELDS = ("char_start", "char_end", "wrong", "correct",
               "class", "class_name", "etymology", "edit_op")


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.open(encoding="utf-8") if line.strip()]


def first_class(it: dict) -> int:
    return it["edits"][0]["class"]


def mined_items() -> list[dict]:
    return [it for it in load_jsonl(DATA / "items_test_private.jsonl")
            if it["source_track"] == "mined"]


def synthetic_topup(per_class: int, mined: list[dict], pools: list[str], seed: int) -> list[dict]:
    """Per class C, take (per_class - mined_count[C]) single-error synthetic items."""
    mined_cls = Counter(first_class(it) for it in mined)
    mined_texts = {it["text_correct"] for it in mined}
    by_cls: dict[int, list[dict]] = defaultdict(list)
    seen: set[str] = set()
    for split in pools:
        for it in load_jsonl(DATA / f"items_{split}.jsonl"):
            if it["source_track"] != "synthetic" or it.get("density") != "single":
                continue
            if it["id"] in seen or it["text_correct"] in mined_texts:
                continue
            seen.add(it["id"])
            by_cls[first_class(it)].append(it)
    rng = random.Random(seed)
    for c in by_cls:
        rng.shuffle(by_cls[c])
    out: list[dict] = []
    for c in range(1, 7):
        need = max(0, per_class - mined_cls.get(c, 0))
        take = by_cls.get(c, [])[:need]
        if len(take) < need:
            print(f"  [warn] class {c}: wanted {need} synthetic, only {len(take)} available")
        out += take
    return out


def slim(it: dict) -> dict:
    """Keep only render + identity + construction-label fields for the baked file."""
    o = {k: it[k] for k in RENDER_FIELDS if k in it}
    o["edits"] = [{k: e[k] for k in EDIT_FIELDS if k in e} for e in it["edits"]]
    return o


def build_set(per_class: int, pools: list[str], seed: int):
    mined = mined_items()
    topup = synthetic_topup(per_class, mined, pools, seed)
    full = [slim(it) for it in mined] + [slim(it) for it in topup]
    random.Random(seed + 1).shuffle(full)   # interleave mined & synthetic
    return full, mined, topup


def bundle(items: list[dict], annotators: list[str], out_dir: Path) -> None:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    if ITEMS_PLACEHOLDER not in tpl or NAME_PLACEHOLDER not in tpl:
        sys.exit("annotate.html is missing the bake placeholders — did the template change?")
    items_js = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")  # keep </script> safe
    out_dir.mkdir(parents=True, exist_ok=True)
    for a in annotators:
        html = tpl.replace(ITEMS_PLACEHOLDER, f"const BAKED_ITEMS = {items_js};")
        html = html.replace(NAME_PLACEHOLDER, f"const BAKED_NAME  = {json.dumps(a)};")
        path = out_dir / f"annotate_{a}.html"
        path.write_text(html, encoding="utf-8")
        print(f"  wrote {path.relative_to(HERE)}  ({len(items)} items · id={a})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--annotators", nargs="+", default=["ann1", "ann2", "ann3"])
    ap.add_argument("--per-class", type=int, default=20, help="target units/class in the α-set")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--pools", nargs="+", default=["test_public", "dev"])
    ap.add_argument("--out", type=Path, default=HERE / "dist")
    args = ap.parse_args()

    full, mined, topup = build_set(args.per_class, args.pools, args.seed)
    mc = Counter(first_class(it) for it in mined)
    tc = Counter(first_class(it) for it in topup)
    print(f"α-set: {len(full)} items = {len(mined)} mined + {len(topup)} synthetic "
          f"(target {args.per_class}/class)")
    print(f"  {'class':<6}{'mined':>6}{'synth':>6}{'total':>6}")
    for c in range(1, 7):
        print(f"  {c:<6}{mc.get(c, 0):>6}{tc.get(c, 0):>6}{mc.get(c, 0) + tc.get(c, 0):>6}")

    with ALPHA_SET.open("w", encoding="utf-8") as f:
        for it in full:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"  dumped α-set -> {ALPHA_SET.relative_to(HERE)}  (scorer reads this)")

    bundle(full, args.annotators, args.out)
    print("\nSend each annotator their one dist/annotate_<id>.html; collect one labels_<id>.json back.")


if __name__ == "__main__":
    main()
