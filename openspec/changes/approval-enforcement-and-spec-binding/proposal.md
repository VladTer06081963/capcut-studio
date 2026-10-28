# Change: Approval enforcement at generation entrypoints and spec-bound episode approval

## Why

The project declares an approval gate for paid generation and an approval
gate for episode renders, but neither is enforced in code. The model-approval
artifact is created by a working panel and consumed by nothing, so a paid
generation starts with a default model the user never named. The episode
approval is an empty marker, so regenerating `spec.json` after approval
leaves the approval in place and the final render proceeds on unreviewed
content. Both failures are silent, which is why they survived an audit that
found the rest of the pipeline largely sound.

## What Changes

- Claim the model-approval artifact at every generation entrypoint and refuse
  without it for remote and paid providers.
- Remove the implicit fallback chain from `ProviderRouter.generate()` and the
  automatic local → OpenRouter transition from the spec writer; stop and
  report instead.
- Remove the paid-model default from the AI-clip generation CLI and make that
  CLI exit non-zero when any scene fails.
- Record the sha256 of the reviewed `spec.json` in the episode approval, and
  revoke the approval atomically whenever `spec.json` is rewritten.
- Verify the recorded hash before the final renderer encodes anything; refuse
  with a non-zero exit on mismatch, leaving `final.mp4` untouched.
- Add `scripts/approve_episode.py` as the single supported way to approve an
  episode.

## Capabilities

**New Capabilities**

- `model-approval-enforcement` — how a generation entrypoint obtains and
  consumes the model-approval artifact, and what it must not do when the
  approval is missing or the approved provider is unavailable.
- `episode-approval-binding` — what an episode approval is bound to, when a
  change to the approved content revokes it, and what the final renderer must
  verify before it encodes anything.

**Modified Capabilities**

- None. `openspec/changes/hybrid-media-workflow/` already carries acceptance
  criteria for model approval and for no silent fallback. This change
  implements those criteria rather than restating them, and adds the
  spec-binding capability that change does not cover.

## Impact

- `capcut/lib/model_approval.py`, `capcut/render/provider_router.py`,
  `capcut/episode/spec_writer.py`, `capcut/lib/config.py`,
  `capcut/lib/lifecycle.py`
- `scripts/generate_ai_clips.py` (new required argument, paid-model default
  removed, exit code), `scripts/render_final.py` (hash check), **new**
  `scripts/approve_episode.py`
- `tests/test_model_approval.py`, `tests/test_lifecycle.py`,
  `tests/test_final_renderer.py` — mock-based only, no live API calls
- `AGENTS.md` — the "Approval gate (enforced)" and "Updates only via revise /
  remix" paragraphs, plus the run table
- No new dependency. No schema change to `spec.json` or `draft.json`. No
  change to the approval artifact format. No provider selection.

## Status

Proposed; implementation has not started. No external generation, no paid API
calls, and no provider selection are authorized by this proposal.

## Problem

Two AGENTS.md invariants are declared but not enforced in code. Both fail
*silently* — nothing errors out, so the pipeline looks healthy while the
guarantee is absent.

### 1. The model-approval artifact is never claimed by production code

`capcut/lib/model_approval.py:117` `claim_approval()` is the enforcement
primitive. Its only callers in the whole tree are
`tests/test_model_approval.py:48-89`. No module in `capcut/` or `scripts/`
consumes an approval artifact.

Consequences on the live spend paths:

- `scripts/generate_ai_clips.py:30` defaults `--model` to a paid KIE model
  (`bytedance/v1-lite-text-to-video`) and `:75` calls `client.submit(req)`
  without any approval check. Generation starts immediately, with a model the
  user never named.
- `capcut/render/provider_router.py:139-147` walks a fallback chain and, on
  failure, tries the *next* provider. That is a silent model/provider switch.
- `capcut/episode/spec_writer.py:243-247` falls back from local LM Studio to
  paid OpenRouter. A locally-scoped text task can therefore bill the cloud.
- `capcut/lib/config.py:132` defines `DAILY_AI_BUDGET_USD` and nothing reads
  it — there is no cost guard anywhere.

