# Thai Orthographic Confusion Set (EditingBench v1)

A citable set of **1,044 canonical wrong→correct Thai spelling pairs** across the
6 EditingBench mechanism classes, with etymology, edit-operation, and RID
provenance. Built in Phase 2 from the Phase-1 RID-backed seed (Sources 1–2: Thai
Wiktionary misspelling appendix + บอตแก้คำผิด). Seeds Phase-4 synthetic injection
(§6c) and the Phase-6 ThERRANT error-type rules. Resolves Q2.5.

**File:** `confusion-set.jsonl` (one JSON record per line).
**License:** CC BY-SA (inherited from Thai Wiktionary / บอตแก้คำผิด).

## Record schema

```json
{ "class": "tone_mark", "class_id": 1, "wrong": "กระทั้ง", "correct": "กระทั่ง",
  "correct_alts": [], "etymology": "native", "origin": "",
  "edit_op": "substitution", "also_hits": [],
  "mechanism_detail": "tone-mark change", "sources": ["botfix","wiktionary"],
  "rid_entry": "https://dictionary.orst.go.th/ (lemma: กระทั่ง)",
  "rid_verified": true, "license": "CC BY-SA" }
```

- **`class` / `class_id`** — one of the 6 locked mechanism classes (§4 of `plan.md`).
- **`etymology`** — `native` / `loan` / `proper-noun` (§5). `loan` ⇒ `class_id` 6
  (loanword-absorption, §3d).
- **`origin`** — source language for loans (e.g. `อังกฤษ`).
- **`edit_op`** — `substitution` / `insertion` / `deletion` / `transposition` /
  `mixed`. The keyboard-slip dimension (Phase-1 verdict), **orthogonal** to
  mechanism — no 7th class.
- **`also_hits`** — secondary mechanism classes (for absorbed loans / multi-mechanism).
- **`rid_verified`** — `correct` form found in pythainlp `thai_orst_words`.

## Coverage — class × etymology

| class | native | loan | proper-noun | total |
|---|--:|--:|--:|--:|
| 1 tone_mark | 43 | 0 | 0 | **43** |
| 2 consonant_pair | 167 | 0 | 1 | **168** |
| 3 karan_native | 176 | 0 | 1 | **177** |
| 4 vowel | 187 | 0 | 2 | **189** |
| 5 cluster_metathesis | 334 | 0 | 4 | **338** |
| 6 loanword_translit | 0 | 129 | 0 | **129** |
| **total** | 707 | 129 | 8 | **1,044** |

## Coverage — class × edit_op

| class | subst | insert | delete | transp | mixed |
|---|--:|--:|--:|--:|--:|
| tone_mark | 12 | 17 | 9 | 0 | 5 |
| consonant_pair | 155 | 0 | 0 | 1 | 12 |
| karan_native | 31 | 77 | 61 | 1 | 7 |
| vowel | 41 | 74 | 61 | 0 | 13 |
| cluster_metathesis | 168 | 64 | 53 | 27 | 26 |
| loanword_translit | 67 | 25 | 12 | 9 | 16 |

`edit_op` correlates sensibly with mechanism (consonant-pair ≈ pure substitution;
การันต์ ≈ insert/delete of ์-clusters; cluster carries the 27 transpositions /
metathesis), confirming it is a meaningful orthogonal dimension.

## Provenance

- **Thai Wiktionary** misspelling appendix `ภาคผนวก:รายชื่อคำในภาษาไทยที่มักเขียนผิด` — 1,004 pairs.
- **บอตแก้คำผิด** (hand-classified, user-approved) — 84 pairs (overlap deduped).
- Both RID-backed (forms follow พจนานุกรม / Royal-Institute announcements).

## Etymology methodology

Etymology was finalized (deferred from Phase 1) using **Thai Wiktionary
borrowed-terms categories** (`ศัพท์ภาษาไทยที่ยืมมาจากภาษา…`) via the
`categorymembers`/`prop=categories` API. Decisions baked in:

- **`loan` = contemporary foreign only** (English-dominant: 92; + French, modern
  Chinese variants, Dutch, Japanese, Vietnamese). 80 pairs were absorbed into
  class 6 here, lifting it from the Phase-1 floor of 77 → **129**.
- **Native-integrated origins stay native:** Indic-classical (Pali/Sanskrit),
  Mon-Khmer, and Tai substrate — **and old fully-naturalized loans**
  (Tamil/Persian/Burmese/Malay/Portuguese/Hindi/Arabic: `กะปิ`, `กะหรี่`,
  `กะละแม`, `สบู่`, `อะไหล่`) whose errors are native-feel, not transliteration.
- **Native Sanskrit proper nouns** (`นภดล`, `องคุลิมาล`) are **not** absorbed
  into class 6 — they keep their mechanism class.
- The Phase-1 note-based loan heuristic was **dropped** (it read English text in
  mechanism descriptions and mislabeled native words). Wiktionary categories +
  the บอตแก้คำผิด hand labels are the only loan signals.

## RID verification

**913 / 1,044 (87.5%)** of `correct` forms resolve in pythainlp's offline
`thai_orst_words`. The 131 misses are **dominated by modern loanwords**
(`ลิงก์`, `ซอฟต์แวร์`, `นิวยอร์ก`, `แอปพลิเคชัน`) that are absent from that
offline snapshot but **present on `dictionary.orst.go.th` online** — the Q2.1
distinction (online RID reflects current accepted forms incl. modern loanwords).
This is a dictionary-coverage gap, not a data-quality issue; `rid_verified`
records it per pair.

## Caveats

- **class 1 (tone) = 43**, below the soft ≥50/class seed target: loanword tone
  errors (`เวอร์ชั่น`) moved to class 6 and context-dependent ones (`นะค่ะ`) to
  v2, so native-only tone seeds are fewer. Phase-4 synthetic injection scales
  each seed pair into many test items, so this is sufficient as a seed.
- **7 class-0 edge cases excluded** (abbreviation/symbol/mixed: `ณ.`, `พณฯ`,
  `ไมโครซอฟต์/ท`) — no clean mechanism for injection; retained in
  `error-corpus-inventory.jsonl`.
- The 7 context-dependent + 22 needs-filtering pairs (v2 seed) are likewise in
  the inventory, not here.

## Downstream use

- **Phase 4 (synthetic injection):** group by `correct` → `inject_<class>()`
  replaces a clean correct form with a `wrong` variant of the same class.
- **Phase 6 (ThERRANT):** `class` + `edit_op` + `mechanism_detail` seed the
  error-type classification rules.

## Reproduce

```
phase2/build_loan_lexicon.py    -> phase2/data/etymology_map.jsonl
phase2/edit_op.py               edit-operation tagger (unit-tested)
phase2/build_confusion_set.py   -> confusion-set.jsonl
phase2/confusion_stats.py       the tables above
```
Run: `PYTHONUTF8=1 python phase2/<script>.py`.
