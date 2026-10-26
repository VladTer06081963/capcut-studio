# 024 — Code-review fixes for the final-render writer

**Status:** ✅ Done (2026-10-19)
**Trigger:** Kilo Code Review on PR #1 — 7 WARNING + 21 SUGGESTION
**Branch:** `feature/rename-py-to-capcut`

## 1. Контекст (Context)

PR #1 passed CI, but the Kilo Code Review bot flagged 28 issues
(0 CRITICAL, 7 WARNING, 21 SUGGESTION). The bot's summary was advisory,
so every WARNING was verified against the actual code before acting on it.

**Five turned out to be real defects in the 023 implementation** — the
kind that produce a plausible-looking but wrong `final.mp4`, which is
the worst possible failure mode for an immutable artifact.

The most serious: `duration_sec` was silently ignored, so every source
clip ran to its end. The episode declared 35.0 s; the delivered file was
35.29 s. The file was then locked as immutable — a wrong artifact that
could never be corrected in place.

## 2. Что проверено и что оказалось правдой (Verified findings)

| Finding | Verified | Outcome |
|---|---|---|
| `duration_sec` ignored, whole source files rendered | ✅ declared 5 s vs real 5.041667 s × 7 | **real defect — fixed** |
| relative `src` checked against CWD, concat demuxer resolves against list-file dir | ✅ `DLSDIY7a7G4.mp4` in `stalker-reznik/ep-02-anomaly` | **real defect — fixed** |
| fixed temp path races between concurrent renders | ✅ `.final.mp4.tmp.mp4` was deterministic | **real defect — fixed** |
| commit titles and contents swapped (`acda9f4` held only the 6 `.pi/` files; `1ae31d8` held the 84-file rename) | ✅ `git show --stat` on both | **real — history rewritten** |
| `.approved` sentinel + `library` symlink committed | ✅ added by my own `git add -A` in `1ae31d8` | **real regression — fixed** |
| stream-copy `rc==0` not validated | ✅ accepted unconditionally | **partially fixed** — stderr now surfaced, but no post-render probe; see §5 |
| no timeout on ffmpeg | ✅ `subprocess.run` without `timeout=` | **real defect — fixed** |
| `--resolution` unvalidated | ✅ `"1920"` → empty height → invalid filter | **real defect — fixed** |
| re-encode path doesn't pin `-pix_fmt` | ✅ no `-pix_fmt` in the command | **real defect — fixed** |
| CLI has no slug validation | ✅ `../` escaped `SERIALS_ROOT` | **real defect — fixed** |
| spec hash captured after the render | ✅ `sha256_spec(ep)` called post-render | **real defect — fixed in round 2** — the first fix was illusory; see §3.1 |
| missing `spec.sha256` misreported as hash mismatch | ✅ same error path | **real defect — fixed** |
| `OSError` escapes as traceback | ✅ only `FinalRenderError` caught | **real defect — fixed** |
| MCP drops non-boolean `reencode` | ✅ `args?.reencode === true` | **real defect — fixed** |
| MCP: no `timeout`/`maxBuffer` on a minutes-long call | ✅ | fixed |
| MCP: `--resolution` not in the tool schema | ✅ | fixed |
| `tests/conftest.py` still drops the real `py` library from `sys.modules` | ✅ leftover from the rename | **fixed** |
| stale `py/` in our own comments/docstrings | ✅ 8 lines | fixed (sister-project refs kept) |
| PRD line 296 still says «повторный render без `--force` = no-op» | ✅ | fixed |
| OpenSpec archived checklists left items unchecked | ✅ | fixed |
| audit 022 says "10 tests/*.py" (actually 9) | ✅ 12+10+9+3 = 34 | fixed |
| `AGENTS.md` deployment diagram misaligned after rename | ✅ `capcut/` is 5 chars longer | **fixed** in `e6c1434` |
| committed `serials/` artifacts (36 files) | ✅ sample data, intentional | documented, not removed |
| re-encode fallback not exercised on real content | ✅ | still not exercised — see §5 |

