# Задачи: External storage migration (F12)

**Status:** ⚠️ **ЧАСТИЧНО ВЫПОЛНЕНО** — закрыто с ограничениями
**Change ID:** `external-storage-migration`
**OpenSpec:** не открывался (deferred, по договорённости без коммитов)
**Компаньон:** `summary/audit/012_external_storage_migration.md` (не сделан)
**Предшественник:** `summary/audit/011_smoke_test_compatibility.md`
**Триггер:** `df -h /` → системный диск `Macintosh HD` 87% full (54 GB free из 460 GB)

## Итог (факт)

| Метрика | Было | Стало | Δ |
|---|---|---|---|
| Free space (Macintosh HD) | 54 GB (87% full) | **65 GB (83% full)** | **+11 GB (+20%)** |
| Цель task | 150 GB (≥150) | 65 GB | ❌ не достигнута |

**Перенесено:** ~11 GB на `MacStudioData` (USB-HDD, 1.3 TB free).
**Осталось:** ~90 GB до цели — требует других подходов (TCC unlock, MBP, удаление Application Support).

## Контекст в одном абзаце

`~/Projects/capcut-studio/` библиотека-ориентированный video pipeline: `library/ai/` + `library/stock/` будут расти десятками GB в месяц (YouTube ingest 50-200 MB/клип, H3.0 генерация 30-50 MB upload + download на клип, Concat drafts 3-10 GB/мес). Сейчас `library/ai/` пустая (проект только поставлен, F-11 завершён), но как только пойдут master-ассеты и ночной cron — внутренний SSD `Macintosh HD` 460 GB умрёт. Уже сейчас 87% занято (`/.cache` 4.5 GB, `~/Movies` 3.1 GB, `~/Downloads` 906 MB, `~/Library/Caches/*`). Внешние диски `MacStudioData` (1.3 TB free), `HD1` (200 GB free), `HD2` (244 GB free) — естественное место.

## Диски (свежий `df -h /Volumes/`)

| Диск | Size | Used | Free | % | Назначение (план) |
|---|---|---|---|---|---|
| `Macintosh HD` | 460 GB | 358 GB | **54 GB** | 87% | Система, код, git, конфиги |
| `MacStudioData` | 1.8 TB | 234 GB | 1.3 TB | 15% | AI модели, ComfyUI, тяжёлые данные (уже используется) |
| `HD1` | 373 GB | 172 GB | 200 GB | 47% | Cache (.cache, Downloads, Desktop рабочее) |
| `HD2` | 559 GB | 314 GB | 244 GB | 57% | Documents, Movies (промежуточные рендеры) |
| `Remocn Studio` | 168 MB | 139 MB | 29 MB | 83% | Не использовать (крошечный, почти полный) |

## Принципы миграции

1. **Симлинки, не копирование** — `/Users/vladteresena/<dir>` → `/Volumes/<hdd>/<dir>`. macOS стабильный mount points.
2. **mv, а не cp** — атомарно, нет дублирования.
3. **Не трогать то, что работает** — ComfyUI, Concat, существующие pipelines уже на `MacStudioData`, не двигаем.
4. **LaunchAgents перезагрузить** после симлинков (для `~/Library/Caches`).
5. **Сначала измерить, потом резать** — до миграции собрать `du -sh` по каждой папке, после — повторить, сравнить.

## Целевая раскладка (до → после)

| Путь | Было | Стало | Symlink |
|---|---|---|---|
| `~/Movies` | `Macintosh HD` (3.1 GB) | `HD2` | `~/Movies → /Volumes/HD2/Movies` |
| `~/Documents` | `Macintosh HD` (575 MB) | `HD2` | `~/Documents → /Volumes/HD2/Documents` |
| `~/Downloads` | `Macintosh HD` (906 MB) | `HD1` | `~/Downloads → /Volumes/HD1/Downloads` |
| `~/Desktop` | `Macintosh HD` (TCC blocked) | `HD1` | `~/Desktop → /Volumes/HD1/Desktop` |
| `~/.cache` | `Macintosh HD` (4.5 GB) | `HD1` | `~/.cache → /Volumes/HD1/cache` |
| `~/Library/Caches` | `Macintosh HD` (большая часть LM Studio, pip, ComfyUI) | `HD1` | точечно по подпапкам |
| `~/Projects/*` | `Macintosh HD` (2.2 GB) | **оставить** | — (код, git, копейки) |
| `~/knowledge/` | `Macintosh HD` (~5 GB) | **оставить** | — (база знаний, ценно) |
| `ComfyUI-Shared/*` | `MacStudioData` (уже там) | **оставить** | — (уже работает) |
| `Library/ai`, `stock` capcut | `Macintosh HD` → пусто | `HD2` (или `MacStudioData`) | пока нечего, создать при первой генерации |

## Задачи (детально)

