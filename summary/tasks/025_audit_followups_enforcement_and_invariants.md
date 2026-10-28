# TODO: Аудит-фоллоуапы — enforcement, инварианты и гигиена репозитория

**Статус:** 🟡 В работе; инвентаризация завершена, реализация начата
**Дата:** 2026-10-28
**Основание:** `summary/audit/026_project_audit_enforcement_and_invariants.md`

**Реализовано на 2026-10-28:** P0-3, P0-4, P0-5, P1-1…P1-7, P2-1…P2-10,
P2-12…P2-22 (см. ниже). Осталось: **P0-1, P0-2, P2-11**.

> **Нумерация.** Парный номер 025 в серии `summary/audit/` уже занят
> (`025_draw-things-removed_comfyui_provider.md`), поэтому аудит этой
> фиксации — `026`, а задачи — `025`. Пара намеренно асимметрична;
> `summary/audit/026_…` фиксирует это.

## Цель

Закрыть долг, найденный сквозным read-only аудитом проекта: инварианты,
объявленные в `AGENTS.md`, но не обеспеченные кодом; дефекты, которые
**молча** портят данные вместо того, чтобы падать; и гигиена репозитория,
которая делает всё это невидимым.

Этот TODO **не разрешает** платные генерации, изменение provider defaults,
ререндер `final.mp4`, удаление файлов библиотеки или коммит чужих правок.

## Что уже было известно, а что ново

Главный риск — **не скрытый дефект, а оформленный долг**. Пункт P0-1 ниже
уже заведён в `summary/tasks/016_stabilization_and_spend_safety.md:23-25`
и в acceptance criteria `openspec/changes/hybrid-media-workflow/`. Остальное
найдено этим аудитом впервые.

| Находка | Уже заведена? | Где |
|---|---|---|
| P0-1 approval не enforced | ✅ да | `summary/tasks/016:23-25` |
| P1-1 config-тесты нестабильны | ✅ да | `summary/tasks/016:43` |
| P1-2 pytest не объявлен зависимостью | ✅ да | `summary/tasks/016:44` |
| P0-2 привязка `.approved` к spec | ❌ нет | этот документ |
| P0-3 sha256 клипа не доходит до эпизода | ❌ нет | этот документ |
| P0-4 `.env.example` не в git | ❌ нет | этот документ |
| P0-5 `pytest` из корня = 0 тестов | ❌ нет | этот документ |
| P1-3 AI-клипы не индексируются | ❌ нет | этот документ |
| P1-4 неатомарные записи state-файлов | ❌ нет | этот документ |
| P1-5 `INSERT OR REPLACE` теряет строку | ❌ нет | этот документ |
| P1-6 скачивания неатомарны | ❌ нет | этот документ |

---

## P0 — Инварианты, которые должны быть настоящими

- [ ] **P0-1. Approval-артефакт модели потребляется на всех generation
      entrypoints; silent fallback запрещён.**
      Перекрыто OpenSpec-изменением
      `openspec/changes/approval-enforcement-and-spec-binding/`
      (спека `model-approval-enforcement`). В нём же — решение по
      `DAILY_AI_BUDGET_USD` и `DEFAULT_VIDEO_FALLBACK`.
      Исходная запись долга: `summary/tasks/016:23-25`.
- [ ] **P0-2. Approval эпизода связан с содержимым `spec.json`, которое
      ревьюировали.** `capcut/lib/lifecycle.py:147` `revise()` мёртв
      (0 production-callers), `capcut/episode/spec_writer.py:551`
      перезаписывает `spec.json` и не снимает `.approved`,
      `scripts/render_final.py:111` проверяет только наличие сентинела.
      → Спека `episode-approval-binding` в том же OpenSpec-изменении.
