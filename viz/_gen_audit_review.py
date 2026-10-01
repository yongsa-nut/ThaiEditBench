"""One-off: dump T2/T3 residual-source-typo candidates for human review,
with localized (difflib) diffs + context, register-normalization auto-flag.
Shared-misses (consensus == text_wrong) and punct-only over-edits are excluded
(gold is fine in those). Run: PYTHONUTF8=1 python viz/_gen_audit_review.py"""
import json, sys, glob, os, difflib
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDIT = HERE.parent
sys.path.insert(0, str(EDIT))
from inject import normalize
from variants import reconcile_variants

PUNCT = set(' \t“”"\'`.,!?()[]{}:;…-–—/')
def is_punct(s): return s != "" and all(c in PUNCT for c in s)

# informal -> formal register normalizations: if gold keeps the informal form,
# gold is CORRECT (the task forbids normalization) and the item should be KEPT.
NORM = [("เค้า", "เขา"),   # เค้า -> เขา
        ("มั้ย", "ไหม"),   # มั้ย -> ไหม
        ("มั๊ย", "ไหม"),   # มั๊ย -> ไหม
        ("ก้อ", "ก็"),               # ก้อ -> ก็
        ("เนี่ย", "นี่")]  # เนี่ย -> นี่

# loanword spelling variants: both forms are in use (RID prefers the consensus
# form). Candidate for variant-reconciliation rather than a hard drop.
LOANVAR = [("ดิจิตอล", "ดิจิทัล"),
           ("ออร์แกนิค", "ออร์แกนิก")]

def variant_flag(gold, cons):
    for a, b in LOANVAR:
        if a in gold and b in cons and a not in cons:
            return f"{a} -> {b}"
    return None

