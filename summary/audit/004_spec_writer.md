# Аудит: Episode spec writer (F4)

**Дата:** 2026-10-09
**Change ID:** `spec-writer`
**OpenSpec:** deferred
**Компаньон:** `summary/tasks/004_spec_writer.md`
**Предшественник:** `summary/audit/002_foundation.md`

## 1. Контекст

Второй этап pipeline после ingest: вместо LLM-с-нуля, LLM-генерит
структурированный план эпизода из творческого брифа + show bible. Это
выходной формат для всего matcher'а (F6).

**Цель**: brief.md + bible/<show>.md → spec.json (declarative, schema
versioned, validated) через Qwen3-Max.

## 2. Архитектурные решения

| Вопрос | Решение |
|---|---|
| LLM output format | Strict JSON через `response_format={"type": "json_object"}` |
| Schema versioning | `SCHEMA_VERSION = 1` в spec.json для future migrations |
| Idempotency | `brief_sha256` + `bible_sha256` в spec.json |
| Bible excerpt | Regex-based extraction of known sections (Visual style, Frozen prompt, Cast, Locations) |
| Validation | Post-LLM parse + `validate_spec()` — never trust LLM blindly |
| Provider whitelist | Убран (over-engineering); проверяется только тип |
| Dry-run | Пропускает LLM + validation, пишет stub spec для schema testing |

## 3. Что добавлено

- `py/episode/spec_writer.py` (~360 строк): `EpisodeSpec`/`SceneSpec` dataclasses,
  validation, OpenRouter wrapper, bible excerpt extraction, `write_spec_from_brief`,
  `load_spec` round-trip
- `scripts/spec_from_brief.py` (~60 строк, CLI с `--dry-run`)
- `tests/test_spec_writer.py` (15 тестов)

## 4. Проверка

- [x] LLM strict JSON output
- [x] Schema versioned
- [x] brief_sha256 + bible_sha256 для idempotency
- [x] Bible excerpt regex handles parenthetical headings
- [x] Defensive parsing (RuntimeError на malformed JSON)
- [x] Dry-run mode для schema testing
- [x] 15/15 tests passing

## 5. Связанные

- Используется в `summary/audit/007_matcher_assembler.md` (F6)
- Использует `py.lib.config` (F1)