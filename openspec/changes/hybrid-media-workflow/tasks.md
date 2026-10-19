# Tasks: Hybrid media workflow

- [x] Inventory every generation entrypoint (CLI, Python clients/router, MCP,
  scripts, batch/cron), resolving effective defaults, overrides, retries, and
  fallbacks. Do not call paid APIs. Evidence:
  `summary/audit/016_provider_generation_inventory.md`.
- [x] Specify user-selected provider/model approval for the current task;
  do not require price research, price snapshots, output-count caps, spend
  caps, or MiniMax subscription-limit lookups. Do not silently switch model or
  provider. See `specs/workflow-profiles/spec.md`.
- [x] Select persisted one-task approval artifacts, stored outside the repo,
  with an atomic claim, 30-minute expiry, provider/model + task binding, and
  retained consumed/expired audit state.
- [x] Select a local desktop-accessible web interface for model/task selection;
  initial model choices come from a local registry, not live catalog or pricing
  calls. Selecting a model alone must not submit generation.
- [ ] Specify prototype and production profile names, configuration, and
  isolated asset/index/output roots; add migration/compatibility behavior for
  existing `library/` and `serials/` paths.
- [ ] Define an asset metadata contract covering stock provenance/license and
  prototype image provenance/model/prompt/settings/hash/review/promotion state.
- [ ] Register current free stock sources and requirements; define criteria for
  adding future ingest sources without weakening license and attribution checks.
- [ ] Trace Concat native format and test still images with a local sample;
  define image clip duration, fit/crop, track mapping, and conversion behavior.
- [ ] Update spec/matcher/assembler contracts to support an explicitly
  referenced or requested image on a parallel overlay track, without silently
  replacing the main stock-video track.
- [ ] Implement selected-model approval enforcement across generation
  entrypoints; fail closed when the provider/model is not explicitly approved,
  and stop rather than silently switching models/providers.
- [x] Implement a loopback-only local web UI for provider/model selection and
  task-scope review, creating a one-task approval artifact without collecting
  credentials or contacting provider catalog/pricing endpoints.
- [x] Keep the panel frontend visible as separate `index.html`, `styles.css`,
  and `app.js` files in `frontend/model-approval/`, served by the local API
  process rather than embedded in Python.
- [ ] Implement profile separation and explicit, audited asset promotion from
  prototype to production.
- [ ] Add mocked/unit tests for model approval, no silent retry/fallback to a
  different model/provider, profile isolation, provenance, promotion, and image
  timeline serialization.
- [x] Add focused unit tests for one-task approval creation, private file
  permissions, exact model/scope binding, atomic one-time claim, and expiry.
- [ ] Add HTTP/UI tests and generation-entrypoint rejection tests before
  treating the panel as an enforcement barrier.
- [ ] Run targeted tests and a local Concat UI check with fixtures only; do not
  run a model that the user has not explicitly selected/approved for the task.
- [ ] Update PRD, AGENTS, `.env.example`, task/audit records, and changelog to
  match the verified implementation; archive this change after acceptance.