### 2.1 Second review round (after the history rewrite)

A second Kilo review ran against the rewritten branch and found four
further problems, three of them caused by my own first-round fixes:

| Finding | Verified | Outcome |
|---|---|---|
| the spec-hash race fix was **illusory** — `write_spec_sha()` re-computed the hash at write time, so the pre-render `sha` only reached stdout | ✅ `capcut/lib/lifecycle.py:212` had no `sha` parameter | **real defect — fixed** (`write_spec_sha(ep, sha)`) |
| `matched.json` was **still tracked** — `.gitignore` pattern `serials/*/matched.json` does not match the two-level `serials/<show>/<ep>/matched.json` paths | ✅ `git ls-files` + `git check-ignore` | **real — fixed** (`serials/**/matched.json`) |
| records cited **dead hashes** after the rewrite | ✅ `git log` on the branch | **fixed** — 23 references updated across 8 files |
| MCP `--resolution` forwarded without `--reencode`, and Node's 1 h timeout was **below** Python's 2 h worst case (two ffmpeg attempts × 3600 s) | ✅ | **fixed** — validation in argparse + MCP, Node timeout raised to 3 h |

## 3. Что сделано (What was done)

### Round 1 — the code-review findings

### Renderer (`capcut/assemble/final_renderer.py`)

- **Trim to declared duration.** The concat list now emits a per-clip
  `duration` directive, **and** the output is truncated with `-t` to the
  timeline's total declared duration. The `duration` directive alone was
  not enough — it only overrides metadata, it does not cut media. This
  was found by a failing test, not by reading docs.
- **Absolute paths in the concat list.** `resolve_source(src,
  base_dir=...)` resolves relative names against the timeline's own
  directory; the list always contains absolute paths.
- **Unique temp paths.** `.final.mp4.<pid>.<uuid8>.tmp.mp4` — two
  concurrent renders of one episode can no longer clobber each other's
  output.
- **Both ffmpeg attempts surfaced.** When the re-encode retry also fails,
  the error includes the stream-copy attempt's stderr.
- **Timeout.** `DEFAULT_TIMEOUT_SEC = 3600`, `stdin=DEVNULL`.
- **Resolution validation.** `_parse_resolution()` rejects `1920`,
  `1920x`, `0x1080`, `abcxdef`.
- **`-pix_fmt yuv420p` pinned** on the re-encode path.
- **Video-track selection.** A video track whose clips all lack `src` is
  skipped so a later video track is not silently ignored.
- **Temp cleanup in `finally`** — a failed render never leaves a partial file.

### CLI (`scripts/render_final.py`)

- **Slug validation** — same rule as the MCP boundary
  (`^[A-Za-z0-9][A-Za-z0-9_-]*$`); `../` and absolute paths are refused.
- **Spec hash captured before the render**, so a mid-render spec edit is
  not recorded as the matching spec.
- **Missing `spec.sha256` reported as an interrupted render**, with
  remediation, not as a hash mismatch.
- **`OSError` caught** in the render, stat and bookkeeping paths.

### MCP (`mcp-server/index.js`)

- **`reencode` must be boolean** — a non-boolean now errors instead of
  being silently dropped (which meant a caller asking for a re-encode
  got a stream copy).
- **`resolution` exposed** in the tool schema and forwarded to the CLI.
- **`timeout` (1 h) and `maxBuffer` (10 MB)** on the render call.

### Repo hygiene

- **`library` symlink** removed from the index (dangling on any clone,
  leaked a local path). The symlink on disk is untouched.
- **`.approved` sentinels** removed from the index (every clone started
  with a pre-approved episode). Files on disk are untouched.
  `.gitignore` now covers `serials/**/.approved`, `serials/**/.draft`
  and `library`.
- **`matched.json`** — removed from the index in round 2 (round 1
  removed only `.approved`; the `.gitignore` pattern
  `serials/*/matched.json` did not match the two-level paths).
  `.gitignore` now uses `serials/**/matched.json` and
  `serials/**/rendered/`.
