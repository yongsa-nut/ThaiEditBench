**ThaiEditBench**

**Consolidated ACL Revision Plan**

*A reviewer-safe revision package merging the current draft, the latest additional revision points, and the earlier professor-level comments*

Prepared 25 May 2026

This document consolidates the current paper draft, the latest additional revision points, and the earlier professor-level comments into a single ACL-safe revision package. Each section gives the current draft wording, a proposed revision, the rationale, and the net effect on reviewer risk. The proposed-revision text is written so that it can be pasted directly into the manuscript.

# **Contents**

1\. Title

2\. Abstract

3\. Introduction and contributions

4\. Related work

5\. Benchmark, task, taxonomy, and construction

6\. Contamination control and length tiers

7\. Quality control and the gold audit

8\. Evaluation protocol

9\. Models and inference

10\. Results and analysis

11\. Figure 1 and tables

12\. Conclusion

13\. Limitations

Final implementation order

References

# **Priority corrections to the uploaded comments**

Two corrections take priority over everything else, because they affect claims that a reviewer can check directly.

**1\. Parameter counts.** Do not claim that the proprietary frontier models are 100B+ parameters. Public parameter counts are not available for these systems, so any size figure is unverifiable. Keep the capacity and configuration confound, but state it as a known confound rather than as a specific number.

**2\. Audit-removal percentage.** Do not report the audit removals as approximately 3 percent overall at item level. The item-level arithmetic is 24 of 819 for T1, 27 of 250 for T2, and 26 of 150 for T3, which is 77 of 1,219, or about 6.3 percent of items overall. Removal rates are much higher in the long tiers: about 2.9 percent in T1, 10.8 percent in T2, and 17.3 percent in T3. Either report exact counts only, or compute the percentage correctly with the per-tier breakdown.

# **Global revision checklist**

* Replace all universal claims with benchmark-conditioned claims.

* Define Thai Character Cluster (TCC) on first use, and use TCC-level consistently in place of character-level.

* Correct the VISTEC statement. VISTEC includes misspelling detection and correction, but it is Twitter-domain rather than formal-register, mechanism-typed orthographic correction.

* Remove word-level GLEU from the main metrics, or move it to an appendix as a segmentation-dependent metric only.

* Reframe the model results as configured-system comparisons rather than as intrinsic model-capability rankings.

* Recalculate over-editing using per-clean-TCC, per-clean-character, or per-clean-sentence denominators before claiming a collapse.

* Make gold quality control transparent: construction-derived target edits, automatic flagging, and manual verification of the flagged cases.

# **1\. Title**

**Section checklist**

* Signal the benchmark contribution clearly.

* Avoid overloading the title with technical detail.

* Keep mechanism typing and length stratification visible.

**Current draft.** The working title is ThaiEditBench: A Mechanism-Typed, Length-Stratified Benchmark for Thai Orthographic Error Correction.

**Proposed revision.**

ThaiEditBench: A Mechanism-Typed, Length-Stratified Benchmark for Thai Orthographic Correction

**Rationale.** The title is already strong. Removing the word Error is cleaner, because orthographic correction already implies the correction of orthographic errors. Do not add at TCC Level to the title. Define TCC prominently in the abstract and the metrics section instead.

**Effect.** The title stays concise and communicates the two main axes, mechanism typing and length stratification.

# **2\. Abstract**

**Section checklist**

* Define TCC early.

* Remove the exact gold and no human annotation overstatement.

* Replace correction is detection with benchmark-conditioned wording.

* Avoid the Thai-native not best phrasing.

* Reframe over-editing as exposure-sensitive unless normalized metrics confirm a true rate increase.

**Current draft.** The current abstract calls ThaiEditBench character-level, claims that gold corrections are exact and require no human annotation, and states that correction is a detection problem rather than a knowledge problem, that Thai-native models are not best, and that an over-editing collapse is invisible at sentence level.

**Proposed revision.**

