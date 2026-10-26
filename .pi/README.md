# Pi harness for capcut-studio

Pi is already installed globally on the Mac Studio. The version observed here
is `1.0.4`; do not reinstall Pi on this machine. The repository owns the
project-specific instructions and skills.

## Start

From the repository root in a separate terminal:

```bash
pi --skill .pi/skills
```

Pi should also discover the repository's `AGENTS.md` from the project
directory. At startup, read `AGENTS.md`, this file, and the relevant workflow
skill before taking action. If Pi reports that it cannot load the project
skills, stop and report the discovery issue rather than proceeding without the
harness.

## Required reading

1. `AGENTS.md` — project invariants, lifecycle, user approvals, and repository
   workflow.
2. `README.md` — quick start, local model panel, and current Pi status.
3. `summary/tasks/016_stabilization_and_spend_safety.md` — current generation
   approval work and known limitations.
4. `summary/tasks/018_pi_project_agent_harness.md` and
   `openspec/changes/pi-project-agent/` — intended project-agent architecture.
5. `summary/audit/016_provider_generation_inventory.md` — actual provider and
   generation entrypoints; do not assume they enforce model approval.
6. For a requested change, read its specific task, audit, OpenSpec, and
   neighboring code before editing.

Do not load or dump `.env`, API keys, auth stores, or other credentials. Do not
read generated media or external `library/` contents unless a requested task
specifically requires it.

## Model policy

The user selected MiniMax M3 as the current provider/model direction for Pi
coding sessions, with possible later evaluation of a small local model. Before
the first prompt, verify the exact Pi model identifier corresponding to
MiniMax M3 in Pi's available model list; do not guess or silently substitute a
different MiniMax model. Do not edit the user's global Pi configuration or
store a key in the repository. Pi recognizes the `MINIMAX_API_KEY` environment
variable; credentials must be provided out of band by the user.

This coding-agent model choice is separate from models selected in the
CapCut Studio model-approval frontend. Do not call this provider for project
media generation. Do not initiate a Pi prompt that sends a request until the MiniMax M3 model
identifier has been verified and selected in the Pi session.

## Safety boundary

- Start with read-only inspection and state the exact task/output before edits.
- Preserve unrelated worktree changes and user data; never use `git add .`,
  destructive cleanup, or broad file rewrites.
- Do not commit, push, publish, install extensions, or send Telegram messages.
- Do not run generation, paid APIs, or automatic fallback without the
  task-specific user approval and implemented enforcement.
- Treat the existing local model-approval frontend as the manual model
  management surface; this Pi harness does not replace it.
- Verify persisted outputs and targeted tests before reporting completion.

## Collaboration loop

The user relays bounded tasks from the orchestrator in a separate Pi terminal.
Return a factual handoff: inspected/changed paths, commands run, test results,
unresolved questions, and exact output locations. Do not expand the task.
The orchestrator independently reviews the report and diff. Treat current
skills as an initial scaffold: refine them only after a workflow has been
exercised and verified. Extract repeated deterministic operations into
testable scripts; do not automate an unverified process.

## Skills

Project skills are under `.pi/skills/`. Load the skill that matches the
requested process. Skills add focused steps; they do not override `AGENTS.md`
or user approvals.
