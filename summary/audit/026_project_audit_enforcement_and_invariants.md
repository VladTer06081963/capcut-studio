# 026 — Сквозной аудит проекта: enforcement, инварианты и гигиена репозитория

**Status:** ✅ Done (2026-10-28) — read-only аудит, изменений в коде нет
**Trigger:** вопрос пользователя «какие видишь недостатки в проекте?» после
серии правок MCP-сервера и конвертера Concat
**Scope:** весь репозиторий на `7aa9394` (`main`) — `capcut/`, `scripts/`,
`mcp-server/`, `frontend/`, `tests/`, `openspec/`, `summary/`, конфигурация
и состояние git. **Ни один файл не изменён, ни один платный API не
вызван, ни один генератор не запущен.**

> **Нумерация.** Серия `summary/audit/` уже использовала 025
> (`summary/audit/025_draw-things-removed_comfyui_provider.md`), поэтому
> аудит этой фиксации — **026**, а задачи — **025**
> (`summary/tasks/025_audit_followups_enforcement_and_invariants.md`). Пара
> намеренно асимметрична; это отражено в обоих файлах.

## 1. Контекст

Проект заявляет в `AGENTS.md` набор жёстких инвариантов: approval-гейт,
идемпотентность, иммутабельность `final.mp4`, библиотека как источник
истины с sha256, аддитивность индекса, обязательная атрибуция лицензий.
Пайплайн при этом объявлен «R&D / prep, **not production**» — то есть
статус не-готовности декларируется честно.

Вопрос был в том, **насколько** реальный код соответствует этим
декларациям, и какие дефекты молча портят данные, а не падают.

## 2. Метод

- Полный read-only обход дерева: `capcut/`, `scripts/`, `mcp-server/`,
  `frontend/`, `tests/`, `config/`, `openspec/`, `summary/`.
- Три параллельных скаута по непересекающимся зонам (Python-ядро;
  CLI + инварианты + тесты; MCP/frontend/config/гигиена) плюс
  собственная проверка каждого ключевого утверждения вручную.
- Каждая находка перепроверена точечными командами: `git grep`,
  `awk`/`grep -n` по конкретным строкам, `python3 -m py_compile`,
  `python3 -m pytest`, `pytest --collect-only`.
- Отдельно исследованы локальные примеры `concat.json` (7 штук) и строки
  бинаря `Concat.app` — для проверки формата FPS и переходов.

## 3. Главный вывод

**Проект не в хаосе. У него один явный P0 и около восьми незамеченных
дефектов, и самые опасные из них — те, что молча портят данные.**

Два инварианта из `AGENTS.md` не обеспечены кодом:

| Инвариант | Статус | Где ломается |
|---|---|---|
| Approval-гейт модели | **Не enforced** | `claim_approval()` (`capcut/lib/model_approval.py:117`) вызывается только из `tests/test_model_approval.py:48-89` |
| Approval-гейт эпизода | **Не привязан к spec** | `revise()` (`capcut/lib/lifecycle.py:147`) — 0 production-callers; `spec_writer.py:551` перезаписывает `spec.json` и не снимает `.approved` |
| Библиотека = источник истины (ID + sha256) | **Нарушен** | `SceneMatch` (`capcut/search/matcher.py:48`) не имеет поля `sha256`; `concat_exporter.py:119` проверяет только `exists()` |
| Индекс аддитивен | **Нарушен** | `capcut/index/embedder.py:339` `INSERT OR REPLACE` при `id TEXT PRIMARY KEY` |
| Approval-гейт эпизода (наличие) | Реализован | `scripts/render_final.py:111` — отказ без `.approved`, exit non-zero |
| Идемпотентность рендера | Реализована и покрыта тестами | `scripts/render_final.py:121-141` |
| Иммутабельность `final.mp4` | Реализована **на CLI-уровне** | `final_renderer.py:370` `os.replace` **без** `exists()`-guard — на уровне библиотеки перезапись возможна |

### 3.1. Важное уточнение: P0-1 — это долг, а не баг

Первое, что бросается в глаза, — «approval никем не проверяется». Но проект
**это знает и записал**:

- `summary/tasks/016_stabilization_and_spend_safety.md:3` — «🟡 В работе;
  локальная панель и approval-artifact MVP реализованы, **generation-guard
  ещё не подключён**»;
- там же `:23-25` — три незакрытых P0-пункта: подключить проверку
  approval-артефакта, убрать silent fallback, добавить мок-тесты на отказ;
- там же `:19` — **принятое решение**: «до текущей задачи пользователь явно
  указывает/одобряет точную модель; это достаточное разрешение»;
- `openspec/changes/hybrid-media-workflow/proposal.md` — acceptance criteria
  уже требуют явно выбранного provider и точной модели, атомарно
  потребляемый approval-артефакт и запрет silent fallback;
- `.pi/skills/episode-planning/SKILL.md:28` — скилл прямо предупреждает, что
  entrypoints «do not yet enforce the approval artifact».

