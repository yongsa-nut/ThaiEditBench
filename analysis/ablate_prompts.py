"""Prompt-sensitivity ablation (paper Appendix G): reruns T1 for two systems under an English
instruction and a Thai instruction with two train-split examples. Calls model APIs; see run_editing.py
for the environment variables it needs.
"""
import sys, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import run_editing as R  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 819
MODELS = ["gemma-4-31b", "typhoon-s"]

# --- few-shot: original instruction + 2 train exemplars (classes 1 and 2) ----
def exemplars():
    items = [json.loads(l) for l in (REPO / "data" / "items_train.jsonl").open(encoding="utf-8")]
    ok = [it for it in items if len(it["edits"]) == 1 and len(it["text_wrong"]) <= 90]
    by = {}
    for it in ok:
        c = it["edits"][0].get("class") or it["edits"][0].get("error_class")
        by.setdefault(c, it)
    return [by[c] for c in sorted(by, key=str)[:2]]          # deterministic: classes 1, 2

_instr = R.PROMPT.split("\n\nประโยค:")[0]
_ex = exemplars()
FEWSHOT = (
    _instr + "\n\nตัวอย่าง\n"
    + "\n\n".join(f"ประโยค: {it['text_wrong']}\nประโยคที่แก้ไขแล้ว: {it['text_correct']}" for it in _ex)
    + "\n\nประโยค: {text}\nประโยคที่แก้ไขแล้ว:"
)

EN = (
    "Correct the misspelled Thai words in the following sentence according to standard Thai "
    "orthography. Fix only misspelled consonants, vowels, tone marks, or silent-consonant "
    "(karan) marks. Do not change the wording, do not rephrase, do not add or remove content, "
    "and do not change spacing, numerals, or punctuation. If there are no misspellings, return "
    "the sentence exactly as given. Reply with only the corrected sentence on a single line, "
    "with no explanation.\n\n"
    "Sentence: {text}\nCorrected sentence:"
)

if __name__ == "__main__":
    R.load_env()
    for ex in _ex:
        print(f"exemplar {ex['id']}: {ex['text_wrong'][:50]}...")
    for tag, prompt in [("en", EN), ("fewshot", FEWSHOT)]:
        R.PROMPT = prompt
        R.RESULTS = R.HERE / f"results_prompt_{tag}"
        R.RESULTS.mkdir(exist_ok=True)
        items = R.load_or_make_sample("test_public", N)
        print(f"\n=== variant '{tag}' -> {R.RESULTS.name}/  ({len(items)} items x {MODELS})")
        R.run_matrix(MODELS, items, 8, paragraph=False, min_tokens=0)
    print("\nABLATION DONE")
