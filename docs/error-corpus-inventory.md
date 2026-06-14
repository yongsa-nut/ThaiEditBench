# EditingBench — Error-Corpus Inventory (Phase 1)

**Status:** ✅ **Phase 1 complete** (2026-05-23) — 7 of 8 sources processed;
Source 6 (CTFL-GEC) dropped (access-restricted); Source 8 deferred. Check-in 1 passed.
**Primary deliverable (this file)** + machine-readable catalogs in `phase1/data/`.
**Headline:** a clean, RID-backed **v1 confusion-set seed of 1,051 pairs** across
all 6 mechanism classes (Sources 1–2), plus characterized social/learner pools
and a **verdict against a 7th keyboard-slip class**.

> **Check-in 1 decisions (locked):**
> 1. **Real-word handling** — curated minimal-pair list (`realword_pairs.py`)
>    replaces the over-inclusive lexicon heuristic (213 → 7 genuine v2 pairs).
> 2. **Class 2** — Indic-etymology homophone groups only; `ฝ/ฟ`, `ห/ฮ` stay in 5.
> 3. **Etymology** — loanword-lexicon tagging deferred to Phase 2 (class 6 = floor).
> 4. **Keyboard slips** — verdict below (no 7th class).

---

## 1. Sources — status & role

| # | Source | Access | Yield | Role in v1 |
|---|---|---|---|---|
| 1 | Thai Wiktionary misspelling appendix | MediaWiki API ✓ | 1,044 pairs / 810 headwords | **core clean seed** |
| 2 | บอตแก้คำผิด (hand-classified) | `typo-classification.html` ✓ | 90 (gold) | **core clean seed** + classifier gold |
| 3 | VISTEC-TP-TH-2021 | GitHub `mrpeerat/OSKut` ✓ | 24,403 unique `<msp>` | candidate pool (low precision; tagged, not bulk-merged) |
| 4 | Wisesight + Nakwijit 2022 | GitHub `chameleonTK/misspelling-semantics` ✓ | 1,212 labeled tokens | taxonomy + keyboard-slip evidence (no corrections) |
| 5 | Thai Wikipedia revisions | API **pilot** ✓ | pipeline validated | Phase-4 primary (sizing done here) |
| 6 | CTFL-GEC (L2 learners) | IEEE DataPort | ⛔ **dropped** | access-restricted (no license to download) |
| 7 | Thai Deaf Corpus | GitHub `Supachan/ThaiDeafCorpus` ✓ | 411 candidates (mostly grammar) | low value (grammar-dominated) |
| 8 | GitHub Typo Corpus (Thai) | release gz (~600 MB) | deferred | bonus; not worth bulk download now |

## 2. Core v1 seed — Sources 1 + 2 (the confusion-set seed for Phase 2)

**1,080 unique pairs** total → **1,058 clean_v1** → **1,051 v1** (clean & not
context-dependent). 7 routed to v2; 22 needs-filtering (11 multi-token/spacing,
8 fragment, 3 whole-word). RID-backed (`dictionary.orst.go.th` lemma cited per
pair). Catalog: `error-corpus-inventory.jsonl`.

### Mechanism × etymology (v1 = 1,051)

| class | native | loan | proper-noun | total |
|---|--:|--:|--:|--:|
| 1 tone_mark | 60 | 11 | 0 | **71** |
| 2 consonant_pair | 159 | 6 | 0 | **165** |
| 3 karan_native | 175 | 17 | 0 | **192** |
| 4 vowel | 184 | 8 | 0 | **192** |
| 5 cluster_metathesis | 339 | 8 | 0 | **347** |
| 6 loanword_translit | 0 | 64 | 13 | **77** |
| 0 UNCLASSIFIED | 4 | 3 | 0 | **7** |

