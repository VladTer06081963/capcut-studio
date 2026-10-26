# Tasks: Rename `py/` package to `capcut/`

## 1. Mechanical rename

- [x] `git mv py capcut`
- [x] `capcut/requirements.txt` moved with the directory

## 2. Import rewrite (Python)

- [x] `capcut/**` intra-package imports: `from py.X` → `from capcut.X`,
      `from .X` → unchanged, `import py.X` → `import capcut.X`
- [x] `scripts/*.py` imports
- [x] `tests/*.py` imports
- [x] `sys.path` bootstrap comments mentioning `py/`

## 3. Documentation rewrite

- [x] `AGENTS.md`: project layout tree, all `py/` references, install
      command `pip install -r capcut/requirements.txt`
- [x] `README.md`: quick-start install command
- [x] `README_RU.md`: quick-start install command + the stale footgun block
- [x] `summary/**`: PRD updated (current state); historical audit/tasks
      files **intentionally keep** their original `py/` references — they
      record the tree as it was at the time
- [x] `.pi/**`: no `py/` references found (verified by grep)

## 4. Validation

- [x] `python -m pytest tests/ -q` passes **from repo root** (primary
      acceptance criterion) — 161 passed
- [x] `python -m pytest tests/ -q` passes from an unrelated CWD
- [x] `grep -rnE "^\s*(from|import)\s+py[.\s]" --include="*.py" .`
      returns zero results outside `.venv/`
- [x] `grep -rn "\bpy/" --include="*.md" .` returns zero stale path
      references in live docs (outside `.venv/`, `node_modules/`, and
      historical audit entries that intentionally describe the old layout)
- [x] `python scripts/assemble_episode.py --help` works
- [x] `python -c "import capcut.lib.config"` resolves
- [x] `node mcp-server/test/concat_paths.test.js` still passes (4/4)

## 5. Fixation bookkeeping

- [x] `summary/audit/022_rename_py_to_capcut.md`
- [x] `summary/tasks/022_rename_py_to_capcut.md`
- [x] `CHANGELOG.md` entry
- [x] archive `openspec/changes/rename-py-to-capcut/` →
      `openspec/changes/archive/2026-10-19-rename-py-to-capcut/`
- [x] git commit + push on a feature branch (PR #1)
- [ ] merge to `main` — PR #1 open, merge pending