def _lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def localized(gold, cons, win=30):
    sm = difflib.SequenceMatcher(None, gold, cons, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        out.append((gold[max(0, i1-win):i1], gold[i1:i2], cons[j1:j2], gold[i2:i2+win]))
    return out

def norm_flag(gold, cons):
    for inf, fo in NORM:
        if inf in gold and fo in cons and inf not in cons:
            return f"{inf} -> {fo}"
    return None

def run(resdir, split, n, label):
    p0 = EDIT / resdir
    items = {json.loads(l)["id"]: json.loads(l)
             for l in (p0 / f"_sample_{split}_{n}.jsonl").open(encoding="utf-8")}
    runs = {}
    for p in glob.glob(str(p0 / "*.jsonl")):
        if os.path.basename(p).startswith("_"):
            continue
        rows = {r["id"]: (r.get("output") or "")
                for r in (json.loads(x) for x in open(p, encoding="utf-8"))}
        if len(rows) >= len(items):
            runs[os.path.basename(p)[:-6]] = rows
    full = list(runs)
    cand = []
    for iid, it in items.items():
        goldn = normalize(it["text_correct"]); wrongn = normalize(it["text_wrong"])
        votes = Counter()
        for m in full:
            o = runs[m].get(iid, "")
            rec = normalize(reconcile_variants(o, it["text_correct"])) if o else wrongn
            votes[rec] += 1
        nongold = sorted(((v, k) for k, v in votes.items() if k != goldn), reverse=True)
        if not nongold:
            continue
        cnt, val = nongold[0]; gv = votes.get(goldn, 0)
        if not (cnt >= 3 and cnt >= gv):
            continue
        if val == wrongn:                     # shared miss -> gold OK
            continue
        blocks = localized(goldn, val)
        if all(is_punct(g) or is_punct(c) for _, g, c, _ in blocks):  # punct only -> gold OK
            continue
        nf, vf = norm_flag(goldn, val), variant_flag(goldn, val)
        if _lev(wrongn, val) + _lev(val, goldn) == _lev(wrongn, goldn):
            disp, reason = "keep", "partial fix toward the gold (shared miss)"
        elif nf:
            disp, reason = "drop", f"register change ({nf})"
        elif vf:
            disp, reason = "variant", f"loanword variant ({vf})"
        else:
            disp, reason = "drop", "residual source typo"
        cand.append(dict(cnt=cnt, gv=gv, iid=iid, it=it, blocks=blocks, disp=disp, reason=reason))
    cand.sort(key=lambda r: (-(r["cnt"]-r["gv"]), -r["cnt"]))
    return dict(label=label, items=len(items), full=len(full), cand=cand)


def write_md(tiers, path):
    out = ["# T2/T3 consensus-audit report", "",
           "Flagged items whose consensus equals the input or differs from the gold only in punctuation are kept and not listed.",
           "Each listed item: **N systems** agree on an output the gold lacks (N vs systems returning the gold).",
           "Items marked KEEP are partial fixes toward the gold; every other listed item is dropped by the audit rule.",
           "`⟦gold→cons⟧` = differing span + context.", ""]
    for i, t in enumerate(tiers):
        if i:
            out += ["", "---", ""]
        out.append(f"## {t['label']} — {len(t['cand'])} candidates (of {t['items']})  [full models={t['full']}]")
        out.append("")
        for c in t["cand"]:
            tag = "" if c["disp"] == "drop" else f"  ⚠ {c['reason']} — KEEP"
            out.append(f"### {c['iid']}  [{c['cnt']} vs {c['gv']}]  "
                       f"{c['it'].get('register','')}/{c['it'].get('source_doc','?')}{tag}")
            for pre, g, cc, post in c["blocks"]:
                out.append(f"- …{pre}⟦ gold:`{g or '∅'}` → cons:`{cc or '∅'}` ⟧{post}…")
            out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_html(tiers, path):
    DISP = {"drop": ("DROP", "#c0392b"), "keep": ("KEEP", "#27ae60"), "variant": ("VARIANT?", "#e67e22")}
    cards = []
    counts = {"drop": 0, "keep": 0, "variant": 0}
    for t in tiers:
        cards.append(f'<h2>{esc(t["label"])} <span class="sub">{len(t["cand"])} candidates of {t["items"]} · {t["full"]} models</span></h2>')
        for c in t["cand"]:
            counts[c["disp"]] += 1
            label, col = DISP[c["disp"]]
            diffs = []
            for pre, g, cc, post in c["blocks"]:
                gpart = f'<span class="g">{esc(g)}</span>' if g else '<span class="nil">∅</span>'
                cpart = f'<span class="c">{esc(cc)}</span>' if cc else '<span class="nil">∅</span>'
                diffs.append(f'<div class="diff">…<span class="ctx">{esc(pre)}</span>'
                             f'<span class="br">⟦</span>{gpart} <span class="arr">→</span> {cpart}'
                             f'<span class="br">⟧</span><span class="ctx">{esc(post)}</span>…</div>')
            it = c["it"]
            cards.append(
                f'<div class="card" data-disp="{c["disp"]}" style="border-left-color:{col}">'
                f'<div class="hd"><span class="iid">{esc(c["iid"])}</span>'
                f'<span class="votes">{c["cnt"]} vs {c["gv"]}</span>'
                f'<span class="badge" style="background:{col}">{label}</span>'
                f'<span class="reason">{esc(c["reason"])}</span>'
                f'<span class="src">{esc(it.get("register",""))} · {esc(it.get("source_doc","?"))}</span></div>'
                + "".join(diffs) + '</div>')
    html = f"""<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ThaiEditBench — T2/T3 Gold Audit</title>
<style>
:root{{--bg:#0f1115;--card:#1a1d24;--ink:#e6e6e6;--mut:#8a93a3;}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:"Sarabun","Noto Sans Thai",system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.7}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px}}
h1{{font-size:22px;margin:0 0 4px}}
.lead{{color:var(--mut);font-size:14px;margin:0 0 16px}}
.legend{{font-size:13px;color:var(--mut);margin-bottom:16px}}
.g{{color:#ff7b72;text-decoration:line-through;font-weight:600}}
.c{{color:#7ee787;font-weight:600}}
.nil{{color:#6b7280;font-style:italic}}
.bar{{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid #2a2f3a;z-index:5;margin-bottom:12px}}
.bar button{{background:#222633;color:var(--ink);border:1px solid #333a48;border-radius:6px;padding:6px 12px;margin-right:6px;cursor:pointer;font-size:13px}}
.bar button.on{{background:#2f6feb;border-color:#2f6feb}}
.cnt{{color:var(--mut);font-size:13px;margin-left:8px}}
h2{{font-size:17px;margin:22px 0 10px;border-bottom:1px solid #2a2f3a;padding-bottom:6px}}
h2 .sub{{font-size:13px;color:var(--mut);font-weight:400}}
.card{{background:var(--card);border:1px solid #262b35;border-left:5px solid;border-radius:8px;padding:12px 14px;margin:10px 0}}
.hd{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:8px;font-size:13px}}
.iid{{font-family:ui-monospace,monospace;color:#9ecbff;font-weight:600}}
.votes{{font-family:ui-monospace,monospace;color:var(--mut)}}
.badge{{color:#fff;border-radius:5px;padding:1px 8px;font-size:11px;font-weight:700;letter-spacing:.4px}}
.reason{{color:var(--mut)}}
.src{{margin-left:auto;font-size:12px;color:var(--mut);max-width:48%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.diff{{font-size:17px;padding:3px 0}}
.ctx{{color:#aab2c0}}
.br{{color:#566c86;margin:0 2px}}
.arr{{color:var(--mut);margin:0 4px}}
</style></head><body><div class="wrap">
<h1>ThaiEditBench — T2/T3 Gold Audit (residual source-typo candidates)</h1>
<p class="lead">Cross-model consensus audit; flagged items that are shared misses or punctuation-only differences are kept and not listed.
<span class="g">red strike</span> = current gold · <span class="c">green</span> = what ≥N models converge on.</p>
<div class="legend"><b style="color:#ff7b72">DROP</b> = dropped by the audit rule ·
<b style="color:#27ae60">KEEP</b> = partial fix toward the gold (gold correct) ·
<b style="color:#e67e22">VARIANT?</b> = loanword variant (also dropped by the rule)</div>
<div class="bar">
<button data-f="all" class="on" onclick="flt(this)">All</button>
<button data-f="drop" onclick="flt(this)">DROP only</button>
<button data-f="keep" onclick="flt(this)">KEEP</button>
<button data-f="variant" onclick="flt(this)">VARIANT?</button>
<span class="cnt">{counts['drop']} drop · {counts['keep']} keep · {counts['variant']} variant?</span>
</div>
{''.join(cards)}
</div>
<script>
function flt(b){{
  document.querySelectorAll('.bar button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); var f=b.dataset.f;
  document.querySelectorAll('.card').forEach(c=>{{
    c.style.display=(f==='all'||c.dataset.disp===f)?'':'none';
  }});
}}
</script></body></html>"""
    path.write_text(html, encoding="utf-8")


tiers = [run("results_t3", "t3", 150, "T3 page"),
         run("results_t2", "t2", 250, "T2 paragraph")]
write_md(tiers, EDIT / "viz" / "audit-review-t2t3.md")
write_html(tiers, EDIT / "viz" / "audit-review-t2t3.html")
for t in tiers:
    d = sum(1 for c in t["cand"] if c["disp"] == "drop")
    k = sum(1 for c in t["cand"] if c["disp"] == "keep")
    v = sum(1 for c in t["cand"] if c["disp"] == "variant")
    print(f"{t['label']}: {len(t['cand'])} cand -> {d} drop, {k} keep(register), {v} variant?")
print("wrote viz/audit-review-t2t3.md + .html")
