# EditingBench — Error Analysis

Reproducible (`error_analysis.py`); reads canonical post-audit items + available model runs. Coverage <100% = run still in progress.

## T1 — test_public (774 items)

### Failure decomposition (share of gold edits)

`fixed` = correct · `wrong_corr` = right site, wrong fix · `missed` = site untouched · `over/100` = spurious edits per 100 items (over-editing).

| model | cov | gold edits | fixed | wrong_corr | missed | over/100 |
|---|--:|--:|--:|--:|--:|--:|
| gpt55-high | 100% | 957 | 0.997 | 0.000 | 0.003 | 4.3 |
| gpt55-med | 100% | 957 | 0.995 | 0.000 | 0.005 | 4.8 |
| gemini-3.5-flash | 100% | 957 | 0.994 | 0.002 | 0.004 | 5.2 |
| opus-4.7 | 100% | 957 | 0.993 | 0.002 | 0.005 | 5.2 |
| sonnet-4.6 | 100% | 957 | 0.970 | 0.002 | 0.028 | 6.7 |
| deepseek-flash | 100% | 957 | 0.966 | 0.003 | 0.031 | 6.5 |
| gemma-4-31b | 100% | 957 | 0.963 | 0.002 | 0.034 | 4.8 |
| deepseek-v4-pro | 100% | 957 | 0.960 | 0.001 | 0.039 | 10.3 |
| gpt54-mini | 100% | 957 | 0.952 | 0.008 | 0.040 | 3.1 |
| qwen3.6-35b-a3b | 100% | 957 | 0.819 | 0.018 | 0.163 | 58.5 |
| glm-5.1 | 100% | 957 | 0.801 | 0.003 | 0.195 | 8.4 |
| typhoon25 | 100% | 957 | 0.775 | 0.032 | 0.192 | 30.9 |
| typhoon-s | 100% | 957 | 0.712 | 0.005 | 0.283 | 9.8 |
| openthaigpt | 100% | 957 | 0.701 | 0.007 | 0.292 | 19.1 |
| thalle | 100% | 957 | 0.701 | 0.005 | 0.294 | 17.1 |
| minimax-m2.7 | 100% | 957 | 0.661 | 0.003 | 0.335 | 12.5 |

### Per-class difficulty (pooled across all models)

Splits each class's failures into *detection* (missed) vs *correction* (wrong_corr) — the diagnostic axis.

| class | gold edits | fixed | wrong_corr | missed |
|---|--:|--:|--:|--:|
| 0 (unmapped) | 16 | 0.688 | 0.000 | 0.312 |
| 1 tone | 2480 | 0.906 | 0.008 | 0.085 |
| 2 consonant | 2160 | 0.879 | 0.006 | 0.115 |
| 3 การันต์ | 2640 | 0.887 | 0.010 | 0.103 |
| 4 vowel | 2816 | 0.863 | 0.002 | 0.134 |
| 5 cluster | 3280 | 0.876 | 0.006 | 0.118 |
| 6 loanword | 1920 | 0.810 | 0.003 | 0.186 |

### Item hardness (16 models scored)

How many models got each item *sentence-exact*. 0 = universally missed (intrinsically hard **or** suspect gold → audit); high = easy.

| #models correct | items |
|---:|---:|
| 1/16 | 1 |
| 2/16 | 2 |
| 3/16 | 2 |
| 4/16 | 4 |
| 5/16 | 5 |
| 6/16 | 4 |
| 7/16 | 21 |
| 8/16 | 12 |
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
| ∅→  | 180 |
|  →∅ | 53 |
| “→∅ | 46 |
|  →  | 40 |
| ”→" | 37 |
| “→" | 29 |
| ​→∅ | 17 |
| มั้ย→ไหม | 16 |
| ด้วย→∅ | 16 |
| ได้→∅ | 16 |
| ) →∅ | 14 |
| การ→∅ | 12 |
| ภาคม→จิกายน | 11 |
| )​ →∅ | 11 |
| การการ→การณ์ | 10 |