- [x] **P0-3. sha256 библиотечного клипа доходит до эпизода.** ✅ 2026-10-28
      Было: `capcut/search/matcher.py:48` `class SceneMatch` не имел поля
      `sha256` (embedder его читал и выбрасывал),
      `capcut/assemble/concat_exporter.py:119` проверял только `exists()`.
      Подмена файла в библиотеке **тихо** меняла `final.mp4` вместо
      «громкой» поломки.
      Сделано: `SceneMatch` получил поле `sha256`; матчер переносит хэш из
      строки индекса в сцену, `matched.json` его сохраняет; экспортер
      сверяет фактический sha256 файла с записанным и бросает
      `ClipIntegrityError` при расхождении — то есть ссылка ломается
      **громко**. `scripts/assemble_episode.py` ловит это и выходит с
      кодом 1 и внятным сообщением вместо трейсбека.
      Обратная совместимость: `matched.json`, написанный до появления хэша,
      не содержит `sha256` → проверка пропускается (нечего сверять),
      реестр не ломается.
      Требование content hash уже было сформулировано в
      `openspec/changes/hybrid-media-workflow/specs/media-assets/spec.md`
      («SHALL include a content hash») — это conformance-фикс, не новый
      контракт.
- [x] **P0-4. `.env.example` попадает в git.** ✅ 2026-10-28
      Было: `.gitignore:3` (`.env.*`) матчил и `.env.example`; файл
      **никогда не был закоммичен** (`git log --all -- .env.example` пуст).
      Ломались на чистом клоне `AGENTS.md:21`, `scripts/setup_keys.sh:16`,
      `.github/copilot-instructions.md:35`.
      Сделано: в `.gitignore` добавлено исключение `!.env.example` (с
      пояснением, почему шаблон должен быть в индексе), файл
      застейджен. Заодно исправлено содержимое — впервые опубликованный
      контракт env не должен противоречить `AGENTS.md:196-197`: убраны
      требования «output count» / «bounded spend/credit cap» в блоках
      KIE, MiniMax, runtime-defaults и `DEFAULT_VIDEO_FALLBACK`; исправлен
      устаревший путь `py/ingest/mixkit.py` → `capcut/ingest/mixkit.py`;
      `ARCHIVE_API_KEY` помечен как инертный (`capcut/ingest/archive.py`
      не читает ни одного env). Проверено: `.env` и `.env.local` остались
      в ignore, в застейдженном шаблоне нет значений секретов.
- [x] **P0-5. Тестовая команда по умолчанию работает.** ✅ 2026-10-28
      Было: `python3 -m pytest` из корня → `Interrupted: 1 error during
      collection` (коллизия базовых имён `test_kie.py` в корне и в
      `scripts/`), **0 тестов**; `python3 -m pytest tests/` → 161 passed.
      Нет `pytest.ini`/`testpaths`, нет CI → невидимо.
      Сделано (две причины закрыты, а не одна):
      (1) удалены корневые одноразовые скрипты `test_kie.py`,
      `test_kie_price.py`, `test_kie_wan.py` — это устраняет саму коллизию
      имён, а не маскирует её; они же закрывают P2-5;
      (2) добавлен `pytest.ini` с `testpaths = tests` и
      `norecursedirs` — дефолтный вызов теперь детерминирован, и будущий
      посторонний `test_*.py` в корне его не сломает.
      Проверено: `pytest` → 161 passed; `pytest tests/` → 161 passed;
      `pytest .` → 161 passed (при явном аргументе `testpaths`
      игнорируется — коллизии нет, потому что дубли удалены);
      `--collect-only` → 161 tests collected, без ошибок.

## P1 — Дефекты, которые молча портят данные

- [x] **P1-1. Config-тесты не зависят от локального `.env` и порядка ✅ 2026-10-28 — причина найдена и устранена: `tests/test_config.py` перезагружал `capcut.lib.config` внутри `patch.dict(os.environ, ..., clear=True)`, а константы модуля вычисляются при импорте, поэтому после выхода из патча модуль навсегда сохранял тестовые значения и заражал последующие тесты. Теперь перезагрузка выполняется ещё раз в `finally`; добавлен тест `test_patched_reload_does_not_leak_into_the_module`. Порядок запуска больше не влияет на результат.
      импорта.** `tests/test_config.py:25,49,67,75` — `importlib.reload(config)`
      внутри `patch.dict(..., clear=True)`: после выхода из контекста
      перезагруженный модуль навсегда сохраняет подставленные пути.
      Перекрыто `summary/tasks/016:43`.
