# Аудит: Matcher + Concat timeline exporter (F6)

**Дата:** 2026-10-09
**Change ID:** `matcher-assembler`
**OpenSpec:** deferred (logical unit, ~500 lines)
**Компаньон:** `summary/tasks/007_matcher_assembler.md`
**Предшественник:** `summary/audit/006_library_indexer.md`

## 1. Контекст

Ключевой change. После F5 (indexer) нужны две вещи:
1. `match_episode(spec)` — для каждой scene находим лучший клип в library
2. `assemble_timeline(spec, matched)` — собираем Concat-совместимый timeline

Это завершает end-to-end pipeline: brief.md → spec → index → match → assemble.

## 2. Архитектурные решения

### Matcher
- `SOURCE_PRIORITY`: ai → stock → any fallback chain
- `_resolve_source_filter()` — single function для chain
- Audio tracks скипаются (voiceover без visual query)
- Low-similarity threshold (0.1) фильтрует шумные матчи
- Unmatched scenes → warnings (не fail)

### Concat exporter
- Треки: video-main, audio-main, overlay-character (пустые дропаются)
- Transitions: fade-in на первом, fade-out на последнем, cut между
- Audio voiceover placeholder (TTS заполнит src позже)
- Schema versioned (`SCHEMA_VERSION = 1`)
- `_pick_transition()` — тестируемая функция:
  - single scene → fade-in + fade-out
  - first → fade-in + cut
  - last → cut + fade-out
  - middle → cut + cut

## 3. Что добавлено

- `py/search/matcher.py` (~230 строк): SceneMatch/MatchedEpisode,
  match_episode, write/load round-trip
- `py/assemble/concat_exporter.py` (~270 строк): ConатClip/Track/Project/
  Timeline, assemble_timeline, write/load
- `scripts/assemble_episode.py` (~50 строк, end-to-end CLI)
- `tests/test_matcher_assembler.py` (14 тестов)

## 4. Проверка

- [x] Source priority: ai → stock → any
- [x] Audio tracks skip
- [x] Low-score filter (0.1)
- [x] Unmatched scenes → warnings
- [x] Transitions правила для всех позиций
- [x] Concat JSON schema versioned
- [x] 14/14 tests passing
- [x] End-to-end: spec.json → matched.json → draft.json

## 5. End-to-end pipeline (теперь рабочий)

```
brief.md → [F4 spec_from_brief] → spec.json
                                       ↓
library/ai + library/stock → [F5 index_library] → index.sqlite
                                       ↓
spec.json → [F6 match_episode] → matched.json
                                       ↓
spec.json + matched.json → [F6 assemble_timeline] → rendered/draft.json
```

## 6. Связанные

- `summary/audit/004_spec_writer.md` (F4) — produces spec.json
- `summary/audit/006_library_indexer.md` (F5) — provides index.sqlite
- F7 (capcut-pipeline MCP) — будет использовать matcher + assembler