То есть human-in-the-loop задумывался как **пользователь в диалоге**, а
артефактная панель — как его усиление. Панель построена корректно
(loopback-only, Origin-проверка, CSP, лимит тела 16 KB, артефакты вне
репозитория с 0700/0600 и атомарным claim) — но **ничем не потребляется**.

Корректная формулировка: не «баг», а **«панель, которую легко принять за
защиту, при том что защиты нет»**. Риск реален — `scripts/generate_ai_clips.py:30`
стартует платное задание с дефолтной моделью без вопроса к пользователю,
`capcut/render/provider_router.py:139-147` молча идёт к другому провайдеру,
`capcut/episode/spec_writer.py:243-247` переходит с локального LM Studio на
платный OpenRouter, а `capcut/lib/config.py:132` `DAILY_AI_BUDGET_USD`
**не читается нигде** — «дневной бюджет» равен нулю enforcement.

Остальные находки (P0-2…P1-6) — новые, ранее не заведённые.

### 3.2. Дефекты, которые молча портят данные

Это отдельная категория, и она опаснее падений: падение видно, молчание —
нет.

| Дефект | Место | Последствие |
|---|---|---|
| sha256 клипа не доходит до эпизода | `matcher.py:48`, `concat_exporter.py:119` | Подмена файла в библиотеке **тихо** меняет `final.mp4` вместо «громкой» поломки |
| Метаданные AI-клипов не находятся | `generate_ai_clips.py:56` (`.meta.json`) vs `embedder.py:205` (`.metadata.json`) | `source=NULL`, id `unknown:*`, теги/лицензия теряются; `source_filter="ai"` в матчере **никогда** не срабатывает — вся AI-ветка пайплайна мертва |
| `INSERT OR REPLACE` | `embedder.py:339` + `embedder.py:258` | При коллизии basename один из двух asset'ов **молча** теряется из общего индекса |
| Скачивание неатомарно + переиспользуется | `kie_client.py:458-467` | Прерванная закачка = обрезанный mp4, помеченный `success=True`, и перемещённый в библиотеку (`generate_ai_clips.py:88`) |
| Ingest пишет прямо в цель | `archive.py:165`, `coverr.py:148`, `mixkit.py:226` | Оборванный `.mp4` остаётся под валидным именем; `embedder.py:296` отбрасывает только `duration_sec <= 0` |
| Запись state-файлов неатомарна | `spec_writer.py:518,553`, `matcher.py:214`, `concat_exporter.py:296`, `lifecycle.py:222`, `ingest/*` | Обрыв на середине → битый JSON, который потом не читается |
| `final.mp4` пишется **до** `spec.sha256` | `render_final.py:174-179` | Сбой bookkeeping → эпизод **залипает навсегда**: `final.mp4` есть, хэша нет, immutability запрещает перерендер |
| Ошибки инфраструктуры гасятся | `matcher.py:139`, `embedder.py:318,328` | Недоступный LM Studio даёт «полноценный на вид» `matched.json` с пустыми совпадениями вместо ошибки |
| Бриф молча обрезается | `spec_writer.py:53,492` (`MAX_BRIEF_CHARS = 8_000`) | Spec строится по части брифа, без предупреждения |
| Два несовместимых «spec hash» | `matcher.py:201` (строка сцен) vs `lifecycle.py:192` (файл) | Одинаковые имена, несопоставимые значения |

### 3.3. Гигиена, из-за которой всё это невидимо

- **`.env.example` никогда не был закоммичен.** `.gitignore:3` (`.env.*`)
  матчит и его; `git log --all -- .env.example` пуст. Ломаются на чистом
  клоне `AGENTS.md:21`, `scripts/setup_keys.sh:16`,
  `.github/copilot-instructions.md:35` — весь env-контракт существует
  только локально.
- **`python3 -m pytest` из корня = 0 тестов.** Коллизия базовых имён
  `test_kie.py` (корень) и `scripts/test_kie.py` → `Interrupted: 1 error
  during collection`. `pytest tests/` → 161 passed. Нет `pytest.ini`, нет CI.
- **CI отсутствует** (`.github/` содержит только `copilot-instructions.md`),
  а `mcp-server/package.json:7` — `npm test` = заглушка с `exit 1`.
- **15+ сгенерированных файлов в индексе** (`serials/**/rendered/**`,
  `cache/art/*.jpg` ~430 KB) — добавлены коммитом `1ae31d8` **до**
  появления правила в `.gitignore`; gitignore не раз-трекает. Внутри
  зашиты `/Volumes/MacStudioData/...` пути, которые `.gitignore:22-24` сам
  называет недопустимыми.
- **Корневые `test_kie.py`, `test_kie_price.py`, `test_kie_wan.py`** —
  закоммичены, дублируют `scripts/test_kie.py` и ходят в **платный** API.
- **`scripts/setup_keys.sh:29`** подставляет секрет в исходник `python3 -c`
  → секрет виден в `ps`, вопреки комментарию в шапке скрипта.
- **`.agents/mcp_config.json:6`** — абсолютный путь `/Users/vladteresena/…`
  в индексе; MCP не стартует на другом клоне.
