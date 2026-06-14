# ThaiEditBench — Dataset Construction

Builds the Thai character-level orthographic-error dataset: sentence-level items
where `text_wrong` contains RID-verifiable misspelling(s) and `text_correct` is
the gold. Two tracks, merged into stratified splits.

- **Synthetic injection** (backbone) — the Phase-2 confusion set (1,044 wrong→correct
  pairs × 6 classes) injected into the Phase-3 permissive clean corpus. Gold is exact
  by construction.
- **Wikipedia mining** (ecological validity) — real typo fixes harvested from the
  edit history of the Thai-Wikipedia cleanup bot `BotKung`, RID-gated then curated to
  a class-balanced, high-confidence ship set.

Item format: see [`schema.md`](schema.md). Grading is Phase 7 (not here); items are
built grader-ready (TCC-level gold spans).

## Pipeline

```
inject.py            core injection: whole-token-run match + TCC gold-span emission
  └ test_inject.py   round-trip / boundary-safety / determinism (1,044 pairs, 100%)
inject_dataset.py    pull+normalize+segment+filter+stratified-inject -> synthetic_pool.jsonl
mine_wiki.py         usercontribs of BotKung -> compare-to-parent -> wiki_raw_pairs.jsonl
  └ filter_diffs.py  RID gate + classify + sentence rebuild + class-balanced curate
                     -> wiki_items_all.jsonl (full) + wiki_items.jsonl (curated ~40)
memorization_probe.py  Typhoon verbatim-completion per source -> memorization.json
build_dataset.py     dedup + group + class-balanced split (memo-routed) -> items_*.jsonl
```

Run order:
```
PYTHONUTF8=1 python test_inject.py
PYTHONUTF8=1 python inject_dataset.py            # --refresh to re-pull HF
PYTHONUTF8=1 python mine_wiki.py --users BotKung --max-contribs 6000
PYTHONUTF8=1 python filter_diffs.py
PYTHONUTF8=1 python memorization_probe.py --n 30
PYTHONUTF8=1 python build_dataset.py
```

## Key design decisions

- **Whole-token-run matching (not substring).** 51 confusion correct-forms are ≤3
  chars (`ก็`, `นะ`); injecting by substring would corrupt embedding words. We replace
  only a contiguous newmm token-run equal to the correct form — boundary-safe, and it
  also handles multi-token forms like `จุฬาลงกรณ์มหาวิทยาลัย`. 100% of pairs are injectable.
- **Construction gold + light verify.** Synthetic gold is exact (`gold_source:construction`);
  Phase-5 only spot-verifies a sample. The 3-annotator α-pass concentrates on mined items
  (`gold_source:annotated`), where the correction is uncertain.
- **RID gate + misalignment guards on mined pairs.** `wrong ∉ LEX, correct ∈ LEX`
  (`thai_words ∪ thai_orst_words`) removes the noise the Phase-1 pilot produced
  (e.g. `มีการนำ→ป้องกันไม่`); a min-length-2 + shared-prefix/suffix guard drops
  diff-fragment artifacts (`คศ→ค`, `นเรียะคุ→อัง`) where the diff split a word.
- **Deep mine, then curate.** Mining `BotKung` 6× deeper (6,000 contribs → 3,328 raw
  pairs → 103 sentence-level items) over-delivers; we keep up to 2 distinct article
  contexts per recurring typo, then curate to a **class-balanced, high-confidence ~40**
  (drop ≤2-char forms; rank by confusion-set match > longer correct form > recurs in
  >1 article). The full 103 stay in `wiki_items_all.jsonl` for the appendix / scale-up.
- **NFC + surface repair before injection.** `◌ํ+า → ำ` (decomposed sara-am, thaisum) and
  `เเ → แ` (thaigov) are repaired so the injected error is the *only* deviation (Q2.4).
- **Contamination posture.** The injection track is structurally robust (the corrupted
  input is novel; memorizing the correct original only helps produce the correct answer).
  The residual generalization risk is controlled by routing low-memorization sentences to
  `test_private` (evidence from `memorization.json`), embargoing the dated Wikipedia
  snapshot, and never reusing a clean sentence across splits.