- [x] **P1-2. `pytest` объявлен зависимостью** (или убрана зависимость от ✅ 2026-10-28 — находка оказалась **ложной**: `pytest>=8.0` уже объявлен в `capcut/requirements.txt` (секция `# Tests`) с момента коммита `1ae31d8`. Соответствующий пункт `summary/tasks/016:44` обновлён; отдельного `requirements-dev.txt` не требуется.
      него в тестах). Перекрыто `summary/tasks/016:44`.
- [x] **P1-3. Метаданные AI-клипов находятся индексатором.** ✅ 2026-10-28
      Было: `scripts/generate_ai_clips.py:56` писал `X.meta.json`,
      `capcut/index/embedder.py:205` читал `X.mp4.metadata.json` →
      `metadata={}`, `source=NULL`, id `unknown:<file>`, теги/лицензия
      терялись, `source_filter="ai"` в матчере **никогда** не срабатывал —
      вся AI-ветка пайплайна была мертвой.
      Сделано: введён общий модуль `capcut/lib/media.py` с
      `metadata_path_for()`; теперь **все** производители и потребители
      метаданных берут путь из одной функции — `scripts/generate_ai_clips.py`,
      четыре ingest-модуля и `capcut/index/embedder.py`. Класс ошибки
      закрыт структурно, а не одной правкой.
- [x] **P1-4. Запись state-файлов атомарна.** ✅ 2026-10-28
      Было: `capcut/episode/spec_writer.py:518,553`,
      `capcut/search/matcher.py:214`, `capcut/assemble/concat_exporter.py:296`,
      `capcut/lib/lifecycle.py:222`,
      `capcut/ingest/{youtube:302,archive:240,coverr:224,mixkit:300}` —
      обрыв на середине оставлял битый JSON, который следующий читатель
      не мог отличить от испорченных данных.
      Сделано: введён общий модуль `capcut/lib/atomic.py`
      (`atomic_write_text` / `atomic_write_json` — temp-sibling + `os.replace`,
      сериализация **до** касания файла). Переведены на него все 10 мест
      записи: `spec.json` × 2, `matched.json`, `draft.json`,
      `spec.sha256`, метаданные четырёх ingest-модулей.
      Отдельно — залипание эпизода: `scripts/render_final.py` писал
      `final.mp4` **до** `spec.sha256`, и при сбое bookkeeping получался
      эпизод, который больше нельзя отрендерить никогда (immutable
      `final.mp4` без хэша → следующий прогон отказывает). Теперь хэш
      пишется **до** рендера: сбой записи хэша → ничего не отрендерено,
      прогон чисто повторяем; сбой рендера → остаётся устаревший хэш, но
      проверка идемпотентности требует наличия и `final.mp4`, так что
      устаревший хэш просто перезаписывается.
      Наблюдаемая семантика идемпотентности не изменилась: совпадающий
      хэш → no-op, несовпадающий → отказ «immutable, сделайте remix».
- [x] **P1-5. Индекс остаётся аддитивным.** `capcut/index/embedder.py:339` ✅ 2026-10-28 — две причины: (а) fallback-id строился из **имени файла**, из-за чего два asset'а с одинаковым basename делили один id и второй молча затирал первого — теперь это путь относительно корня библиотеки; (б) `INSERT OR REPLACE` заменён на `INSERT ... ON CONFLICT(id) DO UPDATE` — UPDATE вместо DELETE+INSERT. Добавлен тест на коллизию basename.
      `INSERT OR REPLACE` при `id TEXT PRIMARY KEY` → удаление без
      явного GC; при коллизии basename (`unknown:<name>`,
      `embedder.py:258-261`) один из двух asset'ов **молча** теряется.