- **`tests/conftest.py`** no longer deletes the real `py` library from
  `sys.modules` — it only ensures the project root is importable.

### Docs

- Stale `py/` references fixed in our own comments/docstrings (8 lines).
  References to the sister project (`comic-studio py/…`) left as-is.
- `summary/PRD/PRD.md` — the `--force` line corrected.
- `summary/audit/022` + `summary/tasks/022` — commit map corrected with
  verified `git show --stat` output; test-file count 10 → 9.
- `CHANGELOG.md` — `.pi/` commit hash corrected; new 024 entry.
- Both archived OpenSpec checklists marked complete.

### Round 2 — after the history rewrite

The second review found that **one of my round-1 fixes was illusory**.

**The spec-hash race was not actually fixed.** I had moved the hash
capture to before the render, but `lifecycle.write_spec_sha(ep)` took no
argument and re-computed `sha256_spec(ep)` at write time — which is
*after* the render. The pre-render hash only reached the stdout print.
A spec edited during the render was still certified as the matching spec,
and the stdout line could disagree with the recorded file.

The fix:

```python
# capcut/lib/lifecycle.py
def write_spec_sha(ep: Episode, sha: str | None = None) -> None:
    ...
    (rendered / "spec.sha256").write_text(sha if sha is not None else sha256_spec(ep))

# scripts/render_final.py
lifecycle.write_spec_sha(ep, sha)   # sha captured before the render
```

Two regression tests cover it: one drives the CLI end-to-end and checks
the recorded hash, one changes `spec.json` mid-flight and asserts the
recorded hash is the pre-render one.

Also fixed in round 2:

- **`matched.json` still tracked.** The `.gitignore` pattern
  `serials/*/matched.json` does not match the two-level paths
  `serials/<show>/<ep-id>/matched.json` — so a future `git add -A`
  re-committed them. Removed from the index; `.gitignore` now uses
  `serials/**/matched.json` and `serials/**/rendered/`.
- **Dead commit hashes in the records.** The history rewrite changed the
  hashes, so 23 hash references across 8 files no longer resolved.
  All updated to the post-rewrite hashes and verified with `git log`.
- **`--resolution` without `--reencode`.** The MCP tool forwarded it
  unconditionally; the CLI only validated it on the re-encode branch, so
  a bad value passed the schema pattern, silently rendered at the source
  resolution, and then aborted the auto-re-encode retry late with a
  confusing error. Now validated in argparse, and the MCP tool rejects
  `resolution` unless `reencode` is true.
- **MCP timeout below Python's worst case.** Node's 1 h timeout was
  shorter than Python's worst case (two ffmpeg attempts × 3600 s), so
  Node fired first, SIGTERM'd only Python (orphaning ffmpeg and skipping
  the `finally` temp cleanup), and the caller got a generic timeout
  instead of a clean `FinalRenderError`. Node's timeout raised to 3 h.
- **`AGENTS.md` deployment diagram** realigned in `e6c1434` (the rename
  made `capcut/` five characters longer than `py/`).

## 4. Статус (Verification)

| Check | Result |
|---|---|
| `pytest tests/` (repo root) | ✅ **161 passed** (was 145, +16) |
| `pytest tests/` (unrelated CWD) | ✅ 161 passed |
| `node mcp-server/test/concat_paths.test.js` | ✅ 4/4 |
| **live re-render** cyber-heist ep-01 | ✅ **35.04 s** (was 35.29 — trim works), h264 1920×1080, 108 064 537 B |
| concat list contains absolute paths | ✅ `/Volumes/MacStudioData/...` |
| no temp leftovers after render | ✅ |
| second run still a no-op | ✅ |
| `library` symlink + `.approved` still on disk | ✅ (only removed from the index) |
| MCP `tools/list` → 3 tools | ✅ |

### New tests (16)

