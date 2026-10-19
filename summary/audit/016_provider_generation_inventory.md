# Инвентаризация provider- и generation-путей

**Дата:** 2026-10-12  
**Тип:** Read-only inventory / подготовка к OpenSpec implementation  
**Change:** `openspec/changes/hybrid-media-workflow/`

## Границы проверки

Просмотрены текущие provider-клиенты, CLI и smoke-скрипты, spec writer,
MCP-инструменты, тесты, fallback-код и наличие batch/cron. Проверки не
отправляли запросов к моделям, не читали и не выводили секреты, не запускали
генерацию и не открывали Concat UI.

## Найденные пути

| Путь | Фактическое поведение | Риск / статус |
|---|---|---|
| `scripts/generate_ai_clips.py` → `KieClient.submit()` | По умолчанию выбирает `bytedance/v1-lite-text-to-video`, проходит все сцены с `preferred_source` `ai` или `any` на video-треке и создаёт отсутствующие клипы. | Entry point сам выбирает модель и не проверяет согласование текущей задачи. Ошибка одной сцены не прерывает обработку остальных. Метаданные не сохраняют sha256 исходного результата. |
| `scripts/test_kie.py` → `KieClient` | До генерации запрашивает баланс, каталог и схему модели. По умолчанию доходит до реального `submit`; генерацию пропускает только при `KIE_SMOKE=0`. Может выбрать первую найденную Kling-модель. | Smoke-скрипт по умолчанию способен вызвать генерацию и сам выбирает модель. Даже `KIE_SMOKE=0` выполняет сетевые запросы discovery/balance/schema. |
| `scripts/test_kie_price.py`, `test_kie.py`, `test_kie_wan.py` | Запрашивают каталог/цены моделей при наличии ключа; часть ошибок молча игнорируется. | Не запускались; это реальные API-запросы, не unit-тесты. Цены не подключены к preflight генератора. |
| `py/render/kie_client.py` | `submit()` читает schema и затем вызывает `createTask`; approval-артефакт модели пока не проверяется. | В рабочей копии исправлена телеметрия: `creditsConsumed` теперь попадает в `cost_credits`, а `costTime` — в `latency_sec`; денежная стоимость остаётся неизвестной (`None`). Пользователь может самостоятельно смотреть цены; автоматическая проверка стоимости не является gate. |
| `py/render/provider_router.py` | Использует env default или `kie/veo-3-1`; caller может передать fallback-цепочку. После ошибки/неуспеха последовательно пробует следующие provider entries. Значение `DEFAULT_VIDEO_FALLBACK` автоматически не подключается. | До текущего review canonical ID с vendor/model разбирался как backend, а resolved model не передавалась в `GenerationRequest`. Исправлено в рабочей копии: известные backend-префиксы разбираются отдельно, vendor/model трактуется как полный KIE model ID, а при submit используется разрешённая модель. Silent fallback на другую модель/provider противоречит целевому workflow. |
| `py/render/minimax_client.py` | Есть прямой клиент MiniMax с платными submit/poll/download вызовами. | Не подключён к `ProviderRouter`, не покрыт тестами и не имеет cost/approval guard; нельзя считать рабочей поддерживаемой альтернативой. |
| `py/episode/spec_writer.py` → `scripts/spec_from_brief.py` | Spec writer по коду может использовать локальный LM Studio, направлять выбранную OpenRouter-модель в облако, делать облачный fallback после ошибки LM Studio, либо обращаться к Gemini напрямую по model ID. | Автоматический локальный→облачный fallback способен привести к расходам без отдельного подтверждения. В CLI нет унифицированного предварительного согласования/лимита. |
| MCP (`mcp-server/index.js`) | Имеются `assemble_episode` и `open_in_concat`; явного инструмента генерации модели в MCP нет. | Прямой MCP generation entrypoint в текущей версии не найден. |
| `cron/` / batch | В текущем дереве nightly script отсутствует. | Автоматический cron entrypoint не найден; проверить снова при добавлении automation. |
| `scripts/render_draft.py` | Локальный ffmpeg concat существующих клипов. | Сам по себе не вызывает модель; не считать генератором. |

## Несогласованность defaults и контракта

- `py/lib/config.py` задаёт video default `kie/veo-3-1` и отдельный
  `DEFAULT_VIDEO_MODEL`, однако `ProviderRouter` и
  `scripts/generate_ai_clips.py` разрешают значения независимо.
- `GenerationRequest` имеет собственный model default `veo-3-fast`; генератор
  задаёт другой model ID, а конфигурационный `DEFAULT_VIDEO_MODEL` не
  применяется этим скриптом.
- Router теперь различает известные backend-префиксы и canonical KIE
  vendor/model IDs; если в spec нужен явный KIE backend, допустим namespace
  `kie/<canonical-model-id>`. Исправление ещё не закоммичено.
