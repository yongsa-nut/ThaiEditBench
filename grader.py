"""
Phase 7 — TCC-level grader for EditingBench (plan.md §7).

Primary metric: SIGHAN-CSC-style **detection** and **correction** F1 at Thai
Character Cluster (TCC) level, adapted to span edits (ERRANT/M2 style so it is
robust to insertions/deletions, which Thai orthographic errors produce).

Scoring representation: we DERIVE minimal TCC edits by aligning `text_wrong`
against a target (`text_correct` for gold, the model output for system) with the
SAME deterministic Levenshtein alignment. Consequence: a system output identical
to `text_correct` produces an edit set identical to gold -> score exactly 1.0.

Public API (per item, edits already minimal):
  align_edits(text_wrong, text_target) -> [Edit(start, end, repl), ...]
  score_detection(gold, sys)  -> Counts(tp, n_sys, n_gold)      (span match)
  score_correction(gold, sys) -> Counts(tp, n_sys, n_gold)      (span + repl)
  score_sentence_accuracy(refs, sys_text) -> bool               (any-ref exact)
  per_class_recall(item, sys_edits) -> {class: (corrected, total)}
  gleu(refs_tokens, sys_tokens) -> float                        (word-level)

Corpus helpers: prf_from_counts, micro_prf, bootstrap_ci.
ChERRANT span-F0.5 (score_cherrant) is the SECONDARY metric and depends on the
Phase-6 ThERRANT classifier — deferred; per-class correction recall here already
gives the per-mechanism breakdown the Phase-8 check-in needs.

Run:  PYTHONUTF8=1 python grader.py   (self-test)
"""
from __future__ import annotations

import math
import random
from collections import Counter, namedtuple

from inject import normalize, tcc_segments

Edit = namedtuple("Edit", "start end repl")        # src[start:end] (TCC idx) -> repl
Counts = namedtuple("Counts", "tp n_sys n_gold")


# ---------------------------------------------------------------- alignment ---
def align_edits(text_wrong: str, text_target: str) -> list[Edit]:
    """Minimal TCC-level edits turning text_wrong into text_target.

    Contiguous non-match operations are merged into one edit. A pure insertion is
    a zero-width edit (start == end) at the source position it precedes.
    """
    src = tcc_segments(normalize(text_wrong))
    tgt = tcc_segments(normalize(text_target))
    n, m = len(src), len(tgt)

    # Levenshtein DP (unit sub/ins/del cost)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        si = src[i - 1]
        row, prev = dp[i], dp[i - 1]
        for j in range(1, m + 1):
            cost = 0 if si == tgt[j - 1] else 1
            row[j] = min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + cost)

    # backtrace -> forward op list of (kind, si, tj); kinds: M S D I
    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (0 if src[i - 1] == tgt[j - 1] else 1):
            ops.append(("M" if src[i - 1] == tgt[j - 1] else "S", i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("D", i - 1, None))
            i -= 1
        else:
            ops.append(("I", None, j - 1))
            j -= 1
    ops.reverse()

    # group contiguous non-match ops into edits
    edits, cur, src_ptr = [], None, 0
    for kind, _si, tj in ops:
        if kind == "M":
            if cur is not None:
                edits.append(Edit(cur[0], cur[1], "".join(cur[2])))
                cur = None
            src_ptr += 1
        else:
            if cur is None:
                cur = [src_ptr, src_ptr, []]            # [start, end, tgt tokens]
            if kind in ("S", "D"):
                src_ptr += 1
                cur[1] = src_ptr
            if kind in ("S", "I"):
                cur[2].append(tgt[tj])
    if cur is not None:
        edits.append(Edit(cur[0], cur[1], "".join(cur[2])))
    return edits


# --------------------------------------------------------------- primary F1 ---
def _match_counts(gold: list[Edit], sysd: list[Edit], key) -> Counts:
    pool = Counter(key(e) for e in gold)
    tp = 0
    for e in sysd:
        k = key(e)
        if pool[k] > 0:
            pool[k] -= 1
            tp += 1
    return Counts(tp, len(sysd), len(gold))


def score_detection(gold: list[Edit], sysd: list[Edit]) -> Counts:
    """Right error POSITION flagged (span match, replacement ignored)."""
    return _match_counts(gold, sysd, key=lambda e: (e.start, e.end))


def score_correction(gold: list[Edit], sysd: list[Edit]) -> Counts:
    """Right position AND right replacement."""
    return _match_counts(gold, sysd, key=lambda e: (e.start, e.end, e.repl))


def score_sentence_accuracy(refs: list[str], sys_text: str) -> bool:
    s = normalize(sys_text)
    return any(s == normalize(r) for r in refs)


def per_class_recall(item: dict, sys_edits: list[Edit]) -> dict[int, tuple[int, int]]:
    """Map each minimal gold edit to its mechanism class (via the stored item
    edit whose TCC span contains it), then count how many were corrected.
    Returns {class: (n_corrected, n_total)}."""
    gold = align_edits(item["text_wrong"], item["text_correct"])
    sys_keys = Counter((e.start, e.end, e.repl) for e in sys_edits)
    stored = item["edits"]

    def class_of(e: Edit) -> int:
        for s in stored:                                # containment (pure-ins uses start)
            if s["tcc_start"] <= e.start and e.end <= s["tcc_end"]:
                return s["class"]
            if e.start == e.end and s["tcc_start"] <= e.start <= s["tcc_end"]:
                return s["class"]
        return 0

    out: dict[int, list[int]] = {}
    for e in gold:
        c = class_of(e)
        acc = out.setdefault(c, [0, 0])
        acc[1] += 1
        if sys_keys[(e.start, e.end, e.repl)] > 0:
            sys_keys[(e.start, e.end, e.repl)] -= 1
            acc[0] += 1
    return {c: (v[0], v[1]) for c, v in out.items()}


# ----------------------------------------------------------- tertiary: GLEU ---
def _ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def gleu(src_tokens: list[str], ref_tokens: list[str], sys_tokens: list[str],
         max_n: int = 4) -> float:
    """GEC-GLEU (Napoles et al. 2015), single reference. Rewards sys n-grams that
    match the reference and penalises sys n-grams shared with the (uncorrected)
    source but not the reference."""
    if not sys_tokens:
        return 0.0
    log_sum, used = 0.0, 0
    for n in range(1, max_n + 1):
        if len(sys_tokens) < n:
            break
        h = _ngrams(sys_tokens, n)
        r = _ngrams(ref_tokens, n)
        s = _ngrams(src_tokens, n)
        total = sum(h.values())
        if total == 0:
            break
        num = 0
        for g, cnt in h.items():
            match_r = min(cnt, r.get(g, 0))
            penalty = max(0, min(cnt, s.get(g, 0)) - r.get(g, 0))
            num += match_r - penalty
        p_n = max(num, 0) / total
        log_sum += math.log(p_n) if p_n > 0 else math.log(1e-9)
        used += 1
    if used == 0:
        return 0.0
    bp = 1.0 if len(sys_tokens) > len(ref_tokens) else math.exp(1 - len(ref_tokens) / max(len(sys_tokens), 1))
    return bp * math.exp(log_sum / used)


# --------------------------------------------------------- corpus aggregation -
def prf_from_counts(tp: int, n_sys: int, n_gold: int) -> dict:
    if n_sys == 0 and n_gold == 0:
        return {"P": 1.0, "R": 1.0, "F1": 1.0}
    p = tp / n_sys if n_sys else (1.0 if n_gold == 0 else 0.0)
    r = tp / n_gold if n_gold else (1.0 if n_sys == 0 else 0.0)
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"P": p, "R": r, "F1": f1}


