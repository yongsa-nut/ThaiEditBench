"""
Phase 4b core — synthetic orthographic-error injection for EditingBench.

Given a clean Thai sentence and confusion-set pairs (correct -> wrong), replace a
WHOLE-TOKEN occurrence of a correct form with its wrong form and emit a gold edit
carrying a TCC-level span + the pair's mechanism class / etymology / edit_op.

Word-boundary (newmm) matching is MANDATORY: 51 confusion-set correct forms are
<=3 chars (ก็, นะ, คะ) and a raw substring replace would corrupt unrelated text
(e.g. turning every embedded "นะ" into a typo). We only inject where the correct
form is a standalone newmm token; carrier sentences where it is fused into a
compound are skipped (conservative — we have ~392k thaisum articles to draw from).

Determinism: all sampling goes through an explicit random.Random(seed); the same
seed reproduces the same dataset.

Gold invariant (unit-tested in test_inject.py): applying every emitted edit to
text_wrong reproduces text_correct, and each edit's [tcc_start, tcc_end) indexes
the TCC segmentation of text_wrong.
"""
import json
import sys
from pathlib import Path

from pythainlp.tokenize import tcc, word_tokenize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                        # classify.py lives at the repo root
from classify import normalize                       # NFC compose, strip  # noqa: E402

CONFUSION_SET = HERE / "data" / "confusion-set.jsonl"

CLASS_NAME = {1: "tone_mark", 2: "consonant_pair", 3: "karan_native",
              4: "vowel", 5: "cluster_metathesis", 6: "loanword_translit"}


# --- confusion-set loading --------------------------------------------------

def load_confusion_set(path=CONFUSION_SET):
    """All confusion-set records (NFC-normalized wrong/correct)."""
    recs = []
    for line in Path(path).open(encoding="utf-8"):
        r = json.loads(line)
        r["wrong"] = normalize(r["wrong"])
        r["correct"] = normalize(r["correct"])
        recs.append(r)
    return recs


def group_by_correct(recs):
    """correct-form (str) -> [records]. Injection sites are matched on this key."""
    d = {}
    for r in recs:
        d.setdefault(r["correct"], []).append(r)
    return d


# --- TCC / token geometry ---------------------------------------------------

def tcc_segments(s):
    """List of Thai-Character-Cluster strings for s (pythainlp tcc)."""
    return tcc.segment(s)


def tcc_span_for_char_range(segments, c_start, c_end):
    """(tcc_start, tcc_end) of the TCC cluster range covering chars [c_start, c_end).

    Returns (None, None) if the char range does not align to TCC boundaries.
    Word boundaries are always TCC boundaries, so for whole-token injections this
    aligns; the guard catches any pathological case so we skip rather than mislabel.
    """
    pos = tcc_start = tcc_end = None
    cur = 0
    for i, seg in enumerate(segments):
        if cur == c_start:
            tcc_start = i
        cur += len(seg)
        if cur == c_end:
            tcc_end = i + 1
    return tcc_start, tcc_end


def token_spans(sentence):
    """[(token, char_start, char_end)] from newmm. Assumes tokens partition the
    string exactly (true for pythainlp word_tokenize)."""
    toks = word_tokenize(sentence, engine="newmm")
    if "".join(toks) != sentence:        # safety: bail to a single span set we won't match
        return []
    spans, pos = [], 0
    for t in toks:
        spans.append((t, pos, pos + len(t)))
        pos += len(t)
    return spans


def find_sites(sentence, by_correct, spans=None):
    """Char spans where a confusion-set correct form occupies a whole token-RUN.

    Matching a contiguous run of newmm tokens (not a single token, not a raw
    substring) is boundary-safe AND handles multi-token correct forms like
    'จุฬาลงกรณ์มหาวิทยาลัย' (newmm splits it). Returns [(char_start, char_end,
    correct_form)] — the shortest exact run per start position. Pass precomputed
    `spans` (from token_spans) to avoid re-tokenizing.
    """
    if spans is None:
        spans = token_spans(sentence)
    if not spans:
        return []
    max_len = max((len(k) for k in by_correct), default=0)
    sites = []
    for i in range(len(spans)):
        acc = ""
        for j in range(i, len(spans)):
            acc += spans[j][0]
            if len(acc) > max_len:
                break
            if acc in by_correct:
                sites.append((spans[i][1], spans[j][2], acc))
                break                    # shortest run at this start; move on
    return sites


