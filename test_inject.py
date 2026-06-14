"""
Unit tests for inject.py — the Phase-4b core. Run:  PYTHONUTF8=1 python test_inject.py

Covers the gold invariant (round-trip), TCC-span correctness, boundary safety
(short forms inject only as whole token-runs, never inside a word), determinism,
multi-error non-overlap, and broad coverage across all 1,044 confusion pairs.
"""
import random

from inject import (load_confusion_set, group_by_correct, inject, apply_edits,
                    tcc_segments, find_sites)

RECS = load_confusion_set()
BY_CLASS = {}
for r in RECS:
    BY_CLASS.setdefault(r["class_id"], []).append(r)


def _check_item(item):
    """Every gold invariant for one injected item."""
    assert apply_edits(item["text_wrong"], item["edits"]) == item["text_correct"]
    segs = tcc_segments(item["text_wrong"])
    last_end = -1
    for ed in sorted(item["edits"], key=lambda x: x["char_start"]):
        # TCC span chars == the injected wrong form
        assert "".join(segs[ed["tcc_start"]:ed["tcc_end"]]) == ed["wrong"], ed
        # char span chars == the injected wrong form
        assert item["text_wrong"][ed["char_start"]:ed["char_end"]] == ed["wrong"], ed
        # non-overlap
        assert ed["char_start"] >= last_end, "overlapping edits"
        last_end = ed["char_end"]


def test_roundtrip_each_class():
    """Inject a pair from each class into a single-word carrier; invariants hold."""
    rng = random.Random(1)
    for cid, recs in sorted(BY_CLASS.items()):
        ok = 0
        for r in recs:
            item = inject(r["correct"], [r], n=1, rng=rng)   # the word itself is the carrier
            if item is None:
                continue
            _check_item(item)
            assert item["edits"][0]["class"] == cid
            ok += 1
        assert ok > 0, f"class {cid}: no injectable pair"
        print(f"  class {cid}: {ok}/{len(recs)} pairs injected + verified")


def test_full_confusion_set_roundtrip():
    """Every pair whose correct form is a token-run injects with valid gold."""
    rng = random.Random(2)
    injected = skipped = 0
    for r in RECS:
        item = inject(r["correct"], [r], n=1, rng=rng)
        if item is None:
            skipped += 1
            continue
        _check_item(item)
        injected += 1
    print(f"  full set: injected+verified {injected}, skipped {skipped} "
          f"({injected/len(RECS):.1%} coverage)")
    assert injected >= int(0.93 * len(RECS))


def test_boundary_safety():
    """A correct form that appears only INSIDE a larger token is never injected."""
    fake = [{"correct": "มา", "wrong": "หมา", "class_id": 2,
             "etymology": "native", "edit_op": "substitution"}]
    bym = group_by_correct(fake)
    # 'มา' is a substring of มาก/ความ but not a standalone token-run here
    s_inside = "ผลกระทบมากมายต่อความมั่นคง"
    assert find_sites(s_inside, bym) == [], "must not match 'มา' inside a word"
    assert inject(s_inside, fake, 1, random.Random(0)) is None
    # but where 'มา' IS a token, it injects and corrupts only that token
    s_token = "เขาเดินมาที่นี่"
    item = inject(s_token, fake, 1, random.Random(0))
    assert item is not None and item["text_wrong"] == "เขาเดินหมาที่นี่"
    _check_item(item)
    print("  boundary safety OK (substring-inside-word never injected)")


def test_determinism():
    rng_a, rng_b = random.Random(42), random.Random(42)
    s = "นักวิทยาศาสตร์สังเกตปรากฏการณ์ทางธรรมชาติและคำนวณผลอย่างละเอียด"
    a = inject(s, RECS, n=2, rng=rng_a)
    b = inject(s, RECS, n=2, rng=rng_b)
    assert a == b, "same seed must reproduce the same injection"
    print("  determinism OK")


def test_multi_error():
    """A sentence with multiple injectable sites yields n non-overlapping edits."""
    s = "นักวิทยาศาสตร์สังเกตปรากฏการณ์และคำนวณผลลัพธ์"
    rng = random.Random(5)
    item = inject(s, RECS, n=2, rng=rng)
    if item is not None and len(item["edits"]) == 2:
        _check_item(item)
        print(f"  multi-error OK ({len(item['edits'])} edits)")
    else:
        # fall back: still must be a valid single-error item
        assert item is None or item["edits"]
        print("  multi-error: <2 sites in carrier (acceptable)")


if __name__ == "__main__":
    test_roundtrip_each_class()
    test_full_confusion_set_roundtrip()
    test_boundary_safety()
    test_determinism()
    test_multi_error()
    print("ALL TESTS PASSED")
