"""
Phase 8 — sample model run for EditingBench (plan.md §8).

Feeds each test item's `text_wrong` to a model and asks for the orthographically
corrected sentence (correction only — no rewriting). Resume-safe JSONL per model.
Grading is separate (`score_runs.py`), so a run can be re-graded without re-calling.

Models: see REGISTRY below — OpenAI Responses (gpt-5.x), OpenAI-compatible chat
(OpenTyphoon, OpenRouter, Gemini, ThaiLLM national gateway) and Anthropic Messages
(Claude). Specs mirror prosody/eval/registry.py. Disabled entries (pathumma, kimi)
carry a note explaining why.

Runs are x8-parallel (ThreadPoolExecutor over a flat (model, item) queue); each
model appends to its own resume-safe results/<alias>.jsonl under a per-file lock.

Run:  PYTHONUTF8=1 python run_editing.py --smoke --workers 8           # all enabled, n=16
      PYTHONUTF8=1 python run_editing.py --models gpt55-med typhoon25 --split test_public --n 819
"""
import argparse
import json
import os
import random
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
ENV = HERE / ".env"          # repo-root .env (copy .env.example and fill in keys)
SEED = 20260524

# OpenRouter courtesy headers (mirrors prosody/eval/registry.OPENROUTER_HEADERS).
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://localhost/thai-benchmarks-track1",
    "X-Title": "Thai Benchmarks Track 1",
}
_THAI = "THAILLM_API_KEY"
_GATEWAY = "https://thaillm.or.th/api/v1"            # national gateway (https; http also works)
# The gateway sits behind Cloudflare, which WAF-blocks the default httpx/SDK User-Agent
# (HTTP 403 "error code: 1010" — banned by browser signature, BEFORE the key is checked).
# A browser-like UA clears it; the key is valid. (Re-verified working 2026-05-25.)
_GATEWAY_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
}
_OPENAI = "OPENAI_API_KEY2"                          # falls back to OPENAI_API_KEY
_OROUTER = "OPENROUTER_API_KEY"
_OR_URL = "https://openrouter.ai/api/v1"
_GEMINI = "GEMINI_API_KEY"
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"   # OpenAI-compat
_ANTHROPIC = "ANTHROPIC_API_KEY"

