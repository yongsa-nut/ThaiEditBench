"""
Phase 6 — ThERRANT: Thai adaptation of ERRANT/ChERRANT (subtask2/plan.md §9).

Automatically annotates a (wrong, correct) sentence pair with TYPED edit spans:
  - span extraction at TCC level (shared with the grader: grader.align_edits),
  - each edit expanded to its enclosing newmm word, then classified into the
    6 mechanism classes via phase1.classify (so the auto-type matches how the
    dataset was constructed),
  - edit_op tag via phase2.edit_op.

The loanword class (6) is etymology-gated, so annotate() takes a loan lexicon
(correct-forms known to be loanwords; built from the class-6 confusion set). A
corrected word in that lexicon -> etymology 'loan' -> class 6 (absorption rule).

This unlocks the SECONDARY metric (ChERRANT-style per-error-type span F0.5),
computed in grader.score_cherrant, and is itself the first Thai ERRANT.

Public API:
  annotate(text_wrong, text_target, loan_lex=None) -> [TypedEdit, ...]
  load_loan_lexicon() -> set[str]

Run:  PYTHONUTF8=1 python therrant.py    (demo)
"""
from __future__ import annotations

import json
import sys
from collections import namedtuple
from pathlib import Path

from pythainlp.tokenize import word_tokenize

from grader import align_edits
from inject import normalize, tcc_segments, CLASS_NAME

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                            # classify.py / edit_op.py live at the repo root
from classify import classify                            # noqa: E402
from edit_op import edit_op                              # noqa: E402

TypedEdit = namedtuple("TypedEdit",
                       "tcc_start tcc_end char_start char_end wrong correct klass class_name edit_op")


def load_loan_lexicon() -> set[str]:
    """Correct-forms tagged class 6 (loanword) in the confusion set -> the
    etymology oracle ThERRANT uses to apply the loanword-absorption rule.
    Full-form only: annotate() anchors the corrected word on the target side
    (which tokenizes loanwords as whole words), so sub-token entries are
    unnecessary and only cause false absorptions."""
    lex = set()
    path = HERE / "data" / "confusion-set.jsonl"
    if path.exists():
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("class") == 6 or r.get("etymology") in ("loan", "proper-noun"):
                lex.add(normalize(r["correct"]))
    return lex


def _tcc_char_offsets(segs: list[str]) -> list[int]:
    """Cumulative char offset preceding each TCC index (len = len(segs)+1)."""
    offs, acc = [0], 0
    for s in segs:
        acc += len(s)
        offs.append(acc)
    return offs


def _word_spans(text: str) -> list[tuple[int, int, str]]:
    """newmm tokens with (char_start, char_end, token); tokens concatenate to text."""
    spans, pos = [], 0
    for tok in word_tokenize(text, engine="newmm"):
        spans.append((pos, pos + len(tok), tok))
        pos += len(tok)
    return spans


def _enclosing_word(word_spans, c_start, c_end):
    """Smallest contiguous run of tokens covering [c_start, c_end) (or the token
    containing the point c_start for a zero-width insertion). Returns (w_start,
    w_end)."""
    if c_start == c_end:                                 # zero-width insertion
        covering = [(s, e) for (s, e, _t) in word_spans if s <= c_start < e]
    else:
        covering = [(s, e) for (s, e, _t) in word_spans if s < c_end and e > c_start]
    if not covering:                                     # boundary / end of string
        prev = [(s, e) for (s, e, _t) in word_spans if e <= c_start]
        return prev[-1] if prev else (c_start, c_end)
    return min(s for s, _ in covering), max(e for _, e in covering)


def annotate(text_wrong: str, text_target: str, loan_lex: set[str] | None = None) -> list[TypedEdit]:
    w, tgt = normalize(text_wrong), normalize(text_target)
    segs = tcc_segments(w)
    offs = _tcc_char_offsets(segs)
    tspans = _word_spans(tgt)                              # anchor on the CORRECT side:
    edits = align_edits(w, tgt)                            # it tokenizes loanwords properly
    out, delta = [], 0
    for e in edits:
        c_start, c_end = offs[e.start], offs[e.end]        # source char span (reported)
        wrong_frag = "".join(segs[e.start:e.end])
        t_start = c_start + delta                          # corresponding target char start
        delta += len(e.repl) - (c_end - c_start)
        tws, twe = _enclosing_word(tspans, t_start, t_start + len(e.repl))
        correct_word = tgt[tws:twe]
        off = t_start - tws                                # re-inject the error into the
        wrong_word = correct_word[:off] + wrong_frag + correct_word[off + len(e.repl):]
        ety = "loan" if (loan_lex and normalize(correct_word) in loan_lex) else "native"
        klass = classify(wrong_word, correct_word, etymology=ety)["primary_class"]
        out.append(TypedEdit(
            e.start, e.end, c_start, c_end, wrong_frag, e.repl,
            klass, CLASS_NAME.get(klass, "unclassified"),
            edit_op(wrong_word, correct_word)))
    return out


def f_beta(p: float, r: float, beta: float = 0.5) -> float:
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r) if (b2 * p + r) else 0.0


def cherrant_counts(text_wrong: str, text_correct: str, sys_text: str,
                    loan_lex: set[str] | None = None) -> dict[int, tuple[int, int, int]]:
    """ChERRANT secondary metric, per error-type. Type BOTH gold and system edits
    with ThERRANT, then match on (span + correction) within each class. Returns
    {class: (tp, n_sys, n_gold)} — aggregate across items, then F0.5 per class."""
    from collections import Counter, defaultdict
    gold = annotate(text_wrong, text_correct, loan_lex)
    sysd = annotate(text_wrong, sys_text, loan_lex)
    out = defaultdict(lambda: [0, 0, 0])               # class -> [tp, n_sys, n_gold]
    gold_keys = defaultdict(Counter)
    for e in gold:
        out[e.klass][2] += 1
        gold_keys[e.klass][(e.tcc_start, e.tcc_end, e.correct)] += 1
    for e in sysd:
        out[e.klass][1] += 1
        k = (e.tcc_start, e.tcc_end, e.correct)
        if gold_keys[e.klass][k] > 0:
            gold_keys[e.klass][k] -= 1
            out[e.klass][0] += 1
    return {c: tuple(v) for c, v in out.items()}


if __name__ == "__main__":
    loan = load_loan_lexicon()
    print(f"loan lexicon: {len(loan)} forms")
    demos = [
        ("นักวิทยาศาสตร์สังเกตุปรากฏการณ์", "นักวิทยาศาสตร์สังเกตปรากฏการณ์"),
        ("เขาใช้คอมพิวเตอร์รุ่นใหม่", "เขาใช้คอมพิวเตอร์รุ่นใหม่"),
        ("เว็บไซต์นี้โหลดช้า", "เว็บไซต์นี้โหลดช้า"),
        ("ฝรั่งเศษเป็นประเทศ", "ฝรั่งเศสเป็นประเทศ"),
    ]
    for tw, tc in demos:
        ann = annotate(tw, tc, loan)
        print(f"\n{tw}  ->  {tc}")
        for a in ann:
            print(f"  [{a.tcc_start}:{a.tcc_end}] {a.wrong!r}->{a.correct!r} "
                  f"class {a.klass} ({a.class_name}) {a.edit_op}")
