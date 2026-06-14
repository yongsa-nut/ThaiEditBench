"""
Phase 7 — unit tests for grader.py (plan.md §7 verification).

Covers: gold-corrected -> 1.0; no-op -> 0 recall; detection-right but
correction-wrong; false positives lower precision; TCC substitution vs raw-char;
per-class recall mapping; bootstrap CI sanity.

Run:  PYTHONUTF8=1 python test_grader.py
"""
import json
from pathlib import Path

from grader import (align_edits, score_detection, score_correction,
                    score_sentence_accuracy, per_class_recall, gleu,
                    micro_prf, prf_from_counts, bootstrap_ci)

HERE = Path(__file__).resolve().parent

WRONG = "นักวิทยาศาสตร์สังเกตุปรากฏการณ์"     # error: สังเกตุ (extra ุ)
RIGHT = "นักวิทยาศาสตร์สังเกตปรากฏการณ์"      # gold


def almost(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_perfect():
    gold = align_edits(WRONG, RIGHT)
    sysd = align_edits(WRONG, RIGHT)                 # model returns gold
    assert len(gold) == 1, gold
    assert micro_prf([score_detection(gold, sysd)])["F1"] == 1.0
    assert micro_prf([score_correction(gold, sysd)])["F1"] == 1.0
    assert score_sentence_accuracy([RIGHT], RIGHT) is True
    print("  ok: perfect correction -> det/corr F1 = 1.0, sent-acc True")


def test_noop():
    gold = align_edits(WRONG, RIGHT)
    sysd = align_edits(WRONG, WRONG)                 # model changed nothing
    assert len(sysd) == 0
    c = score_correction(gold, sysd)
    assert c.tp == 0 and c.n_gold == 1
    assert prf_from_counts(*c)["R"] == 0.0
    assert score_sentence_accuracy([RIGHT], WRONG) is False
    print("  ok: no-op -> correction recall 0, sent-acc False")


def test_detection_right_correction_wrong():
    # model flags the right cluster but substitutes a wrong replacement (ตุ -> ตา)
    sys_text = "นักวิทยาศาสตร์สังเกตาปรากฏการณ์"
    gold = align_edits(WRONG, RIGHT)
    sysd = align_edits(WRONG, sys_text)
    det = score_detection(gold, sysd)
    cor = score_correction(gold, sysd)
    assert det.tp == 1, det          # same source span flagged
    assert cor.tp == 0, cor          # wrong replacement
    print("  ok: right position, wrong fix -> det tp=1, corr tp=0")


def test_false_positive():
    # model fixes the real error BUT also corrupts a correct cluster (ณ -> น)
    sys_text = "นักวิทยาศาสตร์สังเกตปรากฏการน์"
    gold = align_edits(WRONG, RIGHT)
    sysd = align_edits(WRONG, sys_text)
    cor = score_correction(gold, sysd)
    assert cor.n_gold == 1
    assert cor.n_sys == 2, sysd      # 1 real fix + 1 spurious change
    assert cor.tp == 1
    p = prf_from_counts(*cor)
    assert almost(p["P"], 0.5) and almost(p["R"], 1.0)
    print("  ok: false positive -> correction P=0.5, R=1.0")


def test_insertion():
    # missing-character error: 'น้ำ' written 'นำ' (gold inserts the cluster)
    w, r = "ปริมาณนำมาก", "ปริมาณน้ำมาก"
    gold = align_edits(w, r)
    assert len(gold) == 1, gold
    sysd = align_edits(w, r)
    assert micro_prf([score_correction(gold, sysd)])["F1"] == 1.0
    print(f"  ok: insertion handled (gold edit repl={gold[0].repl!r}) -> F1 1.0")


def test_per_class():
    items = [json.loads(l) for l in (HERE / "data" / "items_dev.jsonl").open(encoding="utf-8")]
    it = next(x for x in items if x["density"] == "single")
    sysd = align_edits(it["text_wrong"], it["text_correct"])     # perfect
    pc = per_class_recall(it, sysd)
    cls = it["edits"][0]["class"]
    assert pc.get(cls, (0, 0)) == (1, 1), (cls, pc)
    # no-op -> 0 corrected
    pc0 = per_class_recall(it, align_edits(it["text_wrong"], it["text_wrong"]))
    assert pc0.get(cls, (0, 0))[0] == 0
    print(f"  ok: per-class recall maps gold edit to class {cls} (1/1 perfect, 0 no-op)")


def test_bootstrap_and_gleu():
    from pythainlp.tokenize import word_tokenize
    items = [json.loads(l) for l in (HERE / "data" / "items_dev.jsonl").open(encoding="utf-8")][:100]
    counts = [score_correction(align_edits(it["text_wrong"], it["text_correct"]),
                               align_edits(it["text_wrong"], it["text_correct"])) for it in items]
    lo, hi = bootstrap_ci(counts)
    assert lo <= micro_prf(counts)["F1"] <= hi + 1e-9
    # GLEU: perfect > corrupted
    it = items[0]
    s = word_tokenize(it["text_wrong"], engine="newmm")
    r = word_tokenize(it["text_correct"], engine="newmm")
    assert gleu(s, r, r) > gleu(s, r, s)
    print(f"  ok: bootstrap CI [{lo:.3f},{hi:.3f}] brackets F1; GLEU perfect>no-op")


if __name__ == "__main__":
    for fn in [test_perfect, test_noop, test_detection_right_correction_wrong,
               test_false_positive, test_insertion, test_per_class,
               test_bootstrap_and_gleu]:
        fn()
    print("ALL GRADER TESTS PASSED")