- [x] **P1-6. Скачивания атомарны и проверяются.** ✅ 2026-10-28
      Было: `capcut/render/kie_client.py:458-467` писал прямо в финальный
      путь и возвращал любой непустой остаток как «успешную» закачку →
      обрезанный mp4 попадал в библиотеку через
      `scripts/generate_ai_clips.py:88`. То же в ingest:
      `capcut/ingest/archive.py:165`, `coverr.py:148`, `mixkit.py:226` —
      оборванный файл оставался под валидным именем, а ingest ещё и
      оставлял его в библиотеке после провала probe'а.
      Сделано: в `capcut/lib/media.py` добавлен `atomic_download()` — тело
      пишется во временного sibling'а и переименовывается на место только
      после завершения; сверяется с `Content-Length`; пустое тело и
      прерванная передача не публикуют файл и не затирают уже хороший.
      Переведены на него `kie_client._download` и все три ingest-загрузчика
      (youtube не трогал — там yt-dlp, у него свои temp-файлы). Циклы
      ingest'а теперь удаляют файл, если probe провалился.
- [x] **P1-7. `mark_matched()` перестаёт снимать `.approved`.** ✅ 2026-10-28 — `mark_matched()` больше не удаляет `.approved`. Сентинел означает «человек одобрил spec» и ортогонален состоянию matched; удаление разоружало бы render-гейт (`render_final.py:111`), и функция с 0 вызывающих была латентной миной. Добавлен регрессионный тест.
      `capcut/lib/lifecycle.py:154` — функция с «безобидным» именем
      разоружает render-гейт. 0 callers. Вынесено из OpenSpec-change, чтобы
      не раздувать ревью.

## P2 — Гигиена репозитория и конфигурации

- [x] **P2-1. Сгенерированные артефакты убраны из индекса.** ✅ 2026-10-28
      Было: 25 файлов `serials/**/rendered/**` в git — 17 JPEG-ов кэша
      Concat (`cache/art/*.jpg` + `poster.jpg`, ~430 KB бинарных), два
      `concat.json`, три `draft.json`, `ffmpeg_list.txt`, два
      `spec.sha256`. Четыре из них протекали абсолютные пути
      `/Volumes/MacStudioData/...` (7, 20, 7, 7 и 6 совпадений) — то
      самое, что `.gitignore:22-24` называет недопустимым к коммиту.
      Правило `serials/**/rendered/` было добавлено в `.gitignore`
      **позже**, чем файлы попали в индекс (коммит `1ae31d8`), а
      gitignore не раз-трекает — индекс противоречил более новой политике.
      Сделано: `git rm --cached -r` по всем `serials/**/rendered/` — в
      индексе осталось 0, файлы остались на диске, состояния
      «tracked but ignored» больше нет. Отслеживаемыми остались реальные
      данные: `brief.md`, `spec.json`, `episode-log.md`.
      **Конфликт с прежним решением, зафиксированным честно:**
      `summary/tasks/024` (2026-10-19) писал: «38 файлов `serials/` —
      это осознанные sample-данные (включая одобренный эпизод и
      `rendered/`-кэш). Оставлены как есть». Это решение было принято
      раньше, чем появилось правило `.gitignore` для `rendered/`, и в
      пользу «оставить» говорило то, что sample-данные полезны. Решающим
      доводом в пользу удаления стало то, что 4 файла из 25 содержали
      абсолютные пути на несуществующий на другой машине HDD — на чужом
      клоне эти sample-данные указывают в никуда. Ценная часть выжила:
      `brief.md` / `spec.json` / `episode-log.md` остались в индексе.
- [x] **P2-2. `.agents/mcp_config.json` без абсолютного пути.** ✅ 2026-10-28 — абсолютный путь заменён на относительный `./mcp-server/index.js`, как в `.mcp.json`.
      `mcp_config.json:6` → `/Users/vladteresena/Projects/capcut-studio/mcp-server/index.js`.
      MCP не стартует на другом клоне; дублирует `.mcp.json`, который
      корректно использует относительный путь.
- [x] **P2-3. `scripts/setup_keys.sh` не светит секрет через `ps`.** ✅ 2026-10-28 — значение уходит в python по **stdin**, по argv идут только путь файла и имя ключа. Заодно: убран мёртвый `esc_val`, чтение действительно идёт с `/dev/tty` (с откатом на stdin), а замена ключа схлопывает **все** его вхождения — раньше дубликат оставался в `.env` и эффективное значение зависело от парсера.
      `setup_keys.sh:29` — секрет подставляется в исходник `python3 -c`,
      т.е. попадает в argv дочернего процесса, вопреки комментарию в
      шапке скрипта. Передавать через stdin/FD.
