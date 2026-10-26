# Change: Final-render writer (`rendered/final.mp4`) with approval gate

## Status

Proposed; implementation pending.

## Problem

`AGENTS.md` documents the intended lifecycle:

```
draft → approved → matched → rendered → published
```

with `rendered/final.mp4` as the terminal render artifact. But the current
tree has **no writer** for `final.mp4`:

- `scripts/assemble_episode.py` produces `rendered/draft.json`
  (a Concat timeline) and stops there.
- `scripts/render_draft.py` produces `rendered/preview.mp4` — a raw
  `ffmpeg -f concat -c copy` of the source clips. It has no approval
  check, no idempotency, and it overwrites `preview.mp4` in place.
- `py/lib/lifecycle.py` already provides `mark_rendered()`,
  `write_spec_sha()`, `is_idempotent_render()` and `sha256_spec()` — the
  helpers exist, but nothing calls them.

Consequences:

1. `current_state()` never returns `State.RENDERED`, so the `published`
   transition is unreachable and `episode-log.md` never gets entries.
2. The approval gate is **not technically enforced** — nothing prevents a
   render of an unapproved episode. `AGENTS.md` currently warns about
   this rather than claiming enforcement.
3. `serials/cyber-heist/ep-01-infiltration/` sits approved with a
   108 MB `preview.mp4` and no `final.mp4` — stuck mid-lifecycle.

## Change

Add a final-render writer that closes the `matched → rendered` transition.

### New: `scripts/render_final.py`

CLI: `python scripts/render_final.py --serial <slug> --ep <id>`

Behavior:

1. **Resolve episode** (`serials/<show>/<ep-id>/`) and read `spec.json`.
2. **Approval gate — hard requirement.** Refuse to render unless the
   `.approved` sentinel exists. Exit non-zero with a clear message
   otherwise. This is the point of the change: the gate becomes real.
3. **Idempotency.** If `rendered/final.mp4` exists:
   - If `rendered/spec.sha256` matches the current `spec.json` hash →
     no-op, exit 0 (report "already rendered").
   - If the hash differs → refuse. `final.mp4` is immutable by project
     policy; a changed spec requires a **remix** (new episode dir),
     not an overwrite.
4. **Immutability.** Never overwrite or delete an existing `final.mp4`.
   Write to a temporary path and `os.replace()` into place only after a
   successful render, so a failed render cannot leave a partial
   `final.mp4`.
5. **Render.** Build the ffmpeg command from `rendered/draft.json`
   (the Concat timeline already produced by `assemble_episode.py`):
   - video track clips concatenated in timeline order
   - `-c copy` for the fast path (no re-encode) when all sources share
     compatible codecs; fall back to a re-encode pass when ffmpeg rejects
     the copy
   - captions from the Concat timeline are **not** burned in by this
     writer — caption burn-in stays a Concat/CapCut polish step
   - output written to `rendered/.final.mp4.tmp`, then renamed to
     `rendered/final.mp4`
6. **Post-render.** Call `lifecycle.write_spec_sha(ep)` and
   `lifecycle.mark_rendered(ep)` so the filesystem state and the sentinel
   bookkeeping agree.
7. **Report.** Print the output path, size, duration (via `ffprobe`),
   and the spec sha256 that was recorded.

### New: MCP tool `render_final`

Add a third tool to `mcp-server/index.js`, alongside `assemble_episode`
and `open_in_concat`:

- name: `render_final`
- args: `serial`, `ep` (same slug validation as the existing tools)
- shells out to `scripts/render_final.py` and returns stdout/stderr
- surfaces a non-zero exit as `isError: true` with the script's message
  (so an approval-gate refusal is legible to the caller)

### New: `py/assemble/final_renderer.py`

Move the ffmpeg command construction and the render execution into the
package (not the script), so it is unit-testable and reusable:

- `build_ffmpeg_command(draft, output_path) -> list[str]`
- `render_final(timeline, output_path, *, ffmpeg_bin="ffmpeg") -> Path`
- `probe_duration(path, *, ffprobe_bin="ffprobe") -> float | None`

`scripts/render_final.py` stays a thin CLI wrapper, matching the existing
`scripts/assemble_episode.py` pattern.

## Boundaries

- **The approval gate becomes enforced** for the final-render path. This
  is the intended contract change.
- `preview.mp4` generation is **not** touched — `render_draft.py` keeps
  its current behavior (it is a draft preview, not a final asset).
- Caption burn-in, transitions beyond the draft timeline's declared
  values, audio mixing, and voiceover TTS remain **out of scope** —
  those are Concat/CapCut polish steps.
- `published` state (episode-log append) is **not** automated by this
  change. `lifecycle.publish()` already exists and stays manual /
  callable, but this change does not invoke it.
- No change to the `draft.json` schema.

## Validation

- `python scripts/render_final.py --serial cyber-heist --ep ep-01-infiltration`
  produces `rendered/final.mp4` (non-zero size) and
  `rendered/spec.sha256`
- Re-running the same command is a **no-op** (same spec hash) and does
  not rewrite the file (mtime unchanged)
- With `.approved` removed, the command **refuses** and exits non-zero
  with an approval-gate message
- With a mutated `spec.json` (hash mismatch) and an existing
  `final.mp4`, the command **refuses** and leaves `final.mp4` untouched
- `current_state()` for the rendered episode returns `State.RENDERED`
- `node mcp-server/test/concat_paths.test.js` still passes
- New unit tests for `build_ffmpeg_command`, approval-gate refusal,
  idempotent no-op, and hash-mismatch refusal
