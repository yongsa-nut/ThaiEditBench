"""
Curated seed list of GENUINE context-dependent (real-word) confusions for Thai.

Check-in 1 decision: replace the over-inclusive `wrong in pythainlp-lexicon`
heuristic (which over-flagged 213 and missed นะค่ะ/นะคะ) with this curated set.
A pair is routed to the v2 catalog (context_dependent=True) only if its wrong
form appears here -- i.e. the wrong form is itself a valid Thai word with a
distinct meaning/function, so correctness needs sentence context.

Seed only; expanded during annotation. Each entry is a (form, gloss) the wrong
spelling could legitimately be in another context.
"""

# wrong-forms that are themselves valid words (mood/meaning depends on context)
CONTEXT_DEPENDENT_FORMS = {
    "คะ", "ค่ะ", "นะคะ", "นะค่ะ", "คับ", "ครับ",   # polite particles / mood
    "กริยา", "กิริยา",                                 # verb vs manners
    "ไต้", "ใต้",                                        # torch/under
    "มา", "ม้า",                                          # come / horse
    "ยัง", "ย่าง",                                        # still / to grill
    "น่า", "หน้า", "หนา",                              # ought-to / face / thick
    "ขา", "ข้า",                                          # leg / servant-I
    "เกม", "เกมส์",                                       # game (RID เกม) — borderline, keep for review
    "ปาก", "ปาด",                                        # mouth / to slice
    "ค่า", "ฆ่า",                                         # value / to kill
    "ตี", "ที",                                           # to hit / time-instance
    "เพลา", "เพรา",                                       # axle/time / (กะเพรา ctx)
    "สัน", "สรร", "สรรค์",                              # ridge / to select
    "พัน", "พันธ์", "พันธุ์",                          # thousand / bond / lineage
}


def is_context_dependent(wrong: str, correct: str) -> bool:
    return wrong in CONTEXT_DEPENDENT_FORMS
