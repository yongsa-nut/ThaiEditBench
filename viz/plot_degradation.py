"""Figure 1 for the ThaiEditBench paper — length-degradation slope + over-editing.

Panel (a): correction-F1 slope T1->T2->T3 per model (reads each tier's
results/<alias>.json — the SAME files the leaderboard + paper use).
Panel (b): over-edit RATE per 10k clean TCCs across tiers, log scale (reads
error_analysis.json, field `clean_tcc`). Length-normalized: shows a per-unit
false-positive rate (roughly flat across length) rather than the exposure-inflated
per-item count. Weak models run many times the frontier's per-unit rate at every tier.
Output: paper/fig1-degradation.{png,pdf} (300 dpi, paper-ready).

  PYTHONUTF8=1 python viz/plot_degradation.py
  (run error_analysis.py first so error_analysis.json is current)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
EDIT = HERE.parent
OUT = EDIT / "paper"   # repo paper/ dir

TIERS = [("T1\nsentence", "results"), ("T2\nparagraph", "results_t2"),
         ("T3\npage", "results_t3")]
MIN_N = {"results": 700, "results_t2": 100, "results_t3": 100}

# display name + plot group (frontier / open / thai)
MODELS = {
    "gpt55-high": ("GPT-5.5 (high)", "frontier"),
    "gpt55-med": ("GPT-5.5 (med)", "frontier"),
    "opus-4.7": ("Claude Opus 4.7", "frontier"),
    "gemini-3.5-flash": ("Gemini 3.5 Flash", "frontier"),
    "gpt54-mini": ("GPT-5.4-mini", "frontier"),
    "sonnet-4.6": ("Claude Sonnet 4.6", "frontier"),
    "gemma-4-31b": ("Gemma-4-31B", "open"),
    "deepseek-flash": ("DeepSeek V4 Flash", "open"),
    "deepseek-v4-pro": ("DeepSeek V4 Pro", "open"),
    "glm-5.1": ("GLM-5.1", "open"),
    "minimax-m2.7": ("MiniMax-M2.7", "open"),
    "qwen3.6-35b-a3b": ("Qwen3.6-35B-A3B", "open"),
    "typhoon25": ("Typhoon 2.5 30B", "thai"),
    "typhoon-s": ("Typhoon-S 8B", "thai"),
    "openthaigpt": ("OpenThaiGPT v7.2", "thai"),
    "thalle": ("THaLLE 8B", "thai"),
}
GROUP_STYLE = {  # color, linewidth, alpha, zorder
    "frontier": ("#2563eb", 1.8, 0.95, 3),
    "open":     ("#16a34a", 1.4, 0.85, 2),
    "thai":     ("#dc2626", 1.4, 0.85, 2),
}
# a few models get a label callout so the legend stays readable (story carriers only)
CALLOUT = {"gemma-4-31b", "qwen3.6-35b-a3b", "typhoon25"}


def load_tier(subdir: str) -> dict[str, dict]:
    out = {}
    d = EDIT / subdir
    for jp in d.glob("*.json"):
        if jp.stem.startswith("_"):
            continue
        try:
            m = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if m.get("n_errors", 0) >= m.get("n", 0) or m.get("n", 0) < MIN_N[subdir]:
            continue
        out[jp.stem] = m
    return out


def load_overedits() -> dict:
    """error_analysis.json -> {tier_label: {alias: over_edits per 10k clean TCCs}}.

    Length-normalized: the denominator is clean (non-error) TCCs, not item count, so
    the panel shows a per-unit false-positive RATE rather than the exposure-inflated
    per-item count. The rate is roughly flat across tiers (the per-item explosion is
    mostly text exposure), but it still separates weak models from the frontier.
    """
    jp = EDIT / "error_analysis.json"
    if not jp.exists():
        return {}
    d = json.loads(jp.read_text(encoding="utf-8"))
    out = {}
    for tier in ("T1", "T2", "T3"):
        out[tier] = {}
        for alias, m in d.get(tier, {}).items():
            ctcc = m.get("clean_tcc", 0)
            if ctcc:
                out[tier][alias] = 10000.0 * m.get("over_edits", 0) / ctcc
    return out


def main():
    tier_data = [load_tier(sub) for _, sub in TIERS]
    overed = load_overedits()
    x = list(range(len(TIERS)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 4.0))

    # ---- (a) correction-F1 slope ----
    for alias, (disp, grp) in MODELS.items():
        ys = [tier_data[i].get(alias, {}).get("correction", {}).get("F1")
              for i in range(len(TIERS))]
        if any(v is None for v in ys):
            continue
        color, lw, alpha, z = GROUP_STYLE[grp]
        ax1.plot(x, ys, "-o", color=color, lw=lw, alpha=alpha, ms=3.5, zorder=z)
        if alias in CALLOUT:
            ax1.annotate(disp, (x[-1], ys[-1]), xytext=(4, 0),
                         textcoords="offset points", fontsize=7,
                         color=color, va="center")
    ax1.set_xticks(x)
    ax1.set_xticklabels([t for t, _ in TIERS], fontsize=8)
    ax1.set_ylabel("Correction F1", fontsize=9)
    ax1.set_title("(a) Length-degradation slope", fontsize=10)
    ax1.set_ylim(0.25, 1.0)
    ax1.grid(axis="y", ls=":", alpha=0.4)

    # ---- (b) over-edits per 100 items across tiers (log scale) ----
    tier_keys = ["T1", "T2", "T3"]
    for alias, (disp, grp) in MODELS.items():
        ys = [overed.get(tk, {}).get(alias) for tk in tier_keys]
        if any(v is None for v in ys):
            continue
        color, lw, alpha, z = GROUP_STYLE[grp]
        ax2.plot(x, ys, "-o", color=color, lw=lw, alpha=alpha, ms=3.5, zorder=z)
        # stagger labels so the upper cluster (Qwen/OpenThaiGPT/Typhoon) stays legible
        dy = {"qwen3.6-35b-a3b": 6, "openthaigpt": -2, "typhoon25": -10}.get(alias)
        if dy is not None:
            ax2.annotate(disp, (x[-1], ys[-1]), xytext=(5, dy),
                         textcoords="offset points", fontsize=7,
                         color=color, va="center")
    ax2.set_yscale("log")
    ax2.set_xticks(x)
    ax2.set_xticklabels([t for t, _ in TIERS], fontsize=8)
    ax2.set_ylabel("Over-edits per 10k clean TCCs (log; higher = worse)", fontsize=9)
    ax2.set_title("(b) Over-edit rate (length-normalized)", fontsize=10)
    ax2.grid(axis="y", ls=":", alpha=0.4, which="both")

    # shared legend (by group)
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=GROUP_STYLE[g][0], lw=2, marker="o", ms=4)
               for g in ("frontier", "open", "thai")]
    fig.legend(handles, ["Frontier proprietary", "Open-weight", "Thai-native"],
               loc="lower center", ncol=3, fontsize=8, frameon=False,
               bbox_to_anchor=(0.5, -0.02))

    fig.tight_layout(rect=(0, 0.05, 1, 1))
    OUT.mkdir(exist_ok=True)
    png, pdf = OUT / "fig1-degradation.png", OUT / "fig1-degradation.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print(f"-> {png}")
    print(f"-> {pdf}")
    # report the slope numbers used (sanity)
    for alias in ("gpt55-med", "gemma-4-31b", "typhoon25", "qwen3.6-35b-a3b"):
        ys = [tier_data[i].get(alias, {}).get("correction", {}).get("F1") for i in range(3)]
        print(f"   {alias}: " + " -> ".join(f"{v:.3f}" if v else "NA" for v in ys))


if __name__ == "__main__":
    main()