### Register effect (pooled correction recall)

| register | fixed/total | recall |
|---|--:|--:|
| encyclopedic | 2311/2816 | 0.821 |
| gov | 6254/7024 | 0.890 |
| news | 4795/5472 | 0.876 |

### Miscorrection examples (right site, wrong fix) — `src · gold · model`

**class 1 tone:** ไม๊ · ไหม · ไม่ ×5 | น๊ะ · นะ · น่ะ ×4 | ก้อ · ก็ · ∅ ×3 | ก้อ · ก็ ·  ก็ ×2 | ก้อ · ก็ · ก็จ ×1 | ก้อ · ก็ · มันก็ ×1
**class 2 consonant:** ส · ษ · ศ ×2 | ส · ษ · ข ×1 | ฑี · ที · ทีก ×1 | ศ · ษ · ข ×1 | ฏา · ฎา · ฎ ×1 | ฑี · ที · ที  ×1
**class 3 การันต์:** การณ์ · การ · การนี้ ×3 | การณ์ · การ · การฯ  ×3 | เท่ห์ · เท่ · เต ×2 | การณ์ · การ · การก ×2 | ดุลย์ · ดุล · ดุลย ×2 | การณ์ · การ · การ  ×2
**class 4 vowel:** ต · ติ · ติของ ×2 | ฉะเพาะ · เฉพาะ · โดยเฉพาะ ×2 | ธ · ธิ · ธิ  ×1 | ผะ · ผ · ภ ×1 | ส · สะ · รว ×1
**class 5 cluster:** มั๊ย · ไหม · มั้ย ×5 | เร · เล · เรื่อ ×3 | ฅ · ค · ว่า "นำเข้า" ซึ่งเป็นการสะกดผิด ต้องแก้เป็น "นำเข้า" แต่ในประโยคเดิมเขีย ×2 | ด · ติ · ติ  ×1 | ฆาร · ฆรา · คฤห ×1 | น · ล · ณ ×1
**class 6 loanword:** น๊ · น · น็ ×3 | ษ · ส · ส  ×3

## T2 — t2 (224 items)

### Failure decomposition (share of gold edits)

`fixed` = correct · `wrong_corr` = right site, wrong fix · `missed` = site untouched · `over/100` = spurious edits per 100 items (over-editing).

| model | cov | gold edits | fixed | wrong_corr | missed | over/100 |
|---|--:|--:|--:|--:|--:|--:|
| gemini-3.5-flash | 100% | 278 | 0.989 | 0.000 | 0.011 | 8.9 |
| opus-4.7 | 100% | 278 | 0.986 | 0.000 | 0.014 | 11.6 |
| gpt55-high | 100% | 278 | 0.982 | 0.000 | 0.018 | 6.2 |
| deepseek-v4-pro | 100% | 278 | 0.975 | 0.000 | 0.025 | 16.1 |
| gpt55-med | 100% | 278 | 0.975 | 0.000 | 0.025 | 8.9 |
| gemma-4-31b | 100% | 278 | 0.968 | 0.000 | 0.032 | 7.6 |
| deepseek-flash | 100% | 278 | 0.960 | 0.011 | 0.029 | 7.6 |
| sonnet-4.6 | 100% | 278 | 0.942 | 0.004 | 0.054 | 17.0 |
| gpt54-mini | 100% | 278 | 0.914 | 0.014 | 0.072 | 8.5 |
| glm-5.1 | 100% | 278 | 0.813 | 0.004 | 0.183 | 23.2 |
| typhoon25 | 100% | 278 | 0.777 | 0.029 | 0.194 | 81.2 |
| qwen3.6-35b-a3b | 100% | 278 | 0.755 | 0.022 | 0.223 | 267.9 |
| thalle | 100% | 278 | 0.691 | 0.007 | 0.302 | 77.7 |
| minimax-m2.7 | 100% | 278 | 0.651 | 0.007 | 0.342 | 18.8 |
| typhoon-s | 100% | 278 | 0.640 | 0.004 | 0.356 | 22.3 |
| openthaigpt | 100% | 278 | 0.590 | 0.004 | 0.406 | 109.8 |

