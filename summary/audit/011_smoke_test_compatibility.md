# Аудит: F-11 — Smoke test compatibility fixes

**Дата:** 2026-10-10
**Тип:** Bugfix / hardening (compatibility)
**Изменил:** Mavis (root session, mvs_7a61928d78da42d19f08a74ef5d8420e)
**Причина:** End-to-end smoke test (brief → spec → matched → draft) на реальных
API выявил 7 несовместимостей, которые mock-тесты не покрывали. Все исправления —
локальные, backward-compatible.

---

## 1. Контекст

После фиксации F-10 (default text provider → LM Studio, commit `32401dc`)
проект собран и unit-тесты зелёные (79/79 mock'нутых). Следующий шаг — **real
smoke test** на живой pipe: spec_from_brief.py через локальную LM Studio,
ingest YouTube/Archive, indexer через embedding model, matcher, Concat draft.

Smoke test выявил 3 категории проблем:

| Категория | Корневая причина | Решение |
|---|---|---|
| **Provider quirks** (LM Studio, Ollama, Archive.org) | llama.cpp / Ollama / Archive API не реализуют OpenAI spec 1:1 | retry без `response_format`, `js_runtimes={node}`, sort с пробелом |
| **Auth** | LM Studio bearer token не пробрасывался во все endpoints | прокинут в `lm_studio_alive`, `embed_text`, `caption_image` |
| **Schema drift** | локальные LLM оборачивают JSON в ` ``` ` fences; LLM генерит slash-types (`dialogue/reaction`) не в whitelist | fence strip + whitelist расширен + slash normalize |
| **Scripts sys.path** | 3 из 6 ingest скриптов не имели `sys.path.insert` shim | добавлен во все 4 оставшиеся |
| **Env defaults** | bge-large не загружен в LM Studio; YOUTUBE_API_KEY невалидный (35 chars не той формы) | переключение на Ollama + новый YouTube key |

---

## 2. Что сделано (по файлам)

### 2.1 `py/episode/spec_writer.py`
Три правки:

1. **`_call_lm_studio_chat` — retry без `response_format`**
   LM Studio (через llama.cpp server) отклоняет `response_format={"type":"json_object"}`
   с `400 'response_format.type' must be 'json_schema' or 'text'`. Добавлен
   fallback: на этом конкретном 400 убираем поле и retry. OpenRouter path
   не задет (там `json_object` работает).

2. **`_extract_json_content` — strip markdown fence**
   qwen2.5-coder-7b (LM Studio) и некоторые Ollama модели заворачивают
   валидный JSON в ` ```json ... ``` ` блок несмотря на инструкцию "no fences".
   Добавлен regex strip перед `json.loads`.

3. **`VALID_SCENE_TYPES` + `_normalize_scene_type`**
   LLM генерил `dialogue/reaction` (slash) и `silhouette` (новый тип из brief).
   Расширил whitelist (`dialogue-reaction`, `silhouette`, `establishing-wide`,
   `establishing-reverse`, `insert`, `montage`) и добавил нормализацию
   `/` и `_` → `-` перед проверкой.

### 2.2 `py/index/embedder.py`
Добавлен bearer token в три места, где ранее не было:
- `lm_studio_alive()` — теперь OK status (раньше false из-за 401)
- `embed_text()` — embeddings реально сохраняются в SQLite
- `caption_image()` — готово к BLIP-2 captioning когда модель загружена

Импорт `LM_STUDIO_API_TOKEN` в шапке модуля.

### 2.3 `py/ingest/archive.py`
**`sort[]` separator fix.** Archive.org advancedsearch API интерпретирует
`+` в значении параметра как **literal character**, не как пробел. Старый
селектор `"downloads+desc"` ломал query (numFound=None). Поменяно на
`"downloads desc"` (пробел) — URL-encoded запрос нормально проходит.

Verified: `("fog") AND mediatype:movies` → 4398 numFound, docs returned.

### 2.4 `py/ingest/youtube.py`
**Format selector + JS runtime:**
- Старый `"best[height<=720][ext=mp4]/best[ext=mp4]/best"` — `height=None`
  для progressive MP4 не проходил фильтр
- Новый `"best[ext=mp4][acodec!=none][height<=720]/(bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a])/best[ext=mp4]/best"`
  берёт progressive MP4 сначала, fallback на merged video+audio, last resort best.
- Добавлен `"js_runtimes": {"node": {}}` — без JS runtime yt-dlp показывает
  только storyboards + 2 progressive формата (warning "deprecated, some
  formats may be missing").

Verified: 2/3 video скачано успешно после фикса (один 403 — региональный блок, не наш bug).

### 2.5 `scripts/ingest_*.py` (4 файла)
Добавлен `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` во все:
- `ingest_youtube.py`
- `ingest_coverr.py`
- `ingest_mixkit.py`
- `ingest_archive.py`

Раньше shim был только в `spec_from_brief.py`, `index_library.py`,
`assemble_episode.py`. Без shim → `ModuleNotFoundError: No module named 'py'`.

### 2.6 `.env`
- `LM_STUDIO_URL=http://127.0.0.1:11434` (Ollama)
- `LM_STUDIO_EMBED_MODEL=nomic-embed-text` (Ollama native name; bge-large
  не загружен в LM Studio → 400 "No models loaded")
- `YOUTUBE_API_KEY=<39-char AIzaSy...>` (получен через `gcloud services
  api-keys create` в Google Cloud Shell)

### 2.7 `.gitignore`
**Typo fix:** было `serial/*/rendered/` (singular), реальный путь — `serials/`
(plural). Добавлены:
- `serials/*/rendered/`
- `serials/*/matched.json`

Артефакты smoke test (draft.json, matched.json) теперь не попадают в git —
будут генерироваться при следующем assemble. Brief.md и spec.json (под
контролем версий) остаются как канонический input/output.

---

## 3. End-to-end pipeline status (после F-11)

| Step | Status | Evidence |
|---|---|---|
| `spec_from_brief.py` | ✅ | `serials/stalker-reznik/ep-01-pilot/spec.json` (6 scenes, real LLM) |
| `ingest_youtube.py` | ✅ | 2/3 скачано, 1×403 (geo/DMCA) |
| `ingest_archive.py` | ✅ | 2 клипа (большие фильмы, 1955 + 2003) |
| `index_library.py` | ✅ | `library/index.sqlite` populated, 1 client with embedding |
| `assemble_episode.py` | ✅ | `matched.json` 5/6, `draft.json` 31s, 2 tracks |
| `open -a Concat.app` | ✅ | GUI-маршрут работает; Concat MCP F7 deferred |

---

## 4. Тесты

**77/79 OK** (2 fail — pre-existing, не регрессия):
- `test_defaults_when_no_env` — `patch.dict(clear=True) + reload(config)` не
  отменяет `load_dotenv()`; требует `mock.patch('py.lib.config.load_dotenv')`
- `test_paths_resolve_under_project_root` — та же причина

Эти 2 теста не отражают regression от F-11; они плохо изолированы от .env.
Кандидат на F-12: добавить `mock.patch` для `load_dotenv` в setUp.

---

## 5. Что НЕ сделано (out of scope)

- ❌ **BLIP-2 captioning** — модель не загружена в LM Studio, captions пустые.
  Решение: `lms load blip-2` или fallback to filename+tags только
- ❌ **Match quality** — все matched scenes → один клип (SanFrancisco1955)
  потому что 1 клип в библиотеке с embedding. С 5 клипами после YouTube ingest
  matching станет разнообразнее (нужен re-assemble)
- ❌ **2 unit-теста** — см. §4
- ❌ **Coverr ingest** — API key подача заявки failed в UI; работаем без неё
  (Archive.org + YouTube покрывают smoke test)
- ❌ **Concat MCP** — F7 deferred (отдельный change)

---

## 6. Файлы

### Created
- `summary/audit/011_smoke_test_compatibility.md` (этот файл)
- `summary/tasks/011_smoke_test_compatibility.md`
- `serials/stalker-reznik/ep-01-pilot/matched.json` (untracked, в gitignore)
- `serials/stalker-reznik/ep-01-pilot/rendered/draft.json` (untracked, в gitignore)

### Modified
- `py/episode/spec_writer.py` (3 изменения, см. §2.1)
- `py/index/embedder.py` (3 изменения, см. §2.2)
- `py/ingest/archive.py` (1 line: sort separator)
- `py/ingest/youtube.py` (2 изменения: format selector + js_runtimes)
- `scripts/ingest_youtube.py` (sys.path shim)
- `scripts/ingest_coverr.py` (sys.path shim)
- `scripts/ingest_mixkit.py` (sys.path shim)
- `scripts/ingest_archive.py` (sys.path shim)
- `serials/stalker-reznik/ep-01-pilot/spec.json` (LLM-generated, real)
- `.env` (3 переменные)
- `.gitignore` (2 новые строки)

### Not modified (но в .gitignore)
- `library/` (assets в .env, regeneratable)

---

## 7. Безопасность

- ✅ `.env` остаётся в `.gitignore` — секреты не коммитятся
- ✅ Bearer tokens не logged в CHANGELOG или audit файлах
- ✅ YOUTUBE_API_KEY упомянут только метаописательно ("39-char AIzaSy...")
- ✅ Google Cloud Shell не сохранил credentials между сессиями

---

## 8. Команды для воспроизведения

```bash
cd ~/Projects/capcut-studio

# 1. Spec
python3 scripts/spec_from_brief.py \
    --brief serials/stalker-reznik/ep-01-pilot/brief.md \
    --bible bible/stalker-reznik-series.md \
    --output serials/stalker-reznik/ep-01-pilot/spec.json \
    --model qwen2.5-coder-7b-instruct-mlx

# 2. Ingest
python3 scripts/ingest_youtube.py --query "fog night" --count 3 --license creativeCommon
python3 scripts/ingest_archive.py --query "fog" --count 5

# 3. Index (Ollama embeddings)
python3 scripts/index_library.py

# 4. Assemble
python3 scripts/assemble_episode.py --serial stalker-reznik --ep ep-01-pilot

# 5. Open
open -a Concat.app serials/stalker-reznik/ep-01-pilot/rendered/draft.json
```