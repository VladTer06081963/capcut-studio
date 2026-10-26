# capcut-studio

Long-form video series production pipeline. Sister project to
[`comic-studio`](../comic-studio). Library-first: assets are pre-generated
and indexed, episodes are assembled from the library.

## Quick start

```bash
git clone <this-repo>
cd capcut-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -r capcut/requirements.txt
cp .env.example .env   # fill API keys
```

See `AGENTS.md` for the full pipeline, project layout, and invariants.

### Running the tests

```bash
source .venv/bin/activate
python -m pytest tests/ -q
```

Tests run from the repository root. The pipeline package was renamed
`py/` → `capcut/` in fixation 022 precisely because the old name shadowed
the `py` library pytest depends on — see
`summary/audit/021_health_check_followups.md` (§5.1) and
`summary/audit/022_rename_py_to_capcut.md`.

## Local model approval panel

Start the local-only model selection panel from the repository root:

```bash
python3 scripts/model_approval_ui.py
```

Open `http://127.0.0.1:8765/` in a browser. The model/provider suggestions are
read from `config/model_registry.json`; add only exact IDs you have chosen to
that local registry. The panel does not query provider catalogs or prices, ask
for credentials, or start generation. An explicit confirmation creates a
one-task approval artifact under
`~/Library/Application Support/capcut-studio/model-approvals/`, expiring after
30 minutes. Stop the panel with Ctrl+C.

The visible frontend source is in `frontend/model-approval/` (`index.html`,
`styles.css`, `app.js`). The Python script serves these files and the local API.

**Current limitation:** generation entrypoints do not yet consume/check these
approval artifacts. Do not treat the panel as an enforcement barrier or run
generation scripts on the assumption they are gated.

## Project Pi agent (planned)

Pi `1.0.4` is already installed globally on the Mac Studio and must be reused there
without reinstalling. Project setup detects Pi on each host and installs it
only on other hosts where it is missing, then uses this repository's dedicated
harness and skills. The current model
frontend remains the manual surface for provider/model editing. MCP is the
primary project-tool integration for Pi; Telegram is only a possible later
auxiliary command interface, with a Mini App considered for production. See
`summary/tasks/018_pi_project_agent_harness.md`
and `openspec/changes/pi-project-agent/`. Verify current Pi installation
instructions at <https://pi.dev/> before implementing setup automation.

Project-specific Pi harness notes and skills are now staged in `.pi/`. Start
Pi from the repository root in its own terminal:

```bash
pi --skill .pi/skills
```

Read `.pi/README.md` first. The selected coding-agent model is MiniMax M3;
verify its exact Pi model ID before sending the first prompt.
Do not put credentials in project files or change global Pi configuration.

## Status

R&D / prep, not production. See `AGENTS.md` → "Status".