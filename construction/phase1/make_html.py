"""
Render error-corpus-inventory.jsonl into a self-contained interactive HTML
viewer (error-corpus-inventory.html): all 1,080 pairs with class/etymology/
source/flag filters + free-text search + live stats. Data is embedded inline.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INV = HERE.parent / "error-corpus-inventory.jsonl"
OUT = HERE.parent / "error-corpus-inventory.html"

rows = [json.loads(l) for l in INV.read_text(encoding="utf-8").splitlines()]
# slim payload
slim = [dict(w=r["wrong"], c=r["correct"], cls=r["mechanism_class"],
             et=r["etymology"], also=r["also_hits"], src=r["sources"],
             ctx=r["context_dependent"], clean=r["clean_v1"],
             fr=r["filter_reason"], flag=r["flag"] or "",
             d=r["mechanism_detail"], note=r["note"][:120]) for r in rows]
DATA = json.dumps(slim, ensure_ascii=False)

HTML = """<!DOCTYPE html>
<html lang="th"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EditingBench — Error-Corpus Inventory</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Sarabun:wght@400;600;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter','Sarabun',sans-serif;background:#0f172a;color:#e2e8f0;padding:1.5rem 2rem;line-height:1.5}
h1{font-size:1.5rem;color:#f1f5f9}
.sub{color:#94a3b8;font-size:.85rem;margin:.3rem 0 1rem}
.bar{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.75rem;align-items:center}
.pill{padding:.35rem .8rem;border-radius:7px;font-weight:600;font-size:.8rem;cursor:pointer;border:2px solid transparent;user-select:none}
.pill.active{border-color:#f1f5f9}
.pill.all{background:#334155;color:#e2e8f0}
.c1{background:#fee2e2;color:#991b1b}.c2{background:#dbeafe;color:#1e40af}.c3{background:#fef3c7;color:#92400e}
.c4{background:#d1fae5;color:#065f46}.c5{background:#ede9fe;color:#5b21b6}.c6{background:#fce7f3;color:#9d174d}.c0{background:#e2e8f0;color:#475569}
input,select{background:#1e293b;color:#e2e8f0;border:1px solid #475569;border-radius:6px;padding:.35rem .6rem;font-size:.85rem;font-family:inherit}
label.chk{font-size:.8rem;color:#cbd5e1;display:inline-flex;align-items:center;gap:.3rem;cursor:pointer}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{position:sticky;top:0;background:#1e293b;text-align:left;padding:.5rem;color:#94a3b8;font-size:.75rem;text-transform:uppercase;border-bottom:1px solid #334155}
td{padding:.45rem .5rem;border-bottom:1px solid #1e293b;vertical-align:top}
tr:hover td{background:#1e293b}
.w{font-family:'Sarabun';font-size:1.05rem;font-weight:700;color:#f87171;text-decoration:line-through;text-decoration-color:rgba(248,113,113,.4)}
.cor{font-family:'Sarabun';font-size:1.05rem;font-weight:700;color:#34d399}
.badge{display:inline-block;min-width:1.4rem;text-align:center;padding:.1rem .4rem;border-radius:5px;font-weight:700;font-size:.8rem}
.et{font-size:.75rem;color:#cbd5e1;background:#334155;padding:.05rem .4rem;border-radius:4px}
.tag{font-size:.68rem;padding:.05rem .35rem;border-radius:4px;margin-right:.25rem}
.tag.ctx{background:#7c2d12;color:#fed7aa}.tag.dirty{background:#3f3f46;color:#d4d4d8}.tag.flag{background:#581c87;color:#e9d5ff}
.det{font-size:.75rem;color:#94a3b8}
.src{font-size:.7rem;color:#64748b}
a{color:#60a5fa;text-decoration:none}
#count{color:#94a3b8;font-size:.8rem;margin-left:auto}
</style></head><body>
<h1>EditingBench — Error-Corpus Inventory <span style="font-weight:400;color:#64748b;font-size:1rem">(Phase 1 · Sources 1–2 · RID-backed)</span></h1>
<p class="sub">__N__ pairs. Click a class to filter; combine with etymology / source / flags / search. Wrong → correct; class 0 = unclassified. v2-routed pairs tagged <span class="tag ctx">ctx</span>, non-v1 tagged <span class="tag dirty">filtered</span>.</p>
<div class="bar" id="classBar"></div>
<div class="bar">
  <select id="etym"><option value="">all etymology</option><option>native</option><option>loan</option><option>proper-noun</option></select>
  <select id="src"><option value="">all sources</option><option>wiktionary</option><option>botfix</option></select>
  <input id="q" placeholder="search wrong / correct…" style="min-width:220px">
  <label class="chk"><input type="checkbox" id="ctxOnly">context-dep (v2)</label>
  <label class="chk"><input type="checkbox" id="flagOnly">flagged</label>
  <label class="chk"><input type="checkbox" id="dirtyOnly">needs-filtering</label>
  <span id="count"></span>
</div>
<table><thead><tr><th>wrong</th><th></th><th>correct</th><th>cls</th><th>etym</th><th>tags</th><th>mechanism</th><th>note</th><th>src</th></tr></thead>
<tbody id="tb"></tbody></table>
<script>
const DATA=__DATA__;
const CN={0:'c0',1:'c1',2:'c2',3:'c3',4:'c4',5:'c5',6:'c6'};
const CNAME={0:'unclassified',1:'tone',2:'consonant',3:'การันต์',4:'vowel',5:'cluster',6:'loanword'};
let fCls='all';
const classBar=document.getElementById('classBar');
function counts(){const m={all:DATA.length};for(let k=0;k<=6;k++)m[k]=0;DATA.forEach(r=>m[r.cls]++);return m}
function drawBar(){const m=counts();let h=`<div class="pill all ${fCls==='all'?'active':''}" data-k="all">All (${m.all})</div>`;
for(let k=1;k<=6;k++)h+=`<div class="pill ${CN[k]} ${fCls==k?'active':''}" data-k="${k}">${k} ${CNAME[k]} (${m[k]})</div>`;
h+=`<div class="pill c0 ${fCls==0?'active':''}" data-k="0">0 ? (${m[0]})</div>`;classBar.innerHTML=h;
classBar.querySelectorAll('.pill').forEach(p=>p.onclick=()=>{fCls=p.dataset.k;drawBar();render()})}
function render(){const et=document.getElementById('etym').value,sc=document.getElementById('src').value,
q=document.getElementById('q').value.trim(),cx=document.getElementById('ctxOnly').checked,
fl=document.getElementById('flagOnly').checked,dy=document.getElementById('dirtyOnly').checked;
let rows=DATA.filter(r=>(fCls==='all'||r.cls==fCls)&&(!et||r.et===et)&&(!sc||r.src.includes(sc))
&&(!q||r.w.includes(q)||r.c.includes(q))&&(!cx||r.ctx)&&(!fl||r.flag)&&(!dy||!r.clean));
document.getElementById('count').textContent=rows.length+' shown';
const tb=document.getElementById('tb');tb.innerHTML=rows.map(r=>{
let tags='';if(r.ctx)tags+='<span class="tag ctx">ctx→v2</span>';if(!r.clean)tags+=`<span class="tag dirty">${r.fr.split(' ')[0]}</span>`;if(r.flag)tags+=`<span class="tag flag">${r.flag}</span>`;
const also=r.also&&r.also.length?` <span class="src">+${r.also.join('+')}</span>`:'';
return `<tr><td><span class="w">${r.w}</span></td><td style="color:#475569">→</td><td><span class="cor">${r.c}</span></td>
<td><span class="badge ${CN[r.cls]}">${r.cls}</span>${also}</td><td><span class="et">${r.et}</span></td>
<td>${tags}</td><td class="det">${r.d}</td><td class="det">${r.note||''}</td><td class="src">${r.src.join(',')}</td></tr>`}).join('')}
['etym','src','q','ctxOnly','flagOnly','dirtyOnly'].forEach(id=>{const e=document.getElementById(id);e.oninput=render;e.onchange=render});
drawBar();render();
</script></body></html>"""

OUT.write_text(HTML.replace("__DATA__", DATA).replace("__N__", str(len(rows))),
               encoding="utf-8")
print(f"wrote {OUT} ({len(rows)} pairs embedded, {OUT.stat().st_size//1024} KB)")
