# 023 — Final-render writer (`rendered/final.mp4`) with enforced approval gate

**Status:** ✅ Done (2026-10-19)
**Trigger:** Follow-ups 5.2 + 5.3 from
`summary/audit/021_health_check_followups.md`
**Branch:** `feature/rename-py-to-capcut`
**OpenSpec:** `openspec/changes/final-render-writer/` → archived as
`openspec/changes/archive/2026-10-19-final-render-writer/`

## 1. Контекст (Context)

The lifecycle documented in `AGENTS.md` was:

```
draft → approved → matched → rendered → published
```

but nothing in the tree could produce `rendered/final.mp4`:

- `scripts/assemble_episode.py` → `rendered/draft.json` (a Concat timeline)
  and stops.
- `scripts/render_draft.py` → `rendered/preview.mp4` via
  `ffmpeg -f concat -c copy`. No approval check, no idempotency, and it
  overwrites `preview.mp4` in place.
- `capcut/lib/lifecycle.py` already had `mark_rendered()`,
  `write_spec_sha()`, `is_idempotent_render()` and `sha256_spec()` — the
  helpers existed, but nothing called them.

Consequences:

1. `current_state()` could never return `State.RENDERED`, so the
   `published` transition was unreachable.
2. **The approval gate was not technically enforced** — nothing stopped a
   render of an unapproved episode. `AGENTS.md` warned about this rather
   than claiming enforcement.
3. `serials/cyber-heist/ep-01-infiltration/` sat approved with a 108 MB
   `preview.mp4` and no `final.mp4` — stuck mid-lifecycle.

## 2. Что сделано (What was done)

### New: `capcut/assemble/final_renderer.py`

Package module (not a script) so the logic is unit-testable:

- `build_ffmpeg_command(timeline, output_path, *, ffmpeg_bin, concat_list,
  reencode, resolution, fps) -> list[str]`
- `build_concat_list(timeline, concat_list) -> Path`
- `render_final(timeline, output_path, *, ffmpeg_bin, reencode,
  resolution, fps) -> Path`
- `probe_duration(path, *, ffprobe_bin) -> float | None`
- `FinalRenderError` exception

Two encode paths: **stream copy** (`-c copy`, fast) with automatic
**re-encode** fallback (H.264/AAC + scale/pad filter) when ffmpeg
rejects the copy. Renders go to `.final.mp4.tmp.mp4` and are moved into
place with `os.replace()` only after a successful encode — a failed
render leaves no partial file.

### New: `scripts/render_final.py`

CLI wrapper enforcing the three project invariants:

1. **Approval gate** — refuses unless `.approved` exists in the episode
   dir; exit 1, no file written.
2. **Idempotency** — existing `final.mp4` + matching `rendered/spec.sha256`
   → no-op, exit 0, file untouched (mtime preserved).
3. **Immutability** — existing `final.mp4` + hash mismatch → refuses,
   exit 1, file untouched. No `--force` flag exists by design; the
   correct path is a remix.

After a successful render it calls `lifecycle.write_spec_sha()` and
`lifecycle.mark_rendered()`, so the filesystem state and the sentinel
bookkeeping agree. Prints output path, byte size, probed duration and
the recorded spec sha256.

### New: MCP tool `render_final`

Third tool in `mcp-server/index.js` alongside `assemble_episode` and
`open_in_concat`. Same `serial`/`ep` slug validation, optional
`reencode` boolean. Shells out to `scripts/render_final.py`; a non-zero
exit surfaces as `isError: true` with the script's message, so an
approval-gate refusal is legible to the caller.

### Docs updated

- `README.md` + `README_RU.md` — new "Final render" section, MCP tool
  count 2 → 3
- `summary/PRD/PRD.md` — Stage 5 rewritten: the old text said
  "overwrite rendered/final.mp4 (это нормально — final.mp4 не immutable
  до публикации)", which contradicted `AGENTS.md`. The PRD now reflects
  the enforced immutability.
- `AGENTS.md` — approval-gate and idempotency bullets changed from
  "policy" to "enforced"; immutability bullet now says the rule is
  enforced by the writer; workflow diagram updated; the "Run" table gained
  a `Final render` row. The first edit attempt was blocked (protected
  instruction file, no consent); it was applied after the user explicitly
  approved it, as commit `8e32d26`.

## 3. Статус (Verification)

### Unit / integration tests

**New: `tests/test_final_renderer.py` — 16 tests**

| Test | Result |
|---|---|
| `build_ffmpeg_command` stream-copy path | ✅ |
| `build_ffmpeg_command` re-encode path has scale filter | ✅ |
| no video clips → `FinalRenderError` | ✅ |
| clips without `src` are skipped | ✅ |
| concat list: one `file '…'` line per clip | ✅ |
| render produces non-empty output, no temp file left | ✅ |
| missing source → error, no output file | ✅ |
| failed ffmpeg → no partial output | ✅ |
| `probe_duration` reads actual duration | ✅ |
| `probe_duration` → None for missing file | ✅ |
| **CLI refuses without `.approved`** | ✅ exit 1 |
| **CLI renders when approved** | ✅ |
| **CLI second run is a no-op** (mtime unchanged) | ✅ |
| **CLI changed spec refuses, keeps final** | ✅ |
| CLI missing draft.json refused | ✅ |
| `final.mp4` moves lifecycle state to `RENDERED` | ✅ |