## Outputs (`data/`)

| file | what |
|---|---|
| `synthetic_pool.jsonl` | 2,820 synthetic items (gold invariant all-pass) |
| `wiki_raw_pairs.jsonl` / `wiki_filtered_pairs.jsonl` | mining raw (3,328) → filtered clean pairs (222) |
| `wiki_items_all.jsonl` / `wiki_items.jsonl` | full sentence-level (103) → curated ship set (40) |
| `memorization.json` | per-source verbatim-recall scores (Typhoon 2.5 30B) |
| `items_{train,dev,test_public,test_private}.jsonl` | **final splits** |
| `clean_cache/*.jsonl` | cached HF pulls (delete to re-pull) |

### Synthetic pool composition
- Errors per class: 1:618 · 2:511 · 3:554 · 4:583 · 5:697 · 6:457
- Registers: news 1,197 · encyclopedic 1,031 · gov 552 · legal 40 (legal thin — the
  Constitution corpus is only 20 docs / 402 usable sentences; **academic register remains
  the documented Phase-3 gap**)
- Density: single 2,220 · multi 600

### Memorization (Typhoon 2.5 30B verbatim continuation)
All sources score **low** (mean LCP 0.003–0.017, 0 high-memorization sentences) — the
clean text is not trivially regurgitated. Risk ordering (low→high): thaisum < thaigov <
wikipedia < constitution. Conservative metric; the definitive per-benchmarked-model check
is Phase 8.

### Final splits (2,542 unique items; 318 exact dups dropped, 0 VISTEC/Wisesight overlap)

| split | items | tracks | per-class (1–6) | density (single/multi) | memo-risk |
|---|--:|---|---|---|--:|
| `test_private` | 868 | 828 syn + **40 mined** | 164·132·138·146·174·114 | 701/167 | **0.003** (lowest) |
| `test_public` | 819 | synthetic | 143·119·141·147·161·108 | 636/183 | — |
| `dev` | 606 | synthetic | 105·99·99·104·117·82 | 477/129 | — |
| `train` | 249 | synthetic | 46·43·41·39·46·34 | 207/42 | 0.013 |

Per-class proportional slicing keeps **every class present in every split**; the
low-memorization slice of each class routes to `test_private` (blind leaderboard),
which also receives all mined items. **0 sentences span >1 split** (no leakage).
The 6 mechanism classes are balanced within each split (class 6 / loanword is
smaller everywhere — it has the fewest confusion seeds, 129).

## Provenance & licensing
Synthetic items inherit the clean-source license (thaisum MIT, Wikipedia CC BY-SA,
Constitution/thaigov CC0); mined items are CC BY-SA (Wikipedia). The confusion set is
CC BY-SA. All permissive-redistribution — publishable in the public leaderboard subset.

## Grading & sample run (Phases 6–8, built 2026-05-24)
- `grader.py` (+ `test_grader.py`) — TCC-level **detection/correction F1** (ERRANT-style
  span match), sentence accuracy, per-class correction recall, word-level GLEU, bootstrap CI.
- `therrant.py` (+ `test_therrant.py`) — **Phase 6 ThERRANT** (first Thai ERRANT): auto-types
  any (wrong, correct) pair into the 6 classes (correct-side word anchoring + loan lexicon);
  validated **0.981** class-agreement vs construction gold. Powers the secondary metric
  (`cherrant_counts` → ChERRANT span-F0.5 per error-type).
- `run_editing.py` — model harness (Typhoon / OpenRouter / OpenAI Responses; resume-safe).
- `score_runs.py` — grades runs → `sample-run-results.md`.
- `SMOKE-FINDINGS.md` — Phase-8 smoke writeup (gpt55 0.965 ≫ deepseek 0.79 ≫ typhoon 0.70;
  loanword-class hypothesis overturned).

## Not in these phases
3-annotator pass + α-calibration (Phase 5, human-gated; the only remaining step), full
SEA-HELM-CI matrix run. Dump-based full mine = deferred scale-up.