Thai is written without explicit word boundaries and combines tone marks, silenced consonants (ตัวการันต์), homophonous consonant choices, vowel-form variation, consonant-cluster alternations, and extensive loanword transliteration within a Brahmic script. These properties produce orthographic error mechanisms that differ from those primarily emphasized in English Grammatical Error Correction (GEC) and Chinese Spelling Check (CSC). We present ThaiEditBench, a mechanism-typed benchmark for Thai orthographic correction evaluated at the Thai Character Cluster (TCC) level, where TCCs are inseparable Thai orthographic units rather than whitespace-delimited words. ThaiEditBench combines (i) a six-class orthographic mechanism taxonomy with etymology tags, (ii) sentence, paragraph, and page tiers designed to test correction under increasingly long, mostly-correct contexts, and (iii) construction-derived gold edits from confusion-set injection and Wikipedia cleanup-bot mining, with source passages screened by a memorization probe. Because target edits are recorded at injection or mining time, the benchmark provides precise gold corrections for the intended error spans while avoiding new item-level correction annotation. Across 16 configured systems evaluated under a fixed Thai instruction prompt, we find that missed-span detection dominates incorrect replacement, that the evaluated Thai-specialized systems do not outperform the strongest general systems under this setup, and that paragraph and page contexts expose over-edit accumulation and clean-text fidelity failures that sentence-level evaluation largely obscures.

**Rationale.** This version keeps the main contribution but removes the most vulnerable claims. TCC should be defined, because PyThaiNLP describes TCCs as inseparable contiguous Thai character units based on Thai spelling features, which supports the choice to avoid word-level scoring \[1\]. The abstract also avoids saying exact gold in a way that would conflict with the residual-typo audit in the appendix.

**Effect.** The abstract becomes precise, defensible, and aligned with the methodology.

# **3\. Introduction and contributions**

**Section checklist**

* Remove pseudo-headings such as The phenomenon and The gap.

* Narrow the novelty claim to Thai formal-register orthographic correction.

* Acknowledge document-level and context-level GEC instead of claiming that no length axis exists anywhere.

* Replace char-level with TCC-level.

## **Segment 1\. Motivation and gap**

**Current draft.** The draft uses pseudo-headings such as The phenomenon. Thai orthography is error-prone and The gap, followed by the claim of no length-robustness axis anywhere in the GEC and CSC literature.

**Proposed revision.**

Thai orthography presents script-specific correction challenges, including tone-mark selection and placement, silenced-consonant marks (ตัวการันต์), homophonous consonant choices, vowel-form confusions, consonant-cluster alternations, and loanword transliteration. Because Thai is written without whitespace-delimited word boundaries, these errors are difficult to localize and to evaluate with token-based tools.

Existing GEC and CSC resources provide important precedents for edit extraction, error typing, and spelling-error detection. However, for Thai, prior error-annotated resources primarily target social-media, informal, or learner-oriented settings. They do not provide a formal-register, mechanism-typed, contamination-controlled orthographic benchmark. ThaiEditBench addresses this gap by introducing explicit passage-length and error-sparsity tiers for Thai orthographic correction, and by evaluating whether systems preserve mostly-correct long context while correcting sparse errors.

**Rationale.** The claim of no length-robustness axis anywhere is too broad. Document-level GEC explicitly studies context-aware grammatical correction, and RobustGEC evaluates context robustness under perturbations \[2\]. The defensible novelty is not first length robustness anywhere, but formal Thai orthographic correction with controlled length and error-sparsity tiers.

## **Segment 2\. Contributions**

**Current draft.** The draft lists contributions using informal symbols, for example a char-level Thai orthographic correction benchmark with a six-class mechanism taxonomy plus etymology tag, and it frames the leaderboard as a model ranking.

**Proposed revision.**

Our primary contributions are threefold. First, we introduce ThaiEditBench, a formal-register Thai orthographic correction benchmark evaluated at TCC level. It combines a six-class orthographic mechanism taxonomy, etymology tags, and sentence, paragraph, and page tiers designed to test correction under increasingly long, mostly-correct contexts. Second, we release a Thai orthographic edit-typer, adapted from ERRANT-style span matching, that labels TCC-level edits by mechanism class and supports per-mechanism diagnosis. Third, we evaluate 16 configured systems under a fixed Thai instruction prompt, showing that missed-span detection dominates the error budget, that the evaluated Thai-specialized systems trail the strongest general systems under this setup, and that long-context tiers reveal over-edit accumulation and clean-text fidelity failures that sentence-level evaluation does not capture.

**Rationale.** This removes informal symbols such as plus and not-equals, avoids char-level, and frames the leaderboard as configured-system evidence rather than a universal model ranking.