### Per-class difficulty (pooled across all models)

Splits each class's failures into *detection* (missed) vs *correction* (wrong_corr) — the diagnostic axis.

| class | gold edits | fixed | wrong_corr | missed |
|---|--:|--:|--:|--:|
| 1 tone | 672 | 0.871 | 0.015 | 0.115 |
| 2 consonant | 592 | 0.887 | 0.000 | 0.113 |
| 3 การันต์ | 864 | 0.865 | 0.008 | 0.127 |
| 4 vowel | 960 | 0.870 | 0.001 | 0.129 |
| 5 cluster | 880 | 0.809 | 0.007 | 0.184 |
| 6 loanword | 480 | 0.790 | 0.010 | 0.200 |

### Item hardness (16 models scored)

How many models got each item *sentence-exact*. 0 = universally missed (intrinsically hard **or** suspect gold → audit); high = easy.

| #models correct | items |
|---:|---:|
| 1/16 | 3 |
| 4/16 | 3 |
| 5/16 | 4 |
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
| กะ→ก | 7 |
|  →- | 7 |
| -→– | 7 |
| ลิ→ลี | 6 |

### Register effect (pooled correction recall)

| register | fixed/total | recall |
|---|--:|--:|
| encyclopedic | 972/1232 | 0.789 |
| gov | 1461/1632 | 0.895 |
| news | 1350/1584 | 0.852 |

### Miscorrection examples (right site, wrong fix) — `src · gold · model`

**class 1 tone:** เง่า · เหง้า · ฐาน ×3 | ก้อ · ก็ ·  ก็ ×2 | ก้อ · ก็ · คือ ×1 | ก้อ · ก็ · กุ ×1 | เง่า · เหง้า · เหง่า ×1 | ก้อ · ก็ · ก็คือ ×1
**class 3 การันต์:** สิทธ์ · สิทธิ · สิทธี ×1 | การณ์ · การ · การ์ ×1 | การณ์ · การ · การ  ×1 | ยุทธิ์ · ยุทธ์ · ยุทธ์  ×1 | ดุลย์ · ดุล · ดุลย ×1 | การณ์ · การ · การน์ ×1
**class 4 vowel:** ตุ · ต · ต  ×1
**class 5 cluster:** เร · เล · เร่อ ×1 | ฅ · ค · ช ×1 | ฅ · ค ·  ค ×1 | ฅ · ค · คค ×1 | ค · ก · กรา ×1 | ฅ · ค · ขั ×1
**class 6 loanword:** ลิ๊งค์ · ลิงก์ · ลิ้งค์ ×2 | ลิ๊งค์ · ลิงก์ · ลิงค์ ×1 | ษ · ส · ส  ×1 | ค · ก · กรวมทั้ง ×1

## T3 — t3 (122 items)

### Failure decomposition (share of gold edits)

`fixed` = correct · `wrong_corr` = right site, wrong fix · `missed` = site untouched · `over/100` = spurious edits per 100 items (over-editing).

