# EditingBench — Model-Matrix Smoke (triage)

**2026-05-24.** `run_editing.py --smoke --workers 8` = all 15 enabled models × 12
stratified `test_public` items (n=16 → 2/class), then `score_runs.py --n 16`. Purpose
= **triage** (does each provider path RUN end-to-end?), not ranking — n=12 scores are
noisy (wide CIs) and exist only to confirm sane output. The 3 previously-run models
(typhoon25, deepseek-flash, gpt55-med) were served from their cached 819-item runs.

## Resolution (2026-05-24, after .env refresh)

- **sonnet-4.6 → GO.** Root cause was a stale Windows OS env var `ANTHROPIC_API_KEY`
  shadowing the updated `.env` (the harness's `load_env` used `setdefault`). Fixed:
  `load_env` now **overrides** OS vars from `.env` (it is the workspace source of truth).
  Re-smoke = 0 errors, clean corrections.
- **deepseek-flash → re-budgeted** 300 → **24000** tokens + OpenRouter headers/600s
  (it is thinking-native). Re-smoke = 0/12 empty (was 2/12). Old 300-token 819 run
  backed up to `results/deepseek-flash.jsonl.bak300`.
- **openthaigpt / typhoon-s / thalle → STILL BLOCKED.** Their `THAILLM_API_KEY` is read
  from `.env` (not OS-shadowed), so this is a genuine gateway-side 403 — not a key the
  refresh could fix. Left out of the matrix run; re-add if gateway access is restored.

**Working set = 12 models** (added sonnet-4.6). Full 819-item run launched on all 12.

## Verdict (initial smoke): 11 GO · 4 BLOCKED → after fix: 12 GO · 3 BLOCKED

| model | provider | n | err | empty | smoke corrF1 | status |
|---|---|--:|--:|--:|--:|---|
| gpt55-med | OpenAI Responses (med) | 12 | 0 | 0 | 1.00 | **GO** |
| gpt55-high | OpenAI Responses (high) | 12 | 0 | 0 | 1.00 | **GO** |
| gpt54-mini | OpenAI Responses | 12 | 0 | 0 | 0.92 | **GO** |
| gemini-3.5-flash | Gemini (OpenAI-compat) | 12 | 0 | 0 | 1.00 | **GO** |
| gemma-4-31b | OpenRouter | 12 | 0 | 0 | 1.00 | **GO** |
| deepseek-v4-pro | OpenRouter (thinking) | 12 | 0 | 0 | 0.97 | **GO** (slow) |
| glm-5.1 | OpenRouter (thinking) | 12 | 0 | 0 | 0.97 | **GO** (slow) |
| qwen3.6-35b-a3b | OpenRouter (thinking) | 12 | 0 | 0 | 0.85 | **GO** (slow) |
| typhoon25 | OpenTyphoon | 12 | 0 | 0 | 0.82 | **GO** (cached) |
| deepseek-flash | OpenRouter | 12 | 0 | 2 | 0.73 | **GO** ⚠ budget |
| minimax-m2.7 | OpenRouter (thinking) | 12 | 0 | 2 | 0.64 | **GO** ⚠ runout |
| sonnet-4.6 | Anthropic Messages | 12 | 12 | — | 0.00 | **BLOCKED** auth |
| openthaigpt | ThaiLLM gateway | 12 | 12 | — | 0.00 | **BLOCKED** gateway |
| typhoon-s | ThaiLLM gateway | 12 | 12 | — | 0.00 | **BLOCKED** gateway |
| thalle | ThaiLLM gateway | 12 | 12 | — | 0.00 | **BLOCKED** gateway |

(`empty` = non-error blank output, i.e. thinking-runout → scored as no-op. `pathumma`
+ `kimi-k2.6` stay disabled in the registry — prosody-confirmed unusable.)

## Blocked — root cause + fix

- **sonnet-4.6** — `AuthenticationError 401: invalid x-api-key`. The `ANTHROPIC_API_KEY`
  in `.env` is rejected (expired/wrong). Fix: refresh the key, **or** run Sonnet via a
  Claude Code subagent (the workspace's stated path for Claude models) instead of the API.
- **openthaigpt / typhoon-s / thalle** (all three ThaiLLM-gateway models) —
  `PermissionDeniedError 403: "Your request was blocked."` The request reaches
  `http://thaillm.or.th/api/v1` and the gateway refuses it (WAF / key-not-authorized /
  IP gate), not a code or connectivity problem. Prosody reached this gateway before, so
  this is environmental. Fix: verify `THAILLM_API_KEY` is authorized for these model ids
  / the gateway isn't IP-gating this host, or retry later (the national gateway flakes).

## Caveats for the working set

- **deepseek-flash** carries the *old* 300-token budget (predates this matrix). It is
  thinking-native, so ~17% (2/12) of outputs are empty (reasoning eats the budget) — this
  understates it. **Recommend re-running deepseek-flash at the 24k OpenRouter budget** for
  matrix fairness (its cached 819-item result used 300).
- **minimax-m2.7** is reasoning-only (can't disable); ~17% empty at runout and the lowest
  working-set F1. Keep, but expect it near the floor.
- **Thinking models are slow** (deepseek-v4-pro ~3–4 min/call; glm/minimax/qwen/gpt55-high
  also reason). Even x8-parallel, the full 819-item run is multi-hour, dominated by these.

## Next (after user GO)

Full run on the 11 working models:
`run_editing.py --models <11> --split test_public --n 819 --workers 8` →
`score_runs.py --split test_public --n 819` (each resumes its 12 smoke items). Optionally
unblock sonnet/gateway first; optionally re-budget deepseek-flash to 24k.
