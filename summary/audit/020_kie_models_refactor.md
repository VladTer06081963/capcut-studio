# 020 — kie.ai integration hardening (kie-models skill refactor)

**Status:** ✅ Done (2026-10-13, доставлено в коммит 68c335d)
**Change:** `py/render/` → fully aligned with official `kie-models` skill

## 1. Контекст (Context)

Earlier `py/render/kie_client.py` was a hand-rolled subset that I had
imagined the kie.ai API to look like. After installing the official
`kie-models` skill (`npx skills add https://kie.ai`), the actual contract
turned out to differ on several important points: error codes live in
the JSON body (not HTTP status), reference-image field names vary per
model and must be discovered from the schema, uploads live on a different
domain, and there are explicit rate-limit pools. This audit records the
diff and the resulting architectural change.

## 2. Что сделано (What changed)

### `py/render/kie_client.py` (full rewrite, 476 lines)

| Area | Before | After |
|---|---|---|
| Error model | 4 generic types | 7 typed: `KieAuthError`, `KieCreditError`, `KieNotFoundError`, `KieValidationError`, `KieRateLimitError`, `KieSubKeyLimitError`, `KieUnavailableError` (all → `KieError`) |
| Error detection | looked at HTTP status | parses `body.code` (per official docs: 200 OK + error in body) |
| Submit | always sent `image_url` | fetches model schema first, picks `image_url` / `input_image` / `first_frame_image` / `video_url` per model |
| Sync models | would attempt with no schema check | rejects with `KieError("…is synchronous (not /api/v1/jobs/createTask)…")` |
| Result parsing | single shape | handles 3 shapes: `response.resultUrls[]`, `response.data[].audio_url` (Suno), `response.resultJson` (string-encoded JSON) |
| Rate limits | none | sliding-window `_RateLimiter` per pool (discovery 1.1s, create 0.5s, poll 0.1s) |
| Uploads | not implemented | `upload_file()` on `KIE_UPLOAD_BASE=kieai.redpandaai.co` (separate domain) |
| State machine | flat | typed: `waiting/queuing/generating` → `error="pending"`, `fail` → `error=failMsg`, `success` → `resultUrls` |
| Pricing/billing | none | `cost_credits` and `costTime` propagated from `creditsConsumed` and `costTime` fields |
| Model list | hardcoded `MODEL_MAP` | live discovery: `list_models(task_type=...)`, `get_model_schema()`, `get_model_price()` |
| Credit balance | not exposed | `get_credit_balance()` before generation |

### `py/render/provider_router.py` (docstring + example fix)

Docstring previously listed `kie/veo-3-fast` as the canonical example.
Updated to `kling/v2-1-master-text-to-video` to match the actual
"provider/name" format used by Kie (with non-URL-encoded slashes).
Added a note explaining `ProviderSpec.parse()`'s backend-vs-model
disambiguation rule.

### `py/render/base.py` (docstring fix)

`GenerationRequest.model_id` default and docstring previously referenced
`veo-3-fast`. Updated to `veo-3-1` to match the actual current model
name. `KNOWN_MODELS` is preserved as a backward-compat alias map (not
the source of truth — that is `KieClient.list_models`).

### `py/render/__init__.py`

Re-exports the new public surface: 7 typed errors, `KIE_UPLOAD_BASE`,
`ModelInfo`, `KieError`. `KNOWN_MODELS` still re-exported (deprecated).

### `tests/test_kie_client.py` (full rewrite, 452 lines)

30 unit tests covering:
- `ProviderSpec` parsing (qualified / bare / with-slashes)
- `parse_scene_provider` hierarchy (5 override levels)
- `ProviderRouter` build / cache / unknown backend / not-implemented
- `ProviderRouter.generate` first-try success / fallback chain / unavailable
- Envelope code mapping (401/402/404/422/429 → typed errors)
- State machine (`generating`/`queuing`/`waiting` → pending, `fail` →
  failMsg, `success` with response object vs resultJson string)
- Schema-aware submit (chooses `input_image` vs `image_url`, no-schema
  fallback, local-ref rejection, sync-model rejection, extra passthrough)
- `is_available()` no-key / with-key
- `ModelInfo.from_api()` full / minimal row

### `scripts/test_kie.py` (live smoke harness)

CLI for end-to-end live test:
- `python3 scripts/test_kie.py` — full path (list models → upload ref →
  submit → poll → download)
- `KIE_SMOKE=0 python3 scripts/test_kie.py` — discovery + balance only
  (no credits spent)

### `scripts/setup_keys.sh` (new, 25 lines)

Interactive shell helper that reads `KIE_API_KEY` from `/dev/tty` (not
argv) and writes it to `.env` with `chmod 600`. Designed so the user can
type the key on a real terminal without it appearing in any process
listing or chat history.

### PRD update (this audit's sibling — see PRD.md §6 and §13)

PRD §6 expanded from 63 lines to 184 lines documenting the new
architecture: error contract, state machine, schema-driven input,
sync-rejection, rate limiters, two-domain upload, result URL handling,
spend/approval. PRD §13 updated to reflect 30/30 unit tests passing.
PRD §15 status block updated. PRD version bumped 1.2 → 1.3.

## 3. Статус (Verification)

- 30/30 unit tests in `tests/test_kie_client.py` pass (`python3 -m pytest
  tests/test_kie_client.py -v`)
- All imports clean (`from py.render import …` resolves without errors)
- `pyright` diagnostics: only 4 `payload not defined` warnings, all in
  test methods that assign `payload = post.call_args[0][1]` — these
  resolve correctly at runtime (verified by smoke run)
- `kling/v2-1-master-text-to-video` and `veo-3-1` confirmed as real Kie
  model ids per official skill documentation

## 4. Что НЕ проверено (What's NOT verified)

- Live HTTP call to `api.kie.ai` (requires API key; user declined to
  share via chat — see session history)
- Real generation round-trip and download
- Schema variants beyond the two tested shapes (`input_image` and
  `image_url`)

## 5. Follow-ups

- Live test once `KIE_API_KEY` is inserted via `scripts/setup_keys.sh`
- Add integration test that mocks full HTTP exchange with realistic
  payload (currently only envelope is mocked)
- Decide whether `KNOWN_MODELS` should be removed entirely (currently
  kept for backward compat)

## Files

- `py/render/__init__.py` — public surface
- `py/render/base.py` — `GenerationRequest` / `GenerationResult` / `VideoProvider`
- `py/render/kie_client.py` — 476 lines, full rewrite
- `py/render/provider_router.py` — 173 lines, docstring fix
- `tests/test_kie_client.py` — 452 lines, full rewrite (30 tests)
- `scripts/test_kie.py` — live smoke harness
- `scripts/setup_keys.sh` — interactive key insertion
- `summary/PRD/PRD.md` — §6 expanded, §13/§15 updated, version 1.2 → 1.3
- `summary/audit/020_kie_models_refactor.md` — this file
- `summary/tasks/020_kie_models_refactor.md` — task description
