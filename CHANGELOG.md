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

## 2026-10-09T19:00Z — Fixation 003: F2 — YouTube stock ingest

**Context**: первый реальный stock ingest. Data API v3 search + yt-dlp download
+ ffprobe probe + metadata.json writer. Primary stock source per AGENTS.md fallback
chain (YouTube verified reachable from UA via curl 2026-10-09T18:13Z).

**Что добавлено**:
- `py/ingest/youtube.py` (~290 строк): `search_videos()` (Data API v3, два
  запроса — search + videos для enrich), `download_video()` (yt-dlp,
  720p MP4, 500MB hard cap), `probe_metadata()` (ffprobe → duration/resolution/fps),
  `write_metadata()` (sibling `<mp4>.metadata.json` с sha256), высокоуровневый
  `ingest()` с per-video error handling (errors не валят весь batch)
- `scripts/ingest_youtube.py` (~80 строк): CLI с `--query`, `--count`,
  `--license` (any/creativeCommon), `--output-dir`, `--duration`
- `tests/test_youtube_ingest.py` (7 тестов): search response parsing, probe
  metadata, write metadata, download_video, per-video error handling в `ingest()`
- `py/requirements.txt`: yt-dlp + python-dotenv + requests (для F2)

**Архитектурные решения**:
- Убрал `isodate` зависимость — свой `_parse_iso_duration_seconds()` regex
  (PT2M30S → 150) занимает 5 строк и не требует pip install
- `LICENSE_CC` vs `LICENSE_ANY` — CC для re-use-safe материала, any для
  стандартного YouTube license (B-roll где re-use не критично)
- `ingest()` возвращает `IngestResult{videos, files, errors}` — partial success:
  3 из 5 видео скачались, остальные с errors → вызывающий решает что делать
- `probe_metadata()` отдельная функция (не внутри download_video) — позволяет
  пере-зондировать при reindex без re-download

**Тесты**: 25/25 OK (18 предыдущих + 7 новых).
`python -m unittest discover -s tests -p 'test_*.py'`

## 2026-10-09T19:35Z — Fixation 004: F4 — episode spec writer (LLM brief → spec.json)

**Context**: brief.md + bible/<show>.md → spec.json через Qwen3-Max (OpenRouter).
Это второй этап pipeline после ingest: вместо «LLM-генерит-с-нуля», LLM-генерит-
структурированный план эпизода из творческого брифа.

**Что добавлено**:
- `py/episode/spec_writer.py` (~360 строк): dataclasses `EpisodeSpec` +
  `SceneSpec` со schema version 1, валидация (`validate_spec()`), thin wrapper
  над OpenRouter Chat Completions API (`call_openrouter()` с response_format=
  json_object), `extract_bible_excerpt()` (вытаскивает релевантные секции
  bible — Visual style / Frozen prompt / Cast / Locations), `write_spec_from_brief()`
  (read → build prompt → call LLM → parse → validate → write spec.json),
  `load_spec()` (round-trip)
- `scripts/spec_from_brief.py` (~60 строк): CLI с `--brief`, `--bible`,
  `--output`, `--model`, `--dry-run`
- `tests/test_spec_writer.py` (15 тестов): все валидационные кейсы, regex
  для bible excerpt (включая parenthetical в heading), round-trip load/save,
  invalid LLM JSON handling, validation failure handling

**Архитектурные решения**:
- LLM output строгий JSON через `response_format={"type": "json_object"}` —
  проще парсить, меньше галлюцинаций с markdown
- `brief_sha256` + `bible_sha256` в spec.json — для idempotency:
  повторный запуск с теми же входными файлами = no-op
- `extract_bible_excerpt()` regex-friendly к parentheticals в headings
  ("Frozen video prompt suffix (H3.0 / H3 Max)")
- Dry-run пропускает LLM call и валидацию (для testing схемы)
- Provider whitelist в валидаторе убран (over-engineering) — проверяем
  только тип (string), полный список моделей проверяется в client
- Defensive parse: `RuntimeError` на malformed JSON от LLM, не silent fail

