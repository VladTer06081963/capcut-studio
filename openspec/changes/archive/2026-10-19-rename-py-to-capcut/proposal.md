# Change: Rename `py/` package to `capcut/`

## Status

Proposed; implementation pending.

## Problem

The pipeline source directory `py/` shadows the popular PyPI package `py`
(1.11.x), which pytest 7.x depends on for `LEGACY_PATH = py.path.local`.

When pytest runs with CWD inside the repository, `import py` resolves to
`py/__init__.py` (the local pipeline package) instead of the installed
library, and collection fails with:

```
AttributeError: module 'py' has no attribute 'path'
```

This is a recurring footgun: every fresh agent or CI runner must know to
run pytest from a different directory. The workaround is documented in
`summary/audit/021_health_check_followups.md` §5.1 and in `README.md` /
`README_RU.md`, but it is a workaround, not a fix.

Additionally, `py` is a poor package name for a project called
`capcut-studio` — the sister project `comic-studio` and the wider
`~/Projects/` layout make a `capcut/` namespace unambiguous.

## Change

Rename the top-level Python package directory `py/` → `capcut/`.

- `py/` → `capcut/` (git mv, preserves history)
- All intra-package imports `from py.X import ...` → `from capcut.X import ...`
- All script imports `from py.X import ...` → `from capcut.X import ...`
- All test imports likewise
- `py/requirements.txt` → `capcut/requirements.txt`
- Documentation references to `py/<module>` → `capcut/<module>`
  (AGENTS.md, README.md, README_RU.md, summary/*, .pi/*)
- `sys.path` bootstrap comments in `scripts/*.py` updated

## Boundaries

- **No behavior change.** Pure namespace rename.
- No change to runtime configuration, provider selection, lifecycle
  semantics, or the asset-library schema.
- No change to `mcp-server/` (Node; it shells out to `scripts/*.py` by path,
  not by Python import path).
- The `py` PyPI package remains a test-time dependency; after this rename
  the local `capcut/` package no longer conflicts with it.

## Validation

- `python -m pytest tests/ -q` passes **from the repository root** (the
  workaround becomes unnecessary — this is the primary acceptance criterion)
- `python -m pytest tests/ -q` still passes from an unrelated CWD
- `python scripts/assemble_episode.py --help` works
- `grep -rnE "^\s*(from|import)\s+py[.\s]" --include="*.py" .` returns
  zero results outside `.venv/`
- `node mcp-server/test/concat_paths.test.js` still passes
- `python -c "import capcut.lib.config"` resolves to the renamed package
