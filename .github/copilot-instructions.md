# Copilot instructions for capcut-studio

## Project intent

CapCut Studio is a library-first pipeline for long-form video series. Episodes are planned as structured specs, matched against a reusable asset library, assembled into reviewable drafts, then polished and rendered. The project is R&D: optimize for learning and creative iteration without confusing an experiment with a proven production path.

Provider and model choices are deliberately replaceable. The goal is to find a cloud setup that delivers the speed and quality needed for finished work, while using local models, free tiers, or trials where practical to explore concepts and develop creative direction cheaply. Do not treat any provider named in older docs or code as a permanent product decision.

## Source of truth and keeping work coherent

Before changing behavior, read the relevant code and reconcile these project records:

- `AGENTS.md` defines durable architecture and invariants.
- `summary/PRD/PRD.md` describes intended product behavior and scope; check its status and date before treating a proposal as implemented.
- `summary/tasks/` and `summary/audit/` preserve completed work, decisions, evidence, and known gaps.
- Current code, tests, `.env.example`, and package manifests establish what actually runs today.
- `CHANGELOG.md` records notable landed changes.

When these disagree, do not silently pick one or repeat stale claims as facts. Establish whether the difference is an intentional decision, an outdated document, or unfinished work. Make the smallest coherent update to the affected code, tests, configuration reference, and project records; preserve older history as history rather than rewriting it to match current behavior. Do not claim a workflow, provider, or integration works without current evidence.

For multi-step work, keep the requested outcome in view through completion: check the original scope before wrapping up, verify every promised change, and clearly identify anything deferred or blocked. If an implementation decision changes the plan, record that decision where future work will find it.

## OpenSpec change workflow

Use OpenSpec for future substantial changes: cross-component work, pipeline/API or persisted-data contracts, lifecycle/approval rules, provider architecture, or a significant new capability. Before implementation, create `openspec/changes/<slug>/proposal.md` and `tasks.md`; add `specs/<module>/spec.md` when module behavior or a contract changes. Keep these focused on the decision, scope, and acceptance/validation criteria.

Small, isolated fixes that do not change a contract need no OpenSpec proposal; use `summary/tasks/` and `summary/audit/` as appropriate. Do not retroactively OpenSpec-ify completed work. On completion, update the summary audit with actual outcome and validation, update `CHANGELOG.md` when warranted, and archive the change under `openspec/changes/archive/`. Until such a change exists, do not describe OpenSpec as an active process already used by past work.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r py/requirements.txt
cp .env.example .env
```

Set only the credentials and service URLs required for the task. Never put secrets in source files, tests, summaries, or commits.

## Build, test, and lint

There is no configured root build or lint command. Python tests use `unittest` discovery (some tests also use `pytest` fixtures, so install the dependencies declared by the project/test environment):

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Run one test method:

```bash
python -m unittest tests.test_config.ConfigTest.test_defaults_when_no_env
```

Or run a test file directly:

```bash
python -m unittest tests.test_config
```

`mcp-server/package.json` currently has a placeholder `npm test` script that intentionally exits with an error; do not present it as a passing test suite. The MCP server entrypoint is `node mcp-server/index.js` (install its dependencies with `npm install` in `mcp-server/` when needed).

## Architecture

- `py/lib/config.py` loads environment configuration and resolves library/serial paths and provider defaults. `py/lib/lifecycle.py` models episode state through on-disk files.
- `py/episode/spec_writer.py` turns an episode brief and show bible material into validated `spec.json`.
- `py/index/embedder.py` indexes clips and provides text-to-asset search over the shared SQLite library index; `py/search/matcher.py` matches scene descriptions and persists `matched.json`.
- `py/assemble/concat_exporter.py` converts a spec and its matches into a Concat timeline/draft. `mcp-server/` exposes workflow actions to MCP clients, and `scripts/` contains CLI entrypoints for pipeline operations.
- `bible/` holds canonical creative references; `library/` holds reusable source assets and their metadata; `serials/` holds episode inputs, intermediate artifacts, and renders.

The end-to-end flow is brief + bible → validated spec → matched library assets → editable draft/preview → human review and polish → final render. Generation can add assets to the library, but episode assembly should prefer existing indexed assets.

## Durable conventions and safety boundaries

- The library is the source of truth for media. References rely on stable IDs and file hashes; metadata and attribution are part of the asset contract. Index updates should be additive; remove indexed data only through an explicit cleanup/GC operation.
- Episode state is persisted on disk, not held in memory. Respect `.draft`/`.approved`, `matched.json`, and the lifecycle helpers. Preserve approval gates and idempotency.
- Treat `rendered/final.mp4` as immutable. Iterate through revise/remix workflows rather than silently overwriting a final or published episode.
- `spec.json`, match results, asset metadata, and Concat drafts are interfaces between pipeline stages. Validate changes at those boundaries and keep producers, consumers, and tests in sync.
- Provider selection and fallback behavior must be derived from the current implementation, not assumed from this file or historical docs. Provider identifiers and precedence are configuration/API behavior; changes should update the relevant router, CLI/spec handling, `.env.example`, tests, and current documentation together.
- Stock assets require source attribution and license metadata. Keep secrets in local environment configuration and out of committed artifacts.
- Follow the Python 3.11+ and ESM JavaScript patterns used by neighboring code. No formatter or linter is configured.

## Provider and model experiments

Treat provider evaluation as a documented decision process, not a silent default swap:

1. **Approve the model before generation.** State the provider and exact model for the requested task; proceed when the user specifies or approves that model. A configured default is not approval. Never silently switch provider/model or treat approval for one task as approval for an unrelated future task.
2. **Do not impose price research or caps as a gate.** MiniMax image generation is covered by the user's subscription for this workflow: do not query limits, calculate per-output pricing, request a price snapshot, or require a monetary/credit cap. The user may check prices independently if they wish. Do not turn provider-native credits into a fabricated currency estimate.
3. **Keep routing explicit.** Do not automatically switch from a failed local call to a paid cloud provider or silently fall back to a different model. If the chosen model cannot be used, report the failure and wait for the user to select/approve an alternative.
4. **Prototype and production evidence.** Use local/trial options for creative exploration where suitable. Label prototypes, and do not imply they establish final production quality. For provider evaluation, record quality, latency, failures/limitations, and prototype/production status; include cost only when the user requests it or it is material to a specific decision.
5. **Record the decision.** In the relevant `summary/tasks/` or `summary/audit/` record, capture the date, task/use case, provider/model identifiers, tested settings/prompt or sample reference, observed quality, latency, failures/limitations, and whether the result is prototype-only or approved for a workflow. Never include API keys or other secrets.
6. **Promote deliberately.** A trial or prototype provider does not become a default just because it worked once. Update code defaults, configuration examples, tests, PRD/AGENTS guidance, and changelog as appropriate, and state what was actually verified. Preserve a viable fallback where the current design supports one.

The desired outcome may be a hybrid: inexpensive/local experimentation for creative development and a faster, higher-quality cloud route for selected final tasks. Keep provider choice configurable so the project can learn and change without rewriting episode data or obscuring which model produced an asset.

## Change workflow

For changes that affect pipeline behavior, trace the relevant path across CLI, domain module, persisted file format, configuration, and tests before editing. Afterward, run the narrowest relevant tests, then broader tests when warranted. Update the project records when behavior, defaults, status, or decisions change; keep the PRD aspirational/current-state labels accurate and keep audit/task history evidentiary. In the final handoff, summarize what changed and verified, and name any unresolved gap rather than implying completion.
