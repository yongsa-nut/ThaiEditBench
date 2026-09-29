"""Build the blind annotation sheets used in the label study (paper Section 3.7, Appendix E):
two raters see each marked span with its correction and answer error validity and mechanism class,
with no machine label shown.
"""
import sys, json, copy
from collections import Counter
from pathlib import Path

ANN = Path(__file__).resolve().parent
sys.path.insert(0, str(ANN))
from build_sheets import bundle  # noqa: E402

PER_CLASS = 10
STRIP = ("class", "class_name", "etymology", "edit_op")
OLD_INSTR = ("The class / etymology / edit type are <b>pre-filled</b> with our "
             "automatic guess — <b>confirm or override</b> each.")
NEW_INSTR = ("The mechanism class is <b>not pre-selected</b> — read the error and "
             "<b>choose the class yourself</b>.")

# class-only round: drop etymology/edit-op judging (edit-op is deterministic code
# output; etymology is a documented dictionary lookup — neither needs human alpha)
POST_REPLACEMENTS = [
    # relax completeness: accept + class only
    ("if(el.accept===true && (el.class==null||el.etymology==null||el.edit_op==null)) return false;",
     "if(el.accept===true && el.class==null) return false;"),
    # remove the two judged rows from the edit block
    ("""        <div class="row"><span class="rl">ที่มา · etymology</span><div class="pills">${etyBtns}</div></div>
        <div class="row"><span class="rl">การแก้ · edit op</span><div class="pills">${opBtns}</div></div>
""", ""),
    # start-screen task description
    ("For each sentence, confirm the spelling fix: is it a real orthographic error, "
     "what mechanism class, etymology, and edit type.",
     "For each sentence, judge the spelling fix: is it a real orthographic error, "
     "and which mechanism class (1–6)."),
    # enriched rubric: Thai explanations + worked examples per class,
    # absorption rule promoted to a check-first decision step
    ("""    <h4 style="margin:14px 0 4px">The 6 mechanism classes</h4>
    <ul style="margin:4px 0;padding-left:20px;font-size:.9rem;line-height:1.7">
      <li><b>1 วรรณยุกต์ (tone mark)</b> — wrong/extra/missing tone mark (่ ้ ๊ ๋) or ็</li>
      <li><b>2 พยัญชนะคู่ (consonant pair)</b> — homophonous consonant chosen wrong (ฎ/ฏ, ณ/น, ศ/ษ/ส, ท/ธ …)</li>
      <li><b>3 การันต์ (karan)</b> — spurious/missing/misplaced ์ on native or Pali-Sanskrit words</li>
      <li><b>4 สระ (vowel)</b> — wrong vowel, extra/missing vowel, long↔short (ิ/ี, ึ/ื, ุ/ู)</li>
      <li><b>5 สลับ/ควบ (cluster · metathesis)</b> — reordered letters, รร↔ัน, spurious/missing cluster consonant</li>
      <li><b>6 ทับศัพท์ (loanword)</b> — <b>any</b> error on a foreign loanword / proper noun (absorbs the mechanism)</li>
    </ul>
    <p style="font-size:.88rem;margin:10px 0 0"><b>Loanword-absorption rule:</b> if the word is a foreign loanword or proper noun (etymology = loan / proper-noun), the class is <b>6</b> regardless of which letter changed.</p>""",
     """    <h4 style="margin:14px 0 4px">ประเภทคำผิดทั้ง 6 (mechanism class)</h4>
    <p style="font-size:.88rem;margin:4px 0 10px;background:#fef3c7;border-radius:6px;padding:8px 12px"><b>เช็คข้อ 6 ก่อนเสมอ:</b> ถ้าคำที่ผิดเป็น<b>คำทับศัพท์ต่างประเทศยุคใหม่หรือชื่อเฉพาะต่างประเทศ</b> (เช่น กราฟิก ดิจิทัล ลิงก์ ชื่อคนหรือแบรนด์ฝรั่ง) ให้ตอบ <b>6</b> ทันที ไม่ว่าตัวที่ผิดจะเป็นวรรณยุกต์ สระ หรือการันต์ · ส่วนคำยืมเก่าแก่ (บาลี-สันสกฤต เขมร ฯลฯ เช่น กบฏ เกษตร) นับเป็นคำไทย ให้จำแนกตามข้อ 1–5 ตามปกติ</p>
    <ul style="margin:4px 0;padding-left:20px;font-size:.9rem;line-height:1.8">
      <li><b>1 วรรณยุกต์ (tone mark)</b> — รูปวรรณยุกต์ (่ ้ ๊ ๋) หรือไม้ไต่คู้ (็) เกิน ขาด หรือใช้ผิดรูป<br>
          <span style="color:#6b7280">ตัวอย่าง: ค๊ะ → คะ · น๊ะ → นะ · กระทั้ง → กระทั่ง · จั๊กจั่น → จักจั่น</span></li>
      <li><b>2 พยัญชนะพ้องเสียง (consonant pair)</b> — ใช้พยัญชนะผิดตัวในกลุ่มที่ออกเสียงเหมือนกัน (ส/ศ/ษ, ฎ/ฏ, ณ/น, ท/ธ …) เสียงอ่านไม่เปลี่ยน<br>
          <span style="color:#6b7280">ตัวอย่าง: กฏหมาย → กฎหมาย · กบฎ → กบฏ · อากาส → อากาศ</span></li>
      <li><b>3 การันต์ (silent consonant)</b> — ตัวการันต์ (…์) เกิน ขาด หรือผิดตำแหน่ง<br>
          <span style="color:#6b7280">ตัวอย่าง: กลยุทธ → กลยุทธ์ · ขาดดุลย์ → ขาดดุล · เท่ห์ → เท่</span></li>
      <li><b>4 สระ (vowel)</b> — รูปสระผิด เกิน หรือขาด รวมสระสั้น-ยาว (ิ/ี, ึ/ื, ุ/ู) และตำแหน่งสระ<br>
          <span style="color:#6b7280">ตัวอย่าง: สังเกตุ → สังเกต · มาตราฐาน → มาตรฐาน · ฉะเพาะ → เฉพาะ</span></li>
      <li><b>5 สลับ/ควบ (cluster · metathesis)</b> — ลำดับอักษรสลับกัน หรือพยัญชนะควบ/ร เกินหรือขาด (กระ↔กะ, รร↔ัน)<br>
          <span style="color:#6b7280">ตัวอย่าง: กระทันหัน → กะทันหัน · กระบังลม → กะบังลม</span></li>
      <li><b>6 ทับศัพท์ (loanword)</b> — คำผิด<b>ทุกแบบ</b>บนคำทับศัพท์ต่างประเทศยุคใหม่หรือชื่อเฉพาะ (ตามกฎด้านบน)<br>
          <span style="color:#6b7280">ตัวอย่าง: กราฟฟิค → กราฟิก · กงศุล → กงสุล · ลิ๊งค์ → ลิงก์</span></li>
    </ul>"""),
]

