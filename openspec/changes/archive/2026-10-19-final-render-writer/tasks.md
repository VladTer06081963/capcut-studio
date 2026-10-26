# Tasks: Final-render writer (`rendered/final.mp4`) with approval gate

## 1. Package module

- [x] `capcut/assemble/final_renderer.py` (implemented under the post-rename name)
  - [x] `build_ffmpeg_command(draft, output_path) -> list[str]`
  - [x] `render_final(timeline, output_path, *, ffmpeg_bin="ffmpeg") -> Path`
        — writes to a unique temp path, `os.replace()` into place only on success
  - [x] `probe_duration(path, *, ffprobe_bin="ffprobe") -> float | None`
  - [x] `build_concat_list(...)` — absolute paths + per-clip `duration` directives
  - [x] `resolve_source(src, *, base_dir)` — relative names resolved against
        the timeline dir, not the CWD

## 2. CLI wrapper

- [x] `scripts/render_final.py --serial <slug> --ep <id>`
  - [x] resolve episode dir, load `spec.json`
  - [x] slug validation (no traversal out of `SERIALS_ROOT`)
  - [x] **approval gate**: refuse without `.approved`, exit non-zero
  - [x] **idempotency**: existing `final.mp4` + matching `spec.sha256` →
        no-op, exit 0
  - [x] **immutability**: existing `final.mp4` + hash mismatch → refuse,
        exit non-zero, leave file untouched
  - [x] render via `final_renderer`
  - [x] post-render: `write_spec_sha()` + `mark_rendered()`
  - [x] report path, size, duration, sha256

## 3. MCP tool

- [x] `mcp-server/index.js`: add `render_final` tool
  - [x] same `serial`/`ep` slug validation as existing tools
  - [x] shell out to `scripts/render_final.py`
  - [x] non-zero exit → `isError: true` with the script's message
  - [x] update the tool-list description / count references
  - [x] `reencode` must be boolean; `resolution` exposed in the schema

## 4. Tests

- [x] `tests/test_final_renderer.py`
  - [x] `build_ffmpeg_command` produces correct arg order and concat file
  - [x] approval-gate refusal (no `.approved`)
  - [x] idempotent no-op on second run (mtime unchanged)
  - [x] hash-mismatch refusal leaves `final.mp4` untouched
  - [x] render writes non-empty output
  - [x] trim to declared duration (`-t`), not full source length
  - [x] relative `src` resolution + absolute paths in the concat list
  - [x] single-quote escaping
  - [x] malformed resolution rejected
  - [x] `-pix_fmt yuv420p` pinned on the re-encode path
  - [x] distinct temp paths for concurrent renders
  - [x] path-traversal refusal in `--serial` / `--ep`
- [x] `tests/test_lifecycle.py` — extended to cover the new
      `matched → rendered` transition via the real writer

## 5. Live verification on the stuck episode

- [x] `serials/cyber-heist/ep-01-infiltration` (approved, preview.mp4 present)
  - [x] `python scripts/render_final.py --serial cyber-heist --ep ep-01-infiltration`
  - [x] verify `rendered/final.mp4` exists, non-zero, correct duration
  - [x] verify `current_state()` → `State.RENDERED`
  - [x] verify second run is a no-op
  - [x] verify refusal when `.approved` is temporarily removed

## 6. Documentation

- [x] `AGENTS.md` — update the "Approval gate (policy)" and
      "`rendered/final.mp4` is immutable" paragraphs: the gate is now
      **enforced** by `scripts/render_final.py` (commit `794d811`)
- [x] `AGENTS.md` — project layout: add `render_final.py` to the run table
- [x] `README.md` / `README_RU.md` — mention the final-render CLI
- [x] `summary/audit/023_final_render_writer.md`
- [x] `summary/tasks/023_final_render_writer.md`
- [x] `CHANGELOG.md` entry
- [x] archive `openspec/changes/final-render-writer/` →
      `openspec/changes/archive/2026-10-19-final-render-writer/`
- [x] git commit + push on a feature branch (PR #1)
- [ ] merge to `main` — PR #1 open, merge pending