- Поле `cost_usd` заполняется числом `creditsConsumed`; конверсия credits→USD
  не реализована. Надёжный денежный cap на этих данных построить нельзя.
- Тесты `tests/test_kie_client.py` используют pytest, но pytest отсутствует в
  `py/requirements.txt` и текущем Python окружении. Временное изолированное
  окружение было создано вне репозитория; suite запущен с import-path bridge,
  потому что корневой пакет проекта называется `py` и конфликтует с
  совместимостным модулем `py` pytest. Исправлены три NameError в тестах
  (неизвлечённый payload из mock-вызова) и ожидания ProviderSpec после
  исправления parser.
- `test_config.py` повторно воспроизвёл 2 ранее известных failure:
  text default не совпал с `qwen3-max` (в процессе теста фактически
  `gemini-3.6-flash`), а `LIBRARY_ROOT=library` не находится под
  `PROJECT_ROOT` из-за локального пути/симлинка.

## Проверки без внешних вызовов

- `python3 -m py_compile` по provider- и generation-файлам — успешно.
- `python3 -m unittest discover -s tests -p 'test_spec_writer.py' -v` —
  15 тестов успешно.
- Mock-only `tests/test_kie_client.py` — 41 тест прошёл после исправлений
  parser/model forwarding и тестовых NameError; live API не вызывались.
- `python3 -m unittest discover -s tests -p 'test_matcher_assembler.py' -v` —
  14 тестов успешно.
- `python3 -m unittest discover -s tests -p 'test_config.py' -v` — 2 failures,
  воспроизведены причины выше.
- Обычный системный `python3 -m pytest` недоступен: pytest не установлен, а
  системная установка заблокирована PEP 668. Mock suite прошёл во временной
  среде вне репозитория; эта среда удаляется после проверки.
- Ни один smoke/price script и ни один model API не запускались.

## Исправления в рабочей копии

- `py/render/provider_router.py`: исправлена трактовка canonical KIE
  vendor/model IDs и передача выбранной модели в `KieClient.submit()`.
- `py/render/base.py`, `py/render/kie_client.py` и generation/smoke scripts:
  разделены денежная стоимость, provider credits и latency; MiniMax больше не
  возвращает вымышленную денежную стоимость `0`.
- `tests/test_kie_client.py`: исправлены три NameError в проверках payload и
  ожидания parser/model result fields после исправлений. После этого все 41
  мок-тест проходят.
- `py/episode/spec_writer.py`: только удалены trailing spaces в добавленном
  Gemini-блоке; маршрутизация LLM и её облачный fallback не менялись.
- Правки не staged и не committed. Они пока не добавляют защиту расходов.

## Вывод и безопасные следующие действия

Provider/generation-код пока нельзя публиковать как готовый workflow:
генерационные скрипты могут самостоятельно выбрать default model и не
проверяют согласование текущей задачи. По решению пользователя точная
выбранная/одобренная модель для задачи достаточна; цены, лимиты подписки,
price snapshots и budget caps не являются предусловиями. До реализации
approval-артефакта не запускай entrypoint, который сам выбирает модель вместо
пользователя.

Рабочую копию не очищал, не перемещал файлы и ничего не staged/committed.

## Уточнение approval-подхода (2026-10-12)

Пользователь подтвердил одноразовый approval artifact и уточнил правило:
явное указание/согласование конкретной модели для текущей задачи достаточно.
Для подписочного MiniMax не нужно получать pricing/usage limits, считать цену,
фиксировать price snapshot или требовать cap. Пользователь может смотреть
цены самостоятельно; автоматизированный workflow не должен требовать этого.
Артефакт хранится вне репозитория и привязан к provider/model и scope задачи,
без полей цены и лимитов. На момент первичного inventory реализация ещё не
была начата. Не допускается silent switch на другую модель/provider.

## Реализация локальной панели (2026-10-12)

Добавлен MVP локальной панели выбора модели:
`python3 scripts/model_approval_ui.py` → `http://127.0.0.1:8765/`.
Исходники UI находятся в отдельной видимой папке
`frontend/model-approval/` (`index.html`, `styles.css`, `app.js`); Python
скрипт служит loopback static-file/API сервером.
Реестр провайдеров/моделей находится в `config/model_registry.json`; панель
не обращается к внешним каталогам и не запускает генерацию. По явному
подтверждению создаётся одноразовый artifact вне репозитория с TTL 30 минут;
создание и atomic claim используют приватные каталоги/файлы и проверяют
совпадение provider, model и task scope. Повторный claim блокируется, consumed
и expired artifacts сохраняются.

Целевые проверки: шесть локальных unit/HTTP тестов прошли; UI/реестр ответили
по loopback, cross-origin POST отклонён. Генерационные CLI и provider router
ещё не проверяют этот artifact. Поэтому панель пока фиксирует выбор и
разрешение, но **не защищает существующие generation entrypoints**; до
интеграции guard нельзя считать P0 завершённым. Внешние model APIs не
вызывались.