items = [json.loads(l) for l in (ANN / "alpha_set.jsonl").open(encoding="utf-8")]
mined = [it for it in items if it["source_track"] == "mined"]
syn = [it for it in items if it["source_track"] != "mined"]
cls = lambda it: it["edits"][0]["class"]

need = Counter()
for c in range(1, 7):
    need[c] = max(0, PER_CLASS - sum(1 for it in mined if cls(it) == c))
picked = []
for it in syn:                       # file order = deterministic subset of the 120
    if need[cls(it)] > 0:
        picked.append(it)
        need[cls(it)] -= 1
subset = [it for it in items if it in mined or it in picked]   # keep original interleaved order

print(f"blind set: {len(subset)} items = {len(mined)} mined + {len(picked)} synthetic")
tab = Counter((it["source_track"] == "mined", cls(it)) for it in subset)
for c in range(1, 7):
    print(f"  class {c}: mined {tab.get((True, c), 0):>2}  synth {tab.get((False, c), 0):>2}"
          f"  total {tab.get((True, c), 0) + tab.get((False, c), 0):>2}")

with (ANN / "alpha_set_blind.jsonl").open("w", encoding="utf-8") as f:
    for it in subset:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")

blinded = []
for it in subset:
    o = copy.deepcopy(it)
    o["edits"] = [{k: v for k, v in e.items() if k not in STRIP} for e in o["edits"]]
    blinded.append(o)
assert not any(k in e for it in blinded for e in it["edits"] for k in STRIP)

out = ANN / "dist_blind"
bundle(blinded, ["ann1", "ann2"], out)

for a in ("ann1", "ann2"):
    p = out / f"annotate_{a}.html"
    html = p.read_text(encoding="utf-8")
    if OLD_INSTR not in html:
        sys.exit(f"instruction sentence not found in {p.name} — template drift?")
    html = html.replace(OLD_INSTR, NEW_INSTR)
    for old, new in POST_REPLACEMENTS:
        if old not in html:
            sys.exit(f"patch target not found in {p.name}: {old[:60]!r}")
        html = html.replace(old, new)
    p.write_text(html, encoding="utf-8")
    baked = html.split("const BAKED_ITEMS = ", 1)[1].split(";\n", 1)[0]
    assert '"class"' not in baked and '"etymology"' not in baked, f"label leak in {p.name}!"
    assert "ที่มา · etymology" not in html and "การแก้ · edit op" not in html
    assert "(el.class==null||el.etymology==null||el.edit_op==null)" not in html
    print(f"  {p.name}: blinded OK, class-only UI, instruction swapped")
print("BLIND BUILD DONE")
