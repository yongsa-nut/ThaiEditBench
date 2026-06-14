# Clean-Corpus Catalog (EditingBench, Phase 3)

Catalog of **formal-domain Thai clean-text sources** for Phase-4 synthetic error
injection (`plan.md` §6c) and mined-item context (§6a). The clean corpus carries
the paper's headline claim — **first formal-domain Thai orthographic benchmark**
(§3 gap 3: every prior Thai error corpus is social-media). This file documents,
per source: **license · size · register · access · contamination**, plus a
fitness assessment, the recommended injection mix, and the Phase-4 sampling stub.

**Eligibility rule (locked):** only **permissive-redistribution** licenses
(CC BY-SA / CC0 / public-domain) are *eligible to inject into* — synthetic test
items are derivatives whose license flows through to the public leaderboard
subset. Gated (LST20, BEST, TNC, ThaiLIS) and NC-licensed (prachathai-67k,
XL-Sum) sources are catalogued but **excluded** from the injection pool.

**Register scope (locked):** v1 ships **3 formal registers** — encyclopedic +
news + legal-formal. **Academic prose is a documented coverage gap**: no
permissively-licensed Thai academic corpus exists (ThaiLIS theses are
institution-gated); deferred to v2 / a later scrape effort.

All HF figures below were **probed live** on 2026-05-23 via the HF dataset-viewer
API (`phase3/probe_corpora.py`): row counts (`/size`), sampled rows (`/rows`,
100/source), an orthographic-cleanliness proxy, and sentence-segmentability.

---

## 1. Master table

### 1a. ELIGIBLE — injection pool (permissive + formal + verified loadable)

| Source (HF id / URL) | License | Est. size | Register | Access | Contamination risk |
|---|---|---|---|---|---|
| **Thai Wikipedia** `wikimedia/wikipedia` cfg `20231101.th` | CC BY-SA 4.0/3.0 | ~160k articles (dated snapshot) | Encyclopedic | HF `datasets` (parquet) / dataset-viewer | **High** — in C4/mC4 & all major pretraining. Mitigate w/ dated snapshot + article-ID embargo |
| **Thai Wikipedia (cleaned)** `pythainlp/thai-wiki-dataset-v3` | CC BY-SA 3.0 | **196,533** rows | Encyclopedic | HF `datasets` (parquet) | High (same content, cleaned aggregation; snapshot date less explicit) |
| **thaisum** `pythainlp/thaisum` | **MIT** | **391,868** articles (2014–2020) | Formal news (Thairath/ThaiPBS/TheStandard…) | HF `datasets`; field `body` | High — news widely scraped; on HF since 2020. Dated (≤2020) |
| **Thai Government Corpus** `pythainlp/thaigov-v2-corpus-22032023` | **CC0-1.0** | **30,380** docs | Gov news / PR (formal) | HF `datasets`; field `context` | Med-High — gov-site text partially crawled |
| **Thai Constitution** `pythainlp/thai-constitution-corpus` | **CC0-1.0** | **20** docs (~199k Thai tok) | Legal-formal | HF `datasets`; field `txt` | High (constitutions heavily reproduced) but few distinct docs |
| **Royal Gazette** ราชกิจจานุเบกษา · ratchakitcha.soc.go.th | **Public domain** (Copyright Act B.E.2537 §7) | Vast (since 1858; 100k+ docs) | Legal-formal (laws, decrees, notifications) | **Web scrape** — PDF/HTML; **403 to naïve fetch** → needs browser-like UA + PDF text extraction. No HF dataset, no public API | **Lower** — PDF archive less cleanly indexed than HTML ⇒ good private-split candidate |

### 1b. EXCLUDED — catalogued, not in the injection pool

