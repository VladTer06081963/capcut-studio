# Аудит: Initial Scaffold + UA Stock Source Migration

**Дата:** 2026-10-09
**Change ID:** `initial-scaffold`
**OpenSpec:** `openspec/changes/initial-scaffold/` (deferred — этот change описан прямо здесь, формальная OpenSpec-итерация появится при первом коде)
**Компаньон:** `summary/tasks/001_initial-scaffold.md`
**Предшественник:** (нет — это первый change в репо)

## 1. Контекст

CapCut-studio задуман как sister-project к `~/Projects/comic-studio/`. Тот же
паттерн (lifecycle как файлы на диске, approval как persisted artifact, bible
как источник истины для визуальной consistency), но адаптированный к видео:

- Вместо панелей комикса — сцены эпизода (склейка клипов)
- Вместо персонажей с LoRA — персонажи с reference image (для H3.0 image-to-video)
- Вместо LLM-сценариев в JSON → LLM-спека эпизода (`spec.json`) → ассемблер на таймлайн
- Вместо MiniMax image-01 → MiniMax H3.0/H3 Max (video), плюс OpenRouter/Qwen как текст/image
- Вместо единственного провайдера (MiniMax) → asset-library-first: AI primary + stock fallback

**Архитектурное решение, зафиксированное в этом change:**

1. **Asset-library-first** — эпизоды не генерятся целиком с нуля, а **собираются
   из библиотеки клипов** (AI + stock). Библиотека растёт со временем, эпизоды
   переиспользуют её.
2. **AI primary, stock supplement** — Qwen (OpenRouter subscription) для текста/
   image, MiniMax H3.0/H3 Max для видео. Stock — fallback для B-roll где AI
   не нужен или дорог.
3. **Local-first** — Oracle (free tier) не подходит для 24/7 cron и multi-GB
   библиотеки. Всё на Mac Studio + Thunderbolt-share на MBP. VPS появится
   только если commercial revenue оправдает.
4. **Hybrid stock (UA-aware)** — Pixabay и Pexels web/API заблокированы из UA
   (HTTP 403). Используем UA-friendly источники: YouTube Data API v3 →
   Coverr → Mixkit (scrape) → Archive.org.
5. **Discipline comic-studio** — same AGENTS.md / bible / lifecycle /
   fix-`summary` / `CHANGELOG.md` pattern.

## 2. Архитектура (от высшего приоритета к низшему)

### 2.1 Asset-library-first

```
brief.md
    ↓ LLM (Qwen3-Max / Opus)
episode_spec.json (declarative)
    ↓ matcher (CLIP embedding search)
matched.json (chosen library clips)
    ↓ Concat MCP (auto-compose)
draft.json + preview.mp4
    ↓ human review + .approved sentinel
    ↓ assemble + polish
final.mp4
```

Library — единый источник правды. Эпизоды **ссылаются** на clips по
`<source>:<slug>:<id>` и sha256. Если файл меняется → ссылка ломается громко.

### 2.2 AI primary, stock supplement

| Задача | Провайдер | Endpoint |
|---|---|---|
| Текст | Qwen3-Max через OpenRouter | `https://openrouter.ai/api/v1/chat/completions` |
| Image reference | Qwen-Image через OpenRouter | same |
| Видео | MiniMax H3.0 / H3 Max (Plus Plan) | MiniMax video API |
| Stock primary | YouTube Data API v3 + yt-dlp | youtube-dl driven |
| Stock secondary | Coverr API | `https://coverr.co/api` |
| Stock tertiary | Mixkit HTML scrape | requests + bs4 |
| Stock fallback | Archive.org | `https://archive.org/developers/` |
| Blocked | Pixabay, Pexels | skip-if-blocked fallback |

**Fallback chain (UA-aware):**
```
1. AI clip из library/ai/ (exact character/scene match)
2. AI clip из library/ai/ (close match — другой scene, тот же character)
3. Stock YouTube (Data API + yt-dlp)
4. Stock Coverr API
5. Stock Mixkit scrape
6. Stock Archive.org
7. Stub — Concat placeholder clip (НИКОГДА silent, всегда с warning)
```

### 2.3 Local-first deployment

```
┌─ Mac Studio (Apple Silicon) ──────────────────────────┐
│   ~/Projects/capcut-studio/   ← всё в одном месте    │
│   ├─ py/                                            │
│   ├─ library/  (AI + stock + index.sqlite)         │
│   ├─ serials/                                       │
│   ├─ bible/                                         │
│   └─ cron/ (через launchd, не systemd)              │
│   Concat.app, Hermes, Mavis Plus, LM Studio         │
└─────────────────────────────────────────────────────┘
          │ Thunderbolt 40 Gb/s
          ▼
┌─ MacBook Pro (Intel i9) ──────────────────────────────┐
│   DaVinci Resolve (frame polish)                    │
│   CapCut (effect polish)                            │
│   Lapian Notes (story QC)                            │
│   Concat.app (alt GUI)                              │
└─────────────────────────────────────────────────────┘
```