# --- injection --------------------------------------------------------------

def inject(sentence, candidate_pairs, n, rng):
    """Inject up to n non-overlapping errors into `sentence`.

    candidate_pairs : confusion-set records eligible for this stratum (already
                      filtered by class/etymology by the caller).
    n               : number of errors (1 = single density, >=2 = multi).
    rng             : random.Random for deterministic site/pair choice.

    Returns {text_wrong, text_correct, edits:[...]} or None if no site found.
    Each edit: {tcc_start, tcc_end, char_start, char_end, wrong, correct,
                class, class_name, etymology, edit_op}.
    """
    sentence = normalize(sentence)
    bym = group_by_correct(candidate_pairs)
    sites = find_sites(sentence, bym)
    if not sites:
        return None
    rng.shuffle(sites)

    chosen, used = [], []
    for (s, e, t) in sites:
        if any(not (e <= us or s >= ue) for (us, ue) in used):
            continue                                  # overlap guard
        pair = rng.choice(bym[t])
        chosen.append((s, e, t, pair))
        used.append((s, e))
        if len(chosen) >= n:
            break
    if not chosen:
        return None

    # Rebuild left-to-right, tracking final char offsets in text_wrong.
    chosen.sort(key=lambda x: x[0])
    out, edits, prev = [], [], 0
    for (s, e, _t, pair) in chosen:
        out.append(sentence[prev:s])
        new_start = sum(len(x) for x in out)
        wrong = pair["wrong"]
        out.append(wrong)
        edits.append((new_start, new_start + len(wrong), pair))
        prev = e
    out.append(sentence[prev:])
    text_wrong = "".join(out)

    segs = tcc_segments(text_wrong)
    gold = []
    for (cs, ce, pair) in edits:
        ts, te = tcc_span_for_char_range(segs, cs, ce)
        if ts is None or te is None:
            return None                               # boundary misalign -> skip item
        cid = pair["class_id"]
        gold.append({"tcc_start": ts, "tcc_end": te,
                     "char_start": cs, "char_end": ce,
                     "wrong": pair["wrong"], "correct": pair["correct"],
                     "class": cid, "class_name": CLASS_NAME[cid],
                     "etymology": pair["etymology"], "edit_op": pair["edit_op"]})

    return {"text_wrong": text_wrong, "text_correct": sentence, "edits": gold}


def apply_edits(text_wrong, edits):
    """Reconstruct the corrected sentence from text_wrong + gold edits (right-to-left
    so char offsets stay valid). Used by the round-trip test and the Phase-7 grader."""
    out = text_wrong
    for ed in sorted(edits, key=lambda x: x["char_start"], reverse=True):
        out = out[:ed["char_start"]] + ed["correct"] + out[ed["char_end"]:]
    return out


if __name__ == "__main__":
    import random
    recs = load_confusion_set()
    print(f"loaded {len(recs)} confusion-set pairs")
    rng = random.Random(7)
    demo = "นักวิทยาศาสตร์สังเกตปรากฏการณ์ทางธรรมชาติอย่างละเอียด"
    # restrict to pairs whose correct form appears as a token here
    item = inject(demo, recs, n=1, rng=rng)
    print("demo:", item)
    if item:
        assert apply_edits(item["text_wrong"], item["edits"]) == item["text_correct"]
        segs = tcc_segments(item["text_wrong"])
        for ed in item["edits"]:
            got = "".join(segs[ed["tcc_start"]:ed["tcc_end"]])
            print(f"  tcc[{ed['tcc_start']}:{ed['tcc_end']}] = {got!r} (wrong={ed['wrong']!r})")
        print("round-trip OK")