**OpenSpec**: deferred (single-file change ~360 lines + tests).

**Тесты**: 40/40 OK (25 предыдущих + 15 новых).
`python -m unittest discover -s tests -p 'test_*.py'`

## 2026-10-09T20:00Z — Fixation 005: F3 — secondary stock ingest (Coverr + Mixkit + Archive)

**Context**: завершаем UA-friendly stock coverage. YouTube (F2) — primary,
Coverr (F3-1) — secondary API, Mixkit (F3-2) — HTML scrape (no API), Archive.org
(F3-3) — public-domain fallback. Все три verified reachable из UA.

**Что добавлено**:
- `py/ingest/coverr.py` (~220 строк): official API client (Bearer auth),
  `VideoMeta`/`ProbeResult`/`IngestResult` dataclasses, `search_videos` +
  `download_video` (streaming) + `probe_metadata` (ffprobe) + `write_metadata`
  + high-level `ingest()`
- `py/ingest/mixkit.py` (~280 строк): HTML scrape (`_find_video_cards` regex),
  page-level MP4 resolution (`_resolve_download_url` via `<source>` or og:video),
  polite delay (default 2.0s из config). HTML-parsing изолирован в одной
  функции — если Mixkit обновит layout, чинится один фрагмент.
- `py/ingest/archive.py` (~250 строк): advancedsearch API + Lucene-query
  quoting для safety, identifier → MP4 derivative resolver (prefers H.264),
  public-domain metadata
- `scripts/ingest_coverr.py`, `scripts/ingest_mixkit.py`, `scripts/ingest_archive.py`
  (3 CLI, ~30 строк каждый)
- `tests/test_secondary_ingest.py` (12 тестов): coverr search/parse/write,
  mixkit HTML parsing + duration parsing + polite delay + page URL resolution,
  archive search + Lucene quote safety + h.264 preference + no-video-error

**Архитектурные решения**:
- Все три источника имеют одинаковый dataclass shape (`VideoMeta`/`ProbeResult`/
  `IngestResult`) — облегчает будущий универсальный matcher
- Per-video error handling в каждом `ingest()` — partial success,
  не валит весь batch на одной сломанной видео
- Lucene query в archive.py всегда quoted через `f'("{query}")'` — безопасно
  от injection / syntax errors
- `_find_video_cards()` regex покрывает `<article data-href="...">...<h3>title</h3>...
  <img src=...><span class="duration">0:45</span></article>` — если Mixkit
  переедет на другой тег, чинится одна функция
- License URL parsing в archive.py: `rstrip("/").split("/")[-1]` —
  trailing slash обработан (URL вида `https://creativecommons.org/publicdomain/`)

**Тесты**: 52/52 OK (40 предыдущих + 12 новых).
`python -m unittest discover -s tests -p 'test_*.py'`

## 2026-10-09T20:15Z — Fixation 006: F5 — library indexer (BLIP-2 + bge-large via LM Studio)

**Context**: matcher (F6) ищет клипы по `spec.json`-запросу. Нужна индексация
библиотеки: каждый клип получает caption + embedding для similarity search.

**Что добавлено**:
- `py/index/embedder.py` (~400 строк):
  - SQLite schema (`clips` table с caption + embedding BLOB + tags + probe data)
  - `pack_embedding`/`unpack_embedding` (float32 <-> bytes)
  - `caption_image()` через LM Studio `/v1/chat/completions` (multimodal, base64 image)
  - `embed_text()` через LM Studio `/v1/embeddings` (bge-large-en-v1.5 default)
  - `lm_studio_alive()` liveness check (graceful fallback если LM Studio down)
  - `extract_frame()` через ffmpeg (mid-video PNG)
  - `index_clip()` — single clip: probe → extract frame → caption → embed → INSERT
  - `index_library()` — walk library/, skip .tmp/, idempotent на sha256
  - `get_clip_by_id()` / `search_by_text()` (cosine similarity brute-force,
    готов для F6 matcher)
