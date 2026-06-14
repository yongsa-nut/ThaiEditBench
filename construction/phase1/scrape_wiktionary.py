"""
Source 1 scraper: Thai Wiktionary misspelling appendix
  ภาคผนวก:รายชื่อคำในภาษาไทยที่มักเขียนผิด
RID-sourced, CC BY-SA. Table layout:
  col1 = คำที่เขียนถูก (correct, may list >1 acceptable form)
  col2 = มักเขียนผิดเป็น (comma-separated misspellings)
  col3 = หมายเหตุ (notes; often etymology / proper-noun hints)

Emits one (wrong, correct) pair per misspelling form ->
  phase1/data/wiktionary_pairs.jsonl
Fields: source, letter, correct, correct_alts, wrong, note
"""
import json
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "wiktionary_pairs.jsonl"
API = "https://th.wiktionary.org/w/api.php"
PAGE = "ภาคผนวก:รายชื่อคำในภาษาไทยที่มักเขียนผิด"
UA = "ThaiEditBench-research/0.1 (academic; anonymous@example.com)"

LINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]")
TEMPLATE_RE = re.compile(r"\{\{[^}]*\}\}")
TAG_RE = re.compile(r"<[^>]+>")


def clean(cell: str) -> str:
    cell = TEMPLATE_RE.sub("", cell)
    cell = LINK_RE.sub(r"\1", cell)
    cell = cell.replace("'''", "").replace("''", "")
    cell = TAG_RE.sub(" ", cell)          # <br> etc.
    cell = cell.replace("&nbsp;", " ")
    return cell.strip(" \t|")


def fetch_wikitext() -> str:
    p = {"action": "parse", "page": PAGE, "prop": "wikitext",
         "format": "json", "formatversion": "2"}
    r = requests.get(API, params=p, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.json()["parse"]["wikitext"]


def parse(wt: str):
    rows = []
    letter = ""
    for line in wt.splitlines():
        s = line.strip()
        m = re.match(r"==\s*(.+?)\s*==", s)
        if m:
            letter = m.group(1)
            continue
        if not s.startswith("|") or s.startswith("|-") or s.startswith("|+"):
            continue
        if "||" not in s:
            continue
        cells = s.lstrip("|").split("||")
        if len(cells) < 2:
            continue
        correct_raw = clean(cells[0])
        wrong_raw = clean(cells[1])
        note = clean(cells[2]) if len(cells) >= 3 else ""
        if not correct_raw or not wrong_raw:
            continue
        # correct may list multiple acceptable forms
        correct_forms = [c.strip() for c in re.split(r"[,，]", correct_raw) if c.strip()]
        correct = correct_forms[0]
        correct_alts = correct_forms[1:]
        for w in re.split(r"[,，]", wrong_raw):
            w = w.strip()
            if not w or w.startswith("-"):   # shared-suffix abbreviations -> skip (flag-worthy)
                continue
            rows.append(dict(source="wiktionary", letter=letter, correct=correct,
                             correct_alts=correct_alts, wrong=w, note=note))
    return rows


def main():
    wt = fetch_wikitext()
    rows = parse(wt)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    uniq_correct = len({r["correct"] for r in rows})
    print(f"parsed {len(rows)} (wrong,correct) pairs across {uniq_correct} correct headwords")
    print(f"-> {OUT}")
    for r in rows[:8]:
        print(f"  {r['wrong']} -> {r['correct']}   [{r['letter']}] {r['note'][:40]}")


if __name__ == "__main__":
    main()
