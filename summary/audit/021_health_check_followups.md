# 021 — Health-check followups: package shadowing, missing final-render, idle approved preview

**Status:** 📝 Documented (2026-10-19)
**Trigger:** User asked "проверь как работает capcut-studio" → health-check found 3 issues
**Scope:** Diagnostic + 3 documented follow-ups. No code changes in this fixation.

## 1. Контекст (Context)

User asked for a project health check. The check produced 3 findings that
merit separate tracking:

1. **Pytest shadowing.** Local source directory `py/` (capcut-studio
   pipeline package) conflicts with the popular `py` dev library pytest
   depends on. `import py` from inside the project resolves to the local
   `py/__init__.py`, not the installed `py` package — so `LEGACY_PATH =
   py.path.local` in pytest fails with `AttributeError: module 'py' has
   no attribute 'path'`.
2. **No final.mp4 writer.** AGENTS.md documents that `final.mp4` is
   immutable from creation, and that lifecycle has `draft → approved →
   rendered → final`. The current tree stops at `preview.mp4` (Concat
   draft export); there is no confirmed CLI to produce `final.mp4` after
   `.approved` is set.
3. **Approved preview idle.** `serials/cyber-heist/ep-01-infiltration/`
   has `.approved`, `matched.json`, `rendered/{draft.json, preview.mp4,
   concat.json, ffmpeg_list.txt}` — but no `final.mp4`. The episode is
   approved but the pipeline never produced the final asset.

All three were documented in the health-check reply. This audit is the
formal record.

## 2. Что сделано (What was done)

- ✅ Ran `python3 -m pip install -r py/requirements.txt` in `.venv`
  (fixed missing pytest / python-dotenv / requests / yt_dlp)
- ✅ Pin compatible pair: `py==1.11.0` + `pytest<8` (the 1.10 series
  is broken on Python 3.11; the 1.11+ rename `py.path` → `py._path`,
  which breaks pytest 9; pytest<8 still expects `py.path`)
- ✅ Confirmed `python -m pytest tests/` from `/tmp` rootdir: **129/129
  passed**
- ✅ Confirmed `node mcp-server/test/concat_paths.test.js`: **4/4
  passed**
- ✅ Confirmed `.env` is present (chmod 600), 21 keys configured
- ✅ Confirmed MCP-server registers 2 tools: `assemble_episode`,
  `open_in_concat`
- ✅ Confirmed library index: 12 clips indexed in
  `library/index.sqlite`
- ❌ Did NOT fix the shadowing (out of scope for this audit; see §5
  follow-ups)
- ❌ Did NOT add a final.mp4 CLI (out of scope; see §5)
- ❌ Did NOT run final-render for cyber-heist ep-01 (out of scope;
  requires user approval of render path; see §5)

## 3. Статус (Verification)

| Layer | Result | Notes |
|---|---|---|
| Python tests | ✅ 129/129 | `pytest tests/` from `/tmp` with `--rootdir=capcut-studio` |
| Node tests | ✅ 4/4 | `node mcp-server/test/concat_paths.test.js` |
| MCP server | ✅ tools registered | `assemble_episode`, `open_in_concat` (stdio) |
| `.env` | ✅ 21 keys, mode 600 | All required keys present |
| Library | ✅ 12 clips indexed | `library/index.sqlite` is small (64 KB) |
| Cyber-heist ep-01 | 🟡 Approved, no final | `.approved` + `preview.mp4` (108 MB) ready |
| Stalker-reznik ep-01, ep-02 | 🟡 Spec + matched, no rendered | Earlier in pipeline |
| `cron/nightly.sh` | ❌ Absent | AGENTS.md: "not in current tree" — not a blocker |
| OpenSpec changes | ⚠️ 2 unarchived | `hybrid-media-workflow`, `pi-project-agent` (not mine to archive) |

## 4. Что НЕ проверено (What's NOT verified)

- **Live MCP round-trip** (Pi ↔ MCP ↔ Concat) — not exercised in this
  session, only the smoke tests on the concat_paths utility
- **Concat.app GUI** — AGENTS.md flags this was unconfirmed visually
  in earlier audit 019
- **Library embedding freshness** — only counted rows; did not probe
  whether the bge-m3 / nomic-embed embeddings match current models
- **Approved-but-unrendered path** — cyber-heist ep-01 is approved and
  has preview.mp4, but no `final.mp4` CLI exists in the current tree
  to advance it