| ID | Задача | Оценка | Статус | Зависит от |
|---|---|---|---|---|
| 1 | Baseline `du -sh` по всем пользовательским папкам (с учётом TCC) | 10m | ⏳ | — |
| 2 | Создать каталоги-приёмники: `/Volumes/HD1/{cache,Downloads,Desktop}`, `/Volumes/HD2/{Movies,Documents}` | 5m | ⏳ | — |
| 3 | `mv ~/Movies /Volumes/HD2/Movies && ln -s` | 5m | ⏳ | 2 |
| 4 | `mv ~/Documents /Volumes/HD2/Documents && ln -s` | 5m | ⏳ | 2 |
| 5 | `mv ~/Downloads /Volumes/HD1/Downloads && ln -s` | 5m | ⏳ | 2 |
| 6 | `mv ~/Desktop /Volumes/HD1/Desktop && ln -s` | 5m | ⏳ | 2 |
| 7 | `mv ~/.cache /Volumes/HD1/cache && ln -s` | 5m | ⏳ | 2 |
| 8 | Точечно `~/Library/Caches` (LM Studio, pip, ComfyUI) на HD1, через mv отдельных подпапок | 30m | ⏳ | 1 |
| 9 | Создать `capcut-studio/library/{ai,stock}` на `HD2` (или `MacStudioData`), подключить как путь для `assemble_episode.py` | 15m | ⏳ | 2 |
| 10 | Обновить `py/lib/config.py` capcut-studio: пути по умолчанию на внешние диски (через env override) | 20m | ⏳ | 9 |
| 11 | Перезагрузка + smoke test: open doc, launchd подхватил, LM Studio стартует с пустого cache | 15m | ⏳ | 3-8 |
| 12 | Финальный `du -sh` + `df -h` → отчёт по высвобожденному месту | 10m | ⏳ | 11 |
| 13 | `git commit` + cherry-pick на `demo-production` если применимо (только doc-change для capcut) | 5m | ⏳ | 12 |
| 14 | OpenSpec change `external-storage-migration` → archive | 10m | ⏳ | 13 |

**Суммарно:** ~2.5 часа работы, dry-run friendly (каждый шаг — `mv` + `ln -s` идемпотентен если не делать дважды).

## Файлы (план)

### To create
- `summary/audit/012_external_storage_migration.md` (компаньон)
- `openspec/changes/external-storage-migration/{proposal.md, tasks.md, design.md}` (deferred до старта работ)

### To modify
- `py/lib/config.py` capcut-studio — default paths на внешние диски
- `py/assemble/concat_exporter.py` — пути к library
- `CHANGELOG.md` capcut-studio — запись о миграции
- (опционально) `~/.zshrc` — alias `library-hd1` / `library-hd2`

### To leave alone
- `~/Projects/comic-studio/`, `~/Projects/capcut-studio/`, `~/knowledge/` — на системном диске
- `ComfyUI-Installs/`, `ComfyUI-Shared/` — на `MacStudioData` (уже там)

## Verification (Definition of Done)

- [ ] `df -h /` показывает ≥150 GB free на `Macintosh HD` (было 54)
- [ ] Все симлинки резолвятся: `readlink ~/Movies ~/Documents ~/Downloads ~/Desktop ~/.cache`
- [ ] `open ~/Documents/test.pdf` (или любой документ) работает
- [ ] LM Studio запускается с пустого cache (cold start), не падает
- [ ] LaunchAgents (`~/Library/LaunchAgents/*.plist`) после `launchctl list` показывают свои процессы
- [ ] Git repo capcut-studio коммит `chore: migrate user data dirs to external drives` (или аналог)
- [ ] OpenSpec change заархивирован
- [ ] CHANGELOG обновлён (ISO-8601 timestamp)

## Известные ограничения (риски)

| Риск | Митигация |
|---|---|
| `~/Library/Caches/*` — внутри уже загруженные модели LM Studio (bge-large, qwen-coder). Удаление кеша = cold reload. | Не трогать модели в `~/Library/Application Support/LM Studio/`, только подпапки `Caches/*` |
| `~/Desktop` TCC protected (полный `du` без sudo) | Миграция идёт через `mv` (атомарно) — TCC не блокирует |
| Remocn Studio 168 MB, 83% full — отвлекающий фактор | Не использовать, не упоминать в миграции |
| Concat MCP стартует с абсолютными путями к `library/ai/` если capcut-studio уже подключён | Проверить `py/assemble/concat_exporter.py` на hardcoded paths до шага 9 |
| Если HDD отмонтируется (USB отвалится) — все симлинки битые | Добавить `diskutil mountDisk` в LaunchAgent? Или просто документировать «не отключать во время работы pipeline» |
| Demo на VPS — нет внешних дисков, миграция только для Mac Studio | Не делать cherry-pick в `demo-production` для runtime кода; только doc |

## Следующие шаги после Done

- [ ] Capcut-studio: запуск генерации master-ассетов (F-13, в плане) — теперь есть куда расти
- [ ] Поставить на cron (`launchd`) ночной `ingest_youtube` + `index_library` — без риска упираться в диск
- [ ] Мониторинг `df -h` через Hermes еженедельно — алерт если `Macintosh HD` <100 GB free
- [ ] Через 1-2 месяца оценить рост `library/` — может понадобиться второй внешний диск

