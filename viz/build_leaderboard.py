"""Bake the EditingBench leaderboard (multi-tier) into a self-contained leaderboard.html.

Reads each tier's results/<alias>.json (written by score_runs.py) + the model
registry, and bakes a tier-toggle, ranked, sortable, ArtificialAnalysis-style table
+ per-class heatmap. Open offline; drop into the public site as-is.

  PYTHONUTF8=1 python viz/build_leaderboard.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDIT = HERE.parent
sys.path.insert(0, str(EDIT))
from run_editing import REGISTRY                       # noqa: E402

TEMPLATE = HERE / "leaderboard.html"
BAKED_RE = re.compile(r"^const BAKED = .*$", re.M)

# (label, results subdir, min items to include)
TIERS = [("T1 · sentence", "results", 700),
         ("T2 · paragraph", "results_t2", 100),
         ("T3 · page", "results_t3", 100)]
THAI_NATIVE = {"typhoon25", "typhoon-s", "openthaigpt", "thalle"}


def provider_of(spec) -> str:
    if not spec:
        return "—"
    p, url = spec.get("provider"), spec.get("base_url") or ""
    if p == "responses":
        return "OpenAI"
    if p == "anthropic":
        return "Anthropic"
    if "opentyphoon" in url:
        return "OpenTyphoon"
    if "openrouter" in url:
        return "OpenRouter"
    if "generativelanguage" in url:
        return "Google"
    if "thaillm" in url:
        return "ThaiLLM gateway"
    return "—"


def tier_rows(subdir: str, min_n: int):
    results = EDIT / subdir
    rows, max_n = [], 0
    for jp in sorted(results.glob("*.json")):
        alias = jp.stem
        try:
            m = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:
            continue
        n = m.get("n", 0)
        if m.get("n_errors", 0) >= n or n < min_n:
            continue
        max_n = max(max_n, n)
        rows.append({
            "alias": alias, "display": alias,
            "provider": provider_of(REGISTRY.get(alias)),
            "thai_native": alias in THAI_NATIVE, "n": n,
            "corr_f1": m["correction"]["F1"], "corr_ci": m.get("correction_ci95", [None, None]),
            "det_f1": m["detection"]["F1"], "sent": m["sentence_accuracy"],
            "fidelity": m.get("clean_sentence_fidelity"),
            "gleu": m["gleu"], "cherrant": m.get("cherrant_span_f05_overall", 0.0),
            "per_class": {c: m["per_class_correction_recall"].get(str(c), {}).get("recall")
                          for c in range(1, 7)},
        })
    rows.sort(key=lambda r: -r["corr_f1"])
    return {"max_n": max_n, "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "leaderboard.html")
    args = ap.parse_args()

    tiers = []
    for label, subdir, min_n in TIERS:
        t = tier_rows(subdir, min_n)
        if t["rows"]:
            tiers.append({"label": label, **t})
    baked = {"benchmark": "EditingBench — Thai orthographic correction (Track 1 · Subtask 2)",
             "tiers": tiers}

    tpl = TEMPLATE.read_text(encoding="utf-8")
    if not BAKED_RE.search(tpl):
        raise SystemExit("leaderboard.html has no `const BAKED = …;` line")
    js = json.dumps(baked, ensure_ascii=False).replace("</", "<\\/")
    args.out.write_text(BAKED_RE.sub(lambda _m: f"const BAKED = {js};", tpl, count=1),
                        encoding="utf-8")
    for t in tiers:
        print(f"{t['label']}: {len(t['rows'])} models (max n={t['max_n']})")
    print(f"-> {args.out.relative_to(EDIT)}")


if __name__ == "__main__":
    main()
