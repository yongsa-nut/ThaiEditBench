"""
Source 5 PILOT (not the full mine -- Check-in 1 decision; full pipeline is
Phase 4 §6a). Validates the JWTD-style Thai-Wikipedia approach end-to-end:
  1. scan recentchanges (ns0) for edits whose summary matches a typo-fix
     keyword (แก้คำผิด / พิมพ์ผิด / สะกดผิด / แก้ตัวสะกด / แก้คำเขียนผิด)
  2. for each, action=compare the revision vs its parent
  3. pull inline <del class="diffchange">X</del> / <ins>Y</ins> single-word pairs
  4. classify + dedup; report yield + diff-shape to size the Phase-4 mine.

Output: phase1/data/wiki_pilot_pairs.jsonl  (+ stats)
"""
import json
import re
import sys
import time
from collections import Counter
from html import unescape
from pathlib import Path

import requests

from classify import classify, normalize

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "wiki_pilot_pairs.jsonl"
API = "https://th.wikipedia.org/w/api.php"
UA = "ThaiEditBench-research/0.1 (academic; anonymous@example.com)"
KEYWORDS = ["แก้คำผิด", "พิมพ์ผิด", "สะกดผิด", "แก้ตัวสะกด", "แก้คำเขียนผิด", "คำผิด"]
S = requests.Session()
S.headers["User-Agent"] = UA

DEL = re.compile(r'<del class="diffchange[^"]*">(.*?)</del>', re.S)
INS = re.compile(r'<ins class="diffchange[^"]*">(.*?)</ins>', re.S)
STRIP = re.compile(r"<[^>]+>")
THAI = re.compile(r"[฀-๿]")


def scan_candidates(target=120, max_changes=12000):
    """Return [(revid, parentid, comment)] for typo-fix edits."""
    cands, scanned, cont = [], 0, {}
    while len(cands) < target and scanned < max_changes:
        p = {"action": "query", "list": "recentchanges", "rcnamespace": "0",
             "rctype": "edit", "rcprop": "ids|comment|timestamp",
             "rclimit": "500", "format": "json", "formatversion": "2"}
        p.update(cont)
        r = S.get(API, params=p, timeout=30).json()
        for rc in r.get("query", {}).get("recentchanges", []):
            scanned += 1
            c = rc.get("comment", "")
            if any(k in c for k in KEYWORDS) and rc.get("old_revid"):
                cands.append((rc["revid"], rc["old_revid"], c))
        if "continue" in r:
            cont = r["continue"]
        else:
            break
    return cands, scanned


def diff_pairs(parentid, revid):
    p = {"action": "compare", "fromrev": parentid, "torev": revid,
         "prop": "diff", "format": "json", "formatversion": "2"}
    try:
        r = S.get(API, params=p, timeout=30).json()
    except Exception:
        return []
    html = r.get("compare", {}).get("body", "")
    dels = [unescape(STRIP.sub("", x)).strip() for x in DEL.findall(html)]
    inss = [unescape(STRIP.sub("", x)).strip() for x in INS.findall(html)]
    pairs = []
    for w, c in zip(dels, inss):     # positional pairing of inline changes
        if w and c and w != c and " " not in w and " " not in c \
                and THAI.search(w) and THAI.search(c) and max(len(w), len(c)) <= 30:
            pairs.append((normalize(w), normalize(c)))
    return pairs


def main():
    cands, scanned = scan_candidates()
    print(f"scanned {scanned} recent edits -> {len(cands)} typo-fix candidates "
          f"({len(cands)/max(scanned,1):.2%} hit rate)")
    pairs = Counter()
    for i, (rev, par, _c) in enumerate(cands):
        for pr in diff_pairs(par, rev):
            pairs[pr] += 1
        if i % 20 == 0:
            time.sleep(0.3)
    rows, cls = [], Counter()
    for (w, c), f in pairs.items():
        res = classify(w, c, etymology="native")
        cls[res["primary_class"]] += 1
        rows.append(dict(source="wiki_pilot", wrong=w, correct=c, freq=f,
                         mechanism_class=res["primary_class"], flag=res["flag"],
                         mechanism_detail=res["mechanism_detail"]))
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"extracted {len(rows)} unique (wrong,correct) pilot pairs")
    print("class distribution:", {k: cls[k] for k in sorted(cls)})
    print("examples:")
    for r in sorted(rows, key=lambda x: -x["freq"])[:20]:
        print(f"  {r['wrong']} -> {r['correct']}  cls={r['mechanism_class']} (freq {r['freq']})")


if __name__ == "__main__":
    main()
