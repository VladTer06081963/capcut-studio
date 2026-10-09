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
- Git локально (без remote пока)
- Concat MCP для auto-compose + CapCut/DaVinci на MBP для manual polish

**Commits**:
- `be437d3` — feat: initial scaffold (AGENTS.md, README.md, .env.example,
  .gitignore, bible templates, library/README, py/ skeleton 7 submodules)
- `b9a4486` — fix: drop Pixabay as primary stock source (UA blocked).
  Pixabay/Pexels помечены как skip-if-blocked, добавлены Coverr/Mixkit/Archive

**OpenSpec**: `openspec/changes/initial-scaffold/` — **deferred**. Этот
change описан прямо в audit/tasks. Формальная OpenSpec-итерация появится
при первом функциональном коде (F1: `py/lib/config.py`).

**Tests**: N/A (scaffolding без кода).

**Audit + Tasks**: `summary/audit/001_initial-scaffold.md`,
`summary/tasks/001_initial-scaffold.md`, `summary/PRD/PRD.md`.

**Open Items** (следующие change'ы):
- F1: `py/lib/{config,lifecycle}.py` (High)
- F2: YouTube ingest end-to-end (High)
- F3: Coverr + Archive ingest (Medium)
- F4: Episode spec writer (High)
- F5: Library indexer (Medium)
- F6: Matcher + Concat exporter (Medium)
- F7: capcut-pipeline MCP для Hermes (Medium)
- F8: launchd nightly batch (Low)
- F9: `bible/_TEMPLATE_scene.md` (Medium)
- F10: Character consistency stress test (Low)