| Source | License / barrier | Why excluded | Notes |
|---|---|---|---|
| **prachathai-67k** `PyThaiNLP/prachathai67k` | **CC BY-NC** | Non-commercial ⇒ can't publish derivatives | News; viewer 501 (loading-script dataset) |
| **XL-Sum (th)** `csebuetnlp/xlsum` | **CC BY-NC-SA** | Non-commercial | BBC Thai news, ~8k |
| **LST20** `lst-nectec/lst20` | NECTEC — research-free, **commercial-gated** | Not freely redistributable | 3.16M words, **has gold sentence boundaries**, mixed register — usable as *research-only context*, not public artifact |
| **BEST2010** (NECTEC) | Proprietary / request-gated | Not freely redistributable; not on HF | ~5M words, genre-tagged (news/article/encyclopedia/novel) |
| **Thai National Corpus** (Chula) | "All rights reserved" | Gated, query-only | 32M words |
| **ThaiLIS / TDC theses** | Institution-gated | The would-be **academic** source → gap | 600k+ full-text docs |
| **CulturaX / OSCAR / mC4 / CC100 (th)** | mostly permissive | **Fails cleanliness/register bar** — web-crawl, poor Thai langID, 2018 snapshots | Wrong domain entirely |
| **Mangosteen** (vistec-AI) | permissive (CC/PD) | Pretraining-mix (cleaned web + OCR books) | Note as a *meta-source* — its Gazette/book subsets could feed Phase 4 later |

---

## 2. Fitness assessment (eligible sources)

Criteria: **register** (formal?) · **cleanliness** (low pre-existing error rate) ·
**segmentability** · **license** · **volume** · **contamination**.

| Source | Register | Cleanliness† | Seg. (chars/sent) | License | Volume | Verdict |
|---|---|---:|---:|---|---|---|
| thaisum | formal news | **98.3%** | 57 | MIT | 392k | **★ primary news workhorse** |
| Wikipedia `20231101.th` | encyclopedic | **98.1%** | 148 | CC BY-SA | ~160k | **★ primary encyclopedic** (dated→embargo) |
| thaigov-v2 | gov formal/PR | **98.7%** | 69 | CC0 | 30k | ✔ gov-news supplement |
| Thai Constitution | legal-formal | 95.9%‡ | 190 | CC0 | 20 docs | ✔ legal seed (low doc diversity) |
| Royal Gazette | legal-formal | (not probed — PDF) | — | Public domain | vast | ◐ stretch: heavy legal register; scrape cost in Phase 4 |
| thai-wiki-v3 | encyclopedic | 97.6% | 138 | CC BY-SA 3.0 | 197k | alt. to dated Wikipedia (cleaned, undated) |

† **Cleanliness proxy** = % of pure-Thai word tokens (newmm) present in the offline
RID/Thai lexicon (`thai_words ∪ thai_orst_words`). It is **relative**, not a true
error rate: the OOV residual is dominated by the honest floor — proper nouns
(`ชาลส์`, `เลสเตอร์`), Thai numerals, and the `ๆ`/`ฯ` symbols — not misspellings.
All eligible sources land **96–99%**, vs. the social-media corpora this benchmark
is escaping. ‡ The Constitution's lower 95.9% is a **metric artifact**: section
numbers `มาตรา ๑/๒/๓…` are Thai-script tokens counted as OOV; orthographic
cleanliness is effectively on par with the others.

**Two pre-existing surface variations found** (must be normalized *out* before
injection, so the injected error is the only error — consistent with Q2.4 NFC):
- **thaisum** — decomposed sara-am: `ดํา`, `สํา` (◌ํ + า) instead of composed `ำ`.
- **thaigov-v2** — `เเล้ว` (เ + เ) instead of the single character `แ` in `แล้ว`.

**Segmentability:** `pythainlp.tokenize.sent_tokenize` yields sentences on every
source; mean sentence length tracks formality (news 57 → encyclopedic ~140 →
legal 190 chars). ⇒ Phase 4 needs a **length filter** to produce sentence-level
stimuli (over-long legal/encyclopedic sentences split or dropped).

---

## 3. Recommended injection mix (3 registers)