# provider ∈ {"chat" (OpenAI-compatible /chat/completions), "responses" (OpenAI
# Responses API, gpt-5.x), "anthropic" (Claude Messages)}. Optional keys: reasoning
# (responses effort), or_reasoning (OpenRouter reasoning-control dict via extra_body),
# extra_headers, request_timeout, enabled, note.
REGISTRY = {
    # --- existing entries (UNCHANGED — preserve cached 819-item results) ----------
    "typhoon25": dict(provider="chat", model_id="typhoon-v2.5-30b-a3b-instruct",
                      base_url="https://api.opentyphoon.ai/v1", key_env="TYPHOON_API_KEY",
                      max_tokens=300, note="Thai-native 30B (OpenTyphoon — needs TYPHOON_API_KEY)"),
    "deepseek-flash": dict(provider="chat", model_id="deepseek/deepseek-v4-flash",
                           base_url=_OR_URL, key_env=_OROUTER, extra_headers=OPENROUTER_HEADERS,
                           max_tokens=24000, request_timeout=600,
                           note="DeepSeek V4 Flash (OpenRouter) — thinking-native; 24k budget "
                                "(re-budgeted 2026-05-24, old run used 300 → ~17% empty)"),
    # gpt-5.x = OpenAI Responses API + reasoning effort; big token budget leaves room
    # for the reasoning trace before the short corrected-sentence answer (S1 finding).
    "gpt55-med": dict(provider="responses", model_id="gpt-5.5", base_url=None,
                      key_env=_OPENAI, reasoning="medium", max_tokens=3000),

    # --- OpenAI (Responses API) ---------------------------------------------------
    "gpt55-high": dict(provider="responses", model_id="gpt-5.5", base_url=None,
                       key_env=_OPENAI, reasoning="high", max_tokens=6000),
    "gpt54-mini": dict(provider="responses", model_id="gpt-5.4-mini", base_url=None,
                       key_env=_OPENAI, max_tokens=2000),

    # --- Gemini (Google OpenAI-compat endpoint; thinks → generous budget) ---------
    "gemini-3.5-flash": dict(provider="chat", model_id="gemini-3.5-flash",
                             base_url=_GEMINI_URL, key_env=_GEMINI, max_tokens=24000,
                             request_timeout=600, note="Gemini API (OpenAI-compat); thinks"),

    # --- Claude (Anthropic) — run via Message Batches (50% cheaper, async) ---------
    "sonnet-4.6": dict(provider="anthropic", model_id="claude-sonnet-4-6",
                       key_env=_ANTHROPIC, max_tokens=2000, request_timeout=600, batch=True,
                       note="Anthropic Message Batches; non-thinking, temperature=0"),
    "opus-4.7": dict(provider="anthropic", model_id="claude-opus-4-7",
                     key_env=_ANTHROPIC, max_tokens=2000, request_timeout=600, batch=True,
                     no_temperature=True,
                     note="Anthropic Message Batches; Opus 4.7 REJECTS temperature → omit it"),

    # --- OpenRouter (reasoning-native unless noted; budget must cover CoT + answer) -
    "deepseek-v4-pro": dict(provider="chat", model_id="deepseek/deepseek-v4-pro",
                            base_url=_OR_URL, key_env=_OROUTER, extra_headers=OPENROUTER_HEADERS,
                            max_tokens=24000, request_timeout=600,
                            note="thinking ON natively (slow ~3-4min/call)"),
    "glm-5.1": dict(provider="chat", model_id="z-ai/glm-5.1", base_url=_OR_URL,
                    key_env=_OROUTER, extra_headers=OPENROUTER_HEADERS, max_tokens=24000,
                    request_timeout=600, note="native reasoning ON"),
    "minimax-m2.7": dict(provider="chat", model_id="minimax/minimax-m2.7", base_url=_OR_URL,
                         key_env=_OROUTER, extra_headers=OPENROUTER_HEADERS, max_tokens=24000,
                         request_timeout=600, note="reasoning-only (can't disable); runout=fail"),
    "qwen3.6-35b-a3b": dict(provider="chat", model_id="qwen/qwen3.6-35b-a3b", base_url=_OR_URL,
                            key_env=_OROUTER, extra_headers=OPENROUTER_HEADERS, max_tokens=24000,
                            request_timeout=600, note="thinking → <think> stripped"),
    "gemma-4-31b": dict(provider="chat", model_id="google/gemma-4-31b-it", base_url=_OR_URL,
                        key_env=_OROUTER, extra_headers=OPENROUTER_HEADERS, max_tokens=2000,
                        request_timeout=120, note="non-thinking"),
    "kimi-k2.6": dict(provider="chat", model_id="moonshotai/kimi-k2.6", base_url=_OR_URL,
                      key_env=_OROUTER, extra_headers=OPENROUTER_HEADERS, max_tokens=24000,
                      request_timeout=600, enabled=False,
                      note="SKIPPED (prosody): runs away — ~half of items burn the full 24k "
                           "reasoning budget with no answer"),

    # --- ThaiLLM national gateway -------------------------------------------------
    "openthaigpt": dict(provider="chat", model_id="openthaigpt-thaillm-8b-instruct-v7.2",
                        base_url=_GATEWAY, key_env=_THAI, extra_headers=_GATEWAY_HEADERS,
                        max_tokens=8192, request_timeout=300,
                        note="ThaiLLM gateway; v7.2 now emits <think> (reasoning) → bigger budget"),
    "typhoon-s": dict(provider="chat", model_id="typhoon-s-thaillm-8b-instruct",
                      base_url=_GATEWAY, key_env=_THAI, extra_headers=_GATEWAY_HEADERS,
                      max_tokens=2048, request_timeout=120,
                      note="ThaiLLM gateway — non-thinking, clean output"),
    "thalle": dict(provider="chat", model_id="thalle-0.2-thaillm-8b-fa",
                   base_url=_GATEWAY, key_env=_THAI, extra_headers=_GATEWAY_HEADERS,
                   max_tokens=8192, request_timeout=300,
                   note="ThaiLLM gateway / KBTG — also a thinking model"),
    "pathumma": dict(provider="chat", model_id="pathumma-thaillm-qwen3-8b-think-3.0.0",
                     base_url=_GATEWAY, key_env=_THAI, extra_headers=_GATEWAY_HEADERS,
                     max_tokens=4096, request_timeout=300,
                     enabled=False,
                     note="SKIPPED (prosody): Qwen3 thinking unusable — <=4096 truncates "
                          "(no </think>), >=8192 gateway 504-times-out. No viable budget."),
}

