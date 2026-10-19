# TODO 019: Complete first MCP-to-Concat experiment

**Status:** In progress; first episode assembled and exported, GUI result not
independently confirmed
**Date:** 2026-10-13
**Audit:** `summary/audit/019_concat_first_experiment.md`

## Completed

- [x] Connect Pi to the project `capcut-pipeline` MCP server and list its two
  tools without invoking them during discovery.
- [x] Verify Ollama embeddings at `/v1/embeddings` with
  `nomic-embed-text:latest`; confirm the local index contains usable
  768-dimensional embeddings.
- [x] Read-only inspect `cyber-heist/ep-01-infiltration`: seven valid scenes,
  approval sentinel present, seven matched scenes, and valid existing media
  references.
- [x] With explicit user approval, call `open_in_concat` once for that episode;
  create the Desktop `concat.json`.
- [x] Have Pi dispatch the exact existing `concat.json` to Concat.app once;
  command returned exit code 0. GUI display remains unverified.
- [x] Read-only compare draft and Concat JSON: seven clips, 35 seconds, matching
  timings, resolution, and media paths.
- [x] Fix the converter to propagate integer project FPS to both Concat video
  objects; verify with 3 unit tests and `py_compile`.
- [x] Add the MCP overwrite refusal/path forwarding and path helper tests; 4
  Node tests, syntax check, and diff check passed.

## Remaining

- [ ] Convert the existing draft to a temporary output path and read-validate
  24/1 FPS at both levels, unchanged clips/timings, and no changes to the
  existing Desktop project.
- [ ] If the temporary result is correct, ask the user before any new project
  creation or GUI open; do not overwrite the existing `concat.json`.
- [ ] Research Concat transition/fade format further only if implementing
  transition preservation; current local evidence does not establish the
  accepted nonzero transition schema.

## Fixation procedure

- [x] Audit and task records created.
- [x] Dated CHANGELOG entry added.
- [x] Reviewed active OpenSpec changes; both remain incomplete and were not
  archived.
- [ ] Git commit/push blocked: current checkout is `main`, one commit ahead of
  origin, with a large mixed worktree (106 changed/untracked paths). Isolate the
  intended files on a feature branch before any commit; never push to `main`.

## Boundaries

No `assemble_episode`, no overwrite of the current Concat project, no media
generation/provider API calls, no stage/commit/push, and no cleanup of the
existing dirty worktree without separate user authorization.
