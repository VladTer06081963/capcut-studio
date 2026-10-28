"""Tests for capcut.assemble.final_renderer — final.mp4 writer."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from capcut.assemble import final_renderer
from capcut.lib import lifecycle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source_clip(path: Path, seconds: int = 1) -> Path:
    """Create a tiny real mp4 via ffmpeg (solid color, no audio)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=blue:s=320x240:d={seconds}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(path),
        ],
        capture_output=True,
        check=True,
    )
    return path


def _make_timeline(clips: list[Path], *, resolution: str = "320x240") -> dict:
    return {
        "schema": 1,
        "project": {
            "name": "test-show-ep-01",
            "duration_sec": len(clips),
            "resolution": resolution,
            "fps": 24.0,
        },
        "tracks": [
            {
                "id": "video-main",
                "type": "video",
                "clips": [
                    {
                        "id": f"scene-{i}",
                        "src": str(c),
                        "start_sec": float(i),
                        "duration_sec": 1.0,
                        "caption": None,
                        "voiceover": None,
                        "transition_in": "cut",
                        "transition_out": "cut",
                    }
                    for i, c in enumerate(clips)
                ],
            }
        ],
        "unmatched_scenes": [],
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------

class BuildFfmpegCommandTest(unittest.TestCase):
    def test_stream_copy_path(self) -> None:
        timeline = _make_timeline([Path("/tmp/a.mp4")])
        cmd = final_renderer.build_ffmpeg_command(
            timeline, Path("/tmp/out.mp4")
        )
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-f", cmd)
        self.assertIn("concat", cmd)
        self.assertIn("copy", cmd)
        self.assertTrue(cmd[-1].endswith("out.mp4"))

    def test_reencode_path_has_scale_filter(self) -> None:
        timeline = _make_timeline([Path("/tmp/a.mp4")], resolution="640x480")
        cmd = final_renderer.build_ffmpeg_command(
            timeline, Path("/tmp/out.mp4"), reencode=True
        )
        self.assertIn("libx264", cmd)
        self.assertIn("-vf", cmd)
        vf = cmd[cmd.index("-vf") + 1]
        self.assertIn("640:480", vf)
        self.assertNotIn("copy", cmd)

    def test_no_video_clips_raises(self) -> None:
        timeline = {"project": {}, "tracks": []}
        with self.assertRaises(final_renderer.FinalRenderError):
            final_renderer.build_ffmpeg_command(timeline, Path("/tmp/out.mp4"))

    def test_clips_without_src_are_skipped(self) -> None:
        timeline = {
            "project": {},
            "tracks": [
                {
                    "type": "video",
                    "clips": [
                        {"id": "a", "src": None},
                        {"id": "b", "src": "/tmp/b.mp4"},
                    ],
                }
            ],
        }
        clips = final_renderer._video_clips(timeline)
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0]["id"], "b")


class ConcatListTest(unittest.TestCase):
    def test_writes_one_file_line_per_clip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "list.txt"
            timeline = _make_timeline([Path("/tmp/a.mp4"), Path("/tmp/b.mp4")])
            final_renderer.build_concat_list(timeline, out)
            lines = out.read_text().strip().splitlines()
            file_lines = [ln for ln in lines if ln.startswith("file '")]
            self.assertEqual(len(file_lines), 2)
            self.assertTrue(file_lines[0].startswith("file '"))
            self.assertIn("a.mp4", file_lines[0])


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

class RenderFinalTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self._tmp)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_render_produces_nonempty_output(self) -> None:
        clip = _make_source_clip(self.tmp_path / "src" / "a.mp4")
        timeline = _make_timeline([clip])
        out = self.tmp_path / "out" / "final.mp4"
        final_renderer.render_final(timeline, out)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)
        # no temp file left behind (temp name now carries pid+uuid)
        leftovers = list(out.parent.glob(".final.mp4.*.tmp.mp4"))
        self.assertEqual(leftovers, [])

    def test_render_trims_to_declared_duration(self) -> None:
        """A 5s source declared as 2s must produce a ~2s output, not 5s."""
        clip = _make_source_clip(self.tmp_path / "src" / "a.mp4", seconds=5)
        timeline = _make_timeline([clip])
        timeline["tracks"][0]["clips"][0]["duration_sec"] = 2.0
        out = self.tmp_path / "out" / "final.mp4"
        final_renderer.render_final(timeline, out)
        duration = final_renderer.probe_duration(out)
        assert duration is not None
        self.assertLess(duration, 3.5)
        self.assertGreater(duration, 1.0)

    def test_concat_list_emits_duration_directives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "list.txt"
            timeline = _make_timeline([Path("/tmp/a.mp4")])
            timeline["tracks"][0]["clips"][0]["duration_sec"] = 3.5
            final_renderer.build_concat_list(timeline, out)
            lines = out.read_text().strip().splitlines()
            self.assertIn("duration 3.5", lines)

    def test_relative_src_resolved_against_base_dir(self) -> None:
        """A bare filename must resolve relative to the timeline dir, not CWD."""
        clip = _make_source_clip(self.tmp_path / "media" / "clip.mp4")
        timeline = _make_timeline([Path("clip.mp4")])
        out = self.tmp_path / "out" / "final.mp4"
        final_renderer.render_final(
            timeline, out, base_dir=self.tmp_path / "media"
        )
        self.assertTrue(out.exists())

    def test_concat_list_writes_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / "list.txt"
            timeline = _make_timeline([Path("clip.mp4")])
            final_renderer.build_concat_list(timeline, out, base_dir=base)
            content = out.read_text()
            self.assertIn(str(base / "clip.mp4"), content)

    def test_quote_escaping_in_concat_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / "list.txt"
            odd = base / "it's a clip.mp4"
            odd.touch()
            timeline = _make_timeline([odd])
            final_renderer.build_concat_list(timeline, out, base_dir=base)
            content = out.read_text()
            # the single quote must be escaped as '\'' for the concat demuxer
            self.assertIn(r"it'\''s a clip.mp4", content)

    def test_render_missing_source_raises(self) -> None:
        timeline = _make_timeline([self.tmp_path / "nope.mp4"])
        out = self.tmp_path / "out" / "final.mp4"
        with self.assertRaises(final_renderer.FinalRenderError) as ctx:
            final_renderer.render_final(timeline, out)
        self.assertIn("missing", str(ctx.exception).lower())
        self.assertFalse(out.exists())

    def test_invalid_resolution_raises(self) -> None:
        timeline = _make_timeline([Path("/tmp/a.mp4")])
        for bad in ("1920", "1920x", "0x1080", "abcxdef"):
            with self.assertRaises(final_renderer.FinalRenderError):
                final_renderer.build_ffmpeg_command(
                    timeline,
                    Path("/tmp/out.mp4"),
                    reencode=True,
                    resolution=bad,
                )

    def test_reencode_pins_pixel_format(self) -> None:
        timeline = _make_timeline([Path("/tmp/a.mp4")])
        cmd = final_renderer.build_ffmpeg_command(
            timeline, Path("/tmp/out.mp4"), reencode=True
        )
        self.assertIn("-pix_fmt", cmd)
        self.assertEqual(cmd[cmd.index("-pix_fmt") + 1], "yuv420p")

    def test_video_track_without_src_is_skipped(self) -> None:
        """A video track whose clips all lack src must not shadow a later one."""
        timeline = {
            "project": {},
            "tracks": [
                {"type": "video", "clips": [{"id": "a", "src": None}]},
                {"type": "video", "clips": [{"id": "b", "src": "/tmp/b.mp4"}]},
            ],
        }
        clips = final_renderer._video_clips(timeline)
        self.assertEqual([c["id"] for c in clips], ["b"])

    def test_failed_ffmpeg_leaves_no_partial_output(self) -> None:
        clip = _make_source_clip(self.tmp_path / "src" / "a.mp4")
        timeline = _make_timeline([clip])
        out = self.tmp_path / "out" / "final.mp4"
        with patch.object(final_renderer.subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="boom"
            )
            with self.assertRaises(final_renderer.FinalRenderError):
                final_renderer.render_final(timeline, out)
        self.assertFalse(out.exists())
        self.assertEqual(list(out.parent.glob(".final.mp4.*.tmp.mp4")), [])

    def test_concurrent_renders_use_distinct_temp_paths(self) -> None:
        """Two renders of the same episode must not share a temp path."""
        clip = _make_source_clip(self.tmp_path / "src" / "a.mp4")
        timeline = _make_timeline([clip])
        out = self.tmp_path / "out" / "final.mp4"
        seen: list[str] = []
        real_replace = os.replace

        def spy(src, dst):
            seen.append(str(src))
            return real_replace(src, dst)

        with patch.object(final_renderer.os, "replace", side_effect=spy):
            final_renderer.render_final(timeline, out)
            out.unlink()
            final_renderer.render_final(timeline, out)
        self.assertEqual(len(seen), 2)
        self.assertNotEqual(seen[0], seen[1])

    def test_probe_duration_reads_actual_duration(self) -> None:
        clip = _make_source_clip(self.tmp_path / "src" / "a.mp4", seconds=2)
        duration = final_renderer.probe_duration(clip)
        assert duration is not None
        self.assertGreater(duration, 1.0)

    def test_probe_duration_none_for_missing_file(self) -> None:
        self.assertIsNone(
            final_renderer.probe_duration(self.tmp_path / "missing.mp4")
        )