SYSTEM = ("คุณเป็นเครื่องมือตรวจแก้การสะกดคำภาษาไทยตามอักขรวิธีมาตรฐานของราชบัณฑิตยสภา")
PROMPT = (
    "จงแก้คำที่สะกดผิดในประโยคต่อไปนี้ให้ถูกต้องตามอักขรวิธี "
    "แก้เฉพาะตัวพยัญชนะ/สระ/วรรณยุกต์/ตัวการันต์ที่สะกดผิดเท่านั้น "
    "ห้ามเปลี่ยนถ้อยคำ ห้ามเรียบเรียงใหม่ ห้ามเพิ่มหรือลบเนื้อความ "
    "ห้ามเปลี่ยนการเว้นวรรค ตัวเลข หรือเครื่องหมายวรรคตอน "
    "ถ้าไม่มีคำผิดให้ตอบประโยคเดิมทุกตัวอักษร "
    "ตอบกลับเป็นประโยคที่แก้ไขแล้วบรรทัดเดียวเท่านั้น ไม่ต้องอธิบาย\n\n"
    "ประโยค: {text}\nประโยคที่แก้ไขแล้ว:"
)
# paragraph (T2) variant: "ข้อความ" (text) instead of "ประโยค", no single-line constraint
PROMPT_PARA = (
    "จงแก้คำที่สะกดผิดในข้อความต่อไปนี้ให้ถูกต้องตามอักขรวิธี "
    "แก้เฉพาะตัวพยัญชนะ/สระ/วรรณยุกต์/ตัวการันต์ที่สะกดผิดเท่านั้น "
    "ห้ามเปลี่ยนถ้อยคำ ห้ามเรียบเรียงใหม่ ห้ามเพิ่มหรือลบเนื้อความ "
    "ห้ามเปลี่ยนการเว้นวรรค ตัวเลข หรือเครื่องหมายวรรคตอน "
    "ถ้าไม่มีคำผิดให้ตอบข้อความเดิมทุกตัวอักษร "
    "ตอบกลับเป็นข้อความที่แก้ไขแล้วเท่านั้น ไม่ต้องอธิบาย\n\n"
    "ข้อความ: {text}\nข้อความที่แก้ไขแล้ว:"
)
THINK = re.compile(r"<think>.*?</think>", re.S)