**Effect.** The introduction makes a strong novelty claim while avoiding the two easiest reviewer attacks, false novelty and inconsistent evaluation terminology.

# **4\. Related work**

**Section checklist**

* Correct the VISTEC description.

* Convert outline fragments into connected academic prose.

* Position ERRANT, SIGHAN CSC, MuCGEC and ChERRANT, and the Thai resources accurately.

* Clarify that ThaiEditBench adapts prior evaluation traditions to Thai orthography.

## **Segment 1\. GEC and CSC**

**Current draft.** The draft presents fragmentary phrases, for example ERRANT automatic error typing and F0.5 span scoring and Character-level Chinese spelling check is the closest task.

**Proposed revision.**

ERRANT provides automatic edit extraction and error-type classification for GEC, while SIGHAN-style CSC evaluates spelling-error detection and correction at the character and location level. MuCGEC and ChERRANT further show how Chinese GEC evaluation can incorporate multi-reference annotation and character-based scoring. ThaiEditBench adapts this span-based evaluation tradition to Thai orthographic correction, but differs by scoring at the TCC level, by using a Thai-specific mechanism taxonomy, and by stratifying evaluation by passage length and error sparsity.

**Rationale.** This gives prior work proper credit. ERRANT is designed to extract edits from parallel original and corrected sentences and to classify them automatically \[3\], and MuCGEC is explicitly multi-reference and discusses character-based evaluation \[5\].

## **Segment 2\. Thai NLP and VISTEC**

**Current draft.** The draft states that the VISTEC-TP-TH-2021 Twitter corpus is used for word segmentation, not formal-domain spelling.

**Proposed revision.**

Thai NLP resources include PyThaiNLP tooling, TCC-based processing, Thai spelling correction on social text, Thai misspelling semantics, and VISTEC-TP-TH-2021. VISTEC includes annotations for word segmentation, misspelling detection and correction, and named-entity recognition. However, it is a Twitter-domain corpus rather than a formal-register, mechanism-typed orthographic benchmark.

**Rationale.** This is a necessary factual correction. VISTEC documentation states that the corpus includes misspelling detection and correction in addition to word segmentation and named-entity annotation \[4\].

**Effect.** Related work now acknowledges prior Thai spelling resources without weakening the contribution.

# **5\. Benchmark, task, taxonomy, and construction**

**Section checklist**

* Define the minimal-edit contract.

* State TCC as the operational unit.

* Scope the confusion-set novelty claim.

* Clarify ORST and RID verification and the fallback evidence.

* Separate the public confusion-set tiers from the private cleanup-bot material.

## **Segment 1\. Task definition**

**Current draft.** The draft says given a Thai passage containing character-level orthographic errors, return the passage with those errors corrected and nothing else changed.

**Proposed revision.**

Given a Thai passage containing orthographic errors, systems must return a minimally corrected output: only gold orthographic error spans may be modified, while spacing, numerals, punctuation, and all non-error text must remain unchanged. Any modification outside a gold span is counted as an over-edit.

**Rationale.** The task is not character-level in a naive Unicode sense. It is a minimal-edit orthographic correction task evaluated at TCC level.

## **Segment 2\. Taxonomy and dictionary verification**

**Current draft.** The draft says canonical forms are verified against the Royal Institute Dictionary (ORST).

**Proposed revision.**

We define six orthographic mechanism classes and attach an etymology tag to each item. Canonical spellings are checked against ORST and RID dictionary entries where available. For modern loanwords that are absent from the offline ORST lexicon, we record the fallback etymological or lexical evidence used to accept the canonical form.

**Rationale.** The appendix states that 87.5 percent of confusion-set pairs are RID and ORST verified, and that the remaining misses are modern loanwords absent from the offline list. The main text should therefore not imply universal dictionary coverage.

## **Segment 3\. Confusion set**

**Current draft.** The draft says a 1,044-pair by six-class Thai confusion set, the first such set.

**Proposed revision.**

We construct and release a 1,044-pair Thai orthographic confusion set, with each pair assigned to one of six mechanism classes and tagged for etymology. To the best of our knowledge, this is the first publicly released Thai confusion set that is systematically organized by orthographic mechanism.