Every class clears the Phase-2 seed need (≥50). Caveats: class 5 is the broadest
(catches non-Indic homophones + structural edits, per decision #2); class 6 is a
floor pending Phase-2 etymology tagging (#3). **Classifier validates at 96.5%**
vs the 90 hand-labels — above the ≥85% bar.

## 3. Social / learner pools (Sources 3, 4, 7) — characterized, not bulk-merged

These are all **social-media / learner domain** — the formal-domain gap the
paper targets. They are tagged candidate pools (`phase1/data/*_pairs.jsonl`),
**not** merged into the clean seed, because precision for *unintentional formal
orthographic errors* is low. Use selectively (high-frequency, manually reviewed)
in Phase 2 + as contamination-dedup references (plan §8).

- **VISTEC (Source 3)** — 24,403 unique `<msp>` pairs. Buckets: ortho 15,230 /
  spacing 3,522 / truncation 3,462 / **repetition 2,148** / context-dep 41.
  VISTEC tags carry no intentional/unintentional label, so a heuristic inverted
  Nakwijit filter was applied (drop spacing, truncation/simplification,
  elongation). Even so the residual is Twitter slang. Ortho-bucket class
  distribution: 1:4632 · 2:588 · 3:1701 · 4:1653 · 5:6478 · 0:178.
- **Nakwijit (Source 4)** — 1,212 hand-labeled tokens; **326 unintentional vs
  661 intentional** (~2:1 intentional dominance). No correct forms in the file →
  informs taxonomy + the verdict, not the confusion set. Unintentional classes:
  สับสนวรรณยุกต์ (tone, 211) → cls 1, พิมพ์ผิด-ไม่ตั้งใจ (typo, 106) → cls 1–5,
  สับสนพยัญชนะ (consonant, 15) → cls 2.
- **Deaf Corpus (Source 7)** — 22,718 sentence rows; only 411 candidate
  char-level pairs after filtering grammar/word-order, and most of those are
  residual word-choice noise. Genuine orthographic typos (`ซื่อ→ซื้อ`,
  `พลิก→พริก`) are a small minority. **Grammar-dominated, as the plan predicted —
  low v1 value.**

## 4. ⭐ Keyboard-slip / 7th-class VERDICT — **no 7th *mechanism* class; tag as edit-operation**

The plan (§3c.5) flagged adding a class 7 *if* keyboard slips cluster as a
distinct mechanism. Cross-source evidence + a web/literature check refine this:

**Our-data evidence:**
1. **Formal sources (1–2):** zero keyboard slips — only systematic errors.
2. **VISTEC (3):** the apparent "slip" cluster is **intentional character
   elongation** (`มากกก→มาก`, `แล้วว→แล้ว`: 2,148 pairs) — Nakwijit *semantic*
   variation, dropped. The residual is **intentional slang** (`กรู→กู`, `ตู→กู`,
   `ฟะ→วะ`), not random adjacent-key errors.
3. **Nakwijit (4):** the most thorough empirical Thai misspelling taxonomy has
   **no keyboard-slip class**; unintentional = typo + tone/consonant confusion,
   all mapping to our classes 1, 2, 4, 5.

**Literature check (web search):** Thai spell-correction work *does* recognise
keyboard-decoding typos — Lertpiya et al.'s UGWC dataset explicitly includes
"errors from incorrect keyboard decoding (striking improper keys)", and
synthetic-augmentation papers inject random char insertion/deletion/
substitution. **But they characterise these as edit *operations*
(insertion / deletion / substitution / transposition), not as a linguistic
mechanism.** This matches ERRANT/ChERRANT's operation-level error types
(Missing / Unnecessary / Replacement).

➡️ **Verdict — keep the 6 *mechanism* classes; do NOT add a 7th.** The
keyboard-slip phenomenon is an **edit-operation dimension orthogonal to
mechanism**, and it is *already* captured by the planned **ThERRANT**
operation-level tags (Phase 6) — no taxonomy change needed. Random
non-linguistic slips are primarily a **Phase-4 synthetic-injection** concern
(inject char perturbations, label by operation, not mechanism). Recommend
adding an orthogonal `edit_op` field (sub/ins/del/transpose) alongside
`mechanism_class` + `etymology` rather than a class 7.

*(The CTFL-GEC learner cross-check is dropped — dataset is access-restricted,
§6 — but the verdict is well-supported without it.)*

## 5. Wikipedia pilot (Source 5) — sizing the Phase-4 mine

Pipeline validated end-to-end (recentchanges → `action=compare` → diff pairs).
**Key finding:** the edit-summary keyword filter on recent changes has a
**0.10% hit rate** (12 typo-fix edits / 12,000 scanned) and modest precision
(positional diff-pairing also catches content edits). Clean examples surfaced
(`จิตกรรม→จิตรกรรม`, `พนัง→ผนัง`, `ถาะยนตร์→ภาพยนตร์`).

➡️ **Phase-4 implication:** the projected 30–70K pairs **cannot** come from
summary keywords (high precision, low recall). The full mine must process the
**revision-history dump** with **diff-shape mining** (small TCC-edit-distance
single-token changes) + **RID/LM filtering** + sentence-level alignment — the
JWTD recipe — not recentchanges scanning. The 80+ บอตแก้คำผิด patterns + the
1,051-pair seed act as high-confidence bootstrap labels (plan §6a.7).

## 6. v2 routing & pending items

- **v2 (deferred):** 7 curated context-dependent pairs (`กริยา/กิริยา`,
  `นะค่ะ/นะคะ`, `ใต้/ไต้`, `เกมส์/เกม`…), 11 spacing/multi-token, 3 whole-word.
  All retained in the JSONL with `context_dependent` / `clean_v1=false`.
- **Source 6 — CTFL-GEC:** **dropped** — IEEE DataPort access-restricted (no
  license to download). The keyboard-slip verdict (§4) is well-supported without
  it; learner-domain coverage is a v2/nice-to-have, not a v1 blocker.
- **Source 8 — GitHub Typo Corpus:** deferred (~600 MB release gz for <1K Thai
  edits); revisit in Phase 2 if technical-domain coverage is wanted.

## 7. Artifacts & reproduction

```
phase1/classify.py            heuristic TCC-diff classifier (Indic class-2; +Nakwijit filter)
phase1/realword_pairs.py      curated context-dependent minimal-pair list
phase1/extract_botfix_html.py typo-classification.html -> data/botfix_gold.jsonl
phase1/validate_classifier.py 96.5% vs gold
phase1/scrape_wiktionary.py   Source 1 -> data/wiktionary_pairs.jsonl
phase1/build_inventory.py     Sources 1+2 -> error-corpus-inventory.jsonl
phase1/make_sample.py         -> data/sample.md
phase1/vistec_extract.py      Source 3 -> data/vistec_pairs.jsonl
phase1/wiki_pilot.py          Source 5 pilot -> data/wiki_pilot_pairs.jsonl
phase1/deaf_extract.py        Source 7 -> data/deaf_pairs.jsonl
# Source 4: data/nakwijit_annotated.jsonl + nakwijit_unintentional.json
```
Run: `PYTHONUTF8=1 python phase1/<script>.py` (Windows console = UTF-8).

## 8. → Phase 2 readiness

Phase 1 delivers what Phase 2 needs: a **1,051-pair RID-backed seed** spanning
all 6 classes (→ `confusion-set.jsonl`), a validated classifier (→ ThERRANT
seed), a **locked 6-class taxonomy** (keyboard-slip question resolved — add an
orthogonal `edit_op` tag, not a class 7), tagged social pools for selective
augmentation + contamination dedup, and a de-risked Phase-4 Wikipedia-mining
design. **No blockers** — Phase 2 can start now from the 1,051-pair seed.
Interactive viewer of all pairs: `error-corpus-inventory.html`.