def load_env():
    """Load .env, letting it OVERRIDE any pre-existing OS env var. (.env is the
    workspace's source of truth for keys; a stale Windows ANTHROPIC_API_KEY was
    otherwise shadowing the updated .env value via setdefault.)"""
    if ENV.exists():
        for line in ENV.open(encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()


def clean_output(raw: str, paragraph: bool = False) -> str:
    """Strip reasoning, prompt echoes, quotes; keep the corrected text.

    Sentence mode keeps the last non-empty line (T1). Paragraph mode (T2) joins all
    remaining non-empty lines with a space — the model may wrap a long paragraph."""
    t = THINK.sub("", raw or "").strip()
    for label in ("ข้อความที่แก้ไข", "ประโยคที่แก้ไข"):
        if label in t:                              # model echoed the label
            t = t.split(label)[-1].lstrip("แล้ว:： ").strip()
            break
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if lines:
        t = " ".join(lines) if paragraph else lines[-1]
    return t.strip().strip('"“”\'`').strip()


def sample_items(split: str, n: int) -> list[dict]:
    items = [json.loads(l) for l in (DATA / f"items_{split}.jsonl").open(encoding="utf-8")]
    rng = random.Random(SEED)
    if n <= 0 or n >= len(items):                     # --n 0 / n>=split size => ALL items
        rng.shuffle(items)
        return items
    by_cls = defaultdict(list)
    for it in items:
        by_cls[it["edits"][0]["class"]].append(it)
    for c in by_cls:
        rng.shuffle(by_cls[c])
    classes = sorted(by_cls)
    per = max(1, n // len(classes))
    out = []
    for c in classes:
        out += by_cls[c][:per]
    rng.shuffle(out)
    return out[:n]


# per-key-env fallback chain (used only when the primary env var is unset)
_KEY_FALLBACK = {
    "OPENAI_API_KEY2": "OPENAI_API_KEY",
    "TYPHOON_API_KEY": "THAILLM_API_KEY",
}


def resolve_key(spec) -> str:
    key = os.environ.get(spec["key_env"], "")
    if not key and spec["key_env"] in _KEY_FALLBACK:
        key = os.environ.get(_KEY_FALLBACK[spec["key_env"]], "")
    return key


def make_client(spec):
    key = resolve_key(spec)
    if not key:
        raise RuntimeError(f"no {spec['key_env']} in {ENV}")
    if spec["provider"] == "anthropic":
        from anthropic import Anthropic
        kw = {"api_key": key}
        if spec.get("request_timeout"):
            kw["timeout"] = spec["request_timeout"]
        return Anthropic(**kw)
    from openai import OpenAI
    kw = {"api_key": key}
    if spec.get("base_url"):
        kw["base_url"] = spec["base_url"]
    if spec.get("extra_headers"):
        kw["default_headers"] = spec["extra_headers"]
    if spec.get("request_timeout"):
        kw["timeout"] = spec["request_timeout"]
    return OpenAI(**kw)


def call(client, spec, text, tries=4, min_tokens=0):
    last, msg = None, PROMPT.format(text=text)
    mt = max(spec.get("max_tokens", 300), min_tokens)
    for k in range(tries):
        try:
            if spec["provider"] == "responses":
                kw = dict(model=spec["model_id"], instructions=SYSTEM, input=msg,
                          max_output_tokens=mt)
                if spec.get("reasoning"):
                    kw["reasoning"] = {"effort": spec["reasoning"]}
                return client.responses.create(**kw).output_text or ""
            if spec["provider"] == "anthropic":
                kw = dict(model=spec["model_id"], max_tokens=mt, system=SYSTEM,
                          messages=[{"role": "user", "content": msg}])
                if not spec.get("no_temperature"):       # Opus 4.7 rejects temperature
                    kw["temperature"] = 0.0
                r = client.messages.create(**kw)
                return "".join(b.text for b in r.content
                               if getattr(b, "type", None) == "text") or ""
            # OpenAI-compatible chat.completions (OpenTyphoon, OpenRouter, Gemini, gateway)
            kw = dict(model=spec["model_id"], temperature=0.0, max_tokens=mt,
                      messages=[{"role": "system", "content": SYSTEM},
                                {"role": "user", "content": msg}])
            if spec.get("or_reasoning") is not None:    # OpenRouter reasoning control
                kw["extra_body"] = {"reasoning": spec["or_reasoning"]}
            r = client.chat.completions.create(**kw)
            return r.choices[0].message.content or ""
        except Exception as e:                      # noqa
            last = repr(e)
            time.sleep(2 * (k + 1))
    raise RuntimeError(last)


def resolve_models(keys: list[str] | None) -> list[str]:
    """Named keys → validated alias list (clear errors). None → every enabled model."""
    if not keys:
        return [k for k, s in REGISTRY.items() if s.get("enabled", True)]
    out = []
    for k in keys:
        s = REGISTRY.get(k)
        if s is None:
            raise SystemExit(f"unknown model {k!r}; choices: {sorted(REGISTRY)}")
        if not s.get("enabled", True):
            raise SystemExit(f"model {k!r} is disabled — {s.get('note', 'not configured')}")
        if not s.get("model_id"):
            raise SystemExit(f"model {k!r} has no model_id")
        if s["provider"] == "chat" and not s.get("base_url"):
            raise SystemExit(f"model {k!r} (chat) needs a base_url")
        out.append(k)
    return out


def load_done(out_path: Path) -> set:
    done = set()
    if out_path.exists():
        for line in out_path.open(encoding="utf-8"):
            try:
                done.add(json.loads(line)["id"])
            except Exception:                       # noqa
                pass
    return done


def load_or_make_sample(split: str, n: int) -> list[dict]:
    """Persist the exact sample so scoring uses the same items; reuse if present so
    parallel runs (and a later full run resuming a smoke) share one sample by id."""
    sample_path = RESULTS / f"_sample_{split}_{n}.jsonl"
    if sample_path.exists():
        items = [json.loads(l) for l in sample_path.open(encoding="utf-8")]
        print(f"reusing existing sample: {len(items)} {split} items <- {sample_path.name}")
    else:
        items = sample_items(split, n)
        with sample_path.open("w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        print(f"sampled {len(items)} {split} items -> {sample_path.name}")
    return items


def _anthropic_requests(spec, todo):
    """Build Message Batches request objects (custom_id = item id)."""
    mt = spec.get("max_tokens", 2000)
    reqs = []
    for it in todo:
        params = dict(model=spec["model_id"], max_tokens=mt, system=SYSTEM,
                      messages=[{"role": "user", "content": PROMPT.format(text=it["text_wrong"])}])
        if not spec.get("no_temperature"):
            params["temperature"] = 0.0
        reqs.append({"custom_id": it["id"], "params": params})
    return reqs


def submit_anthropic_batch(alias, spec, items):
    """Create (or re-attach) one Message Batch for an Anthropic model's pending items.
    Returns (batch_id, todo_ids) or (None, []) if nothing to do. Persists the batch id
    to a sidecar so an interrupted run can re-attach instead of re-paying."""
    out_path = RESULTS / f"{alias}.jsonl"
    sidecar = RESULTS / f"{alias}.batchid"
    done = load_done(out_path)
    todo = [it for it in items if it["id"] not in done]
    print(f"[{alias}] {len(items)} items, {len(done)} cached, {len(todo)} to batch")
    if not todo:
        return None, []
    client = make_client(spec)
    if sidecar.exists():                              # re-attach an in-flight batch
        bid = sidecar.read_text(encoding="utf-8").strip()
        try:
            client.messages.batches.retrieve(bid)
            print(f"[{alias}] re-attached batch {bid}")
            return bid, [it["id"] for it in todo]
        except Exception:                             # noqa — stale/expired → new batch
            pass
    batch = client.messages.batches.create(requests=_anthropic_requests(spec, todo))
    sidecar.write_text(batch.id, encoding="utf-8")
    print(f"[{alias}] submitted batch {batch.id} ({len(todo)} requests)")
    return batch.id, [it["id"] for it in todo]


def collect_anthropic_batch(alias, spec, batch_id, paragraph, poll=20):
    """Poll one Message Batch to completion, then append {id, raw, output} per result."""
    client = make_client(spec)
    out_path = RESULTS / f"{alias}.jsonl"
    sidecar = RESULTS / f"{alias}.batchid"
    while True:
        b = client.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        c = b.request_counts
        print(f"[{alias}] batch {b.processing_status} "
              f"(done {c.succeeded + c.errored + c.canceled + c.expired}/"
              f"{c.processing + c.succeeded + c.errored + c.canceled + c.expired})")
        time.sleep(poll)
    err = 0
    with out_path.open("a", encoding="utf-8") as fh:
        for r in client.messages.batches.results(batch_id):
            if r.result.type == "succeeded":
                raw = "".join(blk.text for blk in r.result.message.content
                              if getattr(blk, "type", None) == "text")
                rec = {"id": r.custom_id, "raw": raw, "output": clean_output(raw, paragraph)}
            else:
                detail = getattr(getattr(r.result, "error", None), "type", r.result.type)
                rec = {"id": r.custom_id, "raw": "", "output": "", "error": str(detail)}
                err += 1
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    sidecar.unlink(missing_ok=True)
    print(f"[{alias}] batch done -> {alias}.jsonl  (errors {err})")


def run_matrix(aliases: list[str], items: list[dict], workers: int,
               paragraph: bool = False, min_tokens: int = 0):
    """Route Anthropic models through Message Batches (submitted up front, so they cook
    while the x8 (model, item) thread pool drives the chat/responses models), then collect.
    One append-lock + cached client + open file per streamed model; a model whose client
    fails to init is skipped (smoke stays robust)."""
    # --- partition: Anthropic batch models vs streamed (chat/responses) models -------
    batch_aliases = [a for a in aliases if REGISTRY[a]["provider"] == "anthropic"]
    stream_aliases = [a for a in aliases if a not in batch_aliases]
    pending_batches = []                              # (alias, spec, batch_id)
    for alias in batch_aliases:
        spec = REGISTRY[alias]
        try:
            bid, _ = submit_anthropic_batch(alias, spec, items)
            if bid:
                pending_batches.append((alias, spec, bid))
        except Exception as e:                      # noqa
            print(f"[{alias}] SKIP — batch submit failed: {e}")

    state: dict[str, dict] = {}
    tasks: list[tuple[str, dict]] = []
    for alias in stream_aliases:
        spec = REGISTRY[alias]
        out_path = RESULTS / f"{alias}.jsonl"
        done = load_done(out_path)
        try:
            client = make_client(spec)
        except Exception as e:                      # noqa — missing key / SDK
            print(f"[{alias}] SKIP — client init failed: {e}")
            continue
        todo = [it for it in items if it["id"] not in done]
        state[alias] = {"spec": spec, "client": client, "lock": threading.Lock(),
                        "fh": out_path.open("a", encoding="utf-8"), "err": 0}
        print(f"[{alias}] {len(items)} items, {len(done)} cached, {len(todo)} to run")
        tasks += [(alias, it) for it in todo]

    def worker(alias: str, it: dict):
        st = state[alias]
        try:
            raw = call(st["client"], st["spec"], it["text_wrong"], min_tokens=min_tokens)
            rec, ok = {"id": it["id"], "raw": raw, "output": clean_output(raw, paragraph)}, True
        except Exception as e:                      # noqa
            rec, ok = {"id": it["id"], "raw": "", "output": "", "error": str(e)}, False
        with st["lock"]:
            st["fh"].write(json.dumps(rec, ensure_ascii=False) + "\n")
            st["fh"].flush()
            if not ok:
                st["err"] += 1

    total, done_n = len(tasks), 0
    if tasks:
        print(f"running {total} calls across {len(state)} models, {workers} workers")
        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = [ex.submit(worker, a, it) for a, it in tasks]
                for _ in as_completed(futs):
                    done_n += 1
                    if done_n % 20 == 0 or done_n == total:
                        errs = sum(st["err"] for st in state.values())
                        print(f"    {done_n}/{total}  (errors {errs})")
        finally:
            for alias, st in state.items():
                st["fh"].close()
                print(f"[{alias}] done -> {alias}.jsonl  (errors {st['err']})")
    else:
        for st in state.values():
            st["fh"].close()

    # --- collect Anthropic batches (cooked while the stream pool ran) ----------------
    for alias, spec, bid in pending_batches:
        try:
            collect_anthropic_batch(alias, spec, bid, paragraph)
        except Exception as e:                      # noqa
            print(f"[{alias}] batch collect FAILED (re-run to re-attach {bid}): {e}")

    if not tasks and not pending_batches:
        print("nothing to run (all cached or all skipped)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=None,
                    help="aliases to run (default: all enabled)")
    ap.add_argument("--split", default="test_public")
    ap.add_argument("--n", type=int, default=None, help="sample size (default 100; 16 with --smoke)")
    ap.add_argument("--workers", type=int, default=8, help="parallel API calls")
    ap.add_argument("--smoke", action="store_true",
                    help="triage run: n=16 over all enabled models unless overridden")
    ap.add_argument("--results", default="results", help="output dir (isolate tiers, e.g. results_t2)")
    ap.add_argument("--paragraph", action="store_true", help="paragraph prompt + multi-line clean (T2/T3)")
    ap.add_argument("--min-tokens", type=int, default=0, help="floor on output budget (raise for long text)")
    args = ap.parse_args()
    load_env()
    global RESULTS, PROMPT
    RESULTS = HERE / args.results
    RESULTS.mkdir(exist_ok=True)
    if args.paragraph:
        PROMPT = PROMPT_PARA
    n = args.n if args.n is not None else (16 if args.smoke else 100)
    aliases = resolve_models(args.models)
    print(f"models ({len(aliases)}): {', '.join(aliases)}  ->  {RESULTS.name}/")
    items = load_or_make_sample(args.split, n)
    run_matrix(aliases, items, args.workers, paragraph=args.paragraph, min_tokens=args.min_tokens)


if __name__ == "__main__":
    main()