**Rationale.** First such set is too exposed. To the best of our knowledge and publicly released make the novelty claim defensible.

## **Segment 4\. Construction sources**

**Current draft.** The draft lists two complementary sources, confusion-set injection and cleanup-bot mining, without fully separating public and private material in the main text.

**Proposed revision.**

ThaiEditBench uses two construction sources. Public tiers use confusion-set injection into permissively redistributable clean text. Each injected item records the TCC span, the mechanism class, and the etymology tag, and injection uses whole-token-run matching rather than substring replacement to protect short valid forms. Cleanup-bot mining provides real pairs of incorrect and corrected spellings from Thai Wikipedia spelling-cleanup history, and these mined items route to the private split.

**Rationale.** Moving this detail into the main text supports reproducibility. It is important to state that the public tiers are 100 percent confusion-set injection and that the cleanup-bot items route to the private split.

**Effect.** The benchmark section becomes auditable and reproducible, and is less vulnerable to first benchmark or dictionary-coverage objections.

# **6\. Contamination control and length tiers**

**Section checklist**

* Stop treating memorization of the clean source as harmless.

* State the actual contamination threat model.

* Avoid claiming that the GEC and CSC literature does not test context robustness at all.

* Explain T2 and T3 as controlled Thai orthographic sparsity tiers.

## **Segment 1\. Contamination control**

**Current draft.** The draft says the benchmark is contamination-robust by design because inputs are novel corrupted text, so memorizing the clean original only helps a model.

**Proposed revision.**

The benchmark reduces contamination risk by evaluating systems on corrupted passages that do not occur verbatim in the source corpora. However, a model that memorized the clean source passage could still benefit by reconstructing it directly. We therefore apply a verbatim-continuation memorization probe and route lower-risk material to the private split.

**Rationale.** Memorization of the clean source is a contamination threat, not a benign advantage. The revised text makes the threat model logically coherent.

## **Segment 2\. Length tiers**

**Current draft.** The draft says T2 and T3 measure precision under long correct context, an axis the CSC and GEC literature does not test.

**Proposed revision.**

The sentence tier uses relatively dense errors, while the paragraph and page tiers contain many clean distractor sentences. These tiers are designed to measure precision under long, mostly-correct context, complementing document-level and context-level GEC work by isolating Thai orthographic correction under controlled error sparsity.

**Rationale.** This retains the key idea but avoids dismissing document-level and context-robustness GEC \[2\].

**Effect.** The construction logic is credible and does not overclaim novelty.

# **7\. Quality control and the gold audit**

**Section checklist**

* Remove fully automatic unless no human decision affected the final drop list.

* Distinguish target-span construction gold from residual source-typo risk.

* Treat model consensus as a flagging heuristic, not as proof.

* Correct the audit-removal percentage.

## **Segment 1\. Main quality-control paragraph**

**Current draft.** The draft labels quality control as fully automatic and says that because errors are introduced by construction, the gold is exact, with two automatic guards and no human annotation.

**Proposed revision.**

Quality control. Target-span corrections are construction-derived: applying the recorded gold edits recovers the clean source passage for the injected or mined span. However, construction does not guarantee that the surrounding source passage is typo-free. We therefore combine automatic consistency checks, variant reconciliation, and a consensus-based residual-typo audit, followed by manual verification of the flagged cases before finalizing the drop list.

**Rationale.** The appendix says that flagged cases were reviewed using an HTML view before the drop list was committed, so fully automatic and no human annotation are misleading. The safer distinction is no new item-level correction annotation for the target edits, together with manual verification of the automatically flagged defects.

## **Segment 2\. Consensus threshold and impact**

**Current draft.** The draft says that when at least k models agree on the same output that differs from gold, the gold is the likely defect, and it reports removals of 24, 27, and 26 items.

**Proposed revision.**

When at least k systems produce the same normalized output that differs from gold, we flag the item for a residual-typo audit. If a majority threshold is used, k equals 9, since the ceiling of 16 divided by 2, plus 1, is 9\. Otherwise we report the actual threshold. Consensus is used as a flagging heuristic, not as deterministic proof of a gold defect. Flagged cases are classified as shared misses, systematic over-edits, or likely unmarked source typos, and only the final category is removed. This audit removed 24 of 819 T1 items, 27 of 250 T2 items, and 26 of 150 T3 items, that is 77 of 1,219 items overall, or about 6.3 percent. Removal rates are much higher in the long tiers: about 2.9 percent in T1, 10.8 percent in T2, and 17.3 percent in T3.

