# Tasks: Rename `py/` package to `capcut/`

## 1. Mechanical rename

- [ ] `git mv py capcut`
- [ ] `git mv capcut/requirements.txt` stays in place (it moves with the dir)

## 2. Import rewrite (Python)

- [ ] `py/**` intra-package imports: `from py.X` → `from capcut.X`,
      `from .X` → unchanged, `import py.X` → `import capcut.X`
- [ ] `scripts/*.py` imports
- [ ] `tests/*.py` imports
- [ ] `sys.path` bootstrap comments mentioning `py/`

## 3. Documentation rewrite

- [ ] `AGENTS.md`: project layout tree, all `py/` references, install
      command `pip install -r py/requirements.txt` → `capcut/requirements.txt`
- [ ] `README.md`: quick-start install command
- [ ] `README_RU.md`: quick-start install command
- [ ] `summary/**`: audit + tasks files for 021 (and earlier ones that
      reference `py/`)
- [ ] `.pi/**`: skill/task references to `py/`

## 4. Validation

- [ ] `python -m pytest tests/ -q` passes **from repo root** (primary
      acceptance criterion)
- [ ] `python -m pytest tests/ -q` passes from an unrelated CWD
- [ ] `grep -rnE "^\s*(from|import)\s+py[.\s]" --include="*.py" .`
      returns zero results outside `.venv/`
- [ ] `grep -rn "\bpy/" --include="*.md" .` returns zero stale path
      references (outside `.venv/`, `node_modules/`, and historical
      audit entries that intentionally describe the old layout)
- [ ] `python scripts/assemble_episode.py --help` works
- [ ] `python -c "import capcut.lib.config"` resolves
- [ ] `node mcp-server/test/concat_paths.test.js` still passes

## 5. Fixation bookkeeping

- [x] `summary/audit/022_rename_py_to_capcut.md`
- [x] `summary/tasks/022_rename_py_to_capcut.md`
- [x] `CHANGELOG.md` entry
- [x] archive `openspec/changes/rename-py-to-capcut/` →
      `openspec/changes/archive/2026-10-19-rename-py-to-capcut/`
- [x] git commit + push on a feature branch, then merge to `main`