# ---------------------------------------------------------------------------
# CLI: approval gate + idempotency + immutability
# ---------------------------------------------------------------------------

class RenderFinalCliTest(unittest.TestCase):
    """End-to-end CLI checks for scripts/render_final.py.

    Invoked as a subprocess so the real approval gate and filesystem
    state machine are exercised (not mocked).
    """

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self._tmp)
        self.repo_root = Path(__file__).resolve().parents[1]
        self.ep_dir = self.tmp_path / "serials" / "test" / "ep-01"
        (self.ep_dir / "rendered").mkdir(parents=True)
        (self.ep_dir / "brief.md").write_text("# test")
        (self.ep_dir / "spec.json").write_text('{"scenes": []}')
        self.clip = _make_source_clip(self.tmp_path / "src" / "a.mp4")
        timeline = _make_timeline([self.clip])
        (self.ep_dir / "rendered" / "draft.json").write_text(
            json.dumps(timeline)
        )

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run(
        self, *extra: str, serial: str = "test", ep: str = "ep-01"
    ) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["SERIALS_ROOT"] = str(self.tmp_path / "serials")
        env["PYTHONPATH"] = str(self.repo_root)
        return subprocess.run(
            [
                "python3",
                str(self.repo_root / "scripts" / "render_final.py"),
                "--serial", serial,
                "--ep", ep,
                *extra,
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(self.repo_root),
        )

    def test_refuses_without_approval(self) -> None:
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("approval gate", proc.stderr.lower())
        self.assertFalse((self.ep_dir / "rendered" / "final.mp4").exists())

    def test_renders_when_approved(self) -> None:
        (self.ep_dir / ".approved").touch()
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        final = self.ep_dir / "rendered" / "final.mp4"
        self.assertTrue(final.exists())
        self.assertGreater(final.stat().st_size, 0)
        self.assertTrue((self.ep_dir / "rendered" / "spec.sha256").exists())

    def test_second_run_is_idempotent_noop(self) -> None:
        (self.ep_dir / ".approved").touch()
        first = self._run()
        self.assertEqual(first.returncode, 0, first.stderr)
        final = self.ep_dir / "rendered" / "final.mp4"
        mtime = final.stat().st_mtime_ns
        size = final.stat().st_size

        second = self._run()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("no-op", second.stdout.lower())
        self.assertEqual(final.stat().st_mtime_ns, mtime)
        self.assertEqual(final.stat().st_size, size)

    def test_changed_spec_refuses_and_keeps_final(self) -> None:
        (self.ep_dir / ".approved").touch()
        self.assertEqual(self._run().returncode, 0)
        final = self.ep_dir / "rendered" / "final.mp4"
        mtime = final.stat().st_mtime_ns
        size = final.stat().st_size

        # mutate the spec → hash mismatch
        (self.ep_dir / "spec.json").write_text('{"scenes": ["changed"]}')
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("immutable", proc.stderr.lower())
        self.assertEqual(final.stat().st_mtime_ns, mtime)
        self.assertEqual(final.stat().st_size, size)

    def test_missing_draft_is_refused(self) -> None:
        (self.ep_dir / ".approved").touch()
        (self.ep_dir / "rendered" / "draft.json").unlink()
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("draft.json", proc.stderr)

    def test_path_traversal_in_serial_is_refused(self) -> None:
        """`--serial ../../etc` must not escape SERIALS_ROOT."""
        proc = self._run(serial="../../etc")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid serial", proc.stderr.lower())

    def test_path_traversal_in_ep_is_refused(self) -> None:
        proc = self._run(ep="../../../etc/passwd")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid episode id", proc.stderr.lower())

    def test_absolute_path_in_ep_is_refused(self) -> None:
        proc = self._run(ep="/etc")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid episode id", proc.stderr.lower())

    def test_resolution_without_reencode_is_refused(self) -> None:
        """--resolution only affects the re-encode path; using it alone
        would silently render at the source resolution."""
        (self.ep_dir / ".approved").touch()
        proc = self._run("--resolution", "1920x1080")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("only applies to the re-encode", proc.stderr.lower())

    def test_malformed_resolution_is_refused(self) -> None:
        (self.ep_dir / ".approved").touch()
        proc = self._run("--reencode", "--resolution", "0x1080")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid resolution", proc.stderr.lower())
        self.assertFalse((self.ep_dir / "rendered" / "final.mp4").exists())

    def test_failed_render_leaves_the_episode_retryable(self) -> None:
        """A failed render must not strand the episode.

        `final.mp4` is immutable. If it were published before the spec hash
        was recorded, a bookkeeping failure would leave an episode that no
        later run can render: final.mp4 present, spec.sha256 missing, and
        the CLI refusing with "the render was interrupted before its spec
        hash was recorded". The hash is therefore recorded *before* the
        render, so a failed render leaves the episode cleanly retryable.
        """
        (self.ep_dir / ".approved").touch()

        # First run: a fake ffmpeg that always fails.
        fake_bin = self.tmp_path / "fakebin"
        fake_bin.mkdir(exist_ok=True)
        fake_ffmpeg = fake_bin / "ffmpeg"
        fake_ffmpeg.write_text("#!/bin/sh\nexit 1\n")
        fake_ffmpeg.chmod(0o755)

        env = dict(os.environ)
        env["SERIALS_ROOT"] = str(self.tmp_path / "serials")
        env["PYTHONPATH"] = str(self.repo_root)
        env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

        failed = subprocess.run(
            [
                "python3",
                str(self.repo_root / "scripts" / "render_final.py"),
                "--serial", "test",
                "--ep", "ep-01",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(self.repo_root),
        )
        self.assertNotEqual(failed.returncode, 0)
        # No final.mp4 was published...
        self.assertFalse((self.ep_dir / "rendered" / "final.mp4").exists())
        # ...but the hash was recorded up-front, so nothing is stranded.
        self.assertTrue((self.ep_dir / "rendered" / "spec.sha256").exists())

        # Second run with the real ffmpeg: the episode renders normally.
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((self.ep_dir / "rendered" / "final.mp4").exists())

    def test_recorded_sha_is_the_pre_render_one(self) -> None:
        """The recorded spec.sha256 must describe the spec that was
        rendered -- not whatever landed on disk afterwards.

        The CLI runs as a separate process, so the mutation is injected
        through a fake `ffmpeg` on PATH: the shim rewrites spec.json
        (simulating an edit landing while the render is running) and
        then exits successfully. The test therefore fails if
        write_spec_sha() re-computes the hash at write time instead of
        recording the pre-render one.
        """
        (self.ep_dir / ".approved").touch()
        spec_path = self.ep_dir / "spec.json"
        original = spec_path.read_text()

        env = dict(os.environ)
        env["SERIALS_ROOT"] = str(self.tmp_path / "serials")
        env["PYTHONPATH"] = str(self.repo_root)
        fake_bin = self.tmp_path / "fakebin"
        fake_bin.mkdir(exist_ok=True)
        fake_ffmpeg = fake_bin / "ffmpeg"
        fake_ffmpeg.write_text(
            "#!/bin/sh\n"
            f"printf '{{\"scenes\": [\"edited mid-render\"]}}' > '{spec_path}'\n"
            # POSIX-safe way to reach the last argument: the shim has to
            # write its output to the output path, which is the final argv
            # entry. "${@: -1}" is a bashism — /bin/sh is dash on Linux,
            # where it fails with "Bad substitution".
            "for last_arg; do :; done\n"
            "printf 'fake' > \"$last_arg\"\n"
            "exit 0\n"
        )
        fake_ffmpeg.chmod(0o755)
        env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

        proc = subprocess.run(
            [
                "python3",
                str(self.repo_root / "scripts" / "render_final.py"),
                "--serial", "test",
                "--ep", "ep-01",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(self.repo_root),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        recorded = (self.ep_dir / "rendered" / "spec.sha256").read_text().strip()
        post_render = lifecycle.sha256_spec(
            lifecycle.Episode(show="test", ep_id="ep-01", path=self.ep_dir)
        )
        # The recorded hash must NOT be the post-render hash.
        self.assertNotEqual(recorded, post_render)
        self.assertEqual(
            recorded,
            hashlib.sha256(original.encode("utf-8")).hexdigest(),
        )


# ---------------------------------------------------------------------------
# Lifecycle integration
# ---------------------------------------------------------------------------

class RenderedStateTest(unittest.TestCase):
    def test_final_mp4_moves_state_to_rendered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(lifecycle, "SERIALS_ROOT", root):
                ep = lifecycle.Episode.locate("test", "ep-01")
                ep.path.mkdir(parents=True)
                (ep.path / "spec.json").write_text('{"scenes": []}')
                lifecycle.approve(ep)
                self.assertEqual(
                    lifecycle.current_state(ep), lifecycle.State.APPROVED
                )

                (ep.path / "rendered").mkdir()
                (ep.path / "rendered" / "final.mp4").write_bytes(b"x" * 32)
                lifecycle.write_spec_sha(ep)
                lifecycle.mark_rendered(ep)

                self.assertEqual(
                    lifecycle.current_state(ep), lifecycle.State.RENDERED
                )
                self.assertTrue(lifecycle.is_rendered(ep))
                self.assertTrue(lifecycle.is_idempotent_render(ep))

    def test_write_spec_sha_records_the_passed_hash(self) -> None:
        """A spec edited after the render must not be certified as the
        rendered spec -- the caller passes the pre-render hash."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(lifecycle, "SERIALS_ROOT", root):
                ep = lifecycle.Episode.locate("test", "ep-01")
                ep.path.mkdir(parents=True)
                spec = ep.path / "spec.json"
                spec.write_text('{"scenes": []}')
                pre_render_sha = lifecycle.sha256_spec(ep)

                # the spec changes mid-render
                spec.write_text('{"scenes": ["changed"]}')
                lifecycle.write_spec_sha(ep, pre_render_sha)

                recorded = (ep.path / "rendered" / "spec.sha256").read_text().strip()
                self.assertEqual(recorded, pre_render_sha)
                self.assertNotEqual(recorded, lifecycle.sha256_spec(ep))


if __name__ == "__main__":
    unittest.main()
