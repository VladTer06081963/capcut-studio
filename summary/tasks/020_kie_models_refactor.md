# 020 — kie.ai integration hardening (kie-models skill refactor)

## Goal

Bring `py/render/` in line with the actual Kie.ai API as documented by
the official `kie-models` skill installed via `npx skills add
https://kie.ai`. Replace the hand-rolled subset (4 generic errors,
hardcoded model map, single shape) with the full official contract
(7 typed errors, live discovery, schema-driven submit, separate upload
domain, per-pool rate limiters).

## Tasks

- [x] Read `~/.hermes/skills/kie-models/SKILL.md` to extract the real
      API contract (endpoints, error codes, state machine, rate limits,
      upload domain)
- [x] Rewrite `py/render/kie_client.py` to implement the contract:
      - 7 typed exceptions, all inheriting from `KieError`
      - body.code-based error detection
      - `get_credit_balance()` / `list_models()` / `get_model_schema()` /
        `get_model_price()` / `upload_file()` discovery methods
      - `submit()` that fetches model schema and chooses the right
        reference-image field name
      - `submit()` that rejects sync chat models explicitly
      - `poll()` / `wait()` with state machine mapping to `GenerationResult`
      - `_RateLimiter` per pool (discovery / create / poll)
      - `KIE_UPLOAD_BASE` constant for `kieai.redpandaai.co`
- [x] Fix `py/render/provider_router.py` docstring (correct example
      model name, clarify backend-vs-model disambiguation)
- [x] Fix `py/render/base.py` docstring and default model id
- [x] Rewrite `tests/test_kie_client.py` against the new contract
      (30 tests, mocks HTTP)
- [x] Run all 30 unit tests, ensure 30/30 pass
- [x] Verify clean import of `py.render` module surface
- [x] Write `scripts/test_kie.py` — live smoke harness
      (`KIE_SMOKE=0` for discovery-only)
- [x] Write `scripts/setup_keys.sh` — interactive key insertion from
      /dev/tty (so it doesn't appear in process listing)
- [x] Update PRD §6 (architecture, error contract, state machine,
      schema-driven submit, sync-rejection, rate limiters, upload
      domain, result URL handling, spend/approval)
- [x] Update PRD §13 (testing — 30/30 OK, live smoke deferred)
- [x] Update PRD §15 (status — kie refactor reflected)
- [x] Bump PRD version 1.2 → 1.3
- [x] Write `summary/audit/020_kie_models_refactor.md`
- [x] Write `summary/tasks/020_kie_models_refactor.md` (this file)
- [ ] Live test with real `KIE_API_KEY` — blocked on user to provide
      the key via `scripts/setup_keys.sh` (deliberate: not inserting
      a chat-exposed key into `.env`)

## Acceptance

- ✅ `from py.render import ProviderRouter, KieClient, …` works
- ✅ `python3 -m pytest tests/test_kie_client.py` → 30/30 OK
- ✅ PRD §6 documents the actual contract (no fake "veo-3-fast"
      references, no "MODEL_MAP")
- ✅ Setup script reads key from /dev/tty, not argv
- ⏸ Live test — pending user key insertion

## Out of scope (deferred)

- A `Mavis`/Hermes-driven `mcp-server` tool for `list_kie_models` /
  `submit_kie_task` (would be a small wrapper over `KieClient`). Not
  in this change because the user asked for a focused render-layer
  refactor; can be a follow-up if/when desired.
- Removing `KNOWN_MODELS` entirely. Kept as backward-compat alias map.
- Full HTTP integration tests with realistic payload. Current tests
  mock the envelope; integration would require either a real key
  or a recorded HTTP fixture.

## Notes

- The previous `py/render/kie_client.py` was based on a guess at the
  Kie API. The official skill turned out to be substantially different
  in error handling, schema-driven submit, and upload domain. This
  refactor replaces the guess with the real contract.
- The MCP server (`mcp-server/index.js`) does not currently expose
  any `py/render/` tools; it only handles `assemble_episode` and
  `open_in_concat`. Adding render tools there is a separate change.
