# capcut-studio

Долгие видео-сериалы: пайплайн производства. Сестринский проект к
[`comic-studio`](../comic-studio). Подход **library-first**: ассеты
сначала генерируются и индексируются, эпизоды потом собираются
из библиотеки.

## Быстрый старт

```bash
git clone <this-repo>
cd capcut-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -r capcut/requirements.txt
cp .env.example .env   # заполните API-ключи
```

> ✅ **Shadowing устранён (fixation 022):** пакет pipeline переименован
> из `py/` → `capcut/`, поэтому больше не перекрывает библиотеку `py`,
> на которую опирается pytest. Тесты запускаются **из корня
> репозитория**:
> ```bash
> source .venv/bin/activate
> python -m pytest tests/ -q
> ```
> История проблемы — `summary/audit/021_health_check_followups.md` (п. 5.1),
> фикс — `summary/audit/022_rename_py_to_capcut.md`.

Полный пайплайн, раскладка и инварианты — в `AGENTS.md`.

## Панель подтверждения локальных моделей

Запустите локальную панель выбора моделей из корня репозитория:

```bash
python3 scripts/model_approval_ui.py
```

Откройте `http://127.0.0.1:8765/` в браузере. Подсказки моделей/провайдеров
читаются из `config/model_registry.json` — добавляйте туда только
**тот** ID, который вы реально выбрали. Панель **не** запрашивает
каталоги и цены провайдеров, **не** спрашивает учётные данные,
**не** запускает генерацию. Явное подтверждение создаёт одноразовый
артефакт подтверждения в
`~/Library/Application Support/capcut-studio/model-approvals/`,
который истекает через 30 минут. Остановите панель `Ctrl+C`.

Видимый фронтенд — `frontend/model-approval/` (`index.html`,
`styles.css`, `app.js`). Python-скрипт обслуживает эти файлы и
локальный API.

**Текущее ограничение:** точки входа в генерацию **пока не
потребляют и не проверяют** эти артефакты подтверждения. Не считайте
панель «барьером безопасности» и не запускайте скрипты генерации
в предположении, что они подтверждены.

## Project Pi agent (запланировано)

Pi `1.0.4` уже установлен глобально на Mac Studio и должен
переиспользоваться **там же** без переустановки. Установщик проекта
проверяет Pi на каждом хосте и устанавливает его **только** на
других хостах, где его нет; затем использует выделенный harness
и навыки этого репозитория. Текущий фронтенд моделей остаётся
**ручным** интерфейсом правки провайдеров/моделей. MCP — основная
интеграция project-tools для Pi; Telegram — только возможный
вспомогательный интерфейс позже, с Mini App для прода. См.
`summary/tasks/018_pi_project_agent_harness.md`
и `openspec/changes/pi-project-agent/`. Перед автоматизацией установки
**обязательно** сверьтесь с актуальной документацией <https://pi.dev/>.

Заметки и навыки project-specific Pi уже разложены в `.pi/`.
Запускайте Pi из корня репозитория **в отдельном терминале**:

```bash
pi --skill .pi/skills
```

Сначала прочтите `.pi/README.md`. Выбранная coding-agent модель —
MiniMax M3; сверьте её **точный** ID в Pi перед первым промптом.
**Не** кладите учётные данные в файлы проекта и **не** меняйте
глобальный конфиг Pi.

## MCP-сервер

MCP-сервер на **stdio** (не network), регистрирует 2 tool'а:

- `assemble_episode` — собрать эпизод из библиотеки
- `open_in_concat` — открыть черновик в Concat.app

Запуск: `node mcp-server/index.js`. Smoke-тесты:
`node mcp-server/test/concat_paths.test.js` (4/4 ✅).

Подробности — `mcp-server/README.md` (если есть) и
`summary/audit/021_health_check_followups.md`.

## Статус

R&D / подготовка, не продакшен. См. `AGENTS.md` → «Status».

## Follow-ups (fixation 021 → 022 → 023)

- ✅ **5.1** shadowing `py/` ↔ `py` пакет — **закрыт в fixation 022**:
  пакет переименован в `capcut/`, тесты идут из корня репозитория
- ✅ **5.2** нет `final.mp4` writer — **закрыт в fixation 023**:
  `scripts/render_final.py` + MCP-инструмент `render_final`
- ✅ **5.3** cyber-heist ep-01 approved без final — **закрыт в fixation 023**:
  `rendered/final.mp4` создан, состояние эпизода → `rendered`

Детали — `summary/audit/021_health_check_followups.md`,
`summary/audit/022_rename_py_to_capcut.md`,
`summary/audit/023_final_render_writer.md`.