- [x] **P2-4. `package-lock.json` не в `.gitignore`.** ✅ 2026-10-28 — `package-lock.json` больше не игнорируется, файл застейджен. Проверено: 96 пакетов, у всех есть `resolved`, SDK зафиксирован на 1.32.1, `npm ci --dry-run --offline` проходит.
      `.gitignore:18` → `npm ci` невозможен, SDK плавает на `^1.32.1`.
- [x] **P2-5. Корневые `test_kie.py`, `test_kie_price.py`, `test_kie_wan.py`
      убраны из репозитория.** ✅ 2026-10-28 — сделано вместе с P0-5.
      Это были одноразовые отладочные скрипты на 21–23 строки (запрос
      каталога/цен моделей), а не unit-тесты; каноничный live-harness —
      `scripts/test_kie.py` (129 строк, с docstring и `KIE_SMOKE=0`).
      Проект это уже видел: `summary/tasks/022:64` («Странные root-скрипты
      (3)») и `summary/audit/016:20` («реальные API-запросы, не
      unit-тесты»). Возможность запроса цен не потеряна: она остаётся
      методом `KieClient.get_model_price`; вызывать её вручную можно.
      (Замечание: `summary/audit/016:20` указывает путь
      `scripts/test_kie_price.py` — такого файла не было, он лежал в
      корне; путь в исторической записи ошибочен, переписывать её не
      следует — это история на дату.)
- [x] **P2-6. Env-контракт синхронизирован.** Читается, но не задокументировано: ✅ 2026-10-28 — в шаблон добавлены читаемые, но не описанные `KIE_MODEL` и `KIE_SMOKE`; `CONCAT_MCP_URL`, `DEFAULT_VIDEO_MODEL`, `GEMINI_BASE_URL` удалены как мёртвые; `ARCHIVE_API_KEY` и `CONCAT_MCP_URL` оставлены закомментированными с честной пометкой. Добавлены недостающие `has_pixabay()` / `has_pexels()`. Удалён мёртвый `is_test_env()` / `CAPCUT_STUDIO_TEST`. Скан «читается, но не задокументировано» → пусто.
      `CAPCUT_STUDIO_TEST` (`config.py:171`), `KIE_MODEL`
      (`scripts/test_kie.py:77`), `KIE_SMOKE` (`scripts/test_kie.py:94`).
      Задокументировано, но не читается: `ARCHIVE_API_KEY`
      (`capcut/ingest/archive.py` не читает env вообще).
      Не в `config.py.__all__`: `DEFAULT_VIDEO_FALLBACK` (`:62`),
      `LM_STUDIO_API_TOKEN` (`:108`).
- [x] **P2-7. Env-конфигурируемые base URL реально применяются.** ✅ 2026-10-28 — `kie_client` и `minimax_client` берут base URL из конфига (в дереве было три разных значения MiniMax-хоста, а config-значение игнорировалось); добавлен `GEMINI_NATIVE_BASE_URL` для реально вызываемого эндпоинта, `GEMINI_BASE_URL` удалён; ключ Gemini уходит в заголовке `x-goog-api-key`, а не в query-строке; `KIE_DOWNLOAD_DIR` подключён (был мёртвым, клиент хардкодил CWD-относительный путь).
      `capcut/lib/config.py:84` `KIE_BASE_URL` не импортируется —
      `capcut/render/kie_client.py:52` держит свой констант;
      `capcut/render/minimax_client.py:21` импортирует `MINIMAX_BASE_URL`
      и игнорирует; `capcut/episode/spec_writer.py:347` хардкодит
      `generativelanguage.googleapis.com` и ключ в query string.
