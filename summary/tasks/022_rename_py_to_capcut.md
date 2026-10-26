# Задачи: rename `py/` package to `capcut/` (fixation 022)

## Статус: ✅ Done (2026-10-19)

| ID | Задача | Статус |
|---|---|---|
| 1 | `git mv py capcut` (24 файла, история сохранена) | ✅ Done |
| 2 | Импорты в 34 Python-файлах: `py.X` → `capcut.X` | ✅ Done |
| 3 | `capcut/requirements.txt` переехал вместе с директорией | ✅ Done |
| 4 | 6 живых доков переписаны (49 ссылок на пути) | ✅ Done |
| 5 | Исторические `summary/audit/*` + `summary/tasks/*` не тронуты | ✅ Done |
| 6 | `README.md` — секция «Running the tests» | ✅ Done |
| 7 | `README_RU.md` — устаревший footgun-блок заменён | ✅ Done |
| 8 | **pytest из корня репозитория** (главный критерий) | ✅ **129 passed** |
| 9 | pytest из чужого CWD | ✅ 129 passed |
| 10 | 0 остаточных `from py.` / `import py.` | ✅ 0 совпадений |
| 11 | `scripts/assemble_episode.py --help` | ✅ работает |
| 12 | `import capcut.lib.config` | ✅ резолвится |
| 13 | `node mcp-server/test/concat_paths.test.js` | ✅ 4/4 |
| 14 | `.pi/` добавлен в git отдельным коммитом | ✅ `1ae31d8` |
| 15 | OpenSpec proposal + tasks | ✅ |
| 16 | OpenSpec архивирован | ✅ `archive/2026-10-19-rename-py-to-capcut/` |
| 17 | Audit `summary/audit/022_rename_py_to_capcut.md` | ✅ |
| 18 | Tasks (этот файл) | ✅ |
| 19 | CHANGELOG.md | ✅ |
| 20 | Git commit | ✅ `acda9f4` |
| 21 | Merge ветки в `main` + push | ⏸ Требует подтверждения |

## Подробности

### Что переименовано

```
py/                    →  capcut/
├── __init__.py
├── assemble/          (concat_exporter.py)
├── episode/           (spec_writer.py)
├── index/             (embedder.py)
├── ingest/            (archive, coverr, mixkit, youtube)
├── lib/               (config, lifecycle, model_approval)
├── render/            (base, kie_client, minimax_client, provider_router)
├── search/            (matcher.py)
└── requirements.txt
```

### Переписанные импорты (34 файла)

**Пакет (12):**
- `capcut/assemble/concat_exporter.py`
- `capcut/episode/spec_writer.py`
- `capcut/index/embedder.py`
- `capcut/ingest/{archive,coverr,mixkit,youtube}.py`
- `capcut/render/{__init__,kie_client,minimax_client,provider_router}.py`
- `capcut/search/matcher.py`

**Скрипты (10):** `assemble_episode`, `generate_ai_clips`, `index_library`,
`ingest_{archive,coverr,mixkit,youtube}`, `model_approval_ui`,
`spec_from_brief`, `test_kie`

**Тесты (9):** `test_config`, `test_embedder`, `test_kie_client`,
`test_lifecycle`, `test_matcher_assembler`, `test_model_approval`,
`test_secondary_ingest`, `test_spec_writer`, `test_youtube_ingest`

**Странные root-скрипты (3):** `test_kie.py`, `test_kie_price.py`,
`test_kie_wan.py`

### Переписанные доки (6 файлов, 49 ссылок)

| Файл | Замен | Что именно |
|---|---|---|
| `AGENTS.md` | 16 | layout tree, install cmd, `capcut/lib/config.py`, `capcut/episode/spec_writer.py`, `capcut/index/`, `capcut/ingest/`, `capcut/render/{kie_client,provider_router}.py`, `capcut/assemble/concat_exporter.py`, deployment diagram |
| `summary/PRD/PRD.md` | 14 | layout tree, module surface, feature table F1–F6, F-020 |
| `.github/copilot-instructions.md` | 7 | install cmd, module descriptions |
| `.github/copilot-instructions.ru.md` | 7 | то же на русском |
| `README_RU.md` | 4 | install cmd + footgun-блок + follow-ups |
| `README.md` | 1 | install cmd |

### Почему исторические файлы не тронуты

`summary/audit/001…020` и `summary/tasks/001…020` — записи о том, как
выглядело дерево **в момент их написания**. Если переписать в них
`py/` → `capcut/`, история станет недостоверной: читатель не сможет
восстановить, что было на диске, когда принималось решение.

### Главный критерий

```bash
cd ~/Projects/capcut-studio
source .venv/bin/activate
python -m pytest tests/ -q
# 129 passed  ← раньше требовало cd /tmp + --rootdir
```

## Что осталось

- Merge ветки `feature/rename-py-to-capcut` в `main` + push (требует
  подтверждения — `main` защищён по AGENTS.md «Branch workflow»).
