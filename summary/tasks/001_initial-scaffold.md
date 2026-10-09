# Задачи: Initial Scaffold + UA Stock Source Migration

**Change ID:** `initial-scaffold`
**OpenSpec:** (deferred — этот change описан прямо здесь)
**Компаньон:** `summary/audit/001_initial-scaffold.md`

## Статус: ✅ Done (scaffold + UA migration готовы, MVP foundation в работе)

| ID | Задача | Оценка | Статус |
|---|---|---|---|
| 1 | `mkdir` project structure (`bible/`, `library/`, `py/`, `mcp-server/`, `scripts/`, `cron/`, `serials/`, `summary/`, `openspec/`, `tests/`, `docs/`) | 5m | ✅ Done |
| 2 | `AGENTS.md` (полная спека — setup, run, layout, invariants, series workflow, deployment) | 30m | ✅ Done |
| 3 | `README.md` (короткий entry-point) | 5m | ✅ Done |
| 4 | `.env.example` (все провайдеры) | 10m | ✅ Done |
| 5 | `.gitignore` (library/, .env, __pycache__) | 5m | ✅ Done |
| 6 | `bible/_TEMPLATE_show.md` (frozen style template) | 15m | ✅ Done |
| 7 | `bible/_TEMPLATE_character.md` (character template) | 20m | ✅ Done |
| 8 | `bible/README.md` (bible discipline + seed strategy) | 10m | ✅ Done |
| 9 | `library/README.md` (asset schema + index.sqlite + ingest flow) | 15m | ✅ Done |
| 10 | Verify UA stock availability via curl (Pixabay/Pexels blocked, YouTube/Coverr/Mixkit/Archive OK) | 10m | ✅ Done |
| 11 | Update `.env.example` — drop Pixabay primary, add Coverr/Mixkit/Archive | 10m | ✅ Done |
| 12 | Update `library/README.md` — new stock order (UA-friendly) | 5m | ✅ Done |
| 13 | Update `AGENTS.md` — fallback chain + UA-friendly note | 5m | ✅ Done |
| 14 | Git init + initial commit `be437d3` | 5m | ✅ Done |
| 15 | Git commit `b9a4486` for UA migration | 5m | ✅ Done |
| 16 | `summary/audit/001_initial-scaffold.md` | 20m | ✅ Done |
| 17 | `summary/tasks/001_initial-scaffold.md` (этот файл) | 15m | ✅ Done |
| 18 | `summary/PRD/PRD.md` | 30m | ✅ Done |
| 19 | `CHANGELOG.md` с ISO-8601 entries | 10m | ✅ Done |
| 20 | Verify git log + status clean | 5m | ✅ Done |

## Зависимости

- **Mac Studio on WireGuard** (LM Studio на `192.168.55.1:1234` для будущего indexer)
- **Plus Plan active** на Mavis (MiniMax H3.0/H3 Max доступ через Plus)
- **OpenRouter API key** для Qwen3-Max (опционально сейчас, обязательно для текста позже)
- **YouTube Data API v3 key** (опционально сейчас, обязательно для stock ingest)
- **Pixabay/Pexels keys** НЕ требуются (UA блок); но если у пользователя есть VPN/старые ключи — `py/ingest/` поддержит skip-if-blocked fallback

## Как использовать (после завершения)

### Initial scaffold
```bash
cd ~/Projects/capcut-studio
ls -la
# → AGENTS.md, README.md, .env.example, .gitignore,
#   bible/, library/, py/, mcp-server/, scripts/, cron/, serials/,
#   summary/{audit,tasks,PRD}/, openspec/, tests/, docs/

cat AGENTS.md | head -50    # спека проекта
cat bible/_TEMPLATE_show.md # шаблон шоу
```

### Next step (F1: foundation)
```bash
# Следующий change — py/lib/{config.py, lifecycle.py}
# После него: py/ingest/youtube.py и end-to-end test
```

## Env variables