**Rationale.** Multiple models can share the same bias, so consensus should trigger review rather than decide ground truth. The uploaded comment said approximately 3 percent overall, but the item-level calculation is about 6.3 percent. The paper should either report exact counts only or compute the percentage correctly with the per-tier breakdown.

## **Segment 3\. Appendix B wording**

**Current draft.** The appendix says the HTML view is used to eyeball every flagged item before the drop list is committed.

**Proposed revision.**

The audit automatically generates a reproducible HTML review interface that shows gold-versus-consensus diffs and provisional drop, keep, and variant labels. The flagging rules are deterministic, but flagged cases are manually verified before the final drop list is committed, which lets us distinguish residual source typos from shared model misses and systematic over-edits.

**Rationale.** This removes colloquial language and resolves the contradiction between automatic and eyeballed.

**Effect.** The gold-quality section becomes a methodological strength rather than a reviewer liability.

# **8\. Evaluation protocol**

**Section checklist**

* Make TCC-level correction F1 the primary metric.

* Treat detection F1, clean-sentence fidelity, and per-mechanism span-F0.5 as diagnostics.

* Remove word-level GLEU from the main metrics.

* Add length-normalized over-editing metrics.

* Release the variant map.

## **Segment 1\. TCC scoring**

**Current draft.** The draft says grading is at Thai Character Cluster level with ERRANT-style span matching, without fully spelling out why.

**Proposed revision.**

We evaluate edits at the Thai Character Cluster (TCC) level using span matching adapted from ERRANT-style evaluation. A TCC is an inseparable Thai orthographic unit of contiguous characters. TCC-level scoring respects Thai orthographic binding, including vowels, tone marks, and silencers, while avoiding the segmentation variance introduced by word-tokenized evaluation.

**Rationale.** This supplies the justification that the current draft assumes but does not fully state. PyThaiNLP explicitly defines TCCs as inseparable Thai units, which supports this metric choice \[1\].

## **Segment 2\. Metric hierarchy**

**Current draft.** The draft lists primary correction F1, detection F1, clean-sentence fidelity, per-mechanism span-F0.5, and word-level GLEU for comparability.

**Proposed revision.**

Our primary metric is TCC-level correction F1 under span matching. We report detection F1, clean-sentence fidelity, per-mechanism span-F0.5, and spurious edits per 10,000 clean TCCs as diagnostic metrics. We use span-F0.5 in the per-mechanism analysis to emphasize precision, since over-editing is a central failure mode in long, mostly-correct passages.

**Rationale.** Remove word-level GLEU from the main metric list. It contradicts the core claim that Thai word segmentation is unreliable for this task. If it is retained, it belongs in an appendix with the caveat that it is a segmentation-dependent exploratory comparability metric only. The uploaded comments correctly identify this as a major internal-consistency issue.

## **Segment 3\. Variants and single-reference scoring**

**Current draft.** The draft says orthographic correction is essentially single-reference, so the paper does not adopt multi-reference GEC machinery.

**Proposed revision.**

Most target edits have a single canonical spelling under the benchmark guidelines. Accepted orthographic, loanword-transliteration, or register variants are pre-reconciled to the benchmark canonical form through a deterministic variant map, which we release with the scorer.

**Rationale.** This is more reproducible and less dismissive of multi-reference GEC practice. MuCGEC shows that multi-reference evaluation matters in broader Chinese GEC, so ThaiEditBench should explain why formal orthographic correction uses canonicalization rather than appearing unaware of that literature \[5\].

**Effect.** The evaluation protocol becomes internally consistent with the Thai-specific motivation.

# **9\. Models and inference**

**Section checklist**

* Use configured systems.

* Report exact model IDs, access dates, prompts, token budgets, reasoning and thinking settings, and failure handling.

* Do not claim unknown proprietary parameter counts.

* Add prompt-sensitivity and reasoning-mode limitations.

* Consider a small sensitivity ablation.

**Current draft.** The draft lists 16 models and notes mixed reasoning and thinking modes, with Claude in non-thinking mode, GPT-5.x at a set reasoning effort, and open reasoning models in native thinking mode, with no reasoning-mode sweep.