- `scripts/index_library.py` (~50 строк): CLI с `--no-caption`/`--no-embed`
- `tests/test_embedder.py` (13 тестов): pack/unpack roundtrip, init_db,
  LM Studio client (caption/embed/liveness), index_clip (insert, idempotent,
  skip-zero-duration), search_by_text (top match, source filter)

**Архитектурные решения**:
- Текст-эмбеддинг (caption + tags + title), не визуальный — проще, достаточно
  для semantic search на 10k+ клипах. Визуальный эмбеддинг можно добавить
  позже (CLIP-via-LM-Studio уже есть в .env).
- `lm_studio_alive()` graceful fallback: если LM Studio down, indexer всё
  равно работает (без caption/embedding — `NULL` поля).
- Idempotent на sha256: повторный index не перезаписывает row если sha256
  совпадает. Только changed файлы re-caption + re-embed.
- Cosine similarity brute-force (не FAISS). Для <10k клипов — fine.
  Заменяется на sqlite-vss/FAISS если библиотека разрастётся.

**Тесты**: 65/65 OK (52 предыдущих + 13 новых).
`python -m unittest discover -s tests -p 'test_*.py'`

## 2026-10-09T20:45Z — Fixation 007: F6 — matcher + Concat timeline exporter

**Context**: ключевой change. После F5 (indexer) нужны две вещи:
1. `match_episode(spec)` — для каждой scene находим лучший клип в library
2. `assemble_timeline(spec, matched)` — собираем Concat-совместимый timeline

**Что добавлено**:
- `py/search/matcher.py` (~230 строк):
  - Dataclasses `SceneMatch`, `MatchedEpisode`
  - `SOURCE_PRIORITY`: ai → stock → any fallback chain
  - `match_episode()` — для каждой scene embed query → search → priority
    resolution → best match; скипает audio-сцены (voiceover без visual query)
  - `write_matched` / `load_matched` round-trip
  - Low-similarity threshold (0.1) — фильтрует шумные матчи
- `py/assemble/concat_exporter.py` (~270 строк):
  - Dataclasses `ConcatClip`, `ConcatTrack`, `ConcatProject`, `ConcatTimeline`
  - `assemble_timeline()` — spec + matched → Concat-совместимый JSON
  - Треки: video-main, audio-main, overlay-character (пустые дропаются)
  - Transitions: fade-in на первом, fade-out на последнем, cut между
  - Audio voiceover placeholder (TTS заполнит `src` позже)
  - `write_concat_timeline` / `load_concat_timeline`
- `scripts/assemble_episode.py` (~50 строк): end-to-end CLI (spec → matched → draft.json)
- `tests/test_matcher_assembler.py` (14 тестов): source priority, audio skip,
  video match, no-match warnings, low-score skip, persistence round-trip,
  video tracks, audio track voiceover, unmatched warnings, Concat round-trip

**Архитектурные решения**:
- `_resolve_source_filter()` — single function для fallback chain (легко
  расширить если появятся новые источники)
- `_pick_transition()` — отдельная функция, тестируемая:
  - single scene → fade-in + fade-out
  - first → fade-in + cut
  - last → cut + fade-out
  - middle → cut + cut
- Unmatched scenes не валят pipeline — записываются в `unmatched_scenes`
  для последующей AI-генерации или skip'а
- Concat timeline schema versioned (`SCHEMA_VERSION = 1`)

**Тесты**: 79/79 OK (65 предыдущих + 14 новых).
`python -m unittest discover -s tests -p 'test_*.py'`

**End-to-end pipeline теперь рабочий**:
```
brief.md → [F4 spec_from_brief] → spec.json
                                       ↓
library/ai + library/stock → [F5 index_library] → index.sqlite
                                       ↓
spec.json → [F6 match_episode] → matched.json
                                       ↓
spec.json + matched.json → [F6 assemble_timeline] → rendered/draft.json
```

**Open Items**:
- F7: capcut-pipeline MCP для Hermes (uses matcher + assembler)
- F9: bible/_TEMPLATE_scene.md
- F8: cron/nightly.sh + launchd .plist (calls indexer + ingest)
- F11: OpenSpec formal proposal
- F10: Character consistency stress test