- **`.gitignore:18`** игнорирует `package-lock.json` → `npm ci` невозможен.
- **Оба pre-existing in-flight OpenSpec-изменения не проходят
  `openspec validate`.** `openspec validate --all` → `0 passed, 3 failed`:
  падают `openspec/changes/hybrid-media-workflow/` и
  `openspec/changes/pi-project-agent/`. Причина — спеки написаны в
  старом формате (секции `## <требование>` без delta-заголовков
  `## ADDED Requirements` и без `#### Scenario:`), а схема `spec-driven`
  v1.7.0 требует и то, и другое, и минимум один сценарий на требование.
  Ни одна спека в репозитории сейчас не использует delta-формат. То же
  касается `proposal.md`: парсер требует секций `## Why` и
  `## What Changes`.

## 4. Что сделано

### 4.1. Регистрация долга (2026-10-28)

Изменений в коде на этом шаге **не было**. Созданы только записи долга и
контракт:

| Путь | Действие | Описание |
|---|---|---|
| `summary/audit/026_project_audit_enforcement_and_invariants.md` | CREATED | этот аудит |
| `summary/tasks/025_audit_followups_enforcement_and_invariants.md` | CREATED | реестр долга: P0-1…P0-5, P1-1…P1-7, P2-1…P2-21, с критериями завершения |
| `openspec/changes/approval-enforcement-and-spec-binding/proposal.md` | CREATED | контракт для P0-1 и P0-2 |
| `openspec/changes/approval-enforcement-and-spec-binding/tasks.md` | CREATED | план реализации OpenSpec-change |
| `openspec/changes/approval-enforcement-and-spec-binding/specs/model-approval-enforcement/spec.md` | CREATED | SHALL-требования: claim на entrypoint'ах, запрет silent fallback, явный local→remote переход, честный exit code, запрет мёртвых config-значений |
| `openspec/changes/approval-enforcement-and-spec-binding/specs/episode-approval-binding/spec.md` | CREATED | SHALL-требования: approval фиксирует хэш ревьюенного `spec.json`, перезапись spec отзывает approval атомарно, рендер сверяет хэш, legacy-approval отклоняется |

OpenSpec-change закрывает конкретный незакрытый пункт
`summary/tasks/016_stabilization_and_spend_safety.md:56`:
«Перед изменением кода для enforcement approval/immutable подготовить
OpenSpec proposal и delta-spec».

### 4.2. Реализация P0-4 и P0-5 (2026-10-28)

Две правки, снимающие риск «всё ломается тихо»:

| Путь | Действие | Описание |
|---|---|---|
| `.gitignore` | MODIFIED | добавлено исключение `!.env.example` после `.env.*` — шаблон env-контракта должен быть в индексе, а `.env` / `.env.local` остаются игнорируемыми |
| `.env.example` | MODIFIED + ADDED | впервые застейджен; заодно исправлено содержимое — в нём требовались «output count» и «bounded spend/credit cap», что противоречит `AGENTS.md:196-197`; исправлен устаревший путь `py/ingest/mixkit.py`; `ARCHIVE_API_KEY` помечен как инертный |
| `pytest.ini` | CREATED | `testpaths = tests` + `norecursedirs` — дефолтный вызов pytest стал детерминированным |
| `test_kie.py`, `test_kie_price.py`, `test_kie_wan.py` | DELETED | одноразовые корневые отладочные скрипты; источник коллизии базовых имён с `scripts/test_kie.py`. Закрывает P2-5 |

### 4.3. Реализация P1-3, P1-6 и P0-3 (2026-10-28)

Три «тихих» дефекта закрыты. Общий модуль `capcut/lib/media.py` введён как
носитель двух конвенций, которые раньше расходились между модулями.

| Путь | Действие | Описание |
|---|---|---|
| `capcut/lib/media.py` | CREATED | `metadata_path_for()` — единая конвенция пути метаданных; `atomic_download()` — закачка через temp-sibling + `os.replace` + сверка с `Content-Length`; `DownloadError` |
| `scripts/generate_ai_clips.py` | MODIFIED | **P1-3:** путь метаданных берётся из `metadata_path_for()` → `<name>.mp4.metadata.json` вместо `<name>.meta.json`. AI-клипы снова индексируются с `source=ai`, каноническим id и тегами |
| `capcut/index/embedder.py` | MODIFIED | читает метаданные по общей конвенции |
| `capcut/ingest/{youtube,archive,coverr,mixkit}.py` | MODIFIED | пишут метаданные по общей конвенции; три загрузчика (кроме youtube — там yt-dlp) переведены на `atomic_download()`; циклы ingest'а удаляют файл, если probe провалился. **P1-6** |
| `capcut/render/kie_client.py` | MODIFIED | **P1-6:** `_download()` больше не пишет прямо в целевой путь и не переиспользует частичный остаток как «успешную» закачку |
| `capcut/search/matcher.py` | MODIFIED | **P0-3:** `SceneMatch.sha256`; хэш библиотечного файла переносится из строки индекса в сцену и в `matched.json` |
| `capcut/assemble/concat_exporter.py` | MODIFIED | **P0-3:** `ClipIntegrityError` + сверка фактического sha256 с записанным при сборке таймлайна |
| `scripts/assemble_episode.py` | MODIFIED | **P0-3:** `ClipIntegrityError` → внятное сообщение в stderr и exit 1 вместо трейсбека |
| `tests/test_media.py` | CREATED | конвенция метаданных + 6 тестов на атомарную закачку |
| `tests/test_matcher_assembler.py` | MODIFIED | +2 класса: распространение sha256 и «громкая» поломка при изменении файла |
| `tests/test_embedder.py` | MODIFIED | end-to-end: AI-клип по общей конвенции получает `source=ai` и находится через `source_filter="ai"`; негативный контроль (без метаданных → `source=NULL`) |