The approval panel (`frontend/model-approval/`, `scripts/model_approval_ui.py`)
creates a real one-time artifact with a 30-minute TTL and an atomic claim. It
is fully implemented. It is simply never consumed, so it *looks* like an
enforcement barrier to anyone reading the repo, and is not one.

This is already an open, tracked debt — not a newly discovered defect:

- `summary/tasks/016_stabilization_and_spend_safety.md:23-25` — P0 items
  "Подключить проверку/потребление approval-артефакта ко всем generation
  entrypoints и запретить silent fallback", "Убрать молчаливые переходы на
  другую модель/provider", "Добавить мок-тесты на отказ generation
  entrypoints без согласования и отсутствие silent fallback". All unchecked.
- `summary/tasks/016_…:19` — the decided rule: the user's explicit selection
  of an exact model is sufficient authorization for that task; a configured
  default is not.
- `openspec/changes/hybrid-media-workflow/proposal.md` — acceptance criteria
  already require an explicitly user-selected provider and exact model, an
  atomically claimed approval artifact, and no silent fallback. Those criteria
  have no implementation behind them.
- `.pi/skills/episode-planning/SKILL.md:28` — the skill already warns that
  "entrypoints do not yet enforce the approval artifact".

### 2. The episode approval gate is not bound to the spec it approves

`capcut/lib/lifecycle.py:147` `revise()` is the only code in the tree that
removes the `.approved` sentinel. It has no production callers — only
`tests/test_lifecycle.py:58`.

`capcut/episode/spec_writer.py:551-556` rewrites `spec.json` unconditionally
and does not touch `.approved`. `scripts/render_final.py:111` checks only for
the *presence* of the sentinel, never for what it approves.

The resulting sequence:

1. `spec.json` written from `brief.md`, `.approved` absent.
2. Human reviews and creates `.approved`.
3. `scripts/spec_from_brief.py` re-runs; `spec.json` is overwritten with a
   different content.
4. `.approved` is still present.
5. `scripts/render_final.py` renders the **new, unreviewed** spec.

The gate is satisfied literally and defeated in intent. AGENTS.md describes
"`draft` / `approved` → `revise` (regenerate spec.json from brief, **atomic
approval revoke**)" and labels the approval gate "(enforced)" — the revoke is
implemented nowhere.

## Change

Two separable changes. Both touch contracts, so both are specified.

### 1. Claim the approval artifact at every generation entrypoint

**New spec module:** `openspec/changes/approval-enforcement-and-spec-binding/specs/model-approval-enforcement/spec.md`

- `capcut/lib/model_approval.py` gains a public entry point that resolves and
  atomically claims an approval for an exact `(provider, model_id, task_scope)`
  triple, and raises `ApprovalError` when no valid, unclaimed, unexpired
  artifact matches.
- `capcut/render/provider_router.py` — `generate()` takes the claimed
  approval as an explicit input and refuses to construct a client without
  one. The fallback chain is **removed**: on provider failure the router
  returns the failure to the caller instead of trying another provider. The
  provider string in the approval artifact is the only provider that may be
  used for that task.
- `scripts/generate_ai_clips.py` — takes the approval id as an argument, takes
  the model from the claimed artifact rather than from a default, and exits
  non-zero when any scene fails. The current `--model` default
  (`scripts/generate_ai_clips.py:30`) is removed; the default was itself a
  silent paid-model selection.
- `capcut/episode/spec_writer.py` — the LM Studio → OpenRouter transition
  becomes an explicit, reported decision rather than an automatic fallback.
  A task scoped to a local model stops and reports when LM Studio is
  unreachable; it does not cross into a paid route on its own.
- `capcut/lib/config.py` — `DAILY_AI_BUDGET_USD` is either wired into the
  guard or removed from the public config surface. Leaving a config constant
  that reads like a budget but enforces nothing is worse than removing it.

**Boundary:** local generation (LM Studio, ComfyUI) is not required to carry
an artifact. The guard protects the two transitions that actually cost money
or leave the machine — a silent switch to a *different* provider, and an
automatic local → paid route change. A local model is never silently
upgraded to a paid one.

### 2. Bind the episode approval to the spec content it approves

**New spec module:** `openspec/changes/approval-enforcement-and-spec-binding/specs/episode-approval-binding/spec.md`

