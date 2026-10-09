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
pip install -r py/requirements.txt
cp .env.example .env   # fill API keys
```

See `AGENTS.md` for the full pipeline, project layout, and invariants.

## Status

R&D / prep, not production. See `AGENTS.md` → "Status".