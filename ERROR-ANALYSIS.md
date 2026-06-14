# EditingBench — Error Analysis

Reproducible (`error_analysis.py`); reads canonical post-audit items + available model runs. Coverage <100% = run still in progress.

## T1 — test_public (795 items)

### Failure decomposition (share of gold edits)

`fixed` = correct · `wrong_corr` = right site, wrong fix · `missed` = site untouched · `over/100` = spurious edits per 100 items (over-editing).

| model | cov | gold edits | fixed | wrong_corr | missed | over/100 |
|---|--:|--:|--:|--:|--:|--:|
| gpt55-high | 100% | 982 | 0.993 | 0.000 | 0.007 | 6.0 |
| gpt55-med | 100% | 982 | 0.993 | 0.000 | 0.007 | 6.9 |
| gemini-3.5-flash | 100% | 982 | 0.990 | 0.004 | 0.006 | 7.0 |
| opus-4.7 | 100% | 982 | 0.990 | 0.003 | 0.007 | 6.4 |
| deepseek-flash | 100% | 982 | 0.962 | 0.005 | 0.033 | 7.9 |
| sonnet-4.6 | 100% | 982 | 0.962 | 0.005 | 0.033 | 8.1 |
| gemma-4-31b | 100% | 982 | 0.956 | 0.004 | 0.040 | 6.4 |
| deepseek-v4-pro | 100% | 982 | 0.954 | 0.002 | 0.044 | 12.8 |
| gpt54-mini | 100% | 982 | 0.945 | 0.010 | 0.045 | 4.5 |
| qwen3.6-35b-a3b | 100% | 982 | 0.817 | 0.018 | 0.165 | 59.5 |
| glm-5.1 | 100% | 982 | 0.796 | 0.005 | 0.199 | 10.1 |
| typhoon25 | 100% | 982 | 0.764 | 0.036 | 0.201 | 32.1 |
| typhoon-s | 100% | 982 | 0.701 | 0.005 | 0.294 | 10.6 |
| thalle | 100% | 982 | 0.692 | 0.008 | 0.299 | 18.4 |
| openthaigpt | 100% | 982 | 0.690 | 0.012 | 0.297 | 19.7 |
| minimax-m2.7 | 100% | 982 | 0.656 | 0.006 | 0.338 | 13.7 |

### Per-class difficulty (pooled across all models)

Splits each class's failures into *detection* (missed) vs *correction* (wrong_corr) — the diagnostic axis.

| class | gold edits | fixed | wrong_corr | missed |
|---|--:|--:|--:|--:|
| 0 (unmapped) | 16 | 0.688 | 0.000 | 0.312 |
| 1 tone | 2608 | 0.896 | 0.011 | 0.092 |
| 2 consonant | 2192 | 0.876 | 0.006 | 0.117 |
| 3 การันต์ | 2640 | 0.887 | 0.010 | 0.103 |
| 4 vowel | 2896 | 0.857 | 0.002 | 0.140 |
| 5 cluster | 3392 | 0.863 | 0.012 | 0.126 |
| 6 loanword | 1968 | 0.808 | 0.003 | 0.189 |

### Item hardness (16 models scored)

How many models got each item *sentence-exact*. 0 = universally missed (intrinsically hard **or** suspect gold → audit); high = easy.

| #models correct | items |
|---:|---:|
| 1/16 | 1 |
| 2/16 | 6 |
| 3/16 | 6 |
| 4/16 | 8 |
| 5/16 | 7 |
| 6/16 | 6 |
| 7/16 | 26 |
| 8/16 | 11 |
| 9/16 | 30 |
| 10/16 | 59 |
| 11/16 | 58 |
| 12/16 | 90 |
| 13/16 | 110 |
| 14/16 | 112 |
| 15/16 | 162 |
| 16/16 | 97 |

### Top spurious over-edits (pooled `src→repl`)

| src→repl | count |
|---|--:|
| ∅→  | 185 |
| “→∅ | 61 |
|  →∅ | 53 |
| ”→" | 41 |
|  →  | 40 |
| “→" | 29 |
| มั้ย→ไหม | 26 |
| ​→∅ | 17 |
| ค→ก | 16 |
| ได้→∅ | 16 |
| ด้วย→∅ | 15 |
| ) →∅ | 14 |
| วะ→พ | 14 |
| ภาคม→จิกายน | 11 |
| )​ →∅ | 11 |