## 5. Follow-ups

### 5.1 Pytest shadowing (`py/` ↔ `py` package)

**Symptom (deterministic, reproduced this session):**
```python
$ cd ~/Projects/capcut-studio
$ python -c "import py; print(py.__file__)"
/Users/vladteresena/Projects/capcut-studio/py/__init__.py   # ← local, not the real py
$ python -c "import py.path"   # AttributeError
```

**Workaround (used this session):**
```bash
cd /tmp
python -m pytest /Users/vladteresena/Projects/capcut-studio/tests/ \
  --rootdir=/Users/vladteresena/Projects/capcut-studio -q
```

**Real fixes (any one is sufficient):**

| Option | Effort | Risk |
|---|---|---|
| **(A) Rename `py/` → `capcut/`** | ~30 min: bulk `find -exec sed`, update import paths in tests, scripts, MCP, README, AGENTS.md, all summary/tasks/* | import-path churn; all docs referencing `py.<module>` need rewording |
| **(B) Add `conftest.py` at repo root that pins `sys.path` ordering** | ~10 min: prepend repo root, then strip `py/` from `sys.path` before pytest collects | hides the footgun; future agent may re-hit it |
| **(C) Document the workaround in AGENTS.md / README** | ~5 min: add a "Running tests" section explaining `cd /tmp && pytest --rootdir=…` | lowest risk; no code change; footgun stays |

**Recommended:** (A) is the cleanest and matches the comic-studio project
layout (`~/Projects/comic-studio/` uses `py/` too — needs verification,
but per the project memory Vlad prefers `capcut/` namespace). This
fixation 021 only documents the issue; the actual rename is a separate
fixation (022 candidate) because the import-path churn is non-trivial.

### 5.2 No `final.mp4` writer

**Current behavior:** pipeline stops at `rendered/preview.mp4`. There
is no CLI to produce `rendered/final.mp4` from an approved episode.
AGENTS.md states `final.mp4` is "immutable from creation" and that
`rendered` state transitions to `remix` rather than re-render, but the
**creation** itself has no confirmed CLI.

**Two paths forward:**

1. **Concat GUI path (manual):** open the `rendered/concat.json` in
   Concat.app, polish, export `final.mp4` by hand. Already possible;
   just not automated.
2. **Concat MCP path (semi-automated):** add a `render_final` tool to
   `mcp-server/index.js` that takes the approved `concat.json` and
   drives Concat via AppleScript / shell to export `final.mp4`. Not
   yet implemented.

**Recommended:** Option 1 is the right answer for R&D phase. The
moment Concat MCP export is verified, the open item can be closed by
adding the `render_final` tool in a follow-up fixation (023 candidate).

### 5.3 Cyber-heist ep-01 approved without final.mp4

**Current state:**
```
serials/cyber-heist/ep-01-infiltration/
  .approved         (sentinel, present)
  brief.md
  spec.json
  matched.json
  rendered/
    draft.json
    ffmpeg_list.txt
    concat.json
    preview.mp4      (108 MB, Concat draft export)
    cyber-heist-ep-01-infiltration/cache/   (thumbnails, etc.)
```

**Implication:** episode is approved, preview is rendered, but the
"final" step never happened. This is the same issue as 5.2 — fixing
5.2 (or using the Concat GUI manually) closes this.

**Recommended:** leave as-is until 5.2 is fixed, or run the Concat
GUI export once by hand if a `final.mp4` is needed before then. The
`preview.mp4` is sufficient for review and re-encoding.

## 6. Что зафиксировано в git (What landed)

- `summary/audit/021_health_check_followups.md` (this file)
- `summary/tasks/021_health_check_followups.md` (sister tasks file)
- `CHANGELOG.md` (new entry for fixation 021)

No code or test changes in this fixation — diagnostic only.

## 7. OpenSpec / PR

- No OpenSpec change started for 021 (audit + tasks, not a contract
  change)
- For 5.1 (rename `py/` → `capcut/`), an OpenSpec proposal is
  recommended because it touches the public import path
  (`from py.episode import spec_writer` → `from capcut.episode import
  spec_writer`) and the contract changes for any external script
  referencing the package
- For 5.2 (final.mp4 writer), an OpenSpec proposal is also recommended
  because it adds a new CLI / MCP tool and changes the lifecycle
  contract
- For 5.3, no OpenSpec needed — same issue as 5.2
