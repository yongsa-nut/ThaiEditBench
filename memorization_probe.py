"""
Phase 4 — verbatim-completion memorization probe (anti-contamination diagnostic).

EditingBench's injection track is structurally contamination-robust: the corrupted
input is novel, and memorizing the correct original only HELPS a model produce the
correct answer (the measured skill). The residual risk is *generalization optimism*
on heavily-memorized clean text, which would bite the private split.

This probe QUANTIFIES per-source memorization so 4c can route the most-memorized
sentences out of test_private with evidence. For each clean sentence we feed a model
the first half and measure how much of the true second half it reproduces verbatim
(normalized longest-common-prefix ratio + token overlap). High score => likely
memorized => keep out of the blind split.

Proxy model: Typhoon (Thai-native; if Typhoon memorized it, it is high-risk). The
definitive per-benchmarked-model check happens at Phase 8. Cheap by design (small N).

Run:  PYTHONUTF8=1 python memorization_probe.py [--n 40] [--model typhoon-v2.5-instruct]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

from pythainlp.tokenize import word_tokenize

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CACHE = DATA / "clean_cache"
ENV = HERE / ".env"          # repo-root .env (copy .env.example and fill in keys)
OUT = DATA / "memorization.json"

THAI = re.compile(r"[฀-๿]")


def load_env():
    if ENV.exists():
        for line in ENV.open(encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def norm(s):
    return re.sub(r"\s+", "", s)         # ignore whitespace for verbatim comparison


def lcp_ratio(pred, gold):
    """Longest-common-prefix length / gold length, on whitespace-stripped text."""
    p, g = norm(pred), norm(gold)
    if not g:
        return 0.0
    k = 0
    for a, b in zip(p, g):
        if a != b:
            break
        k += 1
    return k / len(g)


def token_overlap(pred, gold):
    pg, gg = set(word_tokenize(pred, engine="newmm")), set(word_tokenize(gold, engine="newmm"))
    if not gg:
        return 0.0
    return len(pg & gg) / len(gg)


def sample_sentences(name, n, minlen=90, maxlen=180):
    """Pull n clean-ish sentences from a cached source for the probe."""
    from inject_dataset import usable_sentences   # reuse the same filter
    path = CACHE / f"{name}.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.open(encoding="utf-8"):
        rec = json.loads(line)
        for s in usable_sentences(rec["text"], name, ""):
            if minlen <= len(s["text"]) <= maxlen:
                out.append(s["text"])
        if len(out) >= n * 4:
            break
    return out[:n]


def make_client():
    from openai import OpenAI
    key = os.environ.get("TYPHOON_API_KEY") or os.environ.get("THAILLM_API_KEY")
    if not key:
        raise RuntimeError("no TYPHOON_API_KEY / THAILLM_API_KEY in .env")
    return OpenAI(api_key=key, base_url="https://api.opentyphoon.ai/v1")


def complete(client, model, first_half):
    prompt = ("เติมข้อความต่อไปนี้ให้สมบูรณ์โดยใช้ถ้อยคำเดิมที่ถูกต้องที่สุด "
              "ตอบเฉพาะส่วนที่เติมต่อ ห้ามอธิบาย:\n\n" + first_half)
    r = client.chat.completions.create(
        model=model, temperature=0.0, max_tokens=120,
        messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="sentences per source")
    ap.add_argument("--model", default="typhoon-v2.5-30b-a3b-instruct")
    args = ap.parse_args()
    load_env()
    client = make_client()

    results, examples = {}, {}
    for name in ["thaisum", "wikipedia", "constitution", "thaigov"]:
        sents = sample_sentences(name, args.n)
        if not sents:
            continue
        lcps, toks, hi = [], [], 0
        ex = []
        for s in sents:
            mid = len(s) // 2
            first, second = s[:mid], s[mid:]
            try:
                pred = complete(client, args.model, first)
            except Exception as e:                       # noqa
                print(f"  {name}: API error {e!r}; stopping source")
                break
            l, t = lcp_ratio(pred, second), token_overlap(pred, second)
            lcps.append(l); toks.append(t)
            if l >= 0.5:
                hi += 1
            if len(ex) < 3:
                ex.append({"first": first, "gold": second, "pred": pred[:120],
                           "lcp": round(l, 3), "tok": round(t, 3)})
        if lcps:
            results[name] = {
                "n": len(lcps),
                "mean_lcp_ratio": round(sum(lcps) / len(lcps), 4),
                "mean_token_overlap": round(sum(toks) / len(toks), 4),
                "n_high_memorization": hi,
                "frac_high": round(hi / len(lcps), 3),
            }
            examples[name] = ex
            print(f"  {name}: n={len(lcps)} mean_lcp={results[name]['mean_lcp_ratio']} "
                  f"tok={results[name]['mean_token_overlap']} high={hi}")

    payload = {"model": args.model, "metric": "verbatim continuation from first half",
               "per_source": results, "examples": examples,
               "note": ("Higher = more memorized = stronger candidate to keep OUT of "
                        "test_private. Injection track is contamination-robust regardless; "
                        "this guards generalization validity of the blind split.")}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