### 2.4 Lifecycle as files on disk

```
serials/<show>/<ep-id>-<slug>/
├─ brief.md            ← вход от пользователя / LLM
├─ spec.json           ← LLM сгенерил (draft state)
├─ .draft              ← sentinel
├─ .approved           ← sentinel (после approve)
├─ matched.json        ← matcher выбрал клипы
├─ rendered/
│  ├─ draft.json       ← Concat draft
│  ├─ preview.mp4      ← low-quality preview
│  ├─ spec.sha256      ← input hash for idempotency
│  └─ final.mp4        ← IMMUTABLE после рендера
└─ episode-log.md entry ← в serials/<show>/episode-log.md
```

## 3. Решение по архитектурным вопросам

| Вопрос | Решение | Обоснование |
|---|---|---|
| Генерация vs сборка | **Asset-library-first** (сборка) | Переиспользование, cost cap, consistency через reference images |
| AI provider для видео | **MiniMax H3.0/H3 Max** | Plus Plan доступен, есть готовый skill, качество на 2026 Q4 high-end |
| AI provider для текста | **Qwen3-Max через OpenRouter** | Сильный text-only, дешевле Opus, есть подписка |
| Stock primary | **YouTube Data API** | UA-friendly (verified curl), обширная база, license-clean |
| Deployment | **Local-first, без VPS** | Oracle free tier не подходит; VPS когда commercial окупит |
| Git | **Локальный git, без remote** | Local-only deploy, remote когда поднимется VPS |
| MCP integration | **capcut-pipeline MCP для Hermes** | Hermes управляет таймлайном, Mavis Plus используется для vision/planning |
| Editor | **Concat (auto) + CapCut (manual) + DaVinci (frame polish)** | Гибрид даёт 80% auto + manual control |
| Indexer | **BLIP-2 captioning + CLIP embeddings через LM Studio** | Локально, без external API для индексации |
| Continuity | **bible/character-<slug>.md + reference image + frozen seed** | Зеркало comic-studio pattern |

## 4. Что создаётся / меняется

### Новые директории и файлы

| Файл | Назначение |
|---|---|
| `AGENTS.md` | Полная спека проекта (зеркало comic-studio/AGENTS.md) |
| `README.md` | Короткий entry-point |
| `.env.example` | Все env vars: MiniMax, OpenRouter, YouTube, Coverr, Mixkit, Archive, LM Studio |
| `.gitignore` | Library/assets excluded, .env excluded |
| `bible/_TEMPLATE_show.md` | Frozen style template (palette, camera, editing, models) |
| `bible/_TEMPLATE_character.md` | Character template (visual, wardrobe, props, behavior) |
| `bible/README.md` | Гайд по bible + seed strategy |
| `library/README.md` | Asset library schema + index.sqlite schema + ingest flow |
| `summary/audit/001_initial-scaffold.md` | Этот файл |
| `summary/tasks/001_initial-scaffold.md` | Tasks checklist |
| `summary/PRD/PRD.md` | Полный PRD для capcut-studio |
| `CHANGELOG.md` | ISO-8601 timestamped log |
| `py/ingest/__init__.py` … `py/assemble/__init__.py` | 7 пустых Python submodules |
| `mcp-server/` (empty) | Под будущий capcut-pipeline MCP |
| `scripts/` (empty) | Под CLI обёртки |
| `cron/` (empty) | Под nightly.sh (launchd timer позже) |
| `serials/` (empty) | Под выходные эпизоды |
| `openspec/`, `tests/`, `docs/` | Skeleton dirs |

### Не создаётся (отложено)

- `py/lib/config.py`, `py/lib/lifecycle.py` — следующий change (`foundation`)
- `py/ingest/youtube.py`, `py/ingest/coverr.py`, `py/ingest/mixkit.py` — change `ingest-sources`
- `py/episode/spec_writer.py` — change `episode-pipeline`
- `py/index/embedder.py`, `py/search/matcher.py` — change `library-indexer`
- `mcp-server/index.js` — change `capcut-pipeline-mcp`
- `cron/com.MiniMax.capcut-studio.nightly.plist` — change `launchd-cron`

## 5. Что НЕ входит в этот change

- **Конкретный Python/Node код** — этот change только scaffolding, без
  функциональности. Следующие change'ы добавят `config.py`, `ingest_youtube.py`,
  и т.д.