### Register effect (pooled correction recall)

| register | fixed/total | recall |
|---|--:|--:|
| encyclopedic | 2364/2896 | 0.816 |
| gov | 6311/7120 | 0.886 |
| news | 4937/5696 | 0.867 |

### Miscorrection examples (right site, wrong fix) — `src · gold · model`

**class 1 tone:** ค๊ะ · คะ · ค่ะ ×8 | ไม๊ · ไหม · ไม่ ×5 | น๊ะ · นะ · น่ะ ×4 | ก้อ · ก็ · ∅ ×3 | ก้อ · ก็ ·  ก็ ×2 | น๊ะ · นะ · นี ×1
**class 2 consonant:** ส · ษ · ศ ×2 | ส · ษ · ข ×1 | ฑี · ที · ทีก ×1 | ศ · ษ · ข ×1 | ฏา · ฎา · ฎ ×1 | ฑี · ที · ที  ×1
**class 3 การันต์:** การณ์ · การ · การนี้ ×3 | การณ์ · การ · การฯ  ×3 | เท่ห์ · เท่ · เต ×2 | การณ์ · การ · การก ×2 | ดุลย์ · ดุล · ดุลย ×2 | การณ์ · การ · การ  ×2
**class 4 vowel:** ต · ติ · ติของ ×2 | ฉะเพาะ · เฉพาะ · โดยเฉพาะ ×2 | ธ · ธิ · ธิ  ×1 | ผะ · ผ · ภ ×1 | ส · สะ · รว ×1
**class 5 cluster:** มั๊ย · ไหม · มั้ย ×22 | เร · เล · เรื่อ ×3 | ฅ · ค · ว่า "นำเข้า" ซึ่งเป็นการสะกดผิด ต้องแก้เป็น "นำเข้า" แต่ในประโยคเดิมเขีย ×2 | ด · ติ · ติ  ×1 | ฆาร · ฆรา · คฤห ×1 | ญ · น · ง ×1
**class 6 loanword:** น๊ · น · น็ ×3 | ษ · ส · ส  ×3

## T2 — t2 (223 items)

### Failure decomposition (share of gold edits)

`fixed` = correct · `wrong_corr` = right site, wrong fix · `missed` = site untouched · `over/100` = spurious edits per 100 items (over-editing).

| model | cov | gold edits | fixed | wrong_corr | missed | over/100 |
|---|--:|--:|--:|--:|--:|--:|
| gemini-3.5-flash | 100% | 276 | 0.989 | 0.000 | 0.011 | 9.0 |
| opus-4.7 | 100% | 276 | 0.986 | 0.000 | 0.014 | 11.7 |
| deepseek-v4-pro | 100% | 276 | 0.975 | 0.000 | 0.025 | 16.1 |
| gpt55-high | 100% | 276 | 0.975 | 0.000 | 0.025 | 4.5 |
| gpt55-med | 100% | 276 | 0.971 | 0.000 | 0.029 | 7.6 |
| gemma-4-31b | 100% | 276 | 0.967 | 0.000 | 0.033 | 7.6 |
| deepseek-flash | 100% | 276 | 0.960 | 0.011 | 0.029 | 7.6 |
| sonnet-4.6 | 100% | 276 | 0.946 | 0.004 | 0.051 | 17.0 |
| gpt54-mini | 100% | 276 | 0.917 | 0.014 | 0.069 | 8.5 |
| glm-5.1 | 100% | 276 | 0.815 | 0.004 | 0.181 | 23.3 |
| typhoon25 | 100% | 276 | 0.779 | 0.029 | 0.192 | 81.6 |
| qwen3.6-35b-a3b | 100% | 276 | 0.754 | 0.022 | 0.225 | 267.7 |
| thalle | 100% | 276 | 0.692 | 0.007 | 0.301 | 77.6 |
| minimax-m2.7 | 100% | 276 | 0.652 | 0.007 | 0.341 | 18.8 |
| typhoon-s | 100% | 276 | 0.641 | 0.004 | 0.355 | 22.4 |
| openthaigpt | 100% | 276 | 0.594 | 0.004 | 0.402 | 110.3 |

