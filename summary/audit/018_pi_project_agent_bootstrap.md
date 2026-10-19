# Audit 018: Pi project harness bootstrap

**Date:** 2026-10-12  
**Scope:** Read-only check of the Pi CLI already installed on this Mac Studio
and creation of project-local harness notes/skills. No Pi prompt or model API
request was sent.

## Existing installation

- `pi --version` returned `1.0.4` on this Mac Studio.
- `pi --help` exposes `--skill <path>`, `--model`, `--provider`,
  `--no-session`, and automatic context-file controls for `AGENTS.md` and
  `CLAUDE.md`.
- Pi is already installed globally on this Mac Studio. This project setup must
  reuse it and must not reinstall it here.
- Other hosts must detect their own Pi installation; installation instructions
  and version policy for hosts without Pi remain to be verified before setup
  automation.

## Project harness

- `.pi/README.md`: startup, required reading list, MiniMax selection boundary,
  and safety rules.
- `.pi/skills/project-orientation/SKILL.md`
- `.pi/skills/worktree-review/SKILL.md`
- `.pi/skills/episode-planning/SKILL.md`
- `.pi/skills/asset-library/SKILL.md`
- `.pi/skills/assembly-handoff/SKILL.md`

Proposed launch from the repository root, in a separate terminal:

```bash
pi --skill .pi/skills
```

The user selected MiniMax M3 for the coding-agent session. Verify the exact Pi
model identifier for MiniMax M3 in Pi's available model list before submitting
the first prompt; do not guess or substitute another model. No model request
was sent, no global Pi configuration was changed, and no API key was read or
stored.

The local model-selection frontend remains independent. Pi's coding-agent
model choice is not an approval to generate project media.

## MCP priority clarification

The project owner clarified that MCP is a primary project goal. The installed
`pi-mcp-adapter` is therefore relevant to the intended Pi integration. Its
available-update notice must not be dismissed as unrelated: inspect the
extension version/changelog and compatibility, then connect Pi to the
capcut-studio MCP server. No extension update was run during this audit.
Telegram commands are an auxiliary/later interface, not a replacement for MCP.

## Remaining verification

- Pi startup showed `AGENTS.md`, all five project skills, and `pi-mcp-adapter`
  loaded.
- Root `.mcp.json` was created with a relative stdio command:
  `node ./mcp-server/index.js`. After project-server approval and Pi restart,
  discovery showed `capcut-pipeline` with two tools; explicit connect reported
  the server live and displayed both schemas. Neither tool was called.
- Before allowing a tool invocation, inspect actual side effects in
  `mcp-server/index.js` and its child scripts; do not rely only on the agent's
  description that assembly writes a single draft file.
- The exact Pi model identifier for MiniMax M3 still needs confirmation before
  a model request.
- Define and test tool allow-lists and approval boundaries; skill text alone is
  guidance, not a technical security sandbox.
- Implement host setup detection and Telegram routing as separate tasks.

## Safety and worktree

No media generation, external provider API call, Telegram setup, package
installation, global Pi config edit, commit, or push was performed. The
project-scoped `.mcp.json` was created after explicit user approval; MCP
discovery, connect, and tool-schema listing were performed without invoking
either project tool.
