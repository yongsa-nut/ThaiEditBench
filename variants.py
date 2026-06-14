"""Accepted-spelling-variant reconciliation for grading.

Some Thai words have more than one standard spelling (Royal Institute lists both),
so penalising a model for choosing the other form is unfair. The canonical case:
**สิทธิ ~ สิทธิ์** — `สิทธิ` is the compounding form (สิทธิมนุษยชน) and `สิทธิ์` the
standalone form (มีสิทธิ์); both are correct, context decides, and the source/gold
just picked one. (Distinct from a *defective* gold like a dropped syllable, which is
dropped from the set, not reconciled.)

`reconcile_variants(output, gold)` rewrites a model output so that a purely-variant
difference adopts the GOLD's chosen form — and nothing else. It is **token-aware**
(pythainlp newmm), so it only touches a standalone variant token and never a word that
merely contains one as a substring (e.g. `ลิขสิทธิ์` is one token, left untouched). It
fires only when gold and output disagree on a variant token, so it can never turn a
genuinely-wrong output into a right one.

Add new equivalences to VARIANT_GROUPS.
"""
from __future__ import annotations

from pythainlp.tokenize import word_tokenize

from inject import normalize                          # NFC compose

#: each group = spellings that are mutually acceptable for the SAME standalone word
VARIANT_GROUPS = [
    frozenset({"สิทธิ", "สิทธิ์"}),
    # loanword transliterations with two in-use forms (RID prefers the 2nd; both common)
    frozenset({"ดิจิตอล", "ดิจิทัล"}),
    frozenset({"ออร์แกนิค", "ออร์แกนิก"}),
    # informal↔formal spelling of the pronoun "he/she" (audit ruling: don't penalize)
    frozenset({"เค้า", "เขา"}),
]
_IN_GROUP = {w: g for g in VARIANT_GROUPS for w in g}

#: words ending in -สิทธิ์ where the การันต์ (์) is MANDATORY (not the optional standalone
#: 'right' word). Protected so we never strip their ์ during reconciliation.
_SIT_KARAN_KEEP = ("ลิขสิทธิ์", "กรรมสิทธิ์", "เอกสิทธิ์", "อภิสิทธิ์", "ประสิทธิ์", "สิทธิ์ขาด")


def _sit_strip(s: str) -> str:
    """Drop the optional ์ on the standalone right-word (สิทธิ์→สิทธิ), protecting the
    compounds where ์ is mandatory (ลิขสิทธิ์, ประสิทธิ์, …)."""
    for i, w in enumerate(_SIT_KARAN_KEEP):
        s = s.replace(w, f"\x00{i}\x00")
    s = s.replace("สิทธิ์", "สิทธิ")
    for i, w in enumerate(_SIT_KARAN_KEEP):
        s = s.replace(f"\x00{i}\x00", w)
    return s


def reconcile_variants(output: str, gold: str) -> str:
    """Rewrite `output` so a purely-variant spelling difference adopts the GOLD's form.
    Returns `output` unchanged otherwise; never alters non-variant tokens.

    Two layers: (1) a compound-safe string pass for สิทธิ์→สิทธิ that survives newmm
    gluing the right-word onto a prefix (มีสิทธิ์, ผู้มีสิทธิ์); (2) the general
    token-level group rule (handles the standalone forms in either direction)."""
    if not output:
        return output
    out = normalize(output)
    # (1) สิทธิ ~ สิทธิ์ — if gold uses the bare form (no standalone ์), strip output's
    # optional ์ on the right-word, even when glued to a prefix. Compound-safe.
    if "สิทธิ์" in out and "สิทธิ" in gold and _sit_strip(gold) == gold:
        out = _sit_strip(out)
    # (1b) loanword transliteration variants — distinctive whole strings, safe to
    # normalise by direct replace toward the gold's chosen form. newmm sometimes
    # splits these mid-word in context (ระบบดิจิทัล), defeating the token rule below.
    gn = normalize(gold)
    for a, b in (("ดิจิทัล", "ดิจิตอล"), ("ออร์แกนิก", "ออร์แกนิค")):
        if a in gn and b in out and a not in out:
            out = out.replace(b, a)
        elif b in gn and a in out and b not in out:
            out = out.replace(a, b)
    # (2) general token-level variant groups (covers the reverse direction too)
    gold_toks = set(word_tokenize(normalize(gold), engine="newmm", keep_whitespace=True))
    out_toks = word_tokenize(out, engine="newmm", keep_whitespace=True)
    changed = False
    res = []
    for t in out_toks:
        g = _IN_GROUP.get(t)
        if g and t not in gold_toks and (g & gold_toks):
            res.append(next(iter(g & gold_toks)))
            changed = True
        else:
            res.append(t)
    out = "".join(res) if changed else out
    return out if out != normalize(output) else output


if __name__ == "__main__":
    cases = [
        ("ผู้ได้รับสิทธิ์ ให้เข้าร่วม", "ผู้ได้รับสิทธิ ให้เข้าร่วม", "ผู้ได้รับสิทธิ ให้เข้าร่วม"),  # สิทธิ์→สิทธิ
        ("ผู้ได้รับสิทธิ ให้เข้าร่วม", "ผู้ได้รับสิทธิ์ ให้เข้าร่วม", "ผู้ได้รับสิทธิ์ ให้เข้าร่วม"),  # สิทธิ→สิทธิ์
        ("หญิงควรมีสิทธิ์ที่จะเลือก", "หญิงควรมีสิทธิที่จะเลือก", "หญิงควรมีสิทธิที่จะเลือก"),         # GLUED มีสิทธิ์→มีสิทธิ
        ("ผู้มีสิทธิ์ออกเสียง", "ผู้มีสิทธิออกเสียง", "ผู้มีสิทธิออกเสียง"),                          # GLUED ผู้มีสิทธิ์
        ("งานนี้มีลิขสิทธิ์", "งานนี้มีลิขสิทธิ์", "งานนี้มีลิขสิทธิ์"),                              # ลิขสิทธิ์ untouched
        ("เขาชื่อประสิทธิ์ จริง", "เขาชื่อประสิทธิ์ จริง", "เขาชื่อประสิทธิ์ จริง"),                  # ประสิทธิ์ ์ kept
        ("ผู้ได้รับสิทธิ ให้", "ผู้ได้รับสิทธิ ให้", "ผู้ได้รับสิทธิ ให้"),                            # already equal → unchanged
        ("เขาเขียนผิดจริง", "เขาเขียนถูกแล้ว", "เขาเขียนผิดจริง"),                                   # non-variant → untouched
    ]
    ok = True
    for out, gold, exp in cases:
        got = reconcile_variants(out, gold)
        flag = "OK " if got == exp else "FAIL"
        if got != exp:
            ok = False
        print(f"[{flag}] out={out!r} gold={gold!r} -> {got!r}")
    print("selftest", "PASS" if ok else "FAILED")
