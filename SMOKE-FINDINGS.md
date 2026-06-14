# EditingBench — Phase 8 Smoke Findings (2026-05-24)

Pipeline: `run_editing.py` (generation) → `score_runs.py` (grading via `grader.py`).
**102 `test_public` items, 17/class, single deterministic run (temp 0), 0 API errors
on all three models.** Auto-generated table: `subtask2/sample-run-results.md`.

## Headline numbers (correction F1, 95% item-bootstrap CI)

| model | detect F1 | correct F1 | CI | sent-acc | GLEU | ChERRANT F0.5 |
|---|--:|--:|:--:|--:|--:|--:|
| **gpt55-med** (frontier) | 0.965 | **0.965** | [0.93, 0.99] | 0.941 | 0.993 | 0.958 |
| deepseek-flash (general) | 0.800 | **0.791** | [0.71, 0.86] | 0.686 | 0.885 | 0.867 |
| **typhoon25** (Thai-native 30B) | 0.722 | **0.699** | [0.62, 0.78] | 0.598 | 0.910 | 0.678 |

ChERRANT span-F0.5 (secondary) = Phase-6 `therrant.py` auto-typing of both gold and
system edits (validated 0.981 class-agreement vs construction gold). It is
precision-weighted, so it reads complementarily to the per-class *recall* table below
— e.g. DeepSeek's tone class is 0.55 recall but 0.86 ChERRANT-F0.5 (precise when it
acts, but misses many).

## Findings

1. **The benchmark discriminates cleanly.** A ~27-point correction-F1 spread
   (0.70 → 0.79 → 0.97); GPT-5.5's CI is fully disjoint from both others. Not
   saturated even at the frontier (gpt55 misses ~3–4%, all in the tone class) —
   there is headroom for a leaderboard.

2. **Thai-native ≠ best at orthography (the counter-intuitive headline).** Typhoon
   2.5 30B, trained Thai-native, is the **weakest** corrector — below a general
   model (DeepSeek). Native-language pretraining does not confer formal
   orthographic-editing skill. This is a publishable framing: orthographic
   correction is a *distinct* competence from Thai fluency.

3. **The loanword hypothesis does NOT hold — revise it.** We expected class 6
   (loanword translit) to trip up non-Thai models. The opposite: loanword is where
   the non-Thai models do *best* (deepseek 0.85, gpt55 1.00), and **Typhoon is
   relatively weak on it (0.65)**. The universally hard classes are **tone (1),
   consonant-pair (2), and cluster (5)** — i.e. difficulty tracks the *error
   mechanism* (subtle tonal / homophonous-consonant / metathesis confusions), not
   cross-lingual loanword knowledge. Per-class recall is the real diagnostic axis.

   | model | tone(1) | cons(2) | การันต์(3) | vowel(4) | cluster(5) | loan(6) |
   |---|--:|--:|--:|--:|--:|--:|
   | gpt55-med | 0.90 | 1.00 | 1.00 | 1.00 | 0.96 | 1.00 |
   | deepseek-flash | 0.55 | 0.78 | 0.74 | 0.74 | 0.54 | 0.85 |
   | typhoon25 | 0.80 | 0.61 | 0.95 | 0.83 | 0.62 | 0.65 |

4. **Behavioral finding — Typhoon over-edits / rewrites.** Despite explicit
   "correct spelling only, don't rewrite" instructions, Typhoon transliterates
   (`SMEs→เอสเอ็มอี`), fills empty parens, and inserts words (`เปิดเผยว่า→เปิดเผยไว้ว่า`).
   That both lowers its correction precision (false-positive edits) and is itself an
   instruction-following weakness worth reporting.

## Grader validation (in situ)
- Gold-corrected output → exactly 1.0 (det/corr F1, sent-acc) — by construction
  (`align_edits` derives identical edits when output == `text_correct`).
- Audit of Typhoon's 41 non-perfect items: **38 genuine orthographic misses, only 3
  whitespace-only** — the §-prompt "don't change spacing" line removed the
  whitespace confound seen in the 12-item pre-run.

## Caveats
- `test_public` is synthetic-only (no mined items; those are blind in `test_private`).
  Synthetic gold is construction-exact, so scores are reliable pre-annotation; the
  Phase-5 human pass still validates instrument quality.
- Single deterministic run; CIs are item-bootstrap, not the SEA-HELM 8-run × 30-boot
  protocol (that's for the production run, not a smoke).
- ChERRANT span-F0.5 (secondary) now included via Phase-6 ThERRANT (auto-typing
  validated at 0.981 vs construction gold); the per-class recall table is the primary
  per-mechanism breakdown.

## Reproduce
```
PYTHONUTF8=1 python run_editing.py --models typhoon25 deepseek-flash gpt55-med --split test_public --n 102
PYTHONUTF8=1 python score_runs.py --split test_public --n 102
```
