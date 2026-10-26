# Tasks: Final-render writer (`rendered/final.mp4`) with approval gate

## 1. Package module

- [ ] `py/assemble/final_renderer.py` (→ `capcut/assemble/final_renderer.py`
      after the rename lands; implement under whichever name is current)
  - [ ] `build_ffmpeg_command(draft, output_path) -> list[str]`
  - [ ] `render_final(timeline, output_path, *, ffmpeg_bin="ffmpeg") -> Path`
        — writes to a temp path, `os.replace()` into place only on success
  - [ ] `probe_duration(path, *, ffprobe_bin="ffprobe") -> float | None`

## 2. CLI wrapper

- [ ] `scripts/render_final.py --serial <slug> --ep <id>`
  - [ ] resolve episode dir, load `spec.json`
  - [ ] **approval gate**: refuse without `.approved`, exit non-zero
  - [ ] **idempotency**: existing `final.mp4` + matching `spec.sha256` →
        no-op, exit 0
  - [ ] **immutability**: existing `final.mp4` + hash mismatch → refuse,
        exit non-zero, leave file untouched
  - [ ] render via `final_renderer`
  - [ ] post-render: `write_spec_sha()` + `mark_rendered()`
  - [ ] report path, size, duration, sha256

## 3. MCP tool

- [ ] `mcp-server/index.js`: add `render_final` tool
  - [ ] same `serial`/`ep` slug validation as existing tools
  - [ ] shell out to `scripts/render_final.py`
  - [ ] non-zero exit → `isError: true` with the script's message
  - [ ] update the tool-list description / count references

## 4. Tests

- [ ] `tests/test_final_renderer.py`
  - [ ] `build_ffmpeg_command` produces correct arg order and concat file
  - [ ] approval-gate refusal (no `.approved`)
  - [ ] idempotent no-op on second run (mtime unchanged)
  - [ ] hash-mismatch refusal leaves `final.mp4` untouched
  - [ ] render writes non-empty output
- [ ] `tests/test_lifecycle.py` — extend to cover the new
      `matched → rendered` transition via the real writer

## 5. Live verification on the stuck episode

- [ ] `serials/cyber-heist/ep-01-infiltration` (approved, preview.mp4 present)
  - [ ] `python scripts/render_final.py --serial cyber-heist --ep ep-01-infiltration`
  - [ ] verify `rendered/final.mp4` exists, non-zero, correct duration
  - [ ] verify `current_state()` → `State.RENDERED`
  - [ ] verify second run is a no-op
  - [ ] verify refusal when `.approved` is temporarily removed

## 6. Documentation

- [ ] `AGENTS.md` — update the "Approval gate (policy)" and
      "`rendered/final.mp4` is immutable" paragraphs: the gate is now
      **enforced** by `scripts/render_final.py`
- [ ] `AGENTS.md` — project layout: add `render_final.py` to the run table
- [ ] `README.md` / `README_RU.md` — mention the final-render CLI
- [ ] `summary/audit/023_final_render_writer.md`
- [ ] `summary/tasks/023_final_render_writer.md`
- [ ] `CHANGELOG.md` entry
- [ ] archive `openspec/changes/final-render-writer/` →
      `openspec/changes/archive/2026-10-19-final-render-writer/`
- [ ] git commit + push on a feature branch, then merge to `main`
