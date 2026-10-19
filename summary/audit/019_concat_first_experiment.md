# Audit 019: First CapCut Studio MCP-to-Concat experiment

**Date:** 2026-10-13
**Scope:** Verify the first assembled episode, the generated Concat project,
and the FPS conversion fix. No media generation or external provider API calls.

## Verified pipeline state

- Pi 1.1.0 and `pi-mcp-adapter` 5.2.0 were reported by the user. The project
  `.mcp.json` registers `capcut-pipeline`; Pi connected live and listed two
  tools.
- Ollama's OpenAI-compatible embeddings endpoint responded successfully for
  `nomic-embed-text:latest` with a 768-dimensional vector. The local library
  index contains 12 clips, 11 with embeddings, stored as 768-dimensional
  float32 vectors.
- `serials/cyber-heist/ep-01-infiltration/spec.json` is a valid seven-scene
  episode. Its approval sentinel exists. The existing `matched.json` has
  matches for all seven scenes; the seven references resolve to five existing
  source files.
- The existing `rendered/draft.json` contains seven clips spanning 35 seconds,
  with no unmatched scenes, warnings, or missing source files.
- The user explicitly approved one `open_in_concat` call for
  `cyber-heist/ep-01-infiltration`. It created
  `~/Desktop/Concat/cyber-heist-ep-01-infiltration/concat.json` and reported
  opening Concat.app. The user then asked Pi to run `open -a Concat.app` once
  with that exact file; Pi reported exit code 0 and empty stdout/stderr.
- Read-only comparison reported seven clips and 35 seconds in both JSON files,
  matching starts, durations, resolution, and existing media paths. The
  generated Concat project uses 30 fps while the draft specifies 24 fps.
- GUI loading/rendering was not independently confirmed. The `open` exit code
  confirms dispatch to Launch Services, not successful project display.

## Changes and validation

- `scripts/convert_draft.py` now reads `project.fps` and writes the resulting
  `rateNum` / `rateDen` at both Concat video levels. Missing/invalid/nonpositive
  FPS falls back to 30/1. The current helper rounds to an integer; fractional
  rates such as 23.976 are not preserved.
- `tests/test_convert_draft.py` covers clip conversion, propagation of 24/1 to
  both levels, and the 30/1 fallback. `python3 -m unittest
  tests.test_convert_draft -v` passed all 3 tests; `python3 -m py_compile
  scripts/convert_draft.py` passed.
- `mcp-server/index.js` has pre-existing working-tree hardening and a scoped
  `open_in_concat` update: refuse to overwrite an existing `concat.json`, and
  pass the new project path to `open`. `mcp-server/lib/concat_paths.js` and
  `mcp-server/test/concat_paths.test.js` provide pure path construction and 4
  passing Node tests; `node --check mcp-server/index.js` and `git diff --check`
  passed.
- The current Concat project on Desktop predates the FPS fix and remains 30 fps.
  It has not been regenerated after the fix. The `open_in_concat` guard now
  refuses to overwrite it.
- Fade/transition fields, captions/voiceover mapping, and media deduplication
  were not changed. Local Concat evidence confirms names such as `fadeIn`,
  `fadeOut`, and `transitionIn`, but does not confirm nonzero fade behavior or
  the transition object format.

## Next safe step

Use a temporary output path to convert the existing draft and read-validate the
result: both video objects should be 24/1, clip count and timings should remain
unchanged, and the existing Desktop Concat project must remain untouched. Do
not call `assemble_episode` or `open_in_concat` for this episode unless the user
explicitly approves the exact write/open action. Do not try to overwrite the
existing Concat project.

After that isolated check, decide whether to create a separate Concat project
for GUI review. Keep any approval scoped to the exact path and action.

## Fixation and worktree

- No changes were staged, committed, or pushed. The repository already had
  numerous unrelated modified, deleted, and untracked files; preserve them.
- The existing project also has unrelated local media/artifacts. Do not clean
  or use `git add .`.
- `summary/FIXATION.md` is now available and was reviewed. This audit and
  `summary/tasks/019_concat_first_experiment.md` record the work; `CHANGELOG.md`
  has a dated entry.
- OpenSpec changes `hybrid-media-workflow` and `pi-project-agent` are still
  incomplete, so neither was archived.
- The Git step is blocked for safety: the checkout is on `main`, which is one
  local commit ahead of `origin/main`, and the worktree contains 106 changed or
  untracked paths. No files were staged; do not commit or push until the
  in-scope files are isolated on a branch without including unrelated work.