**Proposed revision.**

We evaluate 16 configured systems under a unified zero-shot Thai instruction prompt and one prespecified configuration per system. We report provider model IDs, API access dates, decoding parameters, output-token budgets, reasoning or thinking settings where applicable, token-runout handling, and the exact prompt in Appendix E. Because reasoning modes, token budgets, provider defaults, serving stacks, and model scale are not fully controlled, the leaderboard should be interpreted as a comparison of practical configured systems rather than as an intrinsic ranking of base-model capability.

**Rationale.** OpenAI documentation treats reasoning effort as a configurable setting, so mixed reasoning settings must be reported and caveated \[6\]. Keep the model-capacity confound, but do not write that the frontier models are 100B+ parameters unless the paper can publicly document those counts. A safer statement is that the comparison is confounded by known scale differences for the Thai-specialized systems, by proprietary unknowns for the frontier systems, and by differences in serving stack, reasoning mode, and token budget.

**Effect.** This protects the leaderboard from fairness and reproducibility objections.

# **10\. Results and analysis**

**Section checklist**

* Keep detection dominates replacement as T1-specific unless it is shown across tiers.

* Remove causal claims about Thai-native training.

* Normalize over-editing by exposure length.

* Add paired tests or bootstrap comparisons for the major claims.

* Control mechanism difficulty for register and tier confounds.

## **Segment 1\. Leaderboard**

**Current draft.** The draft says the frontier clusters at 0.95 to 0.97 on T1 and that bootstrap CIs separate three strata.

**Proposed revision.**

On T1, the strongest systems cluster around 0.95 to 0.97 correction F1. Bootstrap intervals indicate broad separation between the highest-performing systems, the mid-tier systems, and the weakest systems, while several within-cluster rank differences should be treated as descriptive unless they are supported by paired significance tests.

**Rationale.** Do not overinterpret rank differences without paired bootstrap or McNemar-style tests for the key comparisons.

## **Segment 2\. Detection versus replacement**

**Current draft.** The draft says that once a model notices an error it almost always fixes it correctly, so what separates models is error discrimination, not knowledge of correct spellings.

**Proposed revision.**

In T1, correct-site but incorrect-replacement errors are rare relative to missed spans. This indicates that, under the formal orthographic setting of ThaiEditBench, model differences are driven primarily by error-span detection rather than by replacement selection.

**Rationale.** This keeps the insight but avoids the universal claim that correction is not a knowledge problem.

## **Segment 3\. Thai-specialized systems**

**Current draft.** The draft says Thai-native training confers no orthographic advantage and that the gap widens with length.

**Proposed revision.**

Under the tested prompt and inference settings, the evaluated Thai-specialized systems trail the strongest general systems, with the gap increasing on the longer tiers. This result should not be read as evidence against Thai-specialized pretraining in general, because the comparison is confounded by differences in model scale, serving stack, token budget, and reasoning configuration.

**Rationale.** This preserves the empirical observation but removes the unsupported causal interpretation. It also avoids the undocumented 100B+ claim while keeping the important capacity and configuration caveat.

## **Segment 4\. Over-editing and length normalization**

**Current draft.** The draft describes an over-editing collapse because spurious edits per 100 items rise from T1 to T3, for example Qwen at 59, 268, 484 and Typhoon 2.5 at 32, 82, 201, and the page-5 chart plots this as an over-editing collapse.

**Proposed revision.**

Longer tiers expose larger absolute numbers of spurious edits per passage and lower clean-text fidelity for the weaker systems. However, because item length increases substantially across tiers, raw over-edits per 100 items conflate the false-positive rate with text exposure. We therefore report both absolute spurious edits per 100 passages and spurious edits normalized per 10,000 clean TCCs. The normalized metric tests whether the false-positive rate itself increases, while the absolute metric captures the user-visible accumulation of unwanted edits in longer passages.

**Rationale.** This is the most important quantitative fix. Table 2 gives mean item lengths of about 100, 424, and 1,242 characters for T1, T2, and T3. Using mean characters as a rough denominator, Qwen's raw 59, 268, and 484 over-edits per 100 items convert to roughly 59, then 63, then 39 per 10,000 characters, so the raw explosion may largely reflect exposure rather than a higher per-character false-positive rate. The final claim should be over-edit accumulation unless the clean-TCC-normalized analysis still shows a rate increase.

