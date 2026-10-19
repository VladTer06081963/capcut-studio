# Tasks: Project-scoped Pi agent

- [x] Record that Pi is already installed globally on the Mac Studio and must
  be reused there without reinstalling.
- [x] Record the observed Mac Studio Pi version (`1.0.4`) and project launch
  command; do not force a reinstall or global config change.
- [x] Decide that setup detects Pi on every host, reuses the global Mac Studio
  installation, and installs/verifies Pi on another host only if it is absent;
  the project uses its own dedicated harness.
- [x] Preserve the existing local model-selection frontend for manual provider
  and model management.
- [x] Record MCP as the primary Pi/project integration and Telegram as a
  possible later auxiliary interface.
- [x] Create initial `.pi/README.md` harness notes and project skills for
  orientation, worktree review, episode planning, asset-library work, and
  assembly handoff.
- [x] Define the human-relayed orchestrator ↔ Pi collaboration loop and
  independent evidence-based review.
- [x] Record the user's selection of MiniMax M3 for Pi coding sessions.
- [ ] Verify the exact Pi model identifier for MiniMax M3 before sending the
  first prompt; do not guess or silently substitute another model.
- [ ] Verify the current official Pi package/version and exact installation
  steps at `https://pi.dev/`; define setup detection and version policy without
  reinstalling Pi on the Mac Studio.
- [ ] Define harness layout, project-specific context loading, tool
  permissions, approvals, and persisted run/audit state.
- [ ] Inspect installed `pi-mcp-adapter` version and changelog; decide whether
  `pi update --extensions` is necessary before changing installed software.
- [ ] Connect the capcut-studio MCP server to Pi using the supported adapter
  and transport; validate tool discovery and safe read-only calls.
- [x] Register the project MCP server in root `.mcp.json` using the
  project-relative stdio entrypoint and confirm Pi discovers it.
- [x] Connect the server and verify the live 2-tool list and argument schemas
  without invoking either mutating tool.
- [ ] Review tool side effects against server/scripts before allowing Pi to
  call either one; MCP discovery/trust is not execution approval.
- [ ] Define project skills with input/output contracts for brief/spec,
  continuity, asset ingest/index, assembly, and polish handoff.
- [ ] After MCP integration is working, design an optional Telegram command
  bridge with authentication and a strict allow-list of safe skills.
- [ ] Implement setup checks that verify Pi and the project harness are
  available on every supported host.
- [ ] Add fixture/mock tests for harness discovery, skill loading, permissions,
  approval requirements, and Telegram command routing.
- [ ] Consider a Telegram Mini App only after the text-command workflow is
  validated; it must not replace the existing local model frontend.
- [ ] Verify skill discovery with the project launch command and verify
  `AGENTS.md` context loading without sending a model prompt.
- [ ] Exercise Pi↔MCP through bounded tasks; only then refine skills and
  extract repeated deterministic operations into tested scripts.