| Register | Primary source | License | Role |
|---|---|---|---|
| **News** | **thaisum** (`body`) | MIT | Injection workhorse — largest clean permissive prose, short sentences ideal for stimuli |
| **Encyclopedic** | **Wikipedia `20231101.th`** | CC BY-SA | Second pillar; **dated snapshot** = clean freeze date for the §8 embargo. *Disjoint from the §6a mining article set.* |
| **Legal-formal** | **Thai Constitution** (CC0) + **Royal Gazette** (PD, Phase-4 scrape) | CC0 / PD | Legal register; Gazette is the heavyweight if scrape budget allows |
| *(supplement)* | **thaigov-v2** (CC0) | CC0 | Gov formal/PR — register breadth + a clean CC0 pool |
| **Academic** | — | — | **Documented gap** (no permissive source); deferred to v2 |

**Wikipedia overlap discipline (important).** Thai Wikipedia is *both* the §6a
mining source *and* this encyclopedic injection source. Enforce a **disjoint
article-ID partition**: articles whose revisions feed the mining pool are excluded
from the clean-injection pool, and a held-out article-ID set is **embargoed** for
the private test split (§8). Track the snapshot date for freshness.

---

## 4. Contamination & embargo strategy

The benchmark is **synthetic-injection-first**, which reframes contamination:
- **Injection track:** the corrupted sentence is *novel* (never published) even
  when the clean source is in pretraining — so source contamination is **low-risk**
  for injected items. (If anything, a model knowing the clean text helps it produce
  the correct form, which is the desired behavior.)
- **Mined track (Phase 4a):** the *corrected* Wikipedia sentence exists verbatim
  online ⇒ this is where contamination bites. Mitigations: dated snapshot, embargo
  test-article IDs, require systems to disclose training data (§8).
- **Private blind split:** prefer **lower-contamination / less-indexed** text —
  Royal Gazette PDFs and the most-recent thaigov-v2 / Wikipedia revisions — so the
  private leaderboard split is hardest to have memorized.
- **Cross-corpus dedup:** at sentence level against VISTEC-TP-TH-2021 and Wisesight
  (the social-media error corpora) to avoid leakage between train sources and test.

---

## 5. Phase-4 clean-text sampling protocol (stub)

Feeds `inject_dataset.py` (§6c, Phase 4b). Per source:

1. **Pull** via `datasets` (parquet) or dataset-viewer rows; extract the text field
   (`text` / `body` / `context` / `txt`). Gazette: scrape PDF/HTML w/ browser-like
   UA + PDF text extraction.
2. **NFC-normalize** (reuse `phase1/classify.py:normalize`): compose sara-am `ำ`;
   repair the found variations (`◌ํ+า → ำ`, `เเ → แ`) so pre-existing surface noise
   is removed *before* controlled injection.
3. **Sentence-segment** (`pythainlp.tokenize.sent_tokenize`) + **length-filter**
   to a sentence-level window (≈40–180 chars); drop headers/tables/citation lines
   and non-Thai-dominant lines.
4. **Cleanliness gate:** drop sentences below an in-lexicon-ratio threshold (skip
   already-noisy lines so injection starts from clean text).
5. **Dedup & partition:** disjoint Wikipedia article-IDs vs. the §6a mining pool;
   sentence-level dedup vs. VISTEC/Wisesight; embargo a Wikipedia-ID set + recent
   gazette/gov text → private split.
6. **Stratify** by register, hand to `inject_<class>()` to apply confusion-set
   errors (`confusion-set.jsonl`) across the 6 classes × etymology × density.

---

## 6. Reproduce

```
phase3/probe_corpora.py   -> phase3/data/probe_results.json + <name>_sample.txt
```
Run: `PYTHONUTF8=1 python phase3/probe_corpora.py`. Probes the eligible HF
sources via the dataset-viewer API (no full downloads; sidesteps the
"Dataset scripts no longer supported" failure that breaks `datasets`-loader pulls
for script-based sets like prachathai-67k).

**Caveats logged:** (a) `wikimedia/wikipedia` `/size` returns the all-languages
total (61.6M) — the Thai config is ~160k; use the config figure. (b) `thai-law`
has no canonical permissive HF id (the probed guess 401'd); legal-formal is covered
by Constitution + Gazette. (c) Cleanliness % is a relative noise proxy, not an
error rate (see §2†).