- Approval becomes a recorded act rather than an empty marker. Alongside the
  `.approved` sentinel, the approval records the sha256 of the `spec.json`
  that was reviewed. The sentinel presence keeps its current meaning; the
  recorded hash adds the binding.
- **New** `scripts/approve_episode.py` — the only supported way to approve an
  episode. It reads the current `spec.json`, writes the approval and its hash
  atomically, and is idempotent. It replaces the current practice of
  `touch .approved`, which cannot record what was approved.
- `capcut/episode/spec_writer.py` — every write to `spec.json` revokes the
  approval first, atomically, in the same operation. This is the
  `lifecycle.revise()` behaviour AGENTS.md already promises.
- `scripts/render_final.py` — before rendering, verifies that the recorded
  hash matches the current `spec.json`. A mismatch is a refusal with a
  non-zero exit and an explicit message, not a render of unreviewed content.
- A legacy episode whose approval carries no hash is reported as unbound and
  refused, with the re-approval command in the message. There is exactly one
  such episode today (`serials/cyber-heist/ep-01-infiltration`), and it is
  already rendered.

## Boundaries

- **The approval artifact format does not change.** Provider/model/scope, the
  30-minute TTL, the atomic one-time claim, and the consumed/expired audit
  trail stay as they are. This change only starts *consuming* the artifact.
- **No price research, price snapshot, spend cap, or subscription-limit check
  is introduced.** `summary/tasks/016_…:19` and AGENTS.md are explicit that
  these are not a precondition for the user's own subscription. `DAILY_AI_BUDGET_USD`
  is not a spend cap by this change — it is a stale config constant, and this
  change either wires it into a real guard or removes it.
- **No provider or model is selected, preferred, or made permanent.** The
  approval artifact names the provider/model for one task; nothing here
  changes a default.
- **No change to `spec.json` or `draft.json` schemas**, and no change to the
  `spec.sha256` idempotency key used by the final-render writer.
- **`openspec/changes/hybrid-media-workflow/` stays in-flight** and is not
  archived by this change. This change implements two of its acceptance
  criteria ("Every generation task must have an explicitly user-selected
  provider and exact model"; "Do not silently switch to a different
  model/provider…") and adds the spec-binding module, which that change does
  not cover.
- **The approval panel UI is not modified.** It already produces correct
  artifacts; only the consuming side changes.
- **The final-render writer, the Concat exporter, and the MCP server are not
  modified.** The MCP server exposes no generation tool today
  (`assemble_episode`, `open_in_concat`, `render_final`), so there is no MCP
  generation path to gate in this change.
- **`capcut/lib/lifecycle.py:154` `mark_matched()` is not fixed here.** It
  removes the `.approved` sentinel from a function whose name suggests it
  does the opposite, and it has no callers. It is listed in
  `summary/tasks/025_…` as a separate cleanup so this change stays reviewable.

## Validation

- Mock-based only. No test in this change calls a live API, spends credits, or
  submits a generation job.
- `scripts/generate_ai_clips.py` without a valid approval → refuses, exits
  non-zero, and the mocked client records **zero** `submit()` calls.
- `scripts/generate_ai_clips.py` with an expired, mismatched, or
  already-claimed approval → refuses, exits non-zero, zero `submit()` calls.
- `ProviderRouter.generate()` with a provider that fails → returns the
  failure; the second provider in the former fallback chain is **not**
  contacted.
- `ProviderRouter.generate()` with an approval naming provider A, but only
  provider B available → fails; provider B is not contacted.
- `capcut/episode/spec_writer.py` rewriting `spec.json` → the approval and its
  recorded hash are gone afterwards.
- `scripts/render_final.py` with `.approved` present and a stale recorded
  hash → refuses, exits non-zero, and `rendered/final.mp4` is untouched.
- `scripts/render_final.py` with a matching recorded hash → renders, or is a
  no-op when `final.mp4` already exists with a matching `spec.sha256`.
- `scripts/approve_episode.py` is idempotent and records the hash of the
  current `spec.json`.
- `python3 -m pytest tests/ -q` → green, no previously passing test regresses.
- `node mcp-server/test/concat_paths.test.js` → still passes (unchanged).