- [x] **P2-8. CI-профиль добавлен.** `.github/workflows/` отсутствует; в ✅ 2026-10-28 — добавлен `.github/workflows/ci.yml`: Python-джоб (ubuntu-latest, Python 3.11, ffmpeg, `pip install -r capcut/requirements.txt`, `python3 -m pytest -q`) и Node-джоб (`npm ci` + `node --test test/`). `npm ci` теперь возможен, потому что lockfile отслеживается.
      `.github/` только `copilot-instructions.md`. Никто не запускает
      `pytest` и node-тесты. `mcp-server/package.json:7` — `npm test` =
      заглушка с `exit 1`.
- [x] **P2-9. `render_draft.py` безопасен и покрыт тестом.** ✅ 2026-10-28 — `render_draft.py` переписан: usage и прогресс → stderr; корректные ошибки вместо трейсбеков; экранирование кавычек в concat-листе; вывод через temp-sibling + `os.replace` (раньше `preview.mp4` удалялся **до** кодирования, и неудачный рендер оставлял битый файл вместо валидного).
      `render_draft.py:24` — кавычки не экранированы (в отличие от
      `final_renderer.py:245`); `:29-30` — `unlink()` существующего
      `preview.mp4` до успешного encode; usage печатается в stdout (`:9`);
      нет `duration`-директив. Не документирован в `AGENTS.md`.
- [x] **P2-10. Мёртвый код удалён.** `capcut/lib/lifecycle.py:72-79` ✅ 2026-10-28 — удалены `Episode.from_path` (0 вызывающих, обе ветки идентичны), мёртвый `self._rl_poll` (per-task лимит делает `_last_poll_per_task`) и `KNOWN_MODELS` (сам помечен «OUT OF DATE», использовался только ре-экспортом). `upload_base64/upload_file/upload_url` и `get_model_price` **оставлены** — это живая поверхность API клиента, на них ссылается его собственный текст ошибки. Докстринг lifecycle больше не обещает несуществующий сентинел `.draft`.
      `Episode.from_path` (обе ветки буквально `ep_dir = path`),
      `capcut/lib/lifecycle.py:55` `State.DRAFT: ".draft"` (не пишется и не
      читается, хотя описан в lifecycle `AGENTS.md`),
      `capcut/render/kie_client.py:156` `self._rl_poll`,
      `upload_base64/upload_file/upload_url` (`:237,250,267`),
      `get_model_price` (`:224`), `get_model_success_rate` (`:227`),
      `capcut/render/base.py:117` `KNOWN_MODELS`.
- [ ] **P2-11. Два несовместимых формата «draft» разведены.**
      `scripts/convert_draft.py` пишет `mediaId` без `src`, а
      `capcut/assemble/final_renderer.py:88-99` `_video_clips()` требует
      `clip["src"]` → сконвертированный draft нельзя отрендерить.
- [x] **P2-12. `probe_metadata` вынесен в общий модуль.** Побайтово ✅ 2026-10-28 — пять копий `probe_metadata` (четыре в ingest + `_probe_for_indexing` в индексе) заменены одной реализацией `capcut.lib.media.probe_media()` с флагом строгости; `ProbeResult` в ingest-модулях стал алиасом `MediaProbe` (frozen, как был). `final_renderer.probe_duration` тоже делегирует общей функции.
      продублирован в `capcut/ingest/youtube.py:229`, `archive.py:186`,
      `coverr.py:154`, `mixkit.py:241` и ещё раз в
      `capcut/index/embedder.py:225`; `VideoMeta`/`ProbeResult`/`IngestResult`
      объявлены заново 4 раза. Нужен общий `capcut/lib/media.py` — модуля
      сейчас не существует, это предлагаемое извлечение дубликата.
- [x] **P2-13. `minimax_client.py` либо дописан, либо удалён.** ✅ 2026-10-28 — `tempfile.mktemp` (гонка, deprecated) + `urllib.urlretrieve` без таймаута → `requests` со стримингом и `atomic_download`; добавлен timeout к запросу файла; `resp.json()` под защитой; **модель бралась из хардкода `"video-01"` в обход `req.model_id`** → теперь из запроса; добавлены `poll()` и `list_models()` — клиент удовлетворяет протоколу `VideoProvider`.
      `minimax_client.py:85` — `tempfile.mktemp` (гонка, deprecated), без
      timeout; `:40` хардкодит `"model": "video-01"`, игнорируя
      `req.model_id`; не реализует `VideoProvider` (`capcut/render/base.py:79`);
      ни разу не инстанцируется (`provider_router.py:104` кидает
      `NotImplementedError`).
