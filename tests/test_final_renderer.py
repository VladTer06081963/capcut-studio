"""Tests for capcut.assemble.final_renderer — final.mp4 writer."""

from __future__ import annotations

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
            self.assertEqual(len(lines), 2)
            self.assertTrue(lines[0].startswith("file '"))
            self.assertIn("a.mp4", lines[0])


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
        # no temp file left behind
        leftovers = list(out.parent.glob(".final.mp4.tmp.mp4"))
        self.assertEqual(leftovers, [])

    def test_render_missing_source_raises(self) -> None:
        timeline = _make_timeline([self.tmp_path / "nope.mp4"])
        out = self.tmp_path / "out" / "final.mp4"
        with self.assertRaises(final_renderer.FinalRenderError) as ctx:
            final_renderer.render_final(timeline, out)
        self.assertIn("missing", str(ctx.exception).lower())
        self.assertFalse(out.exists())

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
        self.assertEqual(list(out.parent.glob(".final.mp4.tmp.mp4")), [])

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

    def _run(self, *extra: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["SERIALS_ROOT"] = str(self.tmp_path / "serials")
        env["PYTHONPATH"] = str(self.repo_root)
        return subprocess.run(
            [
                "python3",
                str(self.repo_root / "scripts" / "render_final.py"),
                "--serial", "test",
                "--ep", "ep-01",
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


if __name__ == "__main__":
    unittest.main()
