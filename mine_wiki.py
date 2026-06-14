"""
Phase 4a — Thai-Wikipedia revision mining (JWTD-style), bot/editor-history driven.

The Phase-1 pilot drove from `recentchanges` (recency-capped -> ~10 noisy pairs).
Here we drive from `usercontribs` of the most prolific TYPO-FIX editors, which is
NOT recency-capped and spans years. High precision comes from the edit-summary
keyword filter (แก้คำผิด / พิมพ์ผิด / สะกดผิด / …) — the same signal the
`บอตแก้คำผิด` workflow uses.

Two stages:
  1. discover_typo_editors() — scan recentchanges to TALLY who fixes typos
     (uses recentchanges only to find usernames, then mines their full history).
  2. mine_user() — page usercontribs (ns0), and for each keyword-matching edit,
     action=compare rev<->parent, extract single-token Thai del/ins pairs PLUS
     the surrounding changed line as context (so 4c can rebuild a sentence item).

Output: data/wiki_raw_pairs.jsonl  — {wrong, correct, wrong_line, correct_line,
        article, title, revid, parentid, comment}
Run:  PYTHONUTF8=1 python mine_wiki.py [--max-users 6] [--max-contribs 4000]
"""
import argparse
import json
import re
import time
from collections import Counter
from html import unescape
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
OUT = DATA / "wiki_raw_pairs.jsonl"

API = "https://th.wikipedia.org/w/api.php"
UA = "ThaiEditBench-research/0.1 (academic; anonymous@example.com)"
# เก็บกวาด = the "cleanup" summary BotKung uses when running the systematic typo-fix
# regex patterns (the บอตแก้คำผิด workflow). The RID gate downstream keeps only real
# word-level typo pairs, so the broader keyword is safe.
KEYWORDS = ["แก้คำผิด", "พิมพ์ผิด", "สะกดผิด", "แก้ตัวสะกด", "แก้คำเขียนผิด", "คำผิด", "เก็บกวาด"]
S = requests.Session(); S.headers["User-Agent"] = UA

DEL = re.compile(r'<del class="diffchange[^"]*">(.*?)</del>', re.S)
INS = re.compile(r'<ins class="diffchange[^"]*">(.*?)</ins>', re.S)
ADDED = re.compile(r'<td[^>]*class="diff-addedline[^"]*"[^>]*>(.*?)</td>', re.S)
DELETED = re.compile(r'<td[^>]*class="diff-deletedline[^"]*"[^>]*>(.*?)</td>', re.S)
STRIP = re.compile(r"<[^>]+>")
THAI = re.compile(r"[฀-๿]")


def get(params, tries=4):
    last = None
    for k in range(tries):
        try:
            r = S.get(API, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
        except Exception as e:                       # noqa
            last = repr(e)
        time.sleep(1.5 * (k + 1))
    return {"_error": last}


def has_kw(comment):
    return any(k in (comment or "") for k in KEYWORDS)


def discover_typo_editors(scan=20000, top=6):
    """Tally usernames behind keyword-matching ns0 edits in recentchanges."""
    users, scanned, cont = Counter(), 0, {}
    while scanned < scan:
        p = {"action": "query", "list": "recentchanges", "rcnamespace": "0",
             "rctype": "edit", "rcprop": "user|comment|ids", "rclimit": "500",
             "format": "json", "formatversion": "2"}
        p.update(cont)
        r = get(p)
        rcs = r.get("query", {}).get("recentchanges", [])
        if not rcs:
            break
        for rc in rcs:
            scanned += 1
            if has_kw(rc.get("comment", "")) and rc.get("user"):
                users[rc["user"]] += 1
        if "continue" in r:
            cont = r["continue"]
        else:
            break
    print(f"  discovery: scanned {scanned} edits; typo-fixers = {users.most_common(top)}")
    return [u for u, _ in users.most_common(top)]


def line_text(td_html):
    return unescape(STRIP.sub("", td_html)).strip()


def compare_pairs(parentid, revid):
    """Single-token Thai del/ins pairs + the changed lines as context."""
    r = get({"action": "compare", "fromrev": parentid, "torev": revid,
             "prop": "diff", "format": "json", "formatversion": "2"})
    html = r.get("compare", {}).get("body", "")
    if not html:
        return []
    dels = [unescape(STRIP.sub("", x)).strip() for x in DEL.findall(html)]
    inss = [unescape(STRIP.sub("", x)).strip() for x in INS.findall(html)]
    del_lines = [line_text(x) for x in DELETED.findall(html)]
    add_lines = [line_text(x) for x in ADDED.findall(html)]
    pairs = []
    for k, (w, c) in enumerate(zip(dels, inss)):
        if not (w and c and w != c):
            continue
        if " " in w or " " in c:
            continue
        if not (THAI.search(w) and THAI.search(c)):
            continue
        if max(len(w), len(c)) > 30:
            continue
        wl = del_lines[k] if k < len(del_lines) else ""
        cl = add_lines[k] if k < len(add_lines) else ""
        pairs.append((w, c, wl, cl))
    return pairs


def mine_user(user, max_contribs):
    rows, cont, fetched = [], {}, 0
    while fetched < max_contribs:
        p = {"action": "query", "list": "usercontribs", "ucuser": user,
             "ucnamespace": "0", "ucprop": "ids|title|comment|flags",
             "uclimit": "500", "format": "json", "formatversion": "2"}
        p.update(cont)
        r = get(p)
        contribs = r.get("query", {}).get("usercontribs", [])
        if not contribs:
            break
        for ct in contribs:
            fetched += 1
            if not has_kw(ct.get("comment", "")) or not ct.get("parentid"):
                continue
            for (w, c, wl, cl) in compare_pairs(ct["parentid"], ct["revid"]):
                rows.append({"wrong": w, "correct": c, "wrong_line": wl,
                             "correct_line": cl, "article": ct.get("title", ""),
                             "title": ct.get("title", ""), "revid": ct["revid"],
                             "parentid": ct["parentid"], "comment": ct.get("comment", ""),
                             "user": user})
            time.sleep(0.05)
        if "continue" in r:
            cont = r["continue"]
        else:
            break
        print(f"    {user}: scanned {fetched} contribs -> {len(rows)} raw pairs")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-users", type=int, default=6)
    ap.add_argument("--max-contribs", type=int, default=4000)
    ap.add_argument("--users", nargs="*", default=None, help="override discovery")
    args = ap.parse_args()

    users = args.users or discover_typo_editors(top=args.max_users)
    print(f"Mining usercontribs of: {users}")
    all_rows = []
    for u in users:
        all_rows.extend(mine_user(u, args.max_contribs))
        with OUT.open("w", encoding="utf-8") as f:    # incremental: persist after each user
            for r in all_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  [persisted {len(all_rows)} raw pairs after {u}]")
    print(f"\nwrote {len(all_rows)} raw pairs -> {OUT.name}")


if __name__ == "__main__":
    main()