- **OpenSpec proposal** — этот change описан прямо в audit/tasks. Формальная
  OpenSpec-итерация появится при первом реальном коде (по образцу comic-studio).
- **FIXATION.md** — инструкция 5-шаговой fixation procedure. Упомянута в
  AGENTS.md, но сам файл будет создан при первом использовании.
- **Тесты** — для scaffolding нет что тестировать. Тесты появятся с первым
  функциональным модулем.
- **VPS deploy script** — не пишем пока commercial не потребует.
- **Character consistency Bible** — известный open problem (см. `## 7. Open Items`).

## 6. Файлы

### Created (этот change)

- `AGENTS.md`
- `README.md`
- `.env.example`
- `.gitignore`
- `bible/_TEMPLATE_show.md`
- `bible/_TEMPLATE_character.md`
- `bible/README.md`
- `library/README.md`
- `summary/audit/001_initial-scaffold.md` (этот файл)
- `summary/tasks/001_initial-scaffold.md`
- `summary/PRD/PRD.md`
- `CHANGELOG.md`
- `py/{ingest,episode,render,lib,index,search,assemble}/__init__.py`
- `mcp-server/`, `scripts/`, `cron/`, `serials/` (пустые dirs)

### Modified

- (нет — это первая фиксация в репо)

## 7. Open Items / Follow-ups (отдельные change'ы)

| ID | Что | Приоритет | Зачем |
|---|---|---|---|
| F1 | `py/lib/config.py` + `py/lib/lifecycle.py` | **High** | Фундамент для всех остальных модулей |
| F2 | `py/ingest/youtube.py` + `scripts/ingest_youtube.py` | **High** | Первый реальный ingest, end-to-end pipeline test |
| F3 | `py/ingest/coverr.py` + `py/ingest/mixkit.py` + `py/ingest/archive.py` | Medium | UA-friendly stock coverage |
| F4 | `py/episode/spec_writer.py` (LLM brief → spec.json) | **High** | Без этого нет эпизодов |
| F5 | `py/index/embedder.py` (BLIP-2 + CLIP через LM Studio) | Medium | Matcher без эмбеддингов работает грубо |
| F6 | `py/search/matcher.py` + `py/assemble/concat_exporter.py` | Medium | spec.json → matched.json → draft.json |
| F7 | `mcp-server/index.js` (capcut-pipeline MCP) | Medium | Hermes/Mavis управляют таймлайном |
| F8 | `cron/com.MiniMax.capcut-studio.nightly.plist` + `cron/nightly.sh` | Low | Daily batch (asset gen + reindex) |
| F9 | `bible/_TEMPLATE_scene.md` | Medium | Frozen scene template (lighting, props, composition) |
| F10 | Character consistency stress test (10 episodes same character) | Low | Главный open problem для серий |

## 8. Проверка

- [x] `AGENTS.md` написан, все 5 секций (Setup, Run, Layout, Invariants, Series workflow)
- [x] `bible/_TEMPLATE_show.md` с чеклистом из 11 пунктов
- [x] `bible/_TEMPLATE_character.md` с секциями (Identity, Visual, Wardrobe, Props, Personality, Behavior templates, Seed, Sample prompt)
- [x] `library/README.md` с metadata.json schema + index.sqlite schema + ingest flow
- [x] `.env.example` покрывает все провайдеры (MiniMax, OpenRouter, YouTube, Coverr, Mixkit, Archive, LM Studio)
- [x] `.gitignore` исключает `library/ai/`, `library/stock/`, `index.sqlite`, `.env`
- [x] Pixabay и Pexels помечены как blocked-from-UA (verified curl)
- [x] UA-friendly stock order: YouTube → Coverr → Mixkit → Archive.org
- [x] Git init + initial commit `be437d3 feat: initial scaffold`
- [x] Pixabay drop commit `b9a4486 fix: drop Pixabay as primary stock source`
- [x] `summary/audit/001_initial-scaffold.md` создан
- [x] `summary/tasks/001_initial-scaffold.md` создан
- [x] `summary/PRD/PRD.md` создан
- [x] `CHANGELOG.md` создан с ISO-8601 записями

## 9. Связанные

- `~/Projects/comic-studio/AGENTS.md` — sister-project, тот же паттерн
- `~/Projects/comic-studio/PRD/PRD.md` — образец для структуры нашего PRD
- `~/Projects/comic-studio/summary/audit/028_rerender-promote-and-tgbot-stability.md` — формат audit
- `~/Projects/comic-studio/summary/tasks/028_rerender-promote-and-tgbot-stability.md` — формат tasks
- `~/Projects/comic-studio/CHANGELOG.md` — формат CHANGELOG (ISO-8601 + Context/Commits/OpenSpec/Tests)