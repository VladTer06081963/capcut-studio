# CHANGELOG

ISO-8601 timestamped log. Format mirrors `~/Projects/comic-studio/CHANGELOG.md`.

## 2026-10-09T18:20Z — Fixation 001: initial scaffold + UA stock migration

**Context**: новый проект `~/Projects/capcut-studio/` (sister-project к
`~/Projects/comic-studio/`). Asset-library-first video production pipeline:
AI gen + stock → библиотека клипов → эпизоды собираются матчером из библиотеки.
Sister-pattern: lifecycle as files, bible templates, approval gate, summary/
audit/tasks, CHANGELOG.

**Решения зафиксированы**:
- AI primary (MiniMax H3.0/H3 Max + Qwen через OpenRouter), stock supplement
- UA-friendly stock order: YouTube Data API v3 → Coverr → Mixkit (scrape) →
  Archive.org. Pixabay и Pexels web заблокированы из UA (HTTP 403 verified
  via curl 2026-10-09T18:13Z), остаются как skip-if-blocked fallbacks
- Local-first deployment (Oracle free tier исключён; VPS — при commercial scale)
- Git локально + remote `git@github.com:VladTer06081963/capcut-studio.git` (public)
- Concat MCP для auto-compose + CapCut/DaVinci на MBP для manual polish

**Commits**:
- `be437d3` — feat: initial scaffold (AGENTS.md, README.md, .env.example,
  .gitignore, bible templates, library/README, py/ skeleton 7 submodules)
- `b9a4486` — fix: drop Pixabay as primary stock source (UA blocked).
  Pixabay/Pexels помечены как skip-if-blocked, добавлены Coverr/Mixkit/Archive
- `d476774` — docs: add summary/audit, summary/tasks, summary/PRD, CHANGELOG

**OpenSpec**: `openspec/changes/initial-scaffold/` — deferred. Описан прямо
в audit/tasks. Формальная OpenSpec-итерация появится при первом функциональном
коде (F1).

**Tests**: N/A (scaffolding без кода).

**Audit + Tasks**: `summary/audit/001_initial-scaffold.md`,
`summary/tasks/001_initial-scaffold.md`, `summary/PRD/PRD.md`.

---

## 2026-10-09T18:35Z — Fixation 002: foundation (F1 — config + lifecycle)

**Context**: первый функциональный код в проекте. Foundation для всех
последующих модулей (ingest, episode, render, search, assemble, MCP).

**Что добавлено**:
- `py/lib/config.py` (~180 строк): грузит `.env` через `python-dotenv`,
  экспортирует типизированные константы (LIBRARY_ROOT, DEFAULT_VIDEO_PROVIDER,
  API keys, LM Studio URL, DAILY_AI_BUDGET_USD). Helpers: `has_minimax()`,
  `has_openrouter()`, `has_youtube()`, `has_coverr()`, `is_test_env()`,
  `ensure_dirs()`. Graceful fallback если `dotenv` не установлен.
- `py/lib/lifecycle.py` (~250 строк): state machine для эпизода:
  draft → approved → matched → rendered → published. Sentinel-файлы
  (`.draft`, `.approved`) + detection через `matched.json` и
  `rendered/final.mp4`. Atomic transitions: `approve()`, `revise()`,
  `mark_matched()`, `mark_rendered()`, `publish()`. Idempotency:
  `sha256_spec()`, `is_idempotent_render()`, `write_spec_sha()`.
- `tests/test_config.py` (4 теста): defaults, helpers, paths, ensure_dirs
- `tests/test_lifecycle.py` (14 тестов): все state transitions, идемпотентность,
  sha256, publish log

**Архитектурные решения**:
- `State` как `str` Enum (`State.DRAFT == "draft"`) — JSON-friendly
- Sentinel-файлы вместо in-memory state — соответствует AGENTS.md invariant
  "lifecycle as files on disk"
- Idempotency по sha256(spec.json) — повторный render без изменений = no-op
- Тесты используют `tempfile.mkdtemp()` + `unittest.mock.patch` для
  изоляции — никаких live-вызовов к API

**OpenSpec**: deferred (этот change мелкий, ~430 строк + тесты). Формальная
OpenSpec-итерация — для change'ов >1000 строк или с дельта-spec'ами.

**Tests**: 18/18 OK (`python -m unittest discover -s tests -p 'test_*.py'`).

**Audit + Tasks**: `summary/audit/002_foundation.md` (TODO), `summary/tasks/002_foundation.md` (TODO).

**Open Items**:
- F4: episode spec writer (uses config)
- F2: YouTube ingest (uses config + lifecycle for cache invalidation)
- F11: OpenSpec formal proposal для следующего большого change'а