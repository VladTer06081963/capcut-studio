## Purpose

Give the project one consistent, project-scoped agent harness so that every
host that checks out this repository works from the same rules, skills and
tool policy instead of a personal global configuration.

## ADDED Requirements

### Requirement: Project-scoped Pi runtime and harness

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

#### Scenario: The Mac Studio runtime is reused

- **WHEN** setup runs on the Mac Studio, where a compatible global Pi installation already exists
- **THEN** that installation SHALL be reused and SHALL NOT be reinstalled

#### Scenario: Another host installs only when needed

- **WHEN** setup runs on a host where no compatible Pi runtime is present
- **THEN** Pi SHALL be installed on that host, and only on that host

#### Scenario: Project rules come from the repository

- **WHEN** an agent session starts in this project
- **THEN** the project instructions, context, skills and tool policy SHALL come from this repository's harness, and a personal/global Pi configuration SHALL NOT be the only source of project rules

#### Scenario: The model identifier is verified, not guessed

- **WHEN** the first prompt is prepared for the user-selected MiniMax M3 model
- **THEN** the exact Pi model identifier SHALL have been verified, and the project SHALL NOT guess an identifier, substitute another model, or alter global Pi configuration

#### Scenario: Version facts are not treated as setup proof

- **WHEN** setup automation is implemented
- **THEN** the exact package/version and the project-local installation method MUST have been verified against official Pi documentation first

### Requirement: The existing model-selection frontend is kept and used

The local model-approval frontend SHALL remain available for manual provider
and exact-model selection/editing. Pi SHALL use, not replace or bypass, the
project's explicit model-approval contract for generation.

#### Scenario: Manual selection stays possible

- **WHEN** an operator wants to choose a provider and exact model by hand
- **THEN** the local model-approval frontend SHALL remain available for that selection and editing

#### Scenario: The agent goes through the same contract

- **WHEN** the agent triggers a generation
- **THEN** it SHALL go through the project's explicit model-approval contract rather than replacing or bypassing it

### Requirement: Skills declare their scope and stop conditions

Each project skill SHALL define its purpose, required inputs, allowed tools,
persisted outputs, approval requirements, and stop/error conditions. Skills
SHALL follow the project lifecycle and must not silently overwrite user data,
change provider/model, generate paid media, or publish/commit/push.

Read-only inspection, repository edits, external service calls, generation,
and publishing SHALL be distinct capabilities. Tools with consequential
effects SHALL require the relevant explicit user approval; approval for one
task SHALL NOT authorize unrelated tasks.

#### Scenario: A skill declares its contract

- **WHEN** a project skill is defined
- **THEN** it SHALL state its purpose, required inputs, allowed tools, persisted outputs, approval requirements and stop/error conditions

#### Scenario: A skill cannot do consequential work silently

- **WHEN** a skill runs
- **THEN** it SHALL NOT silently overwrite user data, change provider/model, generate paid media, or publish/commit/push

#### Scenario: Approval does not carry over to another task

- **WHEN** the user approves one action
- **THEN** that approval SHALL NOT authorize an unrelated task

#### Scenario: Capability classes stay distinct

- **WHEN** the harness exposes its tools
- **THEN** read-only inspection, repository edits, external service calls, generation and publishing SHALL be distinct capabilities, and tools with consequential effects SHALL require the relevant explicit user approval

### Requirement: MCP is the primary project-tool integration

The capcut-studio MCP server SHALL be the primary project-tool integration for
Pi. Project setup SHALL configure Pi to discover the repository's MCP tools
through a supported transport/adapter and SHALL verify the exposed tool list.
Tool access SHALL follow the project harness policy; discovery alone SHALL NOT
authorize paid generation or other consequential actions.

#### Scenario: The MCP tools are discovered and verified

- **WHEN** project setup completes
- **THEN** Pi SHALL be configured to discover the repository's MCP tools through a supported transport or adapter, and the exposed tool list SHALL have been verified

#### Scenario: Discovery is not authorization

- **WHEN** the agent has discovered the MCP tool list
- **THEN** discovery alone SHALL NOT authorize paid generation or any other consequential action

### Requirement: Chat interfaces are auxiliary and tested

Telegram text commands MAY be added as an auxiliary interface after the local
Pi-to-MCP integration is established. They SHALL authenticate the sender and
route only to an explicit allow-list of skills. A Telegram Mini App is a later
production option and SHALL NOT replace MCP or the existing local
model-selection frontend.

Telegram and Mini App integrations SHALL not be considered implemented until
their authentication, routing, approval, and audit behavior are tested.

#### Scenario: A chat command reaches only allow-listed skills

- **WHEN** a Telegram text command is received
- **THEN** the sender SHALL be authenticated and the command SHALL route only to an explicit allow-list of skills

#### Scenario: The Mini App does not replace the local path

- **WHEN** a Telegram Mini App is considered
- **THEN** it SHALL NOT replace MCP or the existing local model-selection frontend

#### Scenario: Untested chat integrations are not called implemented

- **WHEN** a Telegram or Mini App integration is reported
- **THEN** its authentication, routing, approval and audit behavior SHALL have been tested before it is called implemented