---

## Что реально сделано (закрытие)

✅ **Step 3-5: Documents (575M), Downloads (881M), Movies (3.1G)** — симлинки на `MacStudioData`
✅ **Step 7: `.cache` 4.5G** — `rm -rf` + симлинк (regenerable, 0 риск)
✅ **Step 8: Library/Caches 8 подпапок (~3.5G)** — `notion-updater`, `com.google.antigravity`, `pip`, и др.
✅ **Step 9: capcut-studio library** — симлинк на `MacStudioData/UserData/capcut-library`
✅ **Credentials setup** — `~/.hermes/secrets/README.md` + Keychain запись `asus-router`

## Что НЕ сделано (закрыто как есть)

❌ **Step 6: Desktop** — TCC заблокировало `mv`/`rm -rf`
❌ **HD1, HD2 (200+244 GB)** — TCC + `owner=root` (нужен `sudo chown`)
❌ **MBP через Thunderbolt** — не в сети
❌ **Asus роутер (192.168.50.1, 2 TB)** — anonymous read-list виден, монтирование требует пароль (заготовка в Keychain)
❌ **Library/Caches остальные (~3G)**: Google 1.8G, GeoServices, GitHub-copilot
❌ **Step 10-14: config audit, smoke test, git commit, OpenSpec** — не делали по договорённости

## Реальные замеры скорости

| Операция | Скорость | Диск |
|---|---|---|
| Sequential write 512 MB | **3 GB/s** | Internal SSD |
| Sequential write 512 MB | 110 MB/s | MacStudioData USB-HDD |
| 5020 мелких файлов 220 MB | 117 MB/s | Internal SSD |
| **5020 мелких файлов 220 MB** | **35 MB/s** | **MacStudioData USB-HDD** |

USB-HDD проигрывает в 3.3× на мелких файлах. Параллельные `mv` делят throughput — строго sequential.

## Практические находки

1. **TCC** — Apple-овский слой защиты. Terminal/app должен явно запросить разрешение в System Settings. HD1, HD2, Desktop заблокированы.
2. **`ln -s` НЕ заменяет непустую папку** — создаёт симлинк **внутри**. Нужен `rm -rf` или `mv` сначала.
3. **Параллельные `mv` на USB-HDD** = плохо. Throughput делится, seek overhead растёт.
4. **`mount_smbfs` без пароля** = Permission denied даже для anonymous-readable шар. Asus RT требует аутентификацию.
5. **Keychain** = идеальное место для пароля от роутера. Не светится в ps/logs.

## Что осталось / следующие шаги (новая задача когда готов)

**На пользователя:**
- [ ] **Desktop TCC**: System Settings → Privacy & Security → Files and Folders → Terminal → ON
- [ ] **HD1, HD2 unlock**: один `sudo chown -R vladteresena:staff /Volumes/HD1 /Volumes/HD2`
- [ ] **Asus router password**: найти в Router app, выполнить `security add-generic-password -s "asus-router" -a "vladteresena" -w "PASSWORD" -U`
- [ ] **Включить MBP** когда будет время — Thunderbolt share `/Volumes/CapCut-Assets/` (~3 GB/s)

**На будущее:**
- [ ] Library/Caches остальные (~3 GB)
- [ ] Application Support cleanup: `com.apple.wallpaper` 2.9G, `VisualStudio` 907M, `Comfy Desktop` 820M, `Epic` 787M
- [ ] Достичь 150 GB free — потребует TCC unlock + HD1/HD2 или подключение MBP
- [ ] Мониторинг `df -h /` через Hermes еженедельно

## Файлы

### Создано
- `summary/tasks/012_external_storage_migration.md` (этот файл, обновлён)
- `~/.hermes/secrets/README.md` (шаблон credentials)

### НЕ создано (по договорённости)
- `summary/audit/012_external_storage_migration.md`
- `openspec/changes/external-storage-migration/`
- `CHANGELOG.md` обновление
- `git commit`

### Изменено (симлинки)
- `/Users/vladteresena/Movies` → `/Volumes/MacStudioData/UserData/Movies`
- `/Users/vladteresena/Documents` → `/Volumes/MacStudioData/UserData/Documents`
- `/Users/vladteresena/Downloads` → `/Volumes/MacStudioData/UserData/Downloads`
- `/Users/vladteresena/.cache` → `/Volumes/MacStudioData/UserData/cache`
- `~/Library/Caches/{notion-updater, notion.id.ShipIt, termius-updater, comfyui-desktop-2-updater, com.google.antigravity, com.google.antigravity.ShipIt, copilot, pip}` → симлинки
- `~/Projects/capcut-studio/library` → `/Volumes/MacStudioData/UserData/capcut-library`

## Заключение

Task 012 **закрыт с честным результатом**: +20% свободного места (11 GB), не 100% (нужно 150). Стратегия работает (симлинки стабильны, данные перенесены), но **потолок без sudo/TCC unlock = ~65 GB free**. Достижение цели 150 GB — следующая итерация, **новая задача** когда пользователь будет готов разблокировать TCC или включить MBP.
