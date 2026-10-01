# T1 consensus-audit report

Every T1 item (819-item public-test pool) that the cross-model consensus audit flags: the most common
output other than the gold comes from at least 3 systems and from at least as many systems as the gold.
A flagged item is kept if that output equals the input (shared miss), is a partial fix toward the gold,
or differs from the gold only in punctuation or whitespace; every other flagged item is dropped.
The same rule is used for T2 and T3 (`audit-review-t2t3.md`).

Flagged: 65; dropped: 45; final T1: 774 items.
For 24 of the dropped items only 9 or 10 systems have outputs (column `systems`); the rule is applied to
those outputs and drops all 24. Empty replies count as the unchanged input.

| id | systems | consensus | gold | decision | gold vs consensus |
|---|---|---|---|---|---|
| syn-000024 | 16 | 7 | 7 | DROP | gold `∅` → consensus `ห`; gold `∅` → consensus `่` |
| syn-000034 | 10 | 7 | 1 | DROP | gold `∅` → consensus `า` |
| syn-000041 | 16 | 7 | 5 | DROP | gold `∅` → consensus `ไห`; gold `ั้ย` → consensus `∅` |
| syn-000071 | 10 | 3 | 1 | DROP | gold `ส` → consensus `ล` |
| syn-000107 | 10 | 7 | 2 | DROP | gold `ะ` → consensus `∅` |
| syn-000112 | 16 | 9 | 3 | DROP | gold `ะ` → consensus `∅` |
| syn-000151 | 10 | 9 | 0 | DROP | gold `∅` → consensus `ี` |
| syn-000326 | 10 | 7 | 0 | DROP | gold `้` → consensus `่` |
| syn-000442 | 10 | 9 | 0 | DROP | gold `∅` → consensus `้` |
| syn-000502 | 16 | 5 | 2 | DROP | gold `ู` → consensus `ิว`; gold `ค` → consensus `ก` |
| syn-001209 | 16 | 8 | 6 | DROP | gold `∅` → consensus `เ`; gold `วะ` → consensus `พ` |
| syn-001226 | 10 | 10 | 0 | DROP | gold `บ` → consensus `น` |
| syn-001314 | 16 | 9 | 5 | DROP | gold `พ` → consensus `ป` |
| syn-001357 | 16 | 6 | 4 | DROP | gold `∅` → consensus `้` |
| syn-001401 | 10 | 7 | 0 | DROP | gold `∅` → consensus `้`; gold `้` → consensus `∅` |
| syn-001413 | 16 | 8 | 7 | DROP | gold `∅` → consensus `เ`; gold `วะ` → consensus `พ` |
| syn-001477 | 16 | 9 | 2 | DROP | gold `่` → consensus `∅` |
| syn-001544 | 9 | 6 | 0 | DROP | gold `์` → consensus `∅` |
| syn-001560 | 16 | 7 | 7 | DROP | gold `ไห` → consensus `∅`; gold `∅` → consensus `ั้ย` |
| syn-001611 | 16 | 6 | 2 | DROP | gold `∅` → consensus `น`; gold `น` → consensus `∅` |
| syn-001650 | 10 | 10 | 0 | DROP | gold `ฏ` → consensus `ฎ` |
| syn-001696 | 10 | 5 | 3 | DROP | gold `∅` → consensus `ล` |
| syn-001698 | 10 | 6 | 0 | DROP | gold `∅` → consensus `่` |
| syn-001731 | 16 | 6 | 6 | DROP | gold `การ` → consensus `∅` |
| syn-001772 | 16 | 7 | 2 | DROP | gold `่` → consensus `∅`; gold `∅` → consensus `ด์` |
| syn-001802 | 10 | 3 | 0 | DROP | gold `๊` → consensus `่`; gold `∅` → consensus `ห`; gold `∅` → consensus `่` |
| syn-001832 | 16 | 5 | 4 | DROP | gold `าน` → consensus `ัญ` |
| syn-001875 | 10 | 6 | 1 | DROP | gold `∅` → consensus `เข้า` |
| syn-001911 | 16 | 6 | 4 | DROP | gold `∅` → consensus `ว`; gold `ว์` → consensus `∅` |
| syn-001926 | 9 | 7 | 0 | DROP | gold `∅` → consensus `ล`; gold `ล` → consensus `∅` |
| syn-001962 | 10 | 10 | 0 | DROP | gold `ฐ` → consensus `ญ` |
| syn-002023 | 9 | 5 | 3 | DROP | gold `∅` → consensus `์` |
| syn-002063 | 16 | 8 | 3 | DROP | gold `ค` → consensus `ก` |
| syn-002085 | 10 | 7 | 0 | DROP | gold `ั` → consensus `้` |
| syn-002162 | 10 | 8 | 1 | DROP | gold `บ` → consensus `น` |
| syn-002165 | 9 | 9 | 0 | DROP | gold `ว` → consensus `า` |
| syn-002178 | 16 | 5 | 4 | DROP | gold `ซ` → consensus `ส` |
| syn-002334 | 9 | 4 | 2 | DROP | gold `∅` → consensus `ญ`; gold `ญ` → consensus `∅` |
| syn-002375 | 9 | 6 | 1 | DROP | gold `­` → consensus `∅`; gold `­` → consensus `∅` |
| syn-002428 | 16 | 8 | 7 | DROP | gold `∅` → consensus `่` |
| syn-002482 | 10 | 9 | 0 | DROP | gold `ฏ` → consensus `ฎ` |
| syn-002497 | 9 | 7 | 1 | DROP | gold `ว` → consensus `า` |
| syn-002710 | 16 | 5 | 0 | DROP | gold `“` → consensus `∅`; gold `ธ` → consensus `ท` |
| syn-002736 | 16 | 6 | 3 | DROP | gold `ไห` → consensus `∅`; gold `∅` → consensus `ั้ย` |
| syn-002811 | 16 | 7 | 3 | DROP | gold `∅` → consensus `ไห`; gold `ั้ย` → consensus `∅` |
| syn-000143 | 16 | 8 | 5 | keep (shared miss: consensus = input) | gold `∅` → consensus `็` |
| syn-000193 | 16 | 9 | 6 | keep (punctuation/whitespace only) | gold ` ` → consensus ` ` |
| syn-000238 | 16 | 6 | 2 | keep (punctuation/whitespace only) | gold ` ` → consensus ` ` |
| syn-000310 | 16 | 8 | 7 | keep (punctuation/whitespace only) | gold ` ` → consensus ` ` |
| syn-000428 | 16 | 8 | 0 | keep (punctuation/whitespace only) | gold `“` → consensus `∅` |
| syn-000461 | 16 | 8 | 5 | keep (shared miss: consensus = input) | gold `ภ` → consensus `ะพ` |
| syn-000562 | 16 | 8 | 1 | keep (shared miss: consensus = input) | gold `ส` → consensus `ษ` |
| syn-000744 | 16 | 14 | 0 | keep (punctuation/whitespace only) | gold `"` → consensus `∅` |
| syn-001341 | 16 | 11 | 0 | keep (punctuation/whitespace only) | gold `“` → consensus `∅` |
| syn-001408 | 16 | 13 | 3 | keep (shared miss: consensus = input) | gold `ะ` → consensus `∅` |
| syn-001735 | 16 | 8 | 7 | keep (shared miss: consensus = input) | gold `น` → consensus `∅` |
| syn-001759 | 16 | 5 | 5 | keep (shared miss: consensus = input) | gold `∅` → consensus `บ`; gold `∅` → consensus `ระ` |
| syn-002209 | 16 | 7 | 2 | keep (shared miss: consensus = input) | gold `∅` → consensus `็` |
| syn-002271 | 16 | 7 | 7 | keep (partial fix toward the gold) | gold `ค์` → consensus `∅` |
| syn-002319 | 16 | 11 | 3 | keep (punctuation/whitespace only) | gold ` ` → consensus ` ` |
| syn-002478 | 16 | 9 | 5 | keep (partial fix toward the gold) | gold `∅` → consensus `ร` |
| syn-002575 | 16 | 14 | 0 | keep (punctuation/whitespace only) | gold `“` → consensus `∅` |
| syn-002600 | 16 | 14 | 0 | keep (partial fix toward the gold) | gold `หนา` → consensus `∅`; gold `∅` → consensus `หนา` |
| syn-002622 | 16 | 6 | 4 | keep (partial fix toward the gold) | gold `ย์` → consensus `∅` |
| syn-002725 | 16 | 8 | 7 | keep (partial fix toward the gold) | gold `ะ` → consensus `∅` |
