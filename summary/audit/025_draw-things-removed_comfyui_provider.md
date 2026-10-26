# 025 — Draw Things removed from the machine, local image backend moved to ComfyUI

**Status:** ✅ Done (2026-10-26)
**Trigger:** User removed the Draw Things app from Mac Studio and asked
"У нас здесь это как-то задействовано?"
**Scope:** `config/model_registry.json`, one test fixture, one in-flight
OpenSpec proposal. **No call code existed in this project.**

## 1. Контекст (Context)

The user removed the **Draw Things** app from Mac Studio and moved to
**ComfyUI**. The question was whether this project used it.

Investigation result — Draw Things was **not** wired into the video
pipeline here:

| Where | Degree of involvement |
|---|---|
| `config/model_registry.json` | one provider entry `"id": "draw-things"` |
| `tests/test_model_approval.py` | one test fixture using that string |
| `openspec/changes/hybrid-media-workflow/proposal.md` | one line: "Prefer local Draw Things for image experiments" |
| **Actual call code** | **none** — the video pipeline goes through KIE / MiniMax / OpenRouter / LM Studio |

So this project needed a **registry correction**, not a port. ComfyUI
was **not** mentioned anywhere in the tree — it was a new provider from
this project's point of view.

The live backend on the machine (shared with `comic-studio` and Hermes)
is ComfyUI 0.42.5 on port **8189**, FLUX dev Q4 GGUF, four LoRAs, with
a standalone runner already in place. Full topology and the Hermes
skill migration are recorded in
`~/Projects/comic-studio/summary/audit/029_draw-things-removed-comfyui-migration.md`.

## 2. Что сделано

### 2.1. `config/model_registry.json` (MODIFIED)

| Было | Стало |
|---|---|
| `"id": "draw-things"`<br>`"label": "Draw Things (локально; ID модели зависит от установленной модели)"` | `"id": "comfyui"`<br>`"label": "ComfyUI (локально; FLUX/GGUF, порт 8189)"` |

The old label promised "the model ID depends on whichever model is
loaded" — that was true of Draw Things' mutable app state. ComfyUI pins
the model in the workflow (`UnetLoaderGGUF.unet_name`), so the label
now names the backend and port.

A `models` entry was added for the same provider
(`flux1-dev-Q4_K_S.gguf`, `task_types: ["image"]`). Without it the
approval UI's model dropdown for `comfyui` offered only manual ID
entry, while every other provider had a populated list — the pinned
model was already verified live, so listing it costs nothing and makes
the dropdown usable.

**The provider string is not validated against the registry** by
`create_approval()` — it only checks type and length — so this change
is a UI/listing correctness fix, not a behavioural one.

### 2.2. `tests/test_model_approval.py` (MODIFIED)

| Было | Стало |
|---|---|
| `"provider": "draw-things"` | `"provider": "comfyui"` |

The fixture used the provider string as an opaque label. Kept in sync
with the registry so the test does not reference a provider that no
longer exists on this machine.

### 2.3. `openspec/changes/hybrid-media-workflow/proposal.md` (MODIFIED)

| Было | Стало |
|---|---|
| "Prefer local Draw Things for image experiments." | "Prefer local ComfyUI for image experiments (FLUX dev GGUF on port 8189). Draw Things was removed from the machine; ComfyUI is the local image backend. Note that FLUX on this hardware runs ~16 s per step, so image experiments are not cheap — prototype at 512–768 px and fewer steps." |

The proposal is **in-flight** (not archived), so it still had to describe
a backend that exists. The speed note was added because the proposal
is about *creative prototyping* — a rate of ~16 s per step changes what
"prototype" means in practice.

## 3. Файлы

| Путь | Действие | Описание |
|---|---|---|
| `config/model_registry.json` | MODIFIED | provider `draw-things` → `comfyui` |
| `tests/test_model_approval.py` | MODIFIED | fixture provider string |
| `openspec/changes/hybrid-media-workflow/proposal.md` | MODIFIED | local image backend + speed caveat |

## 4. Verification

| Шаг | Результат |
|---|---|
| `grep -rn -i 'draw.things' --include='*.py' --include='*.json' --include='*.js'` | ✅ no matches — no call code existed |
| `grep -rn -i 'draw.things'` (all file types) | ⚠ matches remain in **dated historical records** only: `summary/audit/015_project_state_and_prd_alignment.md:109`, `summary/tasks/016_stabilization_and_spend_safety.md:33`, `summary/tasks/012_external_storage_migration.md`. These describe the project state at their own dates and are left untouched on purpose — rewriting them would make the history inaccurate (same reasoning as audit 022). A future "grep Draw Things" pass will re-flag them; the footnote is here so the next reader knows they are intentional. |
| `python3 -c "json.load(open('config/model_registry.json'))"` | ✅ valid JSON |
| `python -m pytest tests/test_model_approval.py -q` | ✅ passes with the new provider string |
| `python -m pytest tests/ -q` | ✅ 161/161 passed |
| `curl http://127.0.0.1:8189/system_stats` | ✅ ComfyUI 0.42.5 alive on 8189 — the registry entry points at a live backend |
| `curl http://127.0.0.1:8189/models/unet` → `UnetLoaderGGUF.unet_name` | ✅ `flux1-dev-Q4_K_S.gguf` — matches the label |

## 5. Связанные

- `~/Projects/comic-studio/summary/audit/029_draw-things-removed-comfyui-migration.md`
  — the Hermes-side migration and the full measured ComfyUI behaviour
- `~/Projects/comic-studio/summary/audit/030_freevideo-removal-plan.md`
  — FreeVideo cleanup plan (50.6 GB), deferred until the user is at the machine
- `openspec/changes/hybrid-media-workflow/proposal.md` — the in-flight
  change whose provider line was corrected here

## 6. Известные ограничения

- **No ComfyUI client exists in this project's code.** The registry now
  offers `comfyui` as a selectable provider, but there is no
  `capcut/render/comfyui_client.py`. Selecting it in the approval UI
  records the choice; it does not route generation to ComfyUI. Wiring
  it in would be a separate change affecting the provider contract
  (`ProviderRouter` + a new client) — per `AGENTS.md`, that needs an
  OpenSpec proposal.
- **The `hybrid-media-workflow` proposal remains in-flight** and is not
  archived by this change.

## 7. Следующие шаги

- [ ] Decide whether ComfyUI should become a real render provider here
      (needs an OpenSpec proposal — changes the provider contract)
- [ ] `comic-studio` still carries ~1300 lines of live Draw Things code
      — separate task, see audit 029
- [ ] Execute the FreeVideo cleanup from audit 030 when the user is at the machine
