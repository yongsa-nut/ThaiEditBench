"""
Phase 8 — grade model runs and emit the results table (plan.md §8).

Reads the persisted sample + each results/<alias>.jsonl, grades with grader.py,
writes results/<alias>.json (full metrics) and a combined markdown leaderboard to
subtask2/sample-run-results.md.

Metrics: detection F1, correction F1 (+95% bootstrap CI), sentence accuracy,
per-class correction recall (the loanword-class diagnostic), word-level GLEU.

Run:  PYTHONUTF8=1 python score_runs.py --split test_public --n 100
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from pythainlp.tokenize import word_tokenize

from grader import (align_edits, score_detection, score_correction,
                    score_sentence_accuracy, per_class_recall, gleu,
                    micro_prf, bootstrap_ci, prf_from_counts)
from therrant import annotate, load_loan_lexicon, cherrant_counts, f_beta
from variants import reconcile_variants

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
REPORT = HERE / "sample-run-results.md"
CLASS_NAME = {1: "tone", 2: "consonant", 3: "การันต์", 4: "vowel",
              5: "cluster", 6: "loanword"}


def grade_run(items_by_id, run_path, loan_lex):
    outputs = {}
    n_err = 0
    for line in run_path.open(encoding="utf-8"):
        r = json.loads(line)
        outputs[r["id"]] = r
        n_err += bool(r.get("error"))

    det, cor, sent = [], [], 0
    pc = defaultdict(lambda: [0, 0])                 # class -> [corrected, total]
    cher = defaultdict(lambda: [0, 0, 0])            # class -> [tp, n_sys, n_gold] (ChERRANT)
    gleus, n = [], 0
    fid_ok = fid_tot = 0                             # clean-sentence fidelity (T2+ paragraph tier)
    for iid, it in items_by_id.items():
        if iid not in outputs:
            continue
        n += 1
        out = outputs[iid].get("output") or ""
        # accept standard spelling variants (สิทธิ~สิทธิ์) by adopting gold's form;
        # empty/failed = no-op (recall 0)
        sys_text = reconcile_variants(out, it["text_correct"]) if out else it["text_wrong"]
        gold = align_edits(it["text_wrong"], it["text_correct"])
        sysd = align_edits(it["text_wrong"], sys_text)
        det.append(score_detection(gold, sysd))
        cor.append(score_correction(gold, sysd))
        sent += score_sentence_accuracy([it["text_correct"]], sys_text)
        # fidelity: did the model leave each CLEAN sentence untouched (no system edit
        # overlapping its TCC span)? = the precision/over-edit signal on long context.
        for sp in it.get("sentences", []):
            if sp.get("has_error") or sp.get("tcc_start") is None:
                continue
            ts, te = sp["tcc_start"], sp["tcc_end"]
            touched = any((e.start < te and e.end > ts) or (e.start == e.end and ts <= e.start <= te)
                          for e in sysd)
            fid_tot += 1
            fid_ok += not touched
        for c, (got, tot) in per_class_recall(it, sysd).items():
            pc[c][0] += got
            pc[c][1] += tot
        for c, (tp, ns, ng) in cherrant_counts(it["text_wrong"], it["text_correct"],
                                               sys_text, loan_lex).items():
            cher[c][0] += tp
            cher[c][1] += ns
            cher[c][2] += ng
        gleus.append(gleu(word_tokenize(it["text_wrong"], engine="newmm"),
                          word_tokenize(it["text_correct"], engine="newmm"),
                          word_tokenize(sys_text, engine="newmm")))
    lo, hi = bootstrap_ci(cor)

    def cher_f05(tp, ns, ng):
        p = tp / ns if ns else (1.0 if ng == 0 else 0.0)
        r = tp / ng if ng else (1.0 if ns == 0 else 0.0)
        return f_beta(p, r, 0.5)

    return {
        "n": n, "n_errors": n_err,
        "detection": micro_prf(det),
        "correction": micro_prf(cor),
        "correction_ci95": [lo, hi],
        "sentence_accuracy": sent / n if n else 0.0,
        "clean_sentence_fidelity": (fid_ok / fid_tot) if fid_tot else None,
        "fidelity_counts": [fid_ok, fid_tot],
        "gleu": sum(gleus) / len(gleus) if gleus else 0.0,
        "per_class_correction_recall": {
            str(c): {"recall": (pc[c][0] / pc[c][1] if pc[c][1] else 0.0),
                     "n": pc[c][1]}
            for c in sorted(pc)},
        "cherrant_span_f05": {
            str(c): {"f05": cher_f05(*cher[c]), "tp": cher[c][0],
                     "n_sys": cher[c][1], "n_gold": cher[c][2]}
            for c in sorted(cher)},
        "cherrant_span_f05_overall": cher_f05(*(sum(cher[c][i] for c in cher) for i in range(3))),
    }


def main():
    global RESULTS, REPORT
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test_public")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--results", default=None, help="results dir (e.g. results_t2 for the paragraph tier)")
    ap.add_argument("--report", default=None, help="markdown report path")
    args = ap.parse_args()
    if args.results:
        RESULTS = HERE / args.results
    if args.report:
        REPORT = Path(args.report)

    sample_path = RESULTS / f"_sample_{args.split}_{args.n}.jsonl"
    items = [json.loads(l) for l in sample_path.open(encoding="utf-8")]
    items_by_id = {it["id"]: it for it in items}

    loan_lex = load_loan_lexicon()
    runs = sorted(p for p in RESULTS.glob("*.jsonl") if not p.name.startswith("_"))
    scored = {}
    for rp in runs:
        alias = rp.stem
        m = grade_run(items_by_id, rp, loan_lex)
        scored[alias] = m
        (RESULTS / f"{alias}.json").write_text(json.dumps(m, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
        fid = m.get("clean_sentence_fidelity")
        fid_s = f" fidelity={fid:.3f}" if fid is not None else ""
        print(f"{alias}: detF1={m['detection']['F1']:.3f} corrF1={m['correction']['F1']:.3f} "
              f"[{m['correction_ci95'][0]:.2f},{m['correction_ci95'][1]:.2f}] "
              f"sent={m['sentence_accuracy']:.3f}{fid_s} GLEU={m['gleu']:.3f} "
              f"ChERRANT-F0.5={m['cherrant_span_f05_overall']:.3f} (n={m['n']}, err={m['n_errors']})")

    # markdown report
    order = sorted(scored.items(), key=lambda kv: -kv[1]["correction"]["F1"])
    lines = [f"# EditingBench — Sample Run ({args.split}, n={args.n})", "",
             "Phase 8 smoke. Primary = `grader.py` (TCC-level detection/correction F1,",
             "ERRANT-style span match). Secondary = ChERRANT span F0.5 per error-type via",
             "`therrant.py`. CI = 95% item bootstrap on correction F1.", "",
             "| model | detect F1 | correct F1 | 95% CI | sent-acc | fidelity | GLEU | ChERRANT F0.5 |",
             "|---|--:|--:|:--:|--:|--:|--:|--:|"]
    for alias, m in order:
        ci = m["correction_ci95"]
        fid = m.get("clean_sentence_fidelity")
        fid_s = f"{fid:.3f}" if fid is not None else "—"
        lines.append(f"| {alias} | {m['detection']['F1']:.3f} | **{m['correction']['F1']:.3f}** | "
                     f"[{ci[0]:.2f}, {ci[1]:.2f}] | {m['sentence_accuracy']:.3f} | {fid_s} | "
                     f"{m['gleu']:.3f} | {m['cherrant_span_f05_overall']:.3f} |")
    lines += ["", "## Per-class correction recall (primary; gold-class buckets)", "",
              "| model | " + " | ".join(f"{CLASS_NAME[c]} ({c})" for c in range(1, 7)) + " |",
              "|---|" + "--:|" * 6]
    for alias, m in order:
        pcr = m["per_class_correction_recall"]
        cells = [f"{pcr[str(c)]['recall']:.2f}" if str(c) in pcr else "—" for c in range(1, 7)]
        lines.append(f"| {alias} | " + " | ".join(cells) + " |")
    lines += ["", "## ChERRANT span F0.5 per error-type (secondary; ThERRANT-typed)", "",
              "| model | " + " | ".join(f"{CLASS_NAME[c]} ({c})" for c in range(1, 7)) + " |",
              "|---|" + "--:|" * 6]
    for alias, m in order:
        ch = m["cherrant_span_f05"]
        cells = [f"{ch[str(c)]['f05']:.2f}" if str(c) in ch else "—" for c in range(1, 7)]
        lines.append(f"| {alias} | " + " | ".join(cells) + " |")
    lines += ["", f"_n per class ≈ {args.n // 6}; class 6 (loanword) is the cross-lingual "
              "diagnostic — watch whether non-Thai-native models trail here._", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {REPORT}")


if __name__ == "__main__":
    main()