## **Segment 5\. Per-mechanism difficulty**

**Current draft.** The draft says class 6, loanwords, is the hardest mechanism and that difficulty is a property of the mechanism rather than of cross-lingual knowledge.

**Proposed revision.**

Loanword transliteration is the hardest mechanism in pooled T1 outcomes, with failures dominated by missed spans rather than by wrong replacements. Because encyclopedic text is also loanword-dense and harder by register, we report per-model class recall and a mixed-effects or stratified analysis that controls for tier, register, and system before attributing difficulty to the mechanism itself.

**Rationale.** The draft itself notes that encyclopedic text is hardest and loanword-dense, which creates a mechanism and register confound. This refinement prevents a reviewer from objecting that the class effect is actually a domain or register effect.

## **Segment 6\. Qualitative examples**

**Current draft.** There is no qualitative example table in the current draft.

**Proposed revision.**

Add an appendix example box or short table with one representative example for each mechanism class, plus one long-tier over-edit example. For each example, show the corrupted input span, the gold correction, the model output, the outcome label, and the mechanism class.

**Rationale.** Qualitative examples make the detection-miss, loanword-difficulty, and over-editing findings concrete.

**Effect.** The results section becomes statistically careful without losing its empirical message.

# **11\. Figure 1 and tables**

**Section checklist**

* Fix the Figure 1(b) caption.

* Distinguish raw accumulation from normalized rate.

* Improve Table 3 readability.

* Ensure every figure and table is interpreted in the text.

## **Segment 1\. Figure 1 caption**

**Current draft.** The current caption says that over-edits per 100 items on a log scale show the frontier staying flat in the low tens while weak models explode into the hundreds, described as the over-editing collapse.

**Proposed revision.**

Figure 1: Length robustness. (a) Correction-F1 slope from the sentence tier to the paragraph and page tiers. (b) Absolute spurious edits per 100 passages, showing the user-visible accumulation of unwanted edits in longer contexts. Because the tiers differ substantially in length, we additionally report spurious edits per 10,000 clean TCCs and clean-sentence fidelity, in order to distinguish an increased false-positive rate from increased text exposure.

**Rationale.** The current page-5 figure is visually persuasive but denominator-vulnerable. The new caption keeps the figure useful while preventing a reviewer from dismissing the conclusion as a length artifact.

## **Segment 2\. Table 3**

**Current draft.** The draft uses one dense leaderboard table that combines detection, correction, and fidelity values.

**Proposed revision.**

Either split Table 3 into two tables, one for detection and correction F1 and one for fidelity and over-editing, or retain a single table but use consistent bolding for the column maxima and add a note that within-cluster differences are descriptive unless they are supported by paired tests.

**Rationale.** The current table is information-rich but dense. Readability improvements help reviewers see the main story quickly.

**Effect.** The figures and tables now support the argument rather than overstate it.

# **12\. Conclusion**

**Section checklist**

* Mirror the revised abstract.

* Use configured-system language.

* Avoid Thai-native not best.

* Avoid the universal detection-problem framing.

* Expand the release statement.

**Current draft.** The draft says that across 16 models the paper reframes correction as a detection problem, shows that Thai-native is not best, and surfaces a length-induced over-editing collapse, and that it releases data, grader, and edit-typer.

**Proposed revision.**

ThaiEditBench is a mechanism-typed, length-stratified benchmark for Thai orthographic correction, released with a TCC-level scorer and a Thai orthographic edit-typer. Across 16 configured systems, ThaiEditBench shows that missed-span detection dominates the evaluation error budget, that the evaluated Thai-specialized systems do not outperform the strongest general systems under this setup, and that extended, mostly-correct passages reveal over-edit accumulation and clean-text fidelity failures that sentence-level evaluation obscures. We release the benchmark data with splits, the TCC-level scorer, the orthographic edit-typer, the full confusion set, the variant map, the audit HTML viewer, the injection scripts, and the exact prompt, in order to support future Thai orthographic correction research.

**Rationale.** The conclusion is strong but scoped, and it implements the release-package recommendation from the latest comment.

**Effect.** The conclusion matches the evidence and introduces no new claims.