### Full suite

| Suite | Before | After | Result |
|---|---|---|---|
| `pytest tests/` | 129 | **145** | ✅ 145 passed |
| `node mcp-server/test/concat_paths.test.js` | 4 | 4 | ✅ 4 passed |

### Live run on the stuck episode

```
$ python scripts/render_final.py --serial cyber-heist --ep ep-01-infiltration
[render_final] rendering serials/cyber-heist/ep-01-infiltration/rendered/final.mp4
[render_final] wrote serials/cyber-heist/ep-01-infiltration/rendered/final.mp4 (108064297 bytes)
[render_final] duration: 35.29s
[render_final] spec sha256: 07b9a1aa29ef4a3157d8497c3c3434a1885663ba05ffcfcd281adaf5350ead42
[render_final] state: rendered
```

ffprobe on the produced file:

```
codec_name=h264
width=1920
height=1080
duration=35.291667
size=108064297
```

### Live gate + idempotency checks

| Check | Result |
|---|---|
| 2nd run on the real episode | ✅ `already rendered for this spec — no-op`, mtime unchanged |
| `stalker-reznik/ep-01-pilot` (no `.approved`) | ✅ refused, **exit code 1**, no `final.mp4` created |
| MCP `tools/list` over stdio | ✅ 3 tools, `render_final` present with `serial, ep, reencode` |

## 4. Что НЕ проверено (What's NOT verified)

- **Captions are not burned in.** The writer concatenates the video
  track only. `transition_in`/`transition_out` from the timeline are
  declarative metadata and are not applied as ffmpeg filters. Caption
  burn-in, transitions, audio mixing and voiceover TTS remain
  Concat/CapCut polish steps — by design (see the OpenSpec boundaries).
- **Only the stream-copy path was exercised on real content.** The
  re-encode fallback is covered by unit tests of the command builder but
  was not triggered on a real mismatched-codec episode.
- **`publish()` was not invoked.** The `published` state (episode-log
  append) is still manual — `lifecycle.publish()` exists and works, but
  this change does not call it, and no episode was published.
- **No MCP client round-trip.** The `render_final` tool was verified via
  a direct stdio `tools/list` probe, not through a live MCP client
  (Hermes) calling `tools/call`.
- **`preview.mp4` path untouched.** `scripts/render_draft.py` still
  overwrites `preview.mp4` in place and still has no approval check. That
  is intentional (a draft preview is pre-approval), but it means the
  word "preview" is now the only marker distinguishing the two outputs.

## 5. Решения (Decisions)

- **Re-encode as an automatic fallback, not a flag-only path.** The
  first attempt is always stream copy; if ffmpeg rejects it, the writer
  retries with an explicit H.264/AAC encode. This makes the CLI work on
  mixed-codec libraries without the operator having to know the codecs.
- **No `--force` flag.** `AGENTS.md` documents `final.mp4` as immutable
  from creation. A force flag would let a tool violate an invariant that
  the lifecycle is supposed to guarantee. The escape hatch is a remix —
  a new episode directory — which keeps the original intact.
- **The gate lives in the CLI, not in the package module.**
  `capcut/assemble/final_renderer.py` stays a pure "timeline → mp4"
  primitive that can be unit-tested without a filesystem episode; the
  policy decision (is this episode approved?) sits in the same layer as
  the other CLI entry points.
- **PRD corrected against AGENTS.md.** The PRD's Stage 5 said overwriting
  `final.mp4` was acceptable before publication. `AGENTS.md` says the
  opposite. The PRD was updated to match the implemented invariant —
  `summary/PRD/PRD.md` is supposed to reflect current state, not
  aspiration.

## 6. Что зафиксировано в git (What landed)

- `capcut/assemble/final_renderer.py` (new)
- `scripts/render_final.py` (new)
- `tests/test_final_renderer.py` (new, 16 tests)
- `mcp-server/index.js` — `render_final` tool (list + handler)
- `README.md`, `README_RU.md`, `summary/PRD/PRD.md`, `AGENTS.md`
- `summary/audit/023_final_render_writer.md` (this file)
- `summary/tasks/023_final_render_writer.md` (sister file)
- `CHANGELOG.md`

## 7. OpenSpec / PR

- Proposal: `openspec/changes/final-render-writer/proposal.md`
- Tasks: `openspec/changes/final-render-writer/tasks.md`
- Archived to `openspec/changes/archive/2026-10-19-final-render-writer/`
- Branch `feature/rename-py-to-capcut` (merge to `main` is a separate step)