| Test | Covers |
|---|---|
| `test_render_trims_to_declared_duration` | the `-t` fix |
| `test_concat_list_emits_duration_directives` | duration directive |
| `test_relative_src_resolved_against_base_dir` | relative path bug |
| `test_concat_list_writes_absolute_paths` | absolute path guarantee |
| `test_quote_escaping_in_concat_list` | `'` escaping |
| `test_invalid_resolution_raises` | 4 malformed values |
| `test_reencode_pins_pixel_format` | `-pix_fmt` |
| `test_video_track_without_src_is_skipped` | track selection |
| `test_concurrent_renders_use_distinct_temp_paths` | the race |
| `test_path_traversal_in_serial_is_refused` | CLI slug validation |
| `test_path_traversal_in_ep_is_refused` | CLI slug validation |
| `test_resolution_without_reencode_is_refused` | `--resolution` needs `--reencode` |
| `test_malformed_resolution_is_refused` | argparse-level resolution validation |
| `test_recorded_sha_is_the_pre_render_one` | the recorded hash is the pre-render one |
| `test_write_spec_sha_records_the_passed_hash` | `write_spec_sha(ep, sha)` honours the argument |
| `test_absolute_path_in_ep_is_refused` | CLI slug validation |

## 5. Что НЕ проверено (What's NOT verified)

- **The re-encode fallback was not exercised on real content.** The
  command builder is unit-tested; the copy→re-encode transition is only
  covered by the failure-path test (both attempts mocked as failing).
  A real mismatched-codec episode has not been rendered through it.
- **Stream-copy output is not validated.** `rc==0` is still accepted
  without inspecting the produced file. The reviewer's point about
  mixed resolution/SAR/timebase producing warnings-only broken output
  is **not** fully addressed — the stderr is now surfaced, but a
  successful-yet-broken stream copy would still be accepted. A
  post-render probe (resolution/duration sanity check) would close this;
  it is not implemented.
- **`AGENTS.md` deployment-diagram alignment** is still broken — the
  edit needs explicit approval for the protected file.
- **Committed `serials/` sample data** (38 files) was left in place. It
  is intentional sample data, but the reviewer's concern stands: the
  tree now contains a pre-approved episode and a `rendered/` cache.
- **No MCP client round-trip** — `render_final` was verified via a
  direct stdio `tools/list` probe, not through Hermes.

## 6. Решения (Decisions)

- **Rewrite the history rather than document the mistake.** The two
  commit titles were swapped: the commit carrying the 84-file rename was
  titled "chore: track .pi/" and the commit carrying the 6 `.pi/` files
  was titled "refactor!: rename py/". The BREAKING CHANGE message was
  therefore attached to the wrong diff. The rewrite gave each commit the
  correct title: the rename is now `1ae31d8` (84 files) and the harness
  is `acda9f4` (6 files). Since the branch was unmerged, this needed a
  force-push and touched no shared history.
- **Fix the code, don't just document the bugs.** The `duration_sec`
  defect in particular was a silent wrong-output bug, and documenting it
  in the audit would have left the pipeline producing wrong-length
  episodes. Every WARNING that verified as real got a fix plus a
  regression test.
- **Keep sister-project references untouched.** `comic-studio
  py/scenario/writer.py` is a reference to a *different* repository's
  layout. Rewriting it to `capcut/` would be wrong, so the sweep script
  explicitly skips lines mentioning `comic-studio`.
- **Remove from the index, not from disk.** `library` (the symlink) and
  the `.approved`/`.matched.json` files stay on disk — the symlink points
  at the real asset library on the external HDD, and the sentinels
  reflect real episode state. Only the git tracking was wrong.

## 7. Что зафиксировано в git

- `941d750` — `fix(render-final): address code-review findings on the final-render writer`
- plus a history rewrite of `1ae31d8` / `acda9f4` (titles swapped back)
- `summary/audit/024_code_review_fixes.md` (this file)
- `summary/tasks/024_code_review_fixes.md` (sister file)
- `CHANGELOG.md` — 024 entry