- [x] **P2-14. Валидация на границах модулей.** `capcut/episode/spec_writer.py:457-460` ✅ 2026-10-28 — `SceneSpec(**s)` теперь даёт `ValueError` с номером сцены и списком ожидаемых полей вместо голого `TypeError`/`KeyError`; молчаливое обрезание брифа на 8000 символов → предупреждение в stderr с фактическим размером; `DEFAULT_MODEL` переопределяем через `SPEC_WRITER_MODEL`, докстринг модуля приведён в соответствие с реальным поведением (локальная модель по умолчанию).
      — `SceneSpec(**s)` даёт `TypeError`/`KeyError` вместо ошибок
      валидации, и `validate_spec` (`:130`) не видит плохой payload;
      `:492` — бриф **молча** обрезается на 8000 символов
      (`MAX_BRIEF_CHARS = 8_000`, `:53`); `:50` `DEFAULT_MODEL` локального
      имени противоречит docstring и `config.py:55`.
- [x] **P2-15. Два несовместимых «spec hash» переименованы.** ✅ 2026-10-28 — `MatchedEpisode.spec_sha256` → `scenes_sha256`: хэш списка сцен несопоставим с `lifecycle.sha256_spec()` (хэш файла), и одинаковые имена провоцировали путаницу. `load_matched` принимает и старый ключ для файлов на диске.
      `capcut/search/matcher.py:201` хэширует строку со списком сцен,
      `capcut/lib/lifecycle.py:192` — файл `spec.json`. Значения
      несопоставимы, названия одинаковые.
- [x] **P2-16. Уникальный concat-лист при параллельном рендере.** ✅ 2026-10-28 — `_concat_list_path` стал уникальным (pid + uuid): два параллельных рендера одного эпизода писали в один список и затирали вход друг друга.
      `capcut/assemble/final_renderer.py:130` — путь детерминирован по
      имени проекта; два параллельных рендера одного эпизода пишут в один
      файл. Уникальность temp-файла покрывает только выходное видео.
- [x] **P2-17. `_resolve_path` проверяет containment.** ✅ 2026-10-28 — `_resolve_path` проверяет, что результат остаётся под корнем библиотеки: `..` больше не выводит наружу.
      `capcut/assemble/concat_exporter.py:118` резолвит `..` без проверки,
      что результат остаётся под `library_root`.
- [x] **P2-18. `provider_router` покрыт прямыми тестами.** ✅ 2026-10-28 — добавлен `tests/test_provider_router.py` (15 тестов): `ProviderSpec.parse` (включая канонические kie-id вида `kling/...`, где первый сегмент — не бэкенд), иерархия `parse_scene_provider`, `resolve_default` и маппинг model_id в запрос. Fallback-семантика роутера **не** зафиксирована тестом: её меняет P0-1.
      Сейчас задевается только транзитно через `tests/test_kie_client.py` —
      а именно иерархия override'ов объявлена в `AGENTS.md` как
      «неподтверждённая».
- [x] **P2-19. `_embed_query` уважает переданную модель.** ✅ 2026-10-28 — `embedder.embed_text` получил параметр `model`, `_embed_query` его передаёт: `match_episode(embed_model=…)` больше не врёт.
      `capcut/search/matcher.py:76-80` игнорирует аргумент `model`.
