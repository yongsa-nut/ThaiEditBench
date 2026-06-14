"""Phase-5 annotation scoring — turns the returned label files into the numbers.

From `alpha_set.jsonl` (the exact set baked by build_sheets.py) + the per-annotator
`labels_<id>.json` files, computes:

  • headline multiclass Krippendorff α (nominal) on the mechanism class — the
    labeling-reliability number to compare against the ≥0.70 gate
  • per-class one-vs-rest α + observed pairwise agreement, per mechanism class
    (one-vs-rest α is prevalence-sensitive; the agreement rate is the intuitive read)
  • acceptance gate — items ≥2 annotators reject as not-a-real-error are dropped
    (mined) / flagged as bad_injection (synthetic)
  • consensus gold (majority class/etymology/edit_op; 3-way split → adjudicate)
  • a disagreement report for the senior adjudicator
  • synthetic construction-gold check — consensus class ≠ construction class

Krippendorff's α is implemented inline (nominal), no third-party dependency.

  PYTHONUTF8=1 python score_annotation.py --labels labels_ann1.json labels_ann2.json labels_ann3.json
  PYTHONUTF8=1 python score_annotation.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALPHA_SET = HERE / "alpha_set.jsonl"
GOLD_OUT = HERE / "gold.json"
CLASS_NAME = {1: "tone_mark", 2: "consonant_pair", 3: "karan_native",
              4: "vowel", 5: "cluster_metathesis", 6: "loanword"}


# ============================ Krippendorff's α (inline) ============================

def krippendorff_alpha(units: list[list], level: str = "nominal") -> float:
    """α from reliability units (each = list of ratings, missing dropped).
    level: 'nominal' or 'ordinal'. Returns nan if undefined (e.g. <2 values)."""
    o: dict[tuple, float] = defaultdict(float)
    for u in units:
        vals = [v for v in u if v is not None]
        m = len(vals)
        if m < 2:
            continue
        for i in range(m):
            for j in range(m):
                if i != j:
                    o[(vals[i], vals[j])] += 1.0 / (m - 1)
    values = sorted({c for c, _ in o} | {k for _, k in o})
    if len(values) < 2:
        return float("nan")
    n_c = {v: sum(o.get((v, k), 0.0) for k in values) for v in values}
    n = sum(n_c.values())
    if n < 2:
        return float("nan")
    if level == "nominal":
        def d2(c, k):
            return 0.0 if c == k else 1.0
    elif level == "ordinal":
        def d2(c, k):
            lo, hi = (c, k) if c <= k else (k, c)
            s = sum(n_c[g] for g in values if lo <= g <= hi)
            return (s - (n_c[c] + n_c[k]) / 2.0) ** 2
    else:
        raise ValueError(level)
    do = sum(cnt * d2(c, k) for (c, k), cnt in o.items())
    de = sum(n_c[c] * n_c[k] * d2(c, k) for c in values for k in values)
    if de == 0:
        return float("nan")
    return 1.0 - (n - 1) * do / de


# ============================ data loading ============================

def load_labels(paths: list[Path]) -> list[tuple[str, dict]]:
    out = []
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        out.append((data.get("annotator", p.stem), data.get("labels", {})))
    return out


def load_alpha_set(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"missing {path.name} — run build_sheets.py first (it dumps the α-set).")
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


# ============================ vote extraction ============================

def edit_label(labs: dict, item_id: str, ei: int) -> dict | None:
    """One annotator's label dict for item/edit, or None if absent/unanswered."""
    l = labs.get(item_id)
    if not l:
        return None
    edits = l.get("edits") or []
    if ei >= len(edits) or not edits[ei] or "accept" not in edits[ei]:
        return None
    return edits[ei]


def class_vote(e: dict | None):
    """The class an annotator assigned, or None if they rejected / didn't answer."""
    if not e or not e.get("accept"):
        return None
    return e.get("class")


def gather(item: dict, labelsets, ei: int = 0):
    """Per annotator: (name, label-dict-or-None) for this item's edit `ei`."""
    return [(name, edit_label(labs, item["id"], ei)) for name, labs in labelsets]