### Per-class difficulty (pooled across all models)

Splits each class's failures into *detection* (missed) vs *correction* (wrong_corr) — the diagnostic axis.

| class | gold edits | fixed | wrong_corr | missed |
|---|--:|--:|--:|--:|
| 1 tone | 672 | 0.868 | 0.015 | 0.118 |
| 2 consonant | 576 | 0.885 | 0.000 | 0.115 |
| 3 การันต์ | 864 | 0.865 | 0.008 | 0.127 |
| 4 vowel | 960 | 0.870 | 0.001 | 0.129 |
| 5 cluster | 880 | 0.807 | 0.007 | 0.186 |
| 6 loanword | 464 | 0.802 | 0.011 | 0.188 |

### Item hardness (16 models scored)

How many models got each item *sentence-exact*. 0 = universally missed (intrinsically hard **or** suspect gold → audit); high = easy.

| #models correct | items |
|---:|---:|
| 1/16 | 3 |
| 4/16 | 3 |
| 5/16 | 3 |
| 6/16 | 5 |
| 7/16 | 8 |
| 8/16 | 8 |
| 9/16 | 10 |
| 10/16 | 27 |
| 11/16 | 21 |
| 12/16 | 38 |
| 13/16 | 39 |
| 14/16 | 38 |
| 15/16 | 14 |
| 16/16 | 2 |

### Top spurious over-edits (pooled `src→repl`)

| src→repl | count |
|---|--:|
| ∅→  | 378 |
|  →∅ | 33 |
| ”→" | 30 |
| ,→  | 30 |
| ”→∅ | 29 |
| “→" | 28 |
|  →  | 22 |
| การ→∅ | 15 |
| ∅→ข้อความ:  | 14 |
| “→∅ | 11 |
| 2→  | 9 |
|  →- | 7 |
| -→– | 7 |
| ลิ→ลี | 6 |
| กษ→กษ์ | 6 |

### Register effect (pooled correction recall)

| register | fixed/total | recall |
|---|--:|--:|
| encyclopedic | 950/1200 | 0.792 |
| gov | 1461/1632 | 0.895 |
| news | 1346/1584 | 0.850 |

### Miscorrection examples (right site, wrong fix) — `src · gold · model`

**class 1 tone:** เง่า · เหง้า · ฐาน ×3 | ก้อ · ก็ ·  ก็ ×2 | ก้อ · ก็ · คือ ×1 | ก้อ · ก็ · กุ ×1 | เง่า · เหง้า · เหง่า ×1 | ก้อ · ก็ · ก็คือ ×1
**class 3 การันต์:** สิทธ์ · สิทธิ · สิทธี ×1 | การณ์ · การ · การ์ ×1 | การณ์ · การ · การ  ×1 | ยุทธิ์ · ยุทธ์ · ยุทธ์  ×1 | ดุลย์ · ดุล · ดุลย ×1 | การณ์ · การ · การน์ ×1
**class 4 vowel:** ตุ · ต · ต  ×1
**class 5 cluster:** เร · เล · เร่อ ×1 | ฅ · ค · ช ×1 | ฅ · ค ·  ค ×1 | ฅ · ค · คค ×1 | ค · ก · กรา ×1 | ฅ · ค · ขั ×1
**class 6 loanword:** ลิ๊งค์ · ลิงก์ · ลิ้งค์ ×2 | ลิ๊งค์ · ลิงก์ · ลิงค์ ×1 | ษ · ส · ส  ×1 | ค · ก · กรวมทั้ง ×1

## T3 — t3 (124 items)

### Failure decomposition (share of gold edits)

`fixed` = correct · `wrong_corr` = right site, wrong fix · `missed` = site untouched · `over/100` = spurious edits per 100 items (over-editing).