def micro_prf(counts: list[Counts]) -> dict:
    return prf_from_counts(sum(c.tp for c in counts),
                           sum(c.n_sys for c in counts),
                           sum(c.n_gold for c in counts))


def bootstrap_ci(counts: list[Counts], n_boot: int = 1000, seed: int = 20260524,
                 alpha: float = 0.05) -> tuple[float, float]:
    """95% CI on micro-F1 by resampling items (deterministic seed)."""
    if not counts:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(counts)
    f1s = []
    for _ in range(n_boot):
        sample = [counts[rng.randrange(n)] for _ in range(n)]
        f1s.append(micro_prf(sample)["F1"])
    f1s.sort()
    lo = f1s[int((alpha / 2) * n_boot)]
    hi = f1s[min(int((1 - alpha / 2) * n_boot), n_boot - 1)]
    return (lo, hi)


# --------------------------------------------------------------- self-test ---
if __name__ == "__main__":
    import json
    from pathlib import Path

    HERE = Path(__file__).resolve().parent
    items = [json.loads(l) for l in (HERE / "data" / "items_dev.jsonl").open(encoding="utf-8")][:200]

    # (a) gold-corrected -> perfect
    det, cor, sent = [], [], 0
    for it in items:
        g = align_edits(it["text_wrong"], it["text_correct"])
        s = align_edits(it["text_wrong"], it["text_correct"])     # system == gold
        det.append(score_detection(g, s))
        cor.append(score_correction(g, s))
        sent += score_sentence_accuracy([it["text_correct"]], it["text_correct"])
    print(f"[gold==sys] detF1={micro_prf(det)['F1']:.3f} corrF1={micro_prf(cor)['F1']:.3f} "
          f"sentacc={sent/len(items):.3f}  (expect 1.000 / 1.000 / 1.000)")

    # (b) no-op system (returns the wrong text unchanged) -> recall 0
    det0, cor0 = [], []
    for it in items:
        g = align_edits(it["text_wrong"], it["text_correct"])
        s = align_edits(it["text_wrong"], it["text_wrong"])       # changed nothing
        det0.append(score_detection(g, s))
        cor0.append(score_correction(g, s))
    print(f"[no-op sys] detF1={micro_prf(det0)['F1']:.3f} corrR={micro_prf(cor0)['R']:.3f} "
          f"(expect 0.000 / 0.000)")

    # (c) GLEU sanity: perfect vs no-op
    from pythainlp.tokenize import word_tokenize
    g_perfect = g_noop = 0.0
    for it in items[:50]:
        srcT = word_tokenize(it["text_wrong"], engine="newmm")
        refT = word_tokenize(it["text_correct"], engine="newmm")
        g_perfect += gleu(srcT, refT, refT)
        g_noop += gleu(srcT, refT, srcT)
    print(f"[GLEU] perfect={g_perfect/50:.3f}  no-op={g_noop/50:.3f}  (perfect should be ~1.0 > no-op)")
    print("self-test OK")