# ============================ α + agreement ============================

def headline_alpha(items, labelsets):
    units = []
    for it in items:
        votes = [class_vote(e) for _, e in gather(it, labelsets)]
        if sum(v is not None for v in votes) >= 2:
            units.append(votes)
    return krippendorff_alpha(units, "nominal"), len(units)


def per_class_alpha(items, labelsets):
    """One-vs-rest nominal α + observed pairwise agreement, per mechanism class.

    α_C uses all items (1 if an accepting annotator chose C, else 0) → prevalence-
    sensitive. agreement_C is the mean pairwise class-match over items whose
    CONSTRUCTION class is C — the intuitive 'do they agree on this class' read."""
    res = {}
    for C in range(1, 7):
        ovr_units = []
        for it in items:
            votes = [class_vote(e) for _, e in gather(it, labelsets)]
            present = [v for v in votes if v is not None]
            if len(present) >= 2:
                ovr_units.append([1 if v == C else 0 for v in present])
        a = krippendorff_alpha(ovr_units, "nominal")

        agr_num = agr_den = n_items = 0
        for it in items:
            if it["edits"][0]["class"] != C:
                continue
            present = [v for v in (class_vote(e) for _, e in gather(it, labelsets)) if v is not None]
            if len(present) >= 2:
                n_items += 1
                for i in range(len(present)):
                    for j in range(i + 1, len(present)):
                        agr_den += 1
                        agr_num += int(present[i] == present[j])
        agreement = agr_num / agr_den if agr_den else float("nan")
        res[C] = {"alpha": a, "n_ovr": len(ovr_units), "agreement": agreement, "n_class": n_items}
    return res


# ============================ acceptance + consensus ============================