### 4.4. Реализация P1-4 и P2-1 (2026-10-28)

| Путь | Действие | Описание |
|---|---|---|
| `capcut/lib/atomic.py` | CREATED | `atomic_write_text()` / `atomic_write_json()` — temp-sibling + `os.replace`; сериализация до касания файла |
| `capcut/episode/spec_writer.py` | MODIFIED | `spec.json` пишется атомарно (оба пути: dry-run и основной) |
| `capcut/search/matcher.py` | MODIFIED | `matched.json` пишется атомарно |
| `capcut/assemble/concat_exporter.py` | MODIFIED | `draft.json` пишется атомарно |
| `capcut/lib/lifecycle.py` | MODIFIED | `spec.sha256` пишется атомарно |
| `capcut/ingest/{youtube,archive,coverr,mixkit}.py` | MODIFIED | файлы метаданных пишутся атомарно |
| `scripts/render_final.py` | MODIFIED | **фикс залипания:** `spec.sha256` записывается **до** рендера, а не после |
| `serials/**/rendered/**` (25 файлов) | UNTRACKED | `git rm --cached -r`; файлы остались на диске, в индексе — 0; `brief.md` / `spec.json` / `episode-log.md` остались отслеживаться |
| `tests/test_atomic.py` | CREATED | 8 тестов на атомарную запись |
| `tests/test_final_renderer.py` | MODIFIED | +1 CLI-тест: провалившийся рендер не оставляет эпизод в непроходимом состоянии |

### 4.5. Реализация мелочи (2026-10-28) — 31 из 34 пунктов

Вторая волна правок: всё, что дешевле контрактного изменения.

| Область | Что сделано |
|---|---|
| Индекс | Fallback-id из **имени файла** → путь относительно корня библиотеки (коллизия basename больше не теряет asset); `INSERT OR REPLACE` → `INSERT ... ON CONFLICT DO UPDATE`; `index_clip()` сам коммитит транзакцию |
| Lifecycle | `mark_matched()` больше не снимает `.approved` (латентная мина: подключи её — и рендер навсегда откажется); удалён мёртвый `Episode.from_path`; `KNOWN_MODELS` (сам помечен «OUT OF DATE») удалён |
| Env-контракт | `kie_client`/`minimax_client` берут base URL из конфига (в дереве было **три** разных MiniMax-хоста, а config-значение игнорировалось); добавлен `GEMINI_NATIVE_BASE_URL`; ключ Gemini уходит в заголовке, а не в query-строке; `KIE_DOWNLOAD_DIR` подключён (был мёртвым, клиент хардкодил CWD-относительный путь); мёртвые `CONCAT_MCP_URL` / `DEFAULT_VIDEO_MODEL` / `GEMINI_BASE_URL` / `is_test_env()` убраны; добавлены `has_pixabay()` / `has_pexels()` |
| Секреты | `setup_keys.sh`: значение уходит в python по **stdin**, а не по argv; ключ читается с `/dev/tty` с откатом на stdin; замена ключа схлопывает все вхождения (дубликат делал эффективное значение зависимым от парсера) |
| Воспроизводимость | `package-lock.json` отслеживается (96 пакетов, все с `resolved`, SDK зафиксирован на 1.32.1, `npm ci --dry-run` проходит) |
| Атомарность | `capcut/lib/atomic.py` — 10 мест записи state-файлов; `spec.sha256` пишется **до** рендера (иначе эпизод залипал навсегда) |
| Метаданные | Одна конвенция пути вместо шести; AI-клипы снова индексируются с `source=ai` и находятся матчером |
| Код | `render_draft.py` переписан (экранирование кавычек, атомарный вывод, ошибки вместо трейсбеков); `minimax_client` переведён с `mktemp` на атомарную закачку и берёт модель из `req.model_id`; `spec_writer` даёт внятные ошибки и предупреждает об обрезании брифа; «spec hash» переименован в `scenes_sha256`; concat-лист стал уникальным; `_resolve_path` проверяет containment; `embed_text` получил параметр `model` |
| Дубли | Пять копий `probe_metadata` → одна `capcut.lib.media.probe_media()` |
| Тесты | `tests/test_config.py` изолирован (порядок запуска больше не влияет на результат); добавлен `tests/test_provider_router.py` (15 тестов) |
| Процесс | Добавлен `.github/workflows/ci.yml` (pytest + node-тест); заглушка `npm test` (`echo … && exit 1`) заменена на `node --test`; `hybrid-media-workflow` и `pi-project-agent` переведены на схему `spec-driven` v1.7.0 — `openspec validate --all` → **3 passed, 0 failed** (было 0/3) |
| Репозиторий | 25 сгенерированных артефактов `serials/**/rendered/**` убраны из индекса, четыре из них протекали абсолютные пути |

