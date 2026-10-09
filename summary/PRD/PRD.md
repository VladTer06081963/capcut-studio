# PRD: CapCut Studio (актуальное состояние)

**Версия:** 1.0 (initial)
**Дата:** 2026-10-09
**Владелец:** Vlad
**Путь проекта:** `~/Projects/capcut-studio/`

> **Это описание нового проекта в его текущем виде** (scaffold готов, MVP
> foundation в работе). Проект — sister к `~/Projects/comic-studio/`. Зеркалит
> его lifecycle discipline (lifecycle as files, bible, approval gate,
> summary/audit/tasks, CHANGELOG), но адаптирован к видео-домену.

---

## Содержание

1. [Обзор](#1-обзор)
2. [Архитектура](#2-архитектура)
3. [Asset library и Lifecycle](#3-asset-library-и-lifecycle)
4. [Pipeline: от брифа до final.mp4](#4-pipeline-от-брифа-до-finalmp4)
5. [Revision и Remix](#5-revision-и-remix)
6. [AI Provider Routing](#6-ai-provider-routing)
7. [Stock Ingest (UA-aware)](#7-stock-ingest-ua-aware)
8. [MCP-сервер](#8-mcp-сервер)
9. [Polishing: Concat + CapCut + DaVinci](#9-polishing-concat--capcut--davinci)
10. [Безопасность и Access Control](#10-безопасность-и-access-control)
11. [OpenSpec и Process](#11-openspec-и-process)
12. [Конфигурация и порты](#12-конфигурация-и-порты)
13. [Тестирование](#13-тестирование)
14. [Cron и Automation](#14-cron-и-automation)
15. [Что известно как работающее](#15-что-известно-как-рабочее)
16. [Open Items / Follow-ups](#16-open-items--follow-ups)

---

## 1. Обзор

### Что это

**CapCut Studio** — pipeline для длинных видео-сценариев (1-3 мин эпизоды,
серии по 10+ эпизодов) с переиспользуемыми визуальными элементами
(сцены, герои, одежда, шаблоны поведения). Sister-project к comic-studio,
но для видео.

### Ключевая идея: Asset-library-first

Вместо «генерим каждый клип с нуля для каждого эпизода» — библиотека клипов
растёт со временем, эпизоды **собираются** из неё через AI-матчинг. AI (MiniMax
H3.0, Qwen-Image) используется для **создания активов** в библиотеку и
**планирования** эпизодов. Stock (YouTube, Coverr, Mixkit, Archive.org) —
для B-roll где AI не нужен.

```
   ┌─ ночь ─┐                        ┌─ день ──────────────┐
   │         │                        │                      │
   │ AI gen  │  ──────library────►  episode_spec  ─►  draft
   │ stock   │      (assets)         │     ↓                │
   │ reindex │                        │  matcher             │
   │         │                        │     ↓                │
   └─────────┘                        │  matched.json        │
                                      │     ↓                │
                                      │  Concat MCP          │
                                      │     ↓                │
                                      │  preview.mp4         │
                                      │     ↓                │
                                      │  DaVinci polish      │
                                      │     ↓                │
                                      │  final.mp4           │
                                      └──────────────────────┘
```

### Стек (текущий)

| Слой | Технология |
|---|---|
| Pipeline | Python 3.11+ |
| Видео генерация | MiniMax H3.0 / H3 Max (Plus Plan) |
| Текст | Qwen3-Max через OpenRouter |
| Image reference | Qwen-Image через OpenRouter |
| Stock primary | YouTube Data API v3 + yt-dlp |
| Stock secondary | Coverr API |
| Stock tertiary | Mixkit (HTML scrape, polite delay) |
| Stock fallback | Archive.org advancedsearch API |
| Indexer | BLIP-2 + CLIP через LM Studio (local, WireGuard) |
| Auto-compose | Concat MCP (Mac Studio) |
| Effect polish | CapCut (MacBook Pro) |
| Frame polish | DaVinci Resolve (MacBook Pro) |
| Story QC | Lapian Notes (MacBook Pro) |
| Editor (alt GUI) | Concat.app (MacBook Pro) |
| Тесты | unittest (Python) + node:test (sub-packages) |
| Process | summary/audit/tasks + CHANGELOG.md (по comic-studio) |

### Что НЕ входит (текущий scope)

- Голосовая озвучка (voice cloning) — отдельный change `voice-pipeline`
- Субтитры (Whisper локально) — отдельный change `subtitle-pipeline`
- Web API / Telegram bot — отдельный change `interfaces`
- Multi-user / collaborative editing — out of scope (single-user)
- Render farm / VPS — не нужен пока; Oracle free tier исключён; VPS появится
  только при commercial scale

---

## 2. Архитектура

### Дерево (актуальное)

```
capcut-studio/
├─ AGENTS.md                       ← спека проекта (главный документ)
├─ README.md                       ← entry-point
├─ CHANGELOG.md                    ← ISO-8601 timestamped log
├─ .env.example                    ← env vars reference
├─ .gitignore
│
├─ bible/                          ← frozen templates (per show/character/scene)
│  ├─ _TEMPLATE_show.md            ← show bible template
│  ├─ _TEMPLATE_character.md       ← character bible template
│  ├─ README.md                    ← bible discipline guide
│  └─ <show-slug>.md               ← real shows
│
├─ library/                        ← asset library (shared, growing)
│  ├─ ai/                          ← AI-generated (MiniMax H3.0, Qwen-Image)
│  │  ├─ characters/<slug>/*.mp4   ← behavior templates (walk/talk/sit/...)
│  │  └─ scenes/<slug>/*.mp4
│  ├─ stock/                       ← downloaded
│  │  ├─ youtube/  coverr/  mixkit/  archive/
│  │  └─ pixabay/  pexels/  (skip-if-blocked from UA)
│  ├─ index.sqlite                 ← embeddings + tags (BLIP-2 + CLIP)
│  └─ README.md                    ← schema + ingest flow
│
├─ serials/<show-slug>/            ← output episodes
│  ├─ episode-log.md               ← append-only chronicle
│  └─ <ep-id>-<slug>/
│     ├─ brief.md
│     ├─ spec.json                 ← declarative episode spec
│     ├─ .draft                    ← sentinel
│     ├─ .approved                 ← sentinel
│     ├─ matched.json              ← which library clips were picked
│     └─ rendered/
│        ├─ draft.json             ← Concat draft
│        ├─ preview.mp4
│        ├─ spec.sha256            ← idempotency
│        └─ final.mp4              ← IMMUTABLE
│
├─ py/
│  ├─ ingest/                      ← stock downloaders (youtube, coverr, mixkit, archive)
│  ├─ episode/                     ← LLM brief → spec.json
│  ├─ render/                      ← MiniMax + OpenRouter clients
│  ├─ lib/                         ← config, lifecycle, logging
│  ├─ index/                       ← BLIP-2 + CLIP embedder
│  ├─ search/                      ← embedding matcher
│  └─ assemble/                    ← spec.json → Concat draft
│
├─ mcp-server/                     ← capcut-pipeline MCP для Hermes / Mavis
├─ scripts/                        ← CLI entry points
├─ cron/                           ← nightly.sh + launchd .plist
├─ openspec/                       ← in-flight changes (mirror comic-studio)
├─ summary/
│  ├─ PRD/PRD.md                   ← этот файл
│  ├─ audit/                       ← audit files (NNN_slug.md)
│  └─ tasks/                       ← task files (NNN_slug.md)
├─ tests/                          ← Python unittest
└─ docs/
```

### Слои и их владельцы

| Слой | Владелец | Где живёт |
|---|---|---|
| Asset library (AI gen + stock) | Mac Studio | `library/` на Studio SSD (для активных) или Transcend 2TB HDD |
| Indexer | Mac Studio | LM Studio на `192.168.55.1:1234` (WireGuard) |
| Episode specs | Mac Studio | `serials/` на Studio SSD |
| Auto-compose | Mac Studio | Concat.app через MCP |
| Effect polish | MacBook Pro | CapCut.app на MBP |
| Frame polish | MacBook Pro | DaVinci Resolve на MBP (CPU-only render) |
| Story QC | MacBook Pro | Lapian Notes (frame extraction + emotion curve) |
| Asset sync | Thunderbolt Bridge | `/Volumes/CapCut-Assets/` shared volume |

---

## 3. Asset library и Lifecycle

### Library — single source of truth

Эпизоды **ссылаются** на клипы из библиотеки по `<source>:<slug>:<id>` и
`sha256` файла. Если файл меняется → ссылка ломается громко (matcher не
находит кандидата, episode не рендерится).

```
library/
  ai/characters/reznik/
      reference.png          ← first frame, для H3.0 init image
      walk.mp4 + walk.meta.json
      talk.mp4 + talk.meta.json
      sit.mp4 + sit.meta.json
  ai/scenes/pripyat-evening/
      wide.mp4 + wide.meta.json
      medium.mp4 + medium.meta.json
  stock/youtube/<video_id>.mp4 + metadata.json
  stock/coverr/<id>.mp4 + metadata.json
  ...
  index.sqlite               ← CLIP embeddings + BLIP-2 captions + tags
```

### `metadata.json` schema

```json
{
  "id": "ai:reznik:walk",
  "source": "ai",                            // ai | youtube | coverr | mixkit | archive | pixabay | pexels | recorded
  "model": "minimax-h3-max",
  "seed": 42,
  "prompt": "...",
  "negative_prompt": "...",
  "duration_sec": 5.2,
  "resolution": "1920x1080",
  "fps": 24,
  "character_ref": "ai:reznik:reference.png",
  "scene_ref": "ai:pripyat-evening:wide",
  "tags": ["reznik", "stalker", "walk", "evening"],
  "license": "self",                         // self | youtube-standard | coverr | etc.
  "attribution": null,
  "created_at": "2026-10-09T21:00:00Z",
  "sha256": "abc123..."
}
```

### `library/index.sqlite` schema

```sql
CREATE TABLE clips (
  id          TEXT PRIMARY KEY,
  path        TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  source      TEXT NOT NULL,
  model       TEXT,
  caption     TEXT,             -- BLIP-2 generated
  embedding   BLOB,             -- CLIP vector
  tags        TEXT,             -- JSON array
  duration_sec REAL,
  created_at  TEXT
);
CREATE INDEX idx_clips_source ON clips(source);
CREATE INDEX idx_clips_tags ON clips(tags);
```

### Episode lifecycle

```
draft            spec.json написан LLM, .draft sentinel есть
   ↓
approved         .approved sentinel (человек или auto-approve)
   ↓
matched          matched.json (matcher выбрал клипы)
   ↓
rendered         rendered/final.mp4 существует
   ↓
published        episode-log.md запись добавлена
```

**Revisions:**
- `draft` → `revise` (LLM regen spec.json, atomic approval revoke)
- `published` → `remix` (новый ep с remixed spec, original immutable)

**Idempotency:**
- Episode id + sha256 of `spec.json` — повторный render без `--force` = no-op
- Library clip sha256 must match reference — иначе matcher refuses

---

## 4. Pipeline: от брифа до final.mp4

```
┌─ Stage 1: brief ─────────────────────────────────┐
│                                                    │
│   User writes brief.md in serials/<show>/<ep-id>/  │
│   LLM (Qwen3-Max / Opus) генерит spec.json         │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓
┌─ Stage 2: match ─────────────────────────────────┐
│                                                    │
│   matcher.py:                                       │
│     for each scene in spec.json:                    │
│       compute query embedding                      │
│       rank candidates from library/index.sqlite    │
│       prefer source:ai for hero scenes             │
│       prefer source:stock for B-roll               │
│   write matched.json                                │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓
┌─ Stage 3: compose ────────────────────────────────┐
│                                                    │
│   concat_exporter.py:                              │
│     read spec.json + matched.json                  │
│     place clips on Concat tracks                   │
│     add captions, transitions                      │
│     write draft.json + preview.mp4                 │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓
┌─ Stage 4: review ────────────────────────────────┐
│                                                    │
│   User opens preview in CapCut (MBP)               │
│   approve → .approved sentinel                     │
│   или revise → loop to Stage 1                     │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓
┌─ Stage 5: render + polish ────────────────────────┐
│                                                    │
│   Concat MCP exports final.mp4                     │
│   (или CapCut manual export если нужен Pro-effect) │
│   User opens final.mp4 в DaVinci на MBP            │
│   frame-by-frame polish (color, chroma key, audio) │
│   overwrite rendered/final.mp4                     │
│   (это нормально — final.mp4 не immutable до       │
│    публикации; после публикации immutable)         │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓
┌─ Stage 6: publish ────────────────────────────────┐
│                                                    │
│   Append entry to serials/<show>/episode-log.md    │
│   (one-line: ep-id, brief, duration, tags)         │
│   Mark rendered/ → published/                      │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 5. Revision и Remix

### Revision (для `draft` / `approved`)

- LLM regen `spec.json` from `brief.md` (или переписанного brief'а)
- Atomic approval revoke (если было `.approved`, удаляется)
- Matcher пересчитывает matched.json
- Cycle повторяется

### Remix (для `published`)

- Новый episode dir создаётся: `serials/<show>/<ep-id>-v2-<slug>/`
- `remix_of: <ep-id>-v1` в spec.json
- Original v1 **immutable** (никогда не редактируется)
- v2 может радикально отличаться (другой стиль, другой POV, другая музыка)

### Continuity check

Перед approve нового эпизода, matcher делает diff против `episode-log.md`:
- тот же персонаж в разных эпизодах → должен быть тот же `character_ref`
- та же локация → должен быть тот же `scene_ref`
- события не противоречат хронологии episode-log

Если diff плохой — warning в `matched.json`, не fail.

---

## 6. AI Provider Routing

### Default providers

| Задача | Провайдер | Endpoint |
|---|---|---|
| Video gen | `minimax-h3-max` | MiniMax Plus API |
| Text | `qwen3-max` | OpenRouter |
| Image reference | `qwen-image` | OpenRouter |

### Override hierarchy (per-scene)

```
1. CLI flag (--video-provider, --text-provider)
   ↓
2. spec.json["scenes"][i]["provider"]
   ↓
3. spec.json["provider"] (ep-level)
   ↓
4. bible/<show>.md → GENRE_DEFAULT table (TBD)
   ↓
5. env DEFAULT_VIDEO_PROVIDER / DEFAULT_TEXT_PROVIDER
   ↓
6. hardcoded "minimax-h3-max" (last resort)
```

### Auto-fallback chain (per-call)

```
1. primary provider call
   ↓ (raises LMRuntimeError / MMError / etc.)
2. fallback provider call (lazy import)
   ↓ (raises)
3. last resort: hardcoded "minimax"
   ↓ (raises)
4. explicit fail with context (no silent fallbacks)
```

В `matched.json` пишется `provider_used`, `provider_fallback: bool` — для аудита.

### Daily budget cap

`DAILY_AI_BUDGET_USD` в `.env` (default 10). `cron/nightly.sh` aborts above.
Per-call cost tracking в `library/.tmp/cost_log.json`.

---

## 7. Stock Ingest (UA-aware)

### Verified sources (curl из UA, 2026-10-09)

| Источник | Web | API | Лицензия | Вердикт |
|---|---|---|---|---|
| YouTube Data API v3 | ✅ 200 | ✅ | youtube-standard | **primary** |
| Coverr | ✅ 200 | ✅ (с ключом) | coverr | **secondary** |
| Mixkit | ✅ 200 | ❌ scrape | mixkit | **tertiary** |
| Archive.org | ✅ 200 | ✅ | public domain | **fallback** |
| Pixabay | ❌ 403 | ? | pixabay | skip-if-blocked |
| Pexels | ❌ 403 | ? | pexels | skip-if-blocked |

### Ingest pattern (per source)

```bash
python scripts/ingest_<source>.py --query "fog night forest" --count 20
# → downloads to library/stock/<source>/<id>.mp4
# → writes <id>.metadata.json with attribution
# → updates library/index.sqlite
```

### Mixkit scrape

У Mixkit нет API. Используем requests + BeautifulSoup:
- Browse `https://mixkit.co/free-stock-video/?q=<query>` (paged)
- Parse each clip card → title, duration, preview URL
- Polite delay `MIXKIT_SCRAPE_DELAY_SEC` (default 2.0)
- **Risk**: Mixkit HTML layout может меняться → скрипт нужно чинить

---

## 8. MCP-сервер

### Цель

Hermes (Qwen local) и Mavis Plus (Opus/GPT) управляют пайплайном через MCP.
Hermes — для рутинного (ingest, index, search, assemble), Mavis — для vision/
planning tasks.

### Планируемые tools

```python
# capcut-pipeline MCP
list_serials() -> list[{slug, eps_count, last_render}]
create_episode_spec(serial, ep_id, brief) -> {spec.json_path, status}
approve_episode(ep_id) -> {ok, warnings[]}
revise_episode(ep_id, feedback) -> {spec.json_path, status}
match_episode(ep_id) -> {matched.json_path, candidates_count}
assemble_episode(ep_id, --no-render) -> {draft.json_path, preview_path}
search_library(query, source=ai) -> [{id, sha256, path, score}]
ingest_stock(source, query, count) -> {clips_added, errors[]}
add_bible_character(slug) -> {bible_path, reference_path}
add_bible_show(slug) -> {bible_path, episode_log_path}
```

### Когда появится

В change `capcut-pipeline-mcp` (см. `summary/tasks/001_*.md` → F7).

---

## 9. Polishing: Concat + CapCut + DaVinci

### Concat MCP (auto, 80% работы)

- Place clips on tracks
- Add captions (text overlay)
- Add transitions (cut, dissolve, fade)
- Apply basic effects (zoom, pan)
- Export `draft.json` + `preview.mp4`

### CapCut (manual, эффекты)

- Ручная доводка когда Concat не справляется
- Pro effects (CapCut-only): chroma key pro, advanced transitions
- Manual keyframe animation
- Export с CapCut-специфичными фичами

### DaVinci Resolve (manual, frame polish)

- Frame-by-frame color grading
- Chroma key на сложных фонах (AI-gen артефакты)
- Audio sync / cleanup
- Render в MBP (CPU-only, медленно но точно)
- Thunderbolt-share `/Volumes/CapCut-Assets/` для read/write

### Lapian Notes (story QC, на MBP)

- Frame extraction (1 fps)
- Emotion curve от rendered episode
- Diff против expected curve from brief
- Output: pass/fail с notes

---

## 10. Безопасность и Access Control

### .env hygiene

- `.env` в `.gitignore` (verified)
- `.env.example` без реальных ключей (verified)
- Все ключи хранятся локально, не в git
- MiniMax, OpenRouter, YouTube — с per-key quotas

### Access control

- Single-user (no multi-tenant yet)
- WireGuard-only для LM Studio (`192.168.55.1:1234`)
- Thunderbolt-share защищён macOS user permissions
- Library index.sqlite не exposed в сеть

### Secrets rotation

- Plus Plan rotation: раз в 3 месяца (MiniMax Plus рекомендует)
- OpenRouter / YouTube: раз в 6 месяцев
- Track rotations в `library/.tmp/key_rotations.json`

---

## 11. OpenSpec и Process

### OpenSpec

По образцу comic-studio — каждый change начинается с `openspec/changes/<slug>/`
содержащей:
- `proposal.md` — обоснование
- `tasks.md` — чеклист
- `specs/<module>/spec.md` — delta specs для модулей

Для первого change (initial-scaffold) формальная OpenSpec-итерация **deferred**
— этот change описан прямо в audit/tasks. С первого функционального кода —
полная OpenSpec discipline.

### Process

1. User запрашивает change
2. Создаём `summary/audit/NNN_<slug>.md` (этот файл) + `summary/tasks/NNN_<slug>.md`
3. Создаём `openspec/changes/<slug>/` (когда есть proposal)
4. Implementation: PR с conventional commits
5. `summary/audit/NNN_*.md` обновляется по мере работы
6. После завершения — запись в `CHANGELOG.md` с ISO-8601 timestamp
7. Change архивируется в `openspec/changes/archive/`

### Branch workflow

- Branch from `main`
- Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`)
- `openspec/` source of truth для in-flight changes

---

## 12. Конфигурация и порты

### Bind ports

| Сервис | Порт | Bind |
|---|---|---|
| LM Studio (WireGuard) | 1234 | 192.168.55.1 |
| Concat MCP | 9847 | 127.0.0.1 |
| (planned) Web API | 3001 | 127.0.0.1 |

### Storage

| Mount | Использование |
|---|---|
| `~/Projects/capcut-studio/` | Project root (Studio SSD, fast) |
| `library/ai/` | AI-generated assets (Studio SSD для активных, HDD Transcend 2TB для архива) |
| `library/stock/` | Stock downloads (HDD Transcend 2TB, write-once) |
| `library/index.sqlite` | Embeddings + tags (Studio SSD, MB даже для 10k clips) |
| `/Volumes/CapCut-Assets/` | Thunderbolt 40 Gb/s share с MBP |

---

## 13. Тестирование

### Python (unittest)

- `tests/test_config.py` — config loader
- `tests/test_lifecycle.py` — sentinel logic
- `tests/test_ingest_youtube.py` — mocked (no live API)
- `tests/test_matcher.py` — embedding search logic
- `tests/test_spec_writer.py` — spec.json schema validation

### Live integration tests (manual)

- `tests/integration/ingest_smoke.py` — реальный YouTube ingest 1-5 клипов
- `tests/integration/match_smoke.py` — реальный matcher query
- `tests/integration/render_smoke.py` — end-to-end one episode

---

## 14. Cron и Automation

### launchd (не systemd, мы на macOS)

- `cron/com.MiniMax.capcut-studio.nightly.plist` — launchd timer
- `cron/nightly.sh` — actual script
- Деплой: `cp .plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/<plist>`

### Nightly batch (when ready)

```bash
# 1. Stock ingest (Pixabay/Pexels skipped if blocked)
python scripts/ingest_youtube.py --top-queries-from-bible
python scripts/ingest_coverr.py --top-queries
python scripts/ingest_mixkit.py --top-queries
python scripts/ingest_archive.py --top-queries

# 2. AI generation (если bible требует новых клипов)
python scripts/generate_assets.py --from-bible --budget 1000

# 3. Reindex (BLIP-2 + CLIP через LM Studio)
python scripts/index_library.py

# 4. Cost report
python scripts/daily_cost_report.py --email-to vlad@local
```

### Daily cost cap

`DAILY_AI_BUDGET_USD` в `.env`. Nightly aborts above. Alert на email/console.

---

## 15. Что известно как работающее

_(на 2026-10-09 — после audit 001)_

- ✅ Project structure (всё на диске в правильных местах)
- ✅ AGENTS.md покрывает все 5 ключевых секций
- ✅ bible templates заполняемы (`_TEMPLATE_show.md`, `_TEMPLATE_character.md`)
- ✅ library schema (`metadata.json` + `index.sqlite`)
- ✅ UA-friendly stock ordering (verified via curl)
- ✅ Git initialised, 2 commits, clean state
- ✅ summary/audit/tasks/PRD/CHANGELOG discipline

### Что НЕ проверено end-to-end

- ❌ Реальный ingest (нет скриптов)
- ❌ Реальный match (нет indexer'а)
- ❌ Реальный episode render (нет poll)
- ❌ Character consistency across AI clips — главный open problem

---

## 16. Open Items / Follow-ups

_(отдельные change'ы — см. `summary/tasks/001_*.md` → "Следующие задачи")_

| ID | Что | Приоритет |
|---|---|---|
| F1 | `py/lib/config.py` + `py/lib/lifecycle.py` | High |
| F2 | YouTube ingest end-to-end | High |
| F3 | Coverr + Archive ingest | Medium |
| F4 | Episode spec writer (LLM brief → spec.json) | High |
| F5 | Library indexer (BLIP-2 + CLIP) | Medium |
| F6 | Matcher + Concat exporter | Medium |
| F7 | capcut-pipeline MCP для Hermes | Medium |
| F8 | launchd nightly batch | Low |
| F9 | `bible/_TEMPLATE_scene.md` | Medium |
| F10 | Character consistency stress test | Low |
| F11 | OpenSpec formal proposal для первого кода | Medium |
| F12 | Voice cloning pipeline (отдельный change) | Future |
| F13 | Subtitle pipeline (Whisper локально) | Future |
| F14 | Web API для approve/revise (без MCP) | Future |
| F15 | VPS deploy script (когда commercial пойдёт) | Future |

---

## Связанные документы

- `AGENTS.md` — главная спека (setup, run, layout, invariants)
- `bible/README.md` — bible discipline guide
- `library/README.md` — asset library schema
- `summary/audit/001_initial-scaffold.md` — audit этого change'а
- `summary/tasks/001_initial-scaffold.md` — tasks этого change'а
- `CHANGELOG.md` — ISO-8601 timestamped log
- `~/Projects/comic-studio/PRD/PRD.md` — sister-project PRD, образец структуры
- `~/Projects/comic-studio/AGENTS.md` — sister-project AGENTS, образец discipline