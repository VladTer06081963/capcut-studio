"""Tests for capcut.lib.media — metadata path convention + atomic downloads.

Two invariants are covered here:

* every producer and consumer of a media file agrees on the sibling
  metadata path (`<name>.mp4.metadata.json`);
* a download that does not complete never publishes a file under a valid
  name, and never destroys a good file that is already there.
"""

from __future__ import annotations

import gzip
import shutil
import tempfile
import unittest
from pathlib import Path

from capcut.lib import media


REPO_ROOT = Path(__file__).resolve().parents[1]

# Every module that writes or reads a sibling metadata file. A producer that
# invents its own filename makes its assets invisible to the index: no
# source, no license, no tags, and the clip can never be matched back.
METADATA_PRODUCERS = (
    "scripts/generate_ai_clips.py",
    "capcut/ingest/youtube.py",
    "capcut/ingest/archive.py",
    "capcut/ingest/coverr.py",
    "capcut/ingest/mixkit.py",
    "capcut/index/embedder.py",
)


class _FakeResponse:
    """Minimal stand-in for a `requests` streaming response."""

    def __init__(
        self,
        chunks: list[bytes],
        *,
        content_length: int | None = None,
        raise_at: int | None = None,
    ) -> None:
        self._chunks = chunks
        self._raise_at = raise_at
        self.headers: dict[str, str] = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def iter_content(self, chunk_size: int = 1):
        for i, chunk in enumerate(self._chunks):
            if self._raise_at is not None and i == self._raise_at:
                raise OSError("connection reset by peer")
            yield chunk


class MetadataPathTest(unittest.TestCase):
    def test_path_is_sibling_with_metadata_json_suffix(self) -> None:
        got = media.metadata_path_for(Path("/lib/ai/scene.mp4"))
        self.assertEqual(got, Path("/lib/ai/scene.mp4.metadata.json"))

    def test_extension_is_preserved(self) -> None:
        got = media.metadata_path_for(Path("/lib/stock/clip.mov"))
        self.assertEqual(got, Path("/lib/stock/clip.mov.metadata.json"))

    def test_every_producer_uses_the_shared_convention(self) -> None:
        """Guard against a producer reintroducing its own filename.

        This is a source-level check on purpose: the bug it prevents is
        exactly the kind that no unit test of the producer would catch —
        the file is written happily, it is simply never read.
        """
        for rel in METADATA_PRODUCERS:
            path = REPO_ROOT / rel
            self.assertTrue(path.exists(), f"{rel} does not exist")
            source = path.read_text(encoding="utf-8")
            self.assertIn(
                "metadata_path_for(",
                source,
                f"{rel} must build the metadata path via "
                f"capcut.lib.media.metadata_path_for()",
            )
            self.assertNotIn(
                '.suffix + ".metadata.json"',
                source,
                f"{rel} still hardcodes the metadata filename",
            )


class AtomicDownloadTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _partials(self) -> list[str]:
        return sorted(p.name for p in self.tmp.iterdir() if p.name.endswith(".part"))

    def test_successful_download_writes_target_and_leaves_no_temp(self) -> None:
        target = self.tmp / "clip.mp4"
        result = media.atomic_download(
            _FakeResponse([b"abc", b"def"], content_length=6), target
        )
        self.assertEqual(result, target)
        self.assertEqual(target.read_bytes(), b"abcdef")
        self.assertEqual(self._partials(), [])

    def test_creates_missing_parent_directory(self) -> None:
        target = self.tmp / "nested" / "deep" / "clip.mp4"
        media.atomic_download(_FakeResponse([b"x"], content_length=1), target)
        self.assertTrue(target.exists())

    def test_empty_body_raises_and_publishes_nothing(self) -> None:
        target = self.tmp / "clip.mp4"
        with self.assertRaises(media.DownloadError) as ctx:
            media.atomic_download(_FakeResponse([]), target)
        self.assertIn("empty response body", str(ctx.exception))
        self.assertFalse(target.exists())
        self.assertEqual(self._partials(), [])

    def test_truncated_body_raises_and_publishes_nothing(self) -> None:
        target = self.tmp / "clip.mp4"
        with self.assertRaises(media.DownloadError) as ctx:
            media.atomic_download(
                _FakeResponse([b"abc"], content_length=99), target
            )
        self.assertIn("incomplete download", str(ctx.exception))
        self.assertFalse(target.exists())
        self.assertEqual(self._partials(), [])

    def test_interrupted_transfer_leaves_no_partial_file(self) -> None:
        target = self.tmp / "clip.mp4"
        with self.assertRaises(OSError):
            media.atomic_download(
                _FakeResponse([b"abc", b"def"], raise_at=1), target
            )
        self.assertFalse(target.exists())
        self.assertEqual(self._partials(), [])

    def test_failed_download_does_not_clobber_existing_file(self) -> None:
        target = self.tmp / "clip.mp4"
        target.write_bytes(b"good")
        with self.assertRaises(media.DownloadError):
            media.atomic_download(
                _FakeResponse([b"abc"], content_length=99), target
            )
        self.assertEqual(target.read_bytes(), b"good")
        self.assertEqual(self._partials(), [])

    def test_body_without_content_length_is_accepted(self) -> None:
        target = self.tmp / "clip.mp4"
        media.atomic_download(_FakeResponse([b"abc", b"def"]), target)
        self.assertEqual(target.read_bytes(), b"abcdef")


class MetadataPathIdempotencyTest(unittest.TestCase):
    def test_applying_twice_does_not_drift_the_name(self) -> None:
        once = media.metadata_path_for(Path("/lib/a.mp4"))
        twice = media.metadata_path_for(once)
        self.assertEqual(twice, once)
        self.assertEqual(twice.name, "a.mp4.metadata.json")


class SafeFilenameComponentTest(unittest.TestCase):
    def test_accepts_ordinary_ids(self) -> None:
        for good in ("abc123", "a-b_c.d", "DLSDIY7a7G4"):
            self.assertEqual(media.safe_filename_component(good), good)

    def test_rejects_traversal_and_separators(self) -> None:
        for bad in ("", ".", "..", "a/b", "../x", "a\b", "a b", "a\x00b"):
            self.assertIsNone(media.safe_filename_component(bad), bad)


class TransferEncodingTest(unittest.TestCase):
    """A gzip-encoded body must not be reported as a truncated download."""

    def _resp(self, decoded: bytes, content_length: int, encoding: str | None = None):
        class _R:
            def __init__(self) -> None:
                self.headers = {"Content-Length": str(content_length)}
                if encoding:
                    self.headers["Content-Encoding"] = encoding

            def iter_content(self, chunk_size: int = 1):
                yield decoded

        return _R()

    def test_gzip_body_with_compressed_content_length_is_accepted(self) -> None:
        payload = b"A" * 5000
        compressed = gzip.compress(payload)
        target = Path(tempfile.mkdtemp()) / "x.mp4"
        media.atomic_download(
            self._resp(payload, len(compressed), "gzip"), target
        )
        self.assertEqual(target.read_bytes(), payload)

    def test_truncated_body_is_still_rejected(self) -> None:
        target = Path(tempfile.mkdtemp()) / "y.mp4"
        with self.assertRaises(media.DownloadError):
            media.atomic_download(self._resp(b"short", 9999), target)
        self.assertFalse(target.exists())


class ProbeMediaRobustnessTest(unittest.TestCase):
    """ffprobe emits "N/A" for the duration of some containers."""

    def _patch(self, payload: dict):
        import json as _json

        original_which = media.shutil.which
        original_check = media.subprocess.check_output
        media.shutil.which = lambda n: "/usr/bin/ffprobe"
        media.subprocess.check_output = lambda cmd, timeout=None: _json.dumps(payload).encode()

        def restore() -> None:
            media.shutil.which = original_which
            media.subprocess.check_output = original_check

        self.addCleanup(restore)

    def test_na_duration_yields_zeroed_result_in_both_modes(self) -> None:
        self._patch({
            "streams": [{"width": 1280, "height": 720, "r_frame_rate": "25/1"}],
            "format": {"duration": "N/A"},
        })
        for strict in (False, True):
            probe = media.probe_media(Path("/tmp/x.mp4"), strict=strict)
            self.assertEqual(probe.duration_sec, 0.0)
            self.assertEqual(probe.width, 1280)

    def test_absent_duration_yields_zero(self) -> None:
        self._patch({
            "streams": [{"width": 640, "height": 480, "r_frame_rate": "30/1"}],
            "format": {},
        })
        probe = media.probe_media(Path("/tmp/x.mp4"), strict=False)
        self.assertEqual(probe.duration_sec, 0.0)


if __name__ == "__main__":
    unittest.main()