| model | cov | gold edits | fixed | wrong_corr | missed | over/100 |
|---|--:|--:|--:|--:|--:|--:|
| gpt55-high | 100% | 195 | 0.985 | 0.000 | 0.015 | 50.8 |
| opus-4.7 | 100% | 195 | 0.985 | 0.000 | 0.015 | 51.6 |
| gemini-3.5-flash | 100% | 195 | 0.979 | 0.005 | 0.015 | 62.3 |
| gpt55-med | 100% | 195 | 0.979 | 0.000 | 0.021 | 49.2 |
| gemma-4-31b | 100% | 195 | 0.969 | 0.005 | 0.026 | 29.5 |
| deepseek-flash | 100% | 195 | 0.954 | 0.005 | 0.041 | 50.0 |
| sonnet-4.6 | 100% | 195 | 0.954 | 0.000 | 0.046 | 57.4 |
| deepseek-v4-pro | 100% | 195 | 0.903 | 0.000 | 0.097 | 78.7 |
| gpt54-mini | 100% | 195 | 0.851 | 0.010 | 0.138 | 17.2 |
| glm-5.1 | 100% | 195 | 0.826 | 0.010 | 0.164 | 108.2 |
| qwen3.6-35b-a3b | 100% | 195 | 0.733 | 0.010 | 0.256 | 478.7 |
| typhoon25 | 100% | 195 | 0.692 | 0.015 | 0.292 | 191.8 |
| openthaigpt | 100% | 195 | 0.677 | 0.015 | 0.308 | 196.7 |
| thalle | 100% | 195 | 0.656 | 0.005 | 0.338 | 148.4 |
| typhoon-s | 100% | 195 | 0.641 | 0.005 | 0.354 | 68.9 |
| minimax-m2.7 | 100% | 195 | 0.436 | 0.000 | 0.564 | 66.4 |

### Per-class difficulty (pooled across all models)

Splits each class's failures into *detection* (missed) vs *correction* (wrong_corr) — the diagnostic axis.

| class | gold edits | fixed | wrong_corr | missed |
|---|--:|--:|--:|--:|
| 1 tone | 512 | 0.809 | 0.018 | 0.174 |
| 2 consonant | 416 | 0.822 | 0.010 | 0.168 |
| 3 การันต์ | 416 | 0.805 | 0.000 | 0.195 |
| 4 vowel | 608 | 0.831 | 0.002 | 0.168 |
| 5 cluster | 864 | 0.845 | 0.003 | 0.152 |
| 6 loanword | 304 | 0.829 | 0.000 | 0.171 |

### Item hardness (16 models scored)

How many models got each item *sentence-exact*. 0 = universally missed (intrinsically hard **or** suspect gold → audit); high = easy.

| #models correct | items |
|---:|---:|
| 1/16 | 2 |
| 2/16 | 2 |
| 3/16 | 1 |
| 4/16 | 8 |
| 5/16 | 8 |
| 6/16 | 6 |
| 7/16 | 7 |
| 8/16 | 9 |
| 9/16 | 20 |
| 10/16 | 14 |
| 11/16 | 8 |
| 12/16 | 18 |
| 13/16 | 7 |
| 14/16 | 4 |
| 15/16 | 2 |

### Top spurious over-edits (pooled `src→repl`)

| src→repl | count |
|---|--:|
| ∅→  | 470 |
|  →  | 95 |
|  →∅ | 89 |
| “→" | 50 |
| ”→" | 45 |
| ,→  | 32 |
| ∅→) | 31 |
| ​→∅ | 31 |
| เอม→เอ็ม | 26 |
| นึง→หนึ่ง | 22 |
| ค→ก | 17 |
| ชั่น→ชัน | 17 |
| ท→ต | 15 |
| ∅→ พ.ศ. | 14 |
| รี่→รี | 13 |

### Register effect (pooled correction recall)

| register | fixed/total | recall |
|---|--:|--:|
| encyclopedic | 726/944 | 0.769 |
| gov | 953/1088 | 0.876 |
| news | 899/1088 | 0.826 |

### Miscorrection examples (right site, wrong fix) — `src · gold · model`

**class 1 tone:** ไม๊ · ไหม · ไม้ ×3 | ก้อ · ก็ ·  ก็ ×2 | ก้อ · ก็ · ก็นำ ×1 | ไม๊ · ไหม · พืช ×1 | ก้อ · ก็ · ∅ ×1 | ไม๊ · ไหม · ไก่ ×1
**class 2 consonant:** ป · บ · พ ×1 | วงษ์ · วงศ์ · วงศ ×1 | ศ · ษ · ข ×1 | ฑี · ที · ฬิกา ×1
**class 4 vowel:** ต · ติ · ติ  ×1
**class 5 cluster:** ฅ · ค ·  ค ×2 | ฅ · ค · **ค ×1