# **13\. Limitations**

**Section checklist**

* Add configured-system and prompt-sensitivity limitations.

* Add the length-normalized over-editing limitation.

* Retain the sparse-error limitation.

* Clarify minimal-edit versus fluency correction.

* Add register and future-work limitations.

**Current draft.** The current limitations mention sparse error density, the reasoning mode not being swept, the minimal-edit versus fluency boundary, and a single-register gap, but they do not fully address model-capacity and configuration confounds, prompt sensitivity, or length-normalized over-editing.

**Proposed revision.**

**Sparse error density.** The long tiers are deliberately sparse, with one to three errors scattered across otherwise-clean passages, in order to isolate precision under extended correct context. They do not test dense multi-error settings such as OCR degradation, heavy typo input, or L2 writing, where interacting errors may change both detection and correction behavior.

**Configured-system comparison.** Systems are evaluated under one practical, prespecified configuration. Reasoning modes, token budgets, provider defaults, serving stacks, and model scale are not fully controlled. The leaderboard should therefore be interpreted as configured-system performance, not as an intrinsic ranking of base-model capability.

**Prompt sensitivity and few-shot settings.** We use a single fixed Thai instruction prompt and do not explore prompt variants, few-shot demonstrations, or domain-adapted prompting. Future work should evaluate whether Thai-specialized systems benefit disproportionately from few-shot or domain-specific examples.

**Length-normalized over-editing.** Raw over-edits per item increase with passage length, because longer passages expose more clean text where false positives can occur. We therefore report both absolute over-edits per 100 passages and spurious edits normalized per 10,000 clean TCCs. Claims about an over-editing collapse should be based on normalized rates, while raw counts should be interpreted as user-visible accumulation.

**Minimal-edit versus fluency correction.** The benchmark intentionally penalizes register normalization, punctuation changes, spacing changes, and fluency rewrites unless they appear in the accepted variant map. A small number of apparent over-edits may nevertheless correspond to residual source errors that are not represented in the construction gold.

**Register coverage.** ThaiEditBench covers news, encyclopedic, and government or legal registers, but academic Thai remains underrepresented because of permissive-redistribution constraints. Future extensions should add academic, educational, OCR, and dense multi-error settings.

**Rationale.** This limitations section preempts the major reviewer critiques instead of minimizing them.

**Effect.** The limitations are specific, honest, and actionable.

# **Final implementation order**

1. Fix VISTEC, the novelty claim, and TCC terminology first. These are factual and framing issues.

2. Rewrite quality control. Remove fully automatic, specify k, report the audit counts correctly, and explain the manual verification.

3. Remove word-level GLEU from the main metrics. Keep it only as an appendix diagnostic if it is truly necessary.

4. Rework the over-editing claims and Figure 1(b). Add per-clean-TCC or per-clean-character normalization before using the word collapse.

5. Reframe the model results as configured-system results. Keep the scale and configuration confounds, but do not claim unknown proprietary parameter counts.

6. Add qualitative examples and pairwise statistical tests. This strengthens the empirical sections.

7. Update the abstract and conclusion last. They must match the corrected claims exactly.

# **References**

1. PyThaiNLP tokenize documentation. [https://pythainlp.org/docs/3.1/api/tokenize.html](https://pythainlp.org/docs/3.1/api/tokenize.html)

2. Document-level grammatical error correction (BEA 2021). [https://aclanthology.org/2021.bea-1.8/](https://aclanthology.org/2021.bea-1.8/)

3. Automatic annotation and evaluation of error types, ERRANT (ACL 2017). [https://aclanthology.org/P17-1074/](https://aclanthology.org/P17-1074/)

4. SEACrowd VISTEC-TP-TH-2021 dataset card. [https://huggingface.co/datasets/SEACrowd/vistec\_tp\_th\_21](https://huggingface.co/datasets/SEACrowd/vistec_tp_th_21)

5. MuCGEC: a multi-reference multi-source evaluation dataset (NAACL 2022). [https://aclanthology.org/2022.naacl-main.227/](https://aclanthology.org/2022.naacl-main.227/)

6. Reasoning models, OpenAI API documentation. [https://developers.openai.com/api/docs/guides/reasoning](https://developers.openai.com/api/docs/guides/reasoning)