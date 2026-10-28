# Tasks: Approval enforcement at generation entrypoints and spec-bound episode approval

> Implements two of the acceptance criteria of `openspec/changes/hybrid-media-workflow/`
> and closes the P0 items 23-25 of `summary/tasks/016_stabilization_and_spend_safety.md`.
> Also satisfies the open documentation item in `summary/tasks/016_…:56`:
> "Перед изменением кода для enforcement approval/immutable подготовить OpenSpec
> proposal и delta-spec".
>
> Numbering note: this change is recorded as `summary/tasks/025_…` and
> `summary/audit/026_…` — the audit series already used 025, so the pair is
> intentionally asymmetric.

## 1. Approval claim primitive

- [ ] `capcut/lib/model_approval.py`
  - [ ] public entry point that resolves an approval for an exact
        `(provider, model_id, task_scope)` triple
  - [ ] atomic claim (consume-once) reused from `claim_approval()`
  - [ ] raises `ApprovalError` when: no artifact matches / provider or model
        differ / scope differs / expired / already claimed
  - [ ] no credentials in the artifact or in any error message

  Spec: `openspec/changes/approval-enforcement-and-spec-binding/specs/model-approval-enforcement/spec.md`

## 2. Enforce at generation entrypoints

- [ ] `capcut/render/provider_router.py`
  - [ ] `generate()` takes the claimed approval as an explicit input
  - [ ] refuses to construct a client without a claimed approval
  - [ ] **removes the fallback chain** (`provider_router.py:139-147`) — on
        failure the router returns the failure instead of trying the next
        provider
  - [ ] `resolve_default()` is no longer reachable from a generation path
  - [ ] per-scene `provider` / `model_id` overrides remain supported, but are
        only honoured when they match the claimed approval
- [ ] `scripts/generate_ai_clips.py`
  - [ ] takes the approval id as an argument
  - [ ] model comes from the claimed artifact; the `--model` default
        (`generate_ai_clips.py:30`) is removed
  - [ ] exits non-zero when any scene fails (currently `return 0` at
        `generate_ai_clips.py:113`)
  - [ ] no job is submitted when the approval is missing/invalid
- [ ] `capcut/episode/spec_writer.py`
  - [ ] the LM Studio → OpenRouter transition (`spec_writer.py:243-247`)
        becomes explicit and reported
  - [ ] a local-scoped task stops and reports when LM Studio is unreachable
  - [ ] a remote provider is used only when the approval names it
- [ ] `capcut/lib/config.py`
  - [ ] `DAILY_AI_BUDGET_USD` (`config.py:132`) is either wired into a real
        guard or removed from the public config surface
  - [ ] `DEFAULT_VIDEO_FALLBACK` (`config.py:62`) — either consumed by the
        router as an explicitly approved alternative, or removed from the
        public surface. It is currently loaded and never used.

## 3. Bind the episode approval to the spec

- [ ] `capcut/lib/lifecycle.py`
  - [ ] approval records the sha256 of the reviewed `spec.json`
  - [ ] approval + hash written atomically
  - [ ] `revise()` removes both the sentinel and the recorded hash
- [ ] **New** `scripts/approve_episode.py`
  - [ ] the only supported way to approve an episode
  - [ ] reads the current `spec.json`, records its hash, idempotent
  - [ ] refuses when `spec.json` is missing or unreadable
  - [ ] non-zero exit and a clear message on failure
- [ ] `capcut/episode/spec_writer.py`
  - [ ] every write to `spec.json` revokes the approval first, in the same
        operation (`spec_writer.py:551-556` currently overwrites and leaves
        `.approved` in place)
- [ ] `scripts/render_final.py`
  - [ ] verifies the recorded hash against the current `spec.json` before any
        encoding work
  - [ ] mismatch → refuse, non-zero exit, `final.mp4` and `spec.sha256`
        untouched
  - [ ] a legacy approval with no hash → refuse with the re-approval command
        in the message
  - [ ] matching hash → render, or no-op when already rendered

## 4. Tests

- [ ] `tests/test_model_approval.py` (extend)
  - [ ] entrypoint refuses without approval — mocked client records zero
        `submit()` calls
  - [ ] entrypoint refuses on expired / mismatched / already-claimed approval
  - [ ] router does not contact the second provider of a former fallback
        chain
  - [ ] router does not substitute a provider that is available but not
        approved
  - [ ] a local-scoped text task does not reach the remote provider
  - [ ] no test calls a live API or spends credits
- [ ] `tests/test_lifecycle.py` (extend)
  - [ ] spec rewrite removes the sentinel and the recorded hash
  - [ ] approval records the hash of the current `spec.json`
  - [ ] `scripts/approve_episode.py` is idempotent
- [ ] `tests/test_final_renderer.py` (extend)
  - [ ] stale recorded hash → refusal, `final.mp4` untouched
  - [ ] matching recorded hash → render / no-op
  - [ ] legacy unbound approval → refusal with the re-approval command
- [ ] `python3 -m pytest tests/ -q` → green, no regression

  Spec: `openspec/changes/approval-enforcement-and-spec-binding/specs/episode-approval-binding/spec.md`

## 5. Documentation

- [ ] `AGENTS.md` — the "Approval gate (enforced)" and "Updates only via
      revise / remix" paragraphs are updated to describe the spec-bound
      approval and the enforced approval claim
- [ ] `AGENTS.md` — run table: add `scripts/approve_episode.py`
- [ ] `summary/tasks/016_stabilization_and_spend_safety.md` — mark P0 items
      23-25 done (or restate them against this change) and close the
      documentation item at line 56
- [ ] `summary/audit/026_…` — record the actual verification performed
- [ ] `CHANGELOG.md` entry
- [ ] archive `openspec/changes/approval-enforcement-and-spec-binding/` →
      `openspec/changes/archive/YYYY-MM-DD-approval-enforcement-and-spec-binding/`
- [ ] git commit + push on a feature branch, PR opened (per AGENTS.md branch
      workflow)

## 6. Not in scope

- [ ] `capcut/lib/lifecycle.py:154` `mark_matched()` removing `.approved` —
      separate cleanup, tracked in `summary/tasks/025_…`
- [ ] `openspec/changes/hybrid-media-workflow/` — stays in-flight; this
      change implements two of its acceptance criteria but does not archive it
- [ ] Approval panel UI changes, provider selection, price/spend policy