def majority(values):
    """Most-common value + its count; None if no values."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None, 0
    c = Counter(vals).most_common()
    return c[0]


def build_consensus(items, labelsets):
    gold, dropped, rows = {}, [], []
    for it in items:
        track = it.get("source_track", "?")
        votes = gather(it, labelsets)  # [(name, e|None)]
        accepts = [e.get("accept") for _, e in votes if e]
        n_reject = sum(a is False for a in accepts)
        n_accept = sum(a is True for a in accepts)

        # acceptance gate
        if n_reject >= 2:
            entry = {"source_track": track, "accept": False, "verified": False,
                     "consensus": "dropped_not_error" if track == "mined" else "bad_injection",
                     "votes": {"accept": accepts}}
            gold[it["id"]] = entry
            if track == "mined":
                dropped.append(it["id"])
            rows.append((it, votes, entry))
            continue

        classes = [class_vote(e) for _, e in votes]
        present = [c for c in classes if c is not None]
        top, cnt = majority(present)
        distinct = len(set(present))
        if not present:
            con = "no_votes"
        elif distinct == 1:
            con = "unanimous"
        elif cnt >= 2:
            con = "majority"
        else:
            con = "adjudicate"   # all distinct (e.g. 1/1/1)

        ety, _ = majority([e.get("etymology") for _, e in votes if e and e.get("accept")])
        op, _ = majority([e.get("edit_op") for _, e in votes if e and e.get("accept")])
        entry = {
            "source_track": track, "accept": True,
            "class": top, "class_name": CLASS_NAME.get(top),
            "etymology": ety, "edit_op": op,
            "consensus": con, "verified": con in ("unanimous", "majority"),
            "votes": {"class": classes,
                      "annotators": [n for n, _ in votes]},
        }
        if track == "synthetic":
            cc = it["edits"][0]["class"]
            entry["construction_class"] = cc
            entry["class_mismatch"] = (top is not None and top != cc)
        gold[it["id"]] = entry
        if con not in ("unanimous",):
            rows.append((it, votes, entry))
    return gold, dropped, rows


# ============================ reporting ============================

def _fmt(x):
    return "  n/a" if (isinstance(x, float) and math.isnan(x)) else f"{x:5.3f}"


def report(items, labelsets, threshold):
    mined = [it for it in items if it.get("source_track") == "mined"]
    synth = [it for it in items if it.get("source_track") == "synthetic"]
    names = ", ".join(n for n, _ in labelsets)
    print(f"\nα-set: {len(items)} items · {len(mined)} mined + {len(synth)} synthetic · "
          f"{len(labelsets)} annotators ({names})")

    a, n = headline_alpha(items, labelsets)
    gate = "PASS" if (not math.isnan(a) and a >= threshold) else "below"
    print("\n── Mechanism class · labeling reliability ──────────────────")
    print(f"  headline multiclass α (nominal) = {_fmt(a)}   (n={n})   gate ≥ {threshold:.2f}: {gate}")
    print("  per-class (one-vs-rest α · prevalence-sensitive | agreement = pairwise match on that gold class):")
    print(f"    {'class':<22}{'α':>8}{'agree':>9}{'n_class':>9}")
    for C, s in per_class_alpha(items, labelsets).items():
        tag = "" if s["n_class"] else "   (no units)"
        print(f"    {C} {CLASS_NAME[C]:<19}{_fmt(s['alpha']):>8}{_fmt(s['agreement']):>9}{s['n_class']:>9}{tag}")

    gold, dropped, rows = build_consensus(items, labelsets)
    con_counts = Counter(v["consensus"] for v in gold.values())
    mism = [k for k, v in gold.items() if v.get("class_mismatch")]
    bad_inj = [k for k, v in gold.items() if v.get("consensus") == "bad_injection"]
    print("\n── Consensus ───────────────────────────────────────────────")
    for k in ("unanimous", "majority", "adjudicate", "no_votes",
              "dropped_not_error", "bad_injection"):
        if con_counts.get(k):
            print(f"    {k:<20} {con_counts[k]}")
    print(f"  mined dropped (≥2 reject): {len(dropped)}")
    print(f"  synthetic flagged bad_injection: {len(bad_inj)}")
    print(f"  synthetic class_mismatch (consensus ≠ construction): {len(mism)}"
          + (f"  → {', '.join(mism[:8])}{' …' if len(mism) > 8 else ''}" if mism else ""))

    if rows:
        print("\n── Disagreement report (for the adjudicator) ───────────────")
        rank = {"adjudicate": 0, "dropped_not_error": 1, "bad_injection": 1,
                "majority": 2, "no_votes": 3}
        rows.sort(key=lambda r: (rank.get(r[2]["consensus"], 9),
                                 0 if r[0].get("source_track") == "mined" else 1))
        for it, votes, entry in rows:
            print(f"\n  [{entry['consensus']}] {it['id']} ({it.get('source_track')}, "
                  f"gold-construction class {it['edits'][0]['class']})")
            print(f"    wrong→correct: {it['edits'][0]['wrong']} → {it['edits'][0]['correct']}")
            for name, e in votes:
                if not e:
                    print(f"      {name:<10} —")
                    continue
                acc = "✓" if e.get("accept") else "✗"
                print(f"      {name:<10} accept={acc} class={e.get('class')} "
                      f"ety={e.get('etymology')} op={e.get('edit_op')}")
    return gold, dropped


def write_gold(gold, items, labelsets, threshold, dropped):
    pca = {str(C): s["alpha"] for C, s in per_class_alpha(items, labelsets).items()}
    a, _ = headline_alpha(items, labelsets)
    payload = {
        "generated": _now(), "threshold": threshold,
        "n_set": len(items),
        "n_mined": sum(1 for it in items if it.get("source_track") == "mined"),
        "n_dropped": len(dropped),
        "headline_alpha": None if math.isnan(a) else round(a, 4),
        "per_class_alpha": {k: (None if math.isnan(v) else round(v, 4)) for k, v in pca.items()},
        "labels": gold,
    }
    GOLD_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {GOLD_OUT.name}  ({len(gold)} items; {payload['n_dropped']} dropped)")


def _now():
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


# ============================ selftest ============================

def selftest():
    assert krippendorff_alpha([[1, 1], [2, 2], [3, 3]], "nominal") == 1.0
    a = krippendorff_alpha([[1, 1], [2, 2], [1, 2], [2, 1]], "nominal")
    assert round(a, 3) == 0.125, a

    # synthetic fixtures: 3 annotators over 4 items
    items = [
        {"id": "m1", "source_track": "mined",
         "edits": [{"class": 1, "wrong": "ก่", "correct": "ก้", "etymology": "native", "edit_op": "substitution"}]},
        {"id": "m2", "source_track": "mined",
         "edits": [{"class": 2, "wrong": "อากาส", "correct": "อากาศ", "etymology": "native", "edit_op": "substitution"}]},
        {"id": "s1", "source_track": "synthetic",
         "edits": [{"class": 4, "wrong": "สังเกตุ", "correct": "สังเกต", "etymology": "native", "edit_op": "insertion"}]},
        {"id": "s2", "source_track": "synthetic",
         "edits": [{"class": 5, "wrong": "สถิติ", "correct": "สถิติ", "etymology": "native", "edit_op": "transposition"}]},
    ]

    def mk(name, m1c, m2c, s1c, s2c, accepts=(True, True, True, True)):
        def ed(c, acc):
            return {"accept": acc, "class": c, "etymology": "native", "edit_op": "substitution"}
        return (name, {"m1": {"edits": [ed(m1c, accepts[0])]},
                       "m2": {"edits": [ed(m2c, accepts[1])]},
                       "s1": {"edits": [ed(s1c, accepts[2])]},
                       "s2": {"edits": [ed(s2c, accepts[3])]}})

    # all agree on the construction class → headline α = 1.0
    ls = [mk("a", 1, 2, 4, 5), mk("b", 1, 2, 4, 5), mk("c", 1, 2, 4, 5)]
    a, n = headline_alpha(items, ls)
    assert n == 4 and a == 1.0, (a, n)
    gold, dropped, rows = build_consensus(items, ls)
    assert all(v["consensus"] == "unanimous" for v in gold.values()), gold
    assert not rows and not dropped

    # m2: a 3-way split (2/3/4) → adjudicate; s2: ≥2 reject → bad_injection
    ls = [mk("a", 1, 2, 4, 5, (True, True, True, False)),
          mk("b", 1, 3, 4, 5, (True, True, True, False)),
          mk("c", 1, 4, 4, 5, (True, True, True, True))]
    gold, dropped, rows = build_consensus(items, ls)
    assert gold["m2"]["consensus"] == "adjudicate", gold["m2"]
    assert gold["s2"]["consensus"] == "bad_injection", gold["s2"]
    assert any(r[0]["id"] == "m2" for r in rows)

    # synthetic class_mismatch: everyone says s1 is class 1 (construction says 4)
    ls = [mk("a", 1, 2, 1, 5), mk("b", 1, 2, 1, 5), mk("c", 1, 2, 1, 5)]
    gold, *_ = build_consensus(items, ls)
    assert gold["s1"]["class_mismatch"] is True and gold["s1"]["class"] == 1, gold["s1"]

    # class-6 with no units prints n/a (no class-6 item in fixtures)
    pca = per_class_alpha(items, ls)
    assert pca[6]["n_class"] == 0
    print("selftest OK  (α=0.125 balanced-2x2; unanimous/adjudicate/bad_injection/class_mismatch paths)")


# ============================ main ============================

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", type=Path, nargs="+", help="labels_<id>.json files (≥2)")
    ap.add_argument("--alpha-set", type=Path, default=ALPHA_SET)
    ap.add_argument("--threshold", type=float, default=0.70)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if not args.labels or len(args.labels) < 2:
        ap.error("need ≥2 --labels files (or --selftest)")

    items = load_alpha_set(args.alpha_set)
    labelsets = load_labels(args.labels)
    gold, dropped = report(items, labelsets, args.threshold)
    write_gold(gold, items, labelsets, args.threshold, dropped)


if __name__ == "__main__":
    main()
