# Change: Project-scoped Pi agent and workflow harness

## Status

Proposed; documentation and implementation planning only. No Pi runtime,
Telegram bot, Mini App, or workflow automation is installed or implemented by
this change.

## Context

The project needs a consistent agent interface for its video-series workflow.
Pi is already installed globally on the Mac Studio, so it must not be
reinstalled there. The intended contract is project-scoped: every machine that
checks out/sets up this project should use this repository's dedicated
harness; setup detects and reuses the existing Pi runtime on the Mac Studio,
and installs/verifies Pi on other hosts only if it is missing. The agent must
not depend on personal global configuration to understand this project.

## Decision

- Keep the existing local model-approval frontend for manually editing and
  selecting providers/models. It is not replaced by Pi.
- Set up Pi as the project agent with an individual, versioned harness:
  project instructions/context, a least-privilege tool policy, and project
  skills for repeatable lifecycle tasks.
- Treat MCP as the primary project integration: Pi must discover and use the
  capcut-studio MCP server through a supported adapter/transport.
- The initial project skill set lives in `.pi/skills/`; start Pi from the
  repository root with `pi --skill .pi/skills` and follow `.pi/README.md`.
- The currently observed Mac Studio Pi CLI version is `1.0.4`; reuse this
  global installation and do not reinstall Pi on that host.
- Make setup detect the Pi runtime on each host. Reuse the Mac Studio's
  existing global installation without reinstalling it; install Pi on other
  hosts only when absent. Do not commit a machine-specific binary or treat the
  Mac Studio's global install as present on other hosts.
- Telegram commands may provide an additional interface to Pi/MCP later, but
  they do not replace MCP and are lower priority than the local Pi↔MCP
  integration. A Telegram Mini App is a later production UI option.
- The user selected MiniMax M3 as the current coding-agent model. Verify the
  exact Pi model identifier before the first prompt; do not guess/substitute a
  different model, alter global Pi configuration, or put credentials in the
  repository.
- Keep workflows approval-gated and file-backed. Model choice remains explicit
  in the existing frontend and any generation action must honor the
  one-task approval artifact.

## Harness responsibilities

- Load repository guidance and the active workflow context.
- Work through bounded orchestrator-authored tasks relayed by the user; return
  inspectable evidence for independent review.
- Promote only verified, repeated workflows into stable skills/scripts; the
  initial skill set is a scaffold, not proof that those workflows are tested.
- Expose named skills for brief/spec/continuity review, asset-library work,
  assembly, and polish handoff, each with clear inputs, outputs, and stop
  conditions.
- Restrict tools to the minimum required for each skill. Separate read-only
  inspection from file writes, external API calls, media generation, and
  publishing actions.
- Require explicit user request/approval before generation with an exact
  provider/model, and prohibit silent provider/model fallback.
- Preserve lifecycle sentinels, source attribution, immutable final renders,
  non-destructive revise/remix, and the user's existing files.
- Surface uncertainty and failures; never report a workflow step as complete
  without checking its persisted output.

## Interfaces

- **Now:** record the design, installation fact, setup reference, and open
  implementation questions in task documentation.
- **Later:** Telegram text-command bridge for task requests/status.
- **Later production option:** Telegram Mini App for richer selection and
  review; keep the local model frontend available for manual model management.

## Open decisions before implementation

- Pi package version and supported project-local installation mechanism.
- Harness file layout and how project setup installs/verifies the Pi runtime.
- Exact skills, schemas, and persisted artifacts per workflow.
- Telegram bot ownership, transport, authentication, hosting, and which skills
  are safe to invoke through chat.
- The installed `pi-mcp-adapter` version, changelog, compatibility, and
  whether an update is needed before the project MCP server is configured.
- Which tools require confirmation, and how each process records its audit
  trail.

## Validation approach

- Verify the Pi installation procedure against the official `https://pi.dev/`
  documentation when implementation is scheduled.
- Test harness discovery, skill loading, tool allow-lists, and project setup on
  each supported host without invoking paid model APIs.
- Test Telegram routing separately from the future Mini App.