**Баг, пойманный в собственном CI-файле сразу после добавления:**
первая версия job'а запускала `node --test test/`. На Node 24 такой аргумент
резолвится как **путь к модулю**, а не как каталог для сканирования, и
тесты падали с `MODULE_NOT_FOUND` (pass 0, fail 1). Заменено на `npm test`,
который вызывает `node --test` без пути — Node сам находит файлы. Проверено
локально: `npm test` → 4/4 pass, exit 0.

**Третий баг пойман не локально, а CI — и он был в чужом коде.** Первый
прогон GitHub Actions упал на `test_recorded_sha_is_the_pre_render_one` с
`/bin/sh: 3: Bad substitution`. Фейковый `ffmpeg` в шиме использовал башизм
`"${@: -1}"` под shebang `#!/bin/sh`: на macOS `/bin/sh` — это bash и всё
работает, на Linux это dash, где такая подстановка не поддерживается и шим
ничего не пишет. Заменено на POSIX-эквивалент `for last_arg; do :; done`
и проверено напрямую под `/bin/dash` (старый вариант — exit 2 с
`Bad substitution`, новый — exit 0 с корректной записью). Это ровно тот
класс дефектов, ради которого CI и нужен: тест, зелёный на машине
разработчика, падал в CI.

**Две находки аудита оказались ложными и исправлены:**
- «`pytest` не объявлен зависимостью» — `pytest>=8.0` был в `capcut/requirements.txt` с коммита `1ae31d8`.
- «правило `.gitignore` для concat-листа содержит литеральный `<name>`» — там уже был глоб `capcut_final_*_concat.txt`; ошибка чтения.

### 4.6. Ревью Kilo Code Review на PR #4 (2026-10-28)

**Trigger:** Kilo Code Review на PR #4 — **30 замечаний** (12 WARNING +
18 SUGGESTION) по диффу из 79 файлов.

По правилу `audit/024` (`summary/audit/024_code_review_fixes.md`: «каждое
WARNING проверялось против реального кода перед тем, как что-то делать»)
каждое замечание сверено с кодом, а не принято на веру. **29 из 30
исправлены, 1 принято с обоснованием.**

Важное наблюдение: **подавляющее большинство замечаний — в коде, написанном
в этом же PR в тот же день.** Бот нашёл ~10 настоящих дефектов, четыре из
которых — «тихие» (ломают данные или деньги без ошибки): ложный
«incomplete download» на любом gzip-ответе, падение `probe_media` на
`duration:"N/A"`, молчаливое усечение векторов при несовпадении моделей
эмбеддинга и повторная платная генерация клипа из-за смены конвенции имени
метаданных. Это ровно тот класс, который `audit/024` называл «самым плохим
режимом отказа», и он был бы не замечен без CI и без ревью.

**Подтверждено воспроизведением (не на слово):**

| Замечание | Проверка | Итог |
|---|---|---|
| `config.__all__` экспортирует удалённый `is_test_env` | `from capcut.lib.config import *` → `AttributeError` | ✅ настоящий |
| `metadata_path_for` не идемпотентен | 2x → `a.mp4.metadata.json.metadata.json` | ✅ настоящий |
| `minimax.poll()` не ходит в API | 0 HTTP-вызовов, всегда «timeout» | ✅ настоящий |
| gzip + `Content-Length` → ложный «incomplete» | `got 5000 bytes, expected 41` | ✅ настоящий, **ломает каждую загрузку с CDN** |
| `probe_media` на `duration:"N/A"` | `ValueError` и в strict, и в non-strict | ✅ настоящий, регрессия к `probe_duration` |
| `search_by_text` усекает векторы | 768-мерный запрос к 384-мерному индексу → **score 1.0** | ✅ настоящий |
| legacy `.meta.json` → платная перегенерация | skip-проверка требует нового имени | ✅ настоящий, **тратит деньги** |
| `except requests.RequestException` не ловит `DownloadError` | `DownloadError` ⊄ `RequestException` | ✅ настоящий |
| уникальный concat-лист не чистится | имя с pid+uuid → файл накапливается | ✅ настоящий |