| Переменная | Default | Назначение |
|---|---|---|
| `MINIMAX_API_KEY` | (required) | MiniMax Plus для H3.0/H3 Max video gen |
| `MINIMAX_BASE_URL` | `https://api.MiniMax.io` | MiniMax API base |
| `OPENROUTER_API_KEY` | (required) | Qwen3-Max text + Qwen-Image reference |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter base |
| `YOUTUBE_API_KEY` | (optional, soon required) | YouTube Data API v3 для stock ingest |
| `COVERR_API_KEY` | (optional) | Coverr API для stock ingest |
| `MIXKIT_SCRAPE_DELAY_SEC` | `2.0` | Polite delay между Mixkit запросами |
| `LM_STUDIO_URL` | `http://127.0.0.1:1234` | Local LM Studio для BLIP-2 + CLIP |
| `LM_STUDIO_EMBED_MODEL` | `bge-large-en-v1.5` | Embedding model в LM Studio |
| `LM_STUDIO_CAPTION_MODEL` | `blip-2` | Captioning model |
| `CONCAT_MCP_URL` | `http://127.0.0.1:9847` | Concat MCP endpoint |
| `LIBRARY_ROOT` | `./library` | Корень asset library |
| `LIBRARY_INDEX` | `./library/index.sqlite` | SQLite индекс |
| `SERIALS_ROOT` | `./serials` | Корень эпизодов |
| `DEFAULT_VIDEO_PROVIDER` | `minimax-h3-max` | Default video provider |
| `DEFAULT_TEXT_PROVIDER` | `qwen3-max` | Default text provider |
| `DEFAULT_IMAGE_PROVIDER` | `qwen-image` | Default image provider |
| `DAILY_AI_BUDGET_USD` | `10` | Daily cap для AI gen (cron aborts above) |
| `PIXABAY_API_KEY` | (skip if blocked) | Pixabay fallback (UA blocked) |
| `PEXELS_API_KEY` | (skip if blocked) | Pexels fallback (UA blocked) |

## Файлы

### Created (этот change)
- `AGENTS.md` — полная спека
- `README.md` — entry-point
- `.env.example` — env vars reference
- `.gitignore` — git exclusions
- `bible/_TEMPLATE_show.md` — show template
- `bible/_TEMPLATE_character.md` — character template
- `bible/README.md` — bible discipline guide
- `library/README.md` — library schema + index.sqlite
- `summary/audit/001_initial-scaffold.md` — этот audit
- `summary/tasks/001_initial-scaffold.md` — этот tasks
- `summary/PRD/PRD.md` — полный PRD
- `CHANGELOG.md` — ISO-8601 log
- `py/{ingest,episode,render,lib,index,search,assemble}/__init__.py` — 7 пустых модулей

### Modified
- (нет)

## Связанные

- `summary/audit/001_initial-scaffold.md` — компаньон audit
- `summary/PRD/PRD.md` — полное описание продукта
- `CHANGELOG.md` — записи с ISO-8601 timestamps
- `~/Projects/comic-studio/` — sister-project, образец паттерна
- `AGENTS.md` → "Status", "Deployment model", "Series workflow" — зафиксированные решения

## Следующие задачи (отдельные change'ы)

| ID | Задача | Приоритет | Оценка |
|---|---|---|---|
| F1 | `py/lib/config.py` + `py/lib/lifecycle.py` | **High** | 1-2h |
| F2 | `py/ingest/youtube.py` + `scripts/ingest_youtube.py` | **High** | 3-4h |
| F3 | `py/ingest/coverr.py` + `py/ingest/mixkit.py` + `py/ingest/archive.py` | Medium | 4-6h |
| F4 | `py/episode/spec_writer.py` (LLM brief → spec.json) | **High** | 3-4h |
| F5 | `py/index/embedder.py` (BLIP-2 + CLIP через LM Studio) | Medium | 4-5h |
| F6 | `py/search/matcher.py` + `py/assemble/concat_exporter.py` | Medium | 5-6h |
| F7 | `mcp-server/index.js` (capcut-pipeline MCP) | Medium | 3-4h |
| F8 | `cron/com.MiniMax.capcut-studio.nightly.plist` + `cron/nightly.sh` | Low | 2-3h |
| F9 | `bible/_TEMPLATE_scene.md` | Medium | 1h |
| F10 | Character consistency stress test (10 episodes same character) | Low | TBD |
| F11 | OpenSpec formal proposal для первого кода (F1) | Medium | 1h |