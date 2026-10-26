---
name: project-orientation
description: Orient Pi to capcut-studio's workflow, current state, and safety boundaries before work.
---

# Project orientation

Before changing files:

1. Read `.pi/README.md`, `AGENTS.md`, and `README.md`.
2. Read `summary/tasks/016_stabilization_and_spend_safety.md` and
   `summary/tasks/018_pi_project_agent_harness.md`.
3. Read the relevant audit/OpenSpec/task for the requested work. For provider
   or generation work, start with `summary/audit/016_provider_generation_inventory.md`
   and `openspec/changes/hybrid-media-workflow/`.
4. Inspect `git status --short` and preserve every unrelated modification and
   untracked user file.
5. Summarize the requested scope, files likely to change, and any required
   approval before using write or external tools.

Project workflow: brief → asset library → spec → assemble → polish. The
library is the source of truth; lifecycle state is persisted on disk;
`rendered/final.mp4` is immutable; revisions use revise/remix rather than
destructive edits. Stock provenance and license/attribution are mandatory.

The user currently wants Pi as a project-specific agent, selected MiniMax M3
for coding sessions, and may later evaluate a small local model. Verify the
exact Pi model identifier for MiniMax M3 before the first prompt; do not
substitute another model or modify global Pi settings. The project-local
model-approval frontend remains the manual interface for media models.

Stop and report when the requested work would require an unapproved model,
paid media generation, credential access, Telegram transmission, destructive
data operations, commit, or push.