- [x] **P2-20. Нумерация `summary/audit` / `summary/tasks` сведена.** ✅ 2026-10-28 — устаревший пункт `summary/tasks/016:43` («два падения config-тестов») пересчитан: причина найдена и устранена (P1-1), а связанный пункт про `pytest` оказался ложной находкой — зависимость объявлена с коммита `1ae31d8`. **Пропуски в нумерации (009, 010, 012, 017 в audit; 009, 010 в tasks) оставлены как есть**: перенумеровать историю сломало бы ссылки в `CHANGELOG.md`, аудитах и на GitHub. Пропуски задокументированы здесь, чтобы новые записи продолжали последовательность с 025/026.
      Пропущены 009, 010, 012 (audit) и 009, 010 (tasks); в audit есть 025,
      в tasks — нет. Пункт `summary/tasks/016:43` говорит о «двух падениях
      config-тестов», хотя сейчас `pytest tests/` — 161 passed: пункт
      устарел и должен быть перепроверен и закрыт.
- [x] **P2-21. Pre-existing OpenSpec-изменения приведены к схеме ✅ 2026-10-28 — `hybrid-media-workflow` и `pi-project-agent` переведены на схему `spec-driven` v1.7.0: спеки получили `## ADDED Requirements` + `### Requirement:` + блоки `#### Scenario:` с WHEN/THEN, proposals — секции `## Why` / `## What Changes` / `## Capabilities` / `## Impact`. `openspec validate --all` → **3 passed, 0 failed** (было 0 passed / 3 failed).
      `spec-driven` v1.7.0.** `openspec validate --all` → **0 passed, 3
      failed**: не проходят `openspec/changes/hybrid-media-workflow/` и
      `openspec/changes/pi-project-agent/`. Причина — спеки написаны в
      старом формате (секции `## <требование>` без delta-заголовков
      `## ADDED Requirements` и без блоков `#### Scenario:`); схема v1.7.0
      требует и то, и другое, и минимум один сценарий на требование.
      Ни одна спека в репозитории сейчас не использует delta-формат.
      Новый change `approval-enforcement-and-spec-binding` написан сразу
      в схеме v1.7.0 и проходит валидацию; два старых надо либо
      переписать в том же формате, либо явно пометить как legacy до
      архивации.
- [x] **P2-22. `index_clip()` не коммитит транзакцию.** Обнаружено при ✅ 2026-10-28 — `index_clip()` теперь сам коммитит свою транзакцию: раньше коммит делал только вызывающий (`index_library()`), и новый прямой вызывающий потерял бы строку молча, а индекс выглядел бы просто пустым.
      написании тестов P1-3: `capcut/index/embedder.py` вставляет строку и
      **не** вызывает `conn.commit()` — коммит делает вызывающий код
      (`index_library()` — после каждого добавленного клипа). Сегодня это
      безопасно: единственный продакшн-путь — `index_library()`. Но любой
      новый вызывающий `index_clip()` потеряет данные при закрытии
      коннекции, и ошибка будет молчаливой — индекс просто окажется
      пустее. Либо коммитить внутри `index_clip()`, либо документировать
      контракт явно (и закрепить тестом).

---

## Критерии завершения

- [ ] Каждый инвариант из `AGENTS.md`, помеченный как «enforced», подкреплён
      кодом **и** тестом; формулировки в `AGENTS.md` соответствуют реальности.
- [ ] Ни один дефект, который **молча** портит данные (P0-3, P1-3…P1-6),
      не остаётся открытым: они либо исправлены, либо явно помечены как
      известный долг с владельцем.
- [ ] `python3 -m pytest` из корня репозитория собирает и запускает все
      тесты; в CI это проверяется автоматически.
- [ ] `git ls-files` не содержит сгенерированных артефактов, абсолютных
      путей и секретов; `.env.example` — в индексе.
- [ ] `summary/tasks/016_stabilization_and_spend_safety.md` пересчитан:
      закрытые пункты отмечены, незакрытые — не помечены как выполненные.

## Связанное

- `summary/audit/026_project_audit_enforcement_and_invariants.md` — сам аудит
- `openspec/changes/approval-enforcement-and-spec-binding/` — контракт для
  P0-1 и P0-2
- `openspec/changes/hybrid-media-workflow/` — уже содержит acceptance
  criteria по P0-1 и требование content hash по P0-3; остаётся in-flight
- `summary/tasks/016_stabilization_and_spend_safety.md` — P0-1, P1-1, P1-2
  уже заведены там
