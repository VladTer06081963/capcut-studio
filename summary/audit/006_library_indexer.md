# Аудит: Library indexer (F5)

**Дата:** 2026-10-09
**Change ID:** `library-indexer`
**OpenSpec:** deferred
**Компаньон:** `summary/tasks/006_library_indexer.md`
**Предшественник:** `summary/audit/005_secondary_stock.md`

## 1. Контекст

Matcher (F6) ищет клипы по spec.json-запросу. Нужна индексация библиотеки:
каждый клип получает caption + embedding для similarity search.

**Цель**: `library/index.sqlite` с captions (BLIP-2) + embeddings (bge-large)
для всех клипов в library/. Idempotent, graceful fallback если LM Studio
недоступен.

## 2. Архитектурные решения

| Вопрос | Решение |
|---|---|
| Embedding type | Text-эмбеддинг (caption + tags + title), не визуальный |
| LM Studio fallback | `lm_studio_alive()` graceful: indexer работает без caption/embed |
| Idempotency | sha256: re-indexing пропускает если (id, sha256) совпадают |
| Vector storage | float32 packed in BLOB, unpack на read |
| Search | Cosine similarity brute-force (replace с FAISS на 10k+) |
| Frame extraction | ffmpeg at t=0.5s, удаляется после embed |

## 3. Что добавлено

- `py/index/embedder.py` (~400 строк): schema, LM Studio clients,
  extract_frame, index_clip, index_library, get_clip_by_id, search_by_text
- `scripts/index_library.py` (~50 строк, CLI с --no-caption/--no-embed)
- `tests/test_embedder.py` (13 тестов)

## 4. Проверка

- [x] SQLite schema с caption + embedding BLOB
- [x] LM Studio clients (caption + embed)
- [x] lm_studio_alive() liveness
- [x] Graceful fallback (NULL fields если LM Studio down)
- [x] Idempotent на sha256
- [x] Cosine similarity search с source filter
- [x] 13/13 tests passing

## 5. Связанные

- Используется в `summary/audit/007_matcher_assembler.md` (F6)
- Подготовлен для F11 cron (nightly reindex)