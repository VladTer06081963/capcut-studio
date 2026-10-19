# Project-scoped Pi agent

## Runtime and harness

The project SHALL use Pi as a project-scoped agent. Setup SHALL detect whether
a compatible Pi runtime is available on each host. The existing global Pi
installation on the Mac Studio SHALL be reused without reinstalling; another
host SHALL install Pi only if it is absent. The repository's dedicated harness
SHALL provide project-specific instructions, context, skills, and
least-privilege tool policy. A personal/global Pi configuration SHALL NOT be
the only source of project rules.

The Mac Studio's existing global Pi installation is an operational fact, not
proof that another host is configured. The exact package/version and
project-local installation method MUST be verified against official Pi
documentation before setup automation is implemented.

The observed Pi CLI version on the Mac Studio is `1.0.4`. The initial project
harness SHALL live in `.pi/README.md` and project skills SHALL live under
`.pi/skills/`. The initial interactive command is
`pi --skill .pi/skills`, run from the repository root. The user selected
MiniMax M3 for coding sessions. Before the first prompt, the exact Pi model
identifier for MiniMax M3 SHALL be verified; the project SHALL not guess,
substitute another model, or alter global Pi configuration.

## Existing model-selection frontend

The local model-approval frontend SHALL remain available for manual provider
and exact-model selection/editing. Pi SHALL use, not replace or bypass, the
project's explicit model-approval contract for generation.

## Skills and tool policy

Each project skill SHALL define its purpose, required inputs, allowed tools,
persisted outputs, approval requirements, and stop/error conditions. Skills
SHALL follow the project lifecycle and must not silently overwrite user data,
change provider/model, generate paid media, or publish/commit/push.

Read-only inspection, repository edits, external service calls, generation,
and publishing SHALL be distinct capabilities. Tools with consequential
effects SHALL require the relevant explicit user approval; approval for one
task SHALL NOT authorize unrelated tasks.

## MCP integration

The capcut-studio MCP server SHALL be the primary project-tool integration for
Pi. Project setup SHALL configure Pi to discover the repository's MCP tools
through a supported transport/adapter and SHALL verify the exposed tool list.
Tool access SHALL follow the project harness policy; discovery alone SHALL NOT
authorize paid generation or other consequential actions.

## User interfaces

Telegram text commands MAY be added as an auxiliary interface after the local
Pi-to-MCP integration is established. They SHALL authenticate the sender and
route only to an explicit allow-list of skills. A Telegram Mini App is a later
production option and SHALL NOT replace MCP or the existing local
model-selection frontend.

Telegram and Mini App integrations SHALL not be considered implemented until
their authentication, routing, approval, and audit behavior are tested.
