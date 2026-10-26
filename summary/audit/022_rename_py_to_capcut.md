# 022 — Rename `py/` package to `capcut/`

**Status:** ✅ Done (2026-10-19)
**Trigger:** Follow-up 5.1 from `summary/audit/021_health_check_followups.md`
**Branch:** `feature/rename-py-to-capcut`
**OpenSpec:** `openspec/changes/rename-py-to-capcut/` → archived as
`openspec/changes/archive/2026-10-19-rename-py-to-capcut/`

## 1. Контекст (Context)

`~/Projects/capcut-studio/py/` held the pipeline sources, and its name
shadowed the PyPI package `py` (1.11.x) that pytest 7.x depends on for
`LEGACY_PATH = py.path.local`. From inside the repo, `import py` resolved
to `py/__init__.py` (the local package), so collection died with:

```
AttributeError: module 'py' has no attribute 'path'
```

Workaround was to run pytest from an unrelated CWD — recorded in the
README as a footgun. Every fresh agent and CI runner had to rediscover it.

## 2. Что сделано (What was done)

- ✅ `git mv py capcut` — history preserved, 24 files moved
- ✅ **34 Python files** rewritten: `from py.X` / `import py.X` →
  `from capcut.X` / `import capcut.X`
  - 12 package files (`capcut/assemble/`, `capcut/episode/`,
    `capcut/index/`, `capcut/ingest/`, `capcut/render/`,
    `capcut/search/`)
  - 10 `scripts/*.py` entry points
  - 9 `tests/*.py`
  - 3 stray root-level `test_kie*.py` scripts
- ✅ **6 live docs** rewritten (49 path references):
  - `AGENTS.md` — project layout tree, install command, extension points,
    deployment diagram
  - `README.md` — quick-start install command
  - `README_RU.md` — quick-start install command + stale footgun block
    replaced with the resolved state
  - `.github/copilot-instructions.md` + `.ru.md`
  - `summary/PRD/PRD.md` — module surface, layout tree, feature table
- ✅ `capcut/requirements.txt` moved with the directory
- ✅ Historical `summary/audit/*` and `summary/tasks/*` files **kept** their
  original `py/` references — they are records of the tree at the time and
  rewriting them would falsify history

## 3. Статус (Verification)

| Criterion | Result | Notes |
|---|---|---|
| **pytest from repo root** | ✅ **129 passed** | primary acceptance criterion — the workaround is gone |
| pytest from unrelated CWD | ✅ 129 passed | `/tmp` run |
| 0 leftover `from py.` / `import py.` | ✅ 0 matches | project-wide grep, `.venv` excluded |
| `python scripts/assemble_episode.py --help` | ✅ works | |
| `import capcut.lib.config` | ✅ resolves | PROJECT_ROOT = capcut-studio |
| `node mcp-server/test/concat_paths.test.js` | ✅ 4/4 | |
| Git history | ✅ preserved | `git mv`, renames detected in diff |

## 4. Что НЕ проверено (What's NOT verified)

- **No external consumer was audited.** Any script outside this repo that
  imports `py.<module>` would break. The repo itself has no such
  consumer, and `mcp-server/` (Node) shells out to `scripts/*.py` by
  path rather than by Python import path, so it is unaffected.
- **`.pi/` harness was not exercised** with the renamed package. Its
  skills contain no `py/` references (verified by grep), but no Pi
  session was run against the renamed tree.
- **Downstream `~/Projects/comic-studio/`** was not checked for a shared
  import of capcut-studio's `py` package. The two projects are
  independent (sister projects, not a shared library), but this was not
  explicitly verified.

## 5. Решения (Decisions)

- **Chose the rename over the alternatives.** Options (B) a `conftest.py`
  sys.path fix and (C) documenting the workaround were both cheaper, but
  both leave the footgun in place for the next agent. The rename also
  gives the package a name that matches the project, which removes the
  ambiguity for humans reading `from capcut.lib.config import ...`.
- **Historical records left untouched.** `summary/audit/` and
  `summary/tasks/` entries describe what the tree looked like when they
  were written. Rewriting them would make the history inaccurate.
- **Tracked `.pi/` in the same branch** as a separate commit
  (`c28c863`) rather than mixing it into the rename diff — the harness
  files were untracked but are referenced by `AGENTS.md` and `README.md`.

## 6. Что зафиксировано в git (What landed)

Коммиты в этом PR (проверено `git log --format=%s` + `git show --stat`):

| Hash | Заголовок | Содержимое |
|---|---|---|
| `9659e16` | `docs: add Russian README mirror (README_RU.md)` | 1 файл |
| `bfa5ab7` | `docs(openspec): proposals for py->capcut rename and final-render writer` | 4 файла (2 proposal'а) |
| `c28c863` | `refactor!: rename py/ package to capcut/` | **84 файла** — rename + переписанные импорты в 34 Python-файлах + 6 живых доков |
| `85b0a95` | `chore: track .pi/ project harness (Pi agent skills)` | **6 файлов** — только `.pi/` harness |

> ⚠️ **Замечание по истории.** В момент коммита заголовки этих двух
> коммитов были переставлены: `c28c863` назывался «chore: track .pi/»,
> а `85b0a95` — «refactor!: rename py/», хотя содержимое было обратным.
> Исправлено принудительным push'ом ветки с переписанной историей.

Содержимое rename-коммита: 24 файла перемещены (`git mv`), 34 Python-файла
переписаны, 6 живых доков обновлены, 49 замен путей. `.pi/` harness добавлен
отдельным коммитом, а не смешан с rename-диффом.

## 7. OpenSpec / PR

- Proposal: `openspec/changes/rename-py-to-capcut/proposal.md`
- Tasks: `openspec/changes/rename-py-to-capcut/tasks.md`
- Archived to `openspec/changes/archive/2026-10-19-rename-py-to-capcut/`
- Branch `feature/rename-py-to-capcut` (main is protected per AGENTS.md
  "Branch workflow" — merge to `main` is a separate step)