| model | cov | gold edits | fixed | wrong_corr | missed | over/100 |
|---|--:|--:|--:|--:|--:|--:|
| opus-4.7 | 100% | 195 | 0.990 | 0.000 | 0.010 | 54.0 |
| gemini-3.5-flash | 100% | 195 | 0.985 | 0.005 | 0.010 | 65.3 |
| gemma-4-31b | 100% | 195 | 0.969 | 0.005 | 0.026 | 32.3 |
| deepseek-flash | 100% | 195 | 0.964 | 0.000 | 0.036 | 57.3 |
| sonnet-4.6 | 100% | 195 | 0.959 | 0.000 | 0.041 | 58.1 |
| gpt55-high | 100% | 195 | 0.949 | 0.000 | 0.051 | 42.7 |
| gpt55-med | 100% | 195 | 0.944 | 0.000 | 0.056 | 41.1 |
| deepseek-v4-pro | 100% | 195 | 0.913 | 0.000 | 0.087 | 83.9 |
| gpt54-mini | 100% | 195 | 0.851 | 0.010 | 0.138 | 21.0 |
| glm-5.1 | 100% | 195 | 0.841 | 0.010 | 0.149 | 106.5 |
| qwen3.6-35b-a3b | 100% | 195 | 0.744 | 0.010 | 0.246 | 483.9 |
| typhoon25 | 100% | 195 | 0.697 | 0.015 | 0.287 | 200.8 |
| openthaigpt | 100% | 195 | 0.682 | 0.010 | 0.308 | 206.5 |
| thalle | 100% | 195 | 0.672 | 0.005 | 0.323 | 145.2 |
| typhoon-s | 100% | 195 | 0.646 | 0.005 | 0.349 | 68.5 |
| minimax-m2.7 | 100% | 195 | 0.446 | 0.000 | 0.554 | 71.0 |

### Per-class difficulty (pooled across all models)

Splits each class's failures into *detection* (missed) vs *correction* (wrong_corr) — the diagnostic axis.

| class | gold edits | fixed | wrong_corr | missed |
|---|--:|--:|--:|--:|
| 1 tone | 544 | 0.807 | 0.017 | 0.176 |
| 2 consonant | 384 | 0.831 | 0.008 | 0.161 |
| 3 การันต์ | 416 | 0.800 | 0.000 | 0.200 |
| 4 vowel | 624 | 0.854 | 0.002 | 0.144 |
| 5 cluster | 848 | 0.838 | 0.002 | 0.159 |
| 6 loanword | 304 | 0.819 | 0.000 | 0.181 |

### Item hardness (16 models scored)

How many models got each item *sentence-exact*. 0 = universally missed (intrinsically hard **or** suspect gold → audit); high = easy.

| #models correct | items |
|---:|---:|
| 1/16 | 2 |
| 2/16 | 1 |
| 3/16 | 1 |
| 4/16 | 10 |
| 5/16 | 9 |
| 6/16 | 6 |
| 7/16 | 8 |
| 8/16 | 8 |
| 9/16 | 21 |
| 10/16 | 13 |
| 11/16 | 8 |
| 12/16 | 18 |
| 13/16 | 7 |
| 14/16 | 4 |
| 15/16 | 2 |

### Top spurious over-edits (pooled `src→repl`)

| src→repl | count |
|---|--:|
| ∅→  | 492 |
|  →  | 95 |
|  →∅ | 91 |
| “→" | 50 |
| ”→" | 45 |
| ,→  | 37 |
| ​→∅ | 31 |
| ∅→) | 30 |
| เอม→เอ็ม | 26 |
| นึง→หนึ่ง | 22 |
| ชั่น→ชัน | 17 |
| ค→ก | 15 |
| ท→ต | 14 |
| ∅→ พ.ศ. | 14 |
| ไหร่→ไร | 13 |

### Register effect (pooled correction recall)

| register | fixed/total | recall |
|---|--:|--:|
| encyclopedic | 675/880 | 0.767 |
| gov | 941/1056 | 0.891 |
| news | 968/1184 | 0.818 |

### Miscorrection examples (right site, wrong fix) — `src · gold · model`

**class 1 tone:** ไม๊ · ไหม · ไม้ ×3 | ก้อ · ก็ ·  ก็ ×2 | ก้อ · ก็ · ก็นำ ×1 | ไม๊ · ไหม · พืช ×1 | ก้อ · ก็ · ∅ ×1 | ไม๊ · ไหม · ไก่ ×1
**class 2 consonant:** วงษ์ · วงศ์ · วงศ ×1 | ศ · ษ · ข ×1 | ฑี · ที · ฬิกา ×1
**class 4 vowel:** ต · ติ · ติ  ×1
**class 5 cluster:** ฅ · ค ·  ค ×2
