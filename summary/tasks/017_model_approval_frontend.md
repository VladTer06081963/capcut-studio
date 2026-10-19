# TODO 017: Отдельная папка фронтенда панели согласования

**Статус:** ✅ Выполнено  
**Дата:** 2026-10-12  
**Основание:** `summary/audit/016_provider_generation_inventory.md`  
**Спецификация:** `openspec/changes/hybrid-media-workflow/specs/workflow-profiles/spec.md`

## Цель

Сделать локальную панель выбора провайдера и модели видимой как обычный
frontend-проект в отдельной папке, а не HTML/JavaScript, спрятанные внутри
Python-скрипта. Python остаётся локальным API и static-file сервером.

## Выполнено

- [x] Вынести UI в `frontend/model-approval/`:
  `index.html`, `styles.css`, `app.js`.
- [x] Оставить запуск панели через `python3 scripts/model_approval_ui.py`;
  сервер обслуживает отдельные frontend-файлы и локальные `/api/*` routes.
- [x] Явно отображать список провайдеров; модели фильтруются по провайдеру и
  типу задачи. Для отсутствующих в локальном registry моделей/провайдеров
  оставить ручной ввод.
- [x] Сохранить ограничения: bind к loopback, no provider catalog/price
  requests, no credentials in UI, no generation on selection/approval.
- [x] Добавить проверку отдачи HTML/CSS/JS и API в HTTP unit tests.
- [x] Обновить README, OpenSpec и audit с layout и командой запуска.

## Проверки

- `python3 -m unittest tests.test_model_approval -v`
- `python3 -m py_compile py/lib/model_approval.py scripts/model_approval_ui.py tests/test_model_approval.py`
- `node --check frontend/model-approval/app.js`
- `git diff --check`

## Отдельная незавершённая задача

Generation entrypoints всё ещё не проверяют/не потребляют approval artifact.
Это не входило в перенос frontend-файлов; см. незавершённый P0 в
`summary/tasks/016_stabilization_and_spend_safety.md`.