**Исправлено (29):** fsync файла и каталога перед/после rename в
`capcut/lib/atomic.py` и `capcut/lib/media.py`; `except BaseException` вместо
`except Exception` (Ctrl-C не оставляет `.part`/`.tmp` сиблингов); сверка
`Content-Length` пропускается при `Content-Encoding` (иначе requests отдаёт
распакованные байты против сжатой длины); `probe_media` больше не падает на
`"N/A"`/`None`; `metadata_path_for` идемпотентен; убран дубль
`KIE_BASE_URL` и мёртвый `is_test_env` из `__all__`; `search_by_text` бросает
`EmbeddingDimensionMismatch` вместо молчаливого усечения, а матчер ловит его
по сцене и пишет в warning; `index_library` вычищает осиротевшие
`unknown:%`-строки (путь-производные id умирают вместе с файлом);
`_verify_clip_integrity` пишет warning при пустом хэше и превращает TOCTOU в
`ClipIntegrityError`; concat-лист удаляется в `finally`; `minimax.poll()`
делает ровно один запрос, `DownloadError` ловится, `job_id` санитизируется
перед тем, как стать компонентом пути, `base_url` очищается от слэша, а
модель берётся из запроса, а не из дефолта «video-01»; ingest-циклы удаляют
файл только при сбое **загрузки** (раньше удалялся полностью скачанный файл,
если падал probe — при отсутствующем ffprobe не ingest'илось бы ничего);
идентификаторы провайдера (`coverr`, `archive`) валидируются как
безопасный компонент пути; `youtube.py` получил тот же cleanup, что и
остальные три источника; `generate_ai_clips.py` мигрирует legacy-файл
метаданных перед skip-проверкой; `brief_sha256` хэширует фактически
отправленный префикс брифа, а не весь файл; комментарий про кэш в
`kie_client` переформулирован (файлы от до-атомарной реализации не
перепроверяются); `render_draft.py` фильтрует клипы без `src` и
документирует, что рендерится только первая дорожка; `assemble_episode.py`
ловит и `OSError`.

**Принято без изменений (1):** `embedder.py:297` — расхождение
`relative_to` (лексическое) и `.resolve()` в `_build_clip_id`.
`index_library()` обходит только файлы под `library_root`, поэтому пути
совпадают; `except ValueError` — это хендлер для файла вне корня, а не
мёртвая ветка. Приведение к одному вычислению — косметика, не дефект.

**Новые тесты (20):** идемпотентность `metadata_path_for`;
`safe_filename_component` против traversal; gzip-ответ принимается, реально
обрезанный — отвергается; `probe_media` на `"N/A"` и без duration;
`EmbeddingDimensionMismatch`; `__all__` без пропусков и дублей, `import *`
работает; девять тестов клиента MiniMax (poll действительно ходит в API,
`DownloadError` ловится, `job_id` санитизируется, модель из запроса).

**Итог:** `python3 -m pytest -q` → **227 passed** (было 207).


## 5. Verification

| Шаг | Результат |
|---|---|
| `python3 -m pytest tests/ -q` | ✅ 161 passed |
| `python3 -m pytest -q` (из корня) | ❌ `Interrupted: 1 error during collection` — коллизия `test_kie` (P0-5) |
| `git ls-files --error-unmatch .env.example` | ❌ `did not match any file(s) known to git` — файл никогда не коммитился (P0-4) |
| `git grep -n 'claim_approval' -- '*.py'` | ❌ только `model_approval.py:117` (определение) и `tests/test_model_approval.py:48,52,60,68,76,89` (вызовы) — production-callers нет (P0-1) |
| `git grep -n 'revise(' -- '*.py'` | ❌ только `lifecycle.py:13,147` и `tests/test_lifecycle.py:58` — production-callers нет (P0-2) |
| `grep -n 'rateNum' scripts/convert_draft.py` | ✅ `rate_num`/`rate_den` на обоих уровнях `video` (правка предыдущей сессии) |
| `sed -n '458,467p' capcut/render/kie_client.py` | ✅ подтверждено: запись в финальный путь + возврат любого непустого остатка (P1-6) |
| `sed -n '367,371p' capcut/assemble/final_renderer.py` | ✅ подтверждено: `os.replace` без `exists()`-guard (нарушение иммутабельности на уровне библиотеки) |
| `grep -n 'INSERT OR REPLACE' capcut/index/embedder.py` | ✅ `embedder.py:339` — деструктивная запись (P1-5) |
| `grep -n 'meta.json\|metadata.json' scripts/generate_ai_clips.py capcut/index/embedder.py` | ✅ подтверждено расхождение имён (P1-3) |
| `sed -n '25,29p' scripts/setup_keys.sh` + `:29` | ✅ секрет подставляется в исходник `python3 -c` (P2-3) |
| `grep -n 'importlib.reload' tests/test_config.py` | ✅ `test_config.py:25,49,67,75` — глобальное состояние (P1-1) |
| `grep -n 'ffmpeg' tests/test_final_renderer.py` + поиск `skipUnless` | ✅ вызов `ffmpeg` есть (`:27`), `skipUnless`/`skipIf` — ни одного: на машине без ffmpeg набор упадёт, а не пропустится |
| `git log --oneline -12` / `git branch -vv` | ✅ `main` = `7aa9394`, синхронизирован с `origin/main`; рабочее дерево чистое на момент аудита |
| `git ls-files \| grep -E 'rendered/\|\.jpg$' | ⚠ 27 совпадений — сгенерированные артефакты в индексе (P2-1) |
| `git grep -nE 'api_key\|secret\|token\|password' -- .` | ✅ совпадений с литеральными секретами нет; полный скан истории по всем refs — ноль |
| `find /Applications/Concat.app -name '*.md' -o -name '*.schema*'` | ✅ схем и документации в бандле нет (v0.2.3, нативный бинарь) — формат Concat известен только по 7 локальным примерам `concat.json` |
| `openspec validate approval-enforcement-and-spec-binding` | ✅ `Change 'approval-enforcement-and-spec-binding' is valid` — единственный проходящий change в репозитории |
| `openspec validate --all` | ❌ `0 passed, 3 failed` — падают и два pre-existing change'а: `hybrid-media-workflow`, `pi-project-agent` (старый формат спек) |
| `openspec show approval-enforcement-and-spec-binding --json --deltas-only` | ✅ `deltaCount: 10` — 10 требований в 2 capabilities, у каждого SHALL-текст и ≥1 сценарий |
| `python3 -m pytest -q` (из корня, после P0-5) | ✅ **161 passed** — до правки был `Interrupted: 1 error during collection`, 0 тестов |
| `python3 -m pytest tests/ -q` (после P0-5) | ✅ 161 passed — без регрессий |
| `python3 -m pytest . -q` (после P0-5) | ✅ 161 passed — при явном аргументе `testpaths` игнорируется; коллизии нет, потому что дубли удалены |
| `python3 -m pytest --collect-only -q` | ✅ `161 tests collected`, без ошибок сбора |
| `python3 -m unittest tests.test_convert_draft -v` | ✅ 3/3 passed |
| `node --test mcp-server/test/concat_paths.test.js` | ✅ 4/4 pass |
| `git ls-files --error-unmatch .env.example` (после P0-4) | ✅ отслеживается |
| `git check-ignore -v --no-index .env` / `.env.local` | ✅ оба остались игнорируемыми (`.gitignore:2` / `:3`) |
| `git diff --cached .env.example \| grep -E '^\+[A-Z_]+=.+'` | ✅ только URL-ы и пути; значений секретов нет (все ключи пустые) |
| `python3 -m pytest -q` (после P1-3/P1-6/P0-3) | ✅ **179 passed** — было 161, добавлено 18 тестов |
| `python3 -m pytest tests/ -q` (после P1-3/P1-6/P0-3) | ✅ 179 passed — без регрессий |
| `python3 -m pytest tests/test_media.py tests/test_matcher_assembler.py -q` | ✅ 29 passed — новые и расширенные тесты |
| `python3 -m pytest tests/test_embedder.py -q` | ✅ 16 passed — включая end-to-end конвенции метаданных |
| `python3 -m py_compile` по 13 изменённым/новым Python-файлам | ✅ все компилируются |
| `grep -r 'suffix + ".metadata.json"' capcut/ scripts/` | ✅ ноль — конвенция больше не захардкожена нигде |
| `python3 -m pytest -q` (после P1-4/P2-1) | ✅ **188 passed** — было 179, добавлено 9 |
| `python3 -m pytest -q` (после ревью Kilo) | ✅ **227 passed** — было 207, добавлено 20 тестов на исправленные дефекты |
| репро замечаний Kilo до фикса | ✅ воспроизведены 9 из 9 проверенных: `import *` → AttributeError; двойной суффикс метаданных; `poll()` → 0 HTTP-вызовов; gzip → «got 5000 bytes, expected 41»; `duration:"N/A"` → ValueError; векторы 768→384 → score 1.0; legacy `.meta.json` → платная перегенерация; `DownloadError` ⊄ `RequestException`; накопление concat-листов |
| репро замечаний Kilo после фикса | ✅ все девять дают ожидаемый результат; полный набор закрытых пунктов — в §4.6 |
| `openspec validate --all` (после P2-21) | ✅ **3 passed, 0 failed** — оба pre-existing change'а переведены на схему v1.7.0 |
| `python3 -m pytest -q` (после волны «мелочи») | ✅ **207 passed** — было 179, добавлено 28 (15 роутер + 13 прочие) |
| `python3 -m pytest tests/test_config.py tests/test_embedder.py tests/test_matcher_assembler.py -q` (три порядка) | ✅ 41 passed в каждом из трёх порядков — тесты больше не зависят от порядка запуска |
| `git ls-files 'serials/**/rendered/*'` (после P2-1) | ✅ 0; `git ls-files 'serials/*'` → остались `brief.md`, `spec.json`, `episode-log.md` |
| `git ls-files 'serials/*' \| xargs grep -l '/Volumes/MacStudioData\|/Users/vladteresena'` | ✅ ни одного совпадения — утечка локальных путей закрыта |
| проверка env-контракта сканом по всем `os.environ.get` | ✅ «читается, но не задокументировано» — пусто |
| `bash -n scripts/setup_keys.sh` + функциональный тест в песочнице | ✅ ключ записан, дубликат схлопнут, повторный запуск заменяет по месту; реальный `.env` на машине не тронут |
| `npm ci --dry-run --offline` в `mcp-server/` | ✅ up to date, exit 0 |
| `python3 -m pytest tests/ -q` (после P1-4/P2-1) | ✅ 188 passed — без регрессий |
| `python3 -m pytest tests/test_atomic.py -q` | ✅ 8 passed — запись, перезапись, отсутствие temp-файлов, сохранение прежнего файла при ошибке сериализации |
| `python3 -m pytest tests/test_final_renderer.py -q` | ✅ 33 passed — включая «провалившийся рендер не залипает» |
| `git ls-files 'serials/**/rendered/*'` (после P2-1) | ✅ 0 — ни одного отслеживаемого артефакта; состояния «tracked but ignored» нет |
| `git ls-files 'serials/*'` (после P2-1) | ✅ остались `brief.md`, `spec.json`, `episode-log.md` — реальные данные на месте |
| проверка на диске после `git rm --cached` | ✅ файлы остались на месте — ничего не удалено с диска |

## 6. Связанные

- `summary/tasks/025_audit_followups_enforcement_and_invariants.md` — реестр долга
- `summary/tasks/016_stabilization_and_spend_safety.md` — P0-1, P1-1, P1-2
  уже заведены там; `:56` закрывается этим OpenSpec-change
- `openspec/changes/approval-enforcement-and-spec-binding/` — контракт для
  P0-1 и P0-2
- `openspec/changes/hybrid-media-workflow/` — уже содержит acceptance criteria
  по P0-1 и требование content hash по P0-3; остаётся in-flight
- `openspec/changes/archive/2026-10-19-final-render-writer/` — образец
  реализованного enforcement-контракта
- `summary/audit/016_provider_generation_inventory.md` — инвентаризация
  generation-путей, на которую опирается P0-1
- `summary/audit/023_final_render_writer.md` — реализация текущего
  approval-гейта и его ограничений

## 7. Известные ограничения аудита

- **Аудит статический.** Поведение при реальном сборе сети, реальном
  обрыве закачки и реальном гонке рендеров не воспроизводилось — выводы
  основаны на чтении кода и точечных проверках.
- **CI не выполнялся** — CI в проекте нет. Все 161 тест прогонялись локально
  на macOS с Python 3.13.3, ffmpeg из `/opt/homebrew/bin`.
- **`library/` на этой машине отсутствует** (симлинк на внешний HDD
  `/Volumes/MacStudioData/…` не подключён). Проверка наличия
  библиотечных файлов и полный прогон индексатора не выполнялись; выводы
  по библиотеке сделаны по коду и по данным, сохранённым в
  `serials/**/rendered/`.
- **Формат Concat подтверждён эмпирически**, а не по спецификации: в бандле
  `Concat.app` нет ни схемы, ни документации. Поля `fadeIn`/`fadeOut`/
  `animationIn`/`animationOut`/`transitionIn` существуют (строки в бинаре),
  но **ненулевого `fadeIn` и заполненного `transitionIn` ни в одном из 7
  локальных примеров нет** — формат переходов на 2026-10-28 не установлен.
- **`capcut/lib/lifecycle.py:154` `mark_matched()`** (снимает `.approved` и
  имеет 0 callers) не включён в OpenSpec-change намеренно, чтобы не
  раздувать ревью; вынесен в `summary/tasks/025_…` как P1-7.
- **`summary/tasks/016:43`** утверждает о «двух падениях config-тестов»,
  тогда как сейчас `pytest tests/` даёт 161 passed. Пункт либо устарел, либо
  описывает другой вызов; его следует перепроверить и закрыть (P2-20).

## 8. Следующие шаги

Осталось **три** пункта из 34. Все три — контрактные, и на два из них уже
есть готовый OpenSpec-change.

- [ ] **PR #4: дождаться повторного ревью Kilo** после фиксов §4.6 и
      смержить. Первое ревью нашло 30 замечаний, 29 исправлены; второе
      прогонится на новом коммите.
- [ ] **P0-1 + P0-2** — реализовать
      `openspec/changes/approval-enforcement-and-spec-binding/`
      (валиден по `openspec validate`). Это единственные пункты, где
      риск реально стоит денег: платный вызов без одобрения и рендер
      неревьюенного spec.
- [ ] **P2-11** — развести два несовместимых формата «draft»
      (`scripts/convert_draft.py` пишет `mediaId` без `src`, а
      `final_renderer._video_clips()` требует `clip["src"]`).
      Это изменение формата данных, поэтому по `AGENTS.md` требует
      OpenSpec-change, а не точечной правки.
- [ ] Завести `CHANGELOG.md`-запись и коммит на feature-ветке (по
      branch workflow `AGENTS.md`); на момент аудита не сделано — правки
      проиндексированы, но не закоммичены.

### Закрыто 2026-10-28

- [x] P0-3, P0-4, P0-5 — §4.3, §4.4
- [x] P1-1…P1-7 — §4.3, §4.4, §4.5
- [x] P2-1…P2-10, P2-12…P2-22 — §4.4, §4.5
