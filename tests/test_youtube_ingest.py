"""Tests for py.ingest.youtube — mocked, no live API calls."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from py.ingest import youtube


YDL_INFO = {
    "id": "abc12345678",
    "ext": "mp4",
    "title": "Sample Video",
    "channel": "Test Channel",
}


SAMPLE_SEARCH_RESPONSE = {
    "items": [
        {"id": {"videoId": "abc12345678"}},
        {"id": {"videoId": "def87654321"}},
    ]
}

SAMPLE_VIDEOS_RESPONSE = {
    "items": [
        {
            "id": "abc12345678",
            "snippet": {
                "title": "Sample Video",
                "channelTitle": "Test Channel",
                "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
            },
            "contentDetails": {"duration": "PT2M30S"},  # 150 sec
            "status": {"license": "youtube"},
        },
        {
            "id": "def87654321",
            "snippet": {
                "title": "CC Video",
                "channelTitle": "CC Channel",
                "thumbnails": {"high": {"url": "https://example.com/thumb2.jpg"}},
            },
            "contentDetails": {"duration": "PT45S"},  # 45 sec
            "status": {"license": "creativeCommon"},
        },
    ]
}

SAMPLE_FFPROBE_OUTPUT = json.dumps({
    "streams": [{
        "width": 1920,
        "height": 1080,
        "r_frame_rate": "30/1",
    }],
    "format": {"duration": "150.5"},
})


class YouTubeIngestTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_search_videos_no_api_key_raises(self) -> None:
        with patch.object(youtube, "has_youtube", return_value=False):
            with self.assertRaises(RuntimeError) as ctx:
                youtube.search_videos("test")
            self.assertIn("YOUTUBE_API_KEY", str(ctx.exception))

    def test_search_videos_parses_response(self) -> None:
        with patch.object(youtube, "has_youtube", return_value=True), \
             patch.object(youtube, "_api_get", side_effect=[
                 SAMPLE_SEARCH_RESPONSE,
                 SAMPLE_VIDEOS_RESPONSE,
             ]):
            metas = youtube.search_videos("fog forest", max_results=2)

        self.assertEqual(len(metas), 2)
        self.assertEqual(metas[0].id, "abc12345678")
        self.assertEqual(metas[0].title, "Sample Video")
        self.assertEqual(metas[0].duration_sec, 150)
        self.assertEqual(metas[0].license, "any")

        self.assertEqual(metas[1].id, "def87654321")
        self.assertEqual(metas[1].license, "creativeCommon")

    def test_probe_metadata_parses_ffprobe(self) -> None:
        fake_file = Path(self._tmp) / "fake.mp4"
        fake_file.write_bytes(b"\x00" * 100)

        with patch.object(youtube, "shutil", wraps=__import__("shutil")):
            with patch("subprocess.check_output", return_value=SAMPLE_FFPROBE_OUTPUT.encode()):
                probe = youtube.probe_metadata(fake_file)

        self.assertAlmostEqual(probe.duration_sec, 150.5, places=2)
        self.assertEqual(probe.width, 1920)
        self.assertEqual(probe.height, 1080)
        self.assertAlmostEqual(probe.fps, 30.0, places=2)

    def test_probe_metadata_requires_ffprobe(self) -> None:
        fake_file = Path(self._tmp) / "fake.mp4"
        fake_file.write_bytes(b"\x00" * 100)

        with patch("shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                youtube.probe_metadata(fake_file)

    def test_write_metadata_creates_sibling(self) -> None:
        mp4 = Path(self._tmp) / "abc.mp4"
        mp4.write_bytes(b"\x00" * 100)

        vm = youtube.VideoMeta(
            id="abc", title="T", channel="C",
            duration_sec=10, license="any", thumbnail_url="",
        )
        probe = youtube.ProbeResult(10.0, 1920, 1080, 30.0)
        meta_path = youtube.write_metadata(mp4, video_meta=vm, probe=probe)

        self.assertTrue(meta_path.exists())
        data = json.loads(meta_path.read_text())
        self.assertEqual(data["source"], "youtube")
        self.assertEqual(data["youtube_id"], "abc")
        self.assertEqual(data["duration_sec"], 10.0)
        self.assertEqual(data["resolution"], "1920x1080")
        self.assertEqual(len(data["sha256"]), 64)
        self.assertIn("via YouTube", data["attribution"])

    def test_download_video_calls_yt_dlp(self) -> None:
        with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = YDL_INFO
            mock_ydl_cls.return_value = mock_ydl

            # Pre-create the file yt-dlp would write
            out = Path(self._tmp) / "abc12345678.mp4"
            out.write_bytes(b"\x00" * 100)

            path = youtube.download_video("abc12345678", Path(self._tmp))
            self.assertTrue(path.exists())
            mock_ydl.extract_info.assert_called_once()

    def test_ingest_handles_per_video_errors(self) -> None:
        with patch.object(youtube, "search_videos", return_value=[
            youtube.VideoMeta("aaa", "T1", "C", 10, "any", ""),
            youtube.VideoMeta("bbb", "T2", "C", 10, "any", ""),
        ]), \
             patch.object(youtube, "download_video", side_effect=[
                 OSError("network"),  # first fails
                 Path(self._tmp) / "bbb.mp4",
             ]), \
             patch.object(youtube, "probe_metadata", return_value=youtube.ProbeResult(10.0, 1280, 720, 30.0)):
            (Path(self._tmp) / "bbb.mp4").parent.mkdir(parents=True, exist_ok=True)
            (Path(self._tmp) / "bbb.mp4").write_bytes(b"\x00" * 100)

            result = youtube.ingest("q", Path(self._tmp), count=2)

        self.assertEqual(len(result.videos), 2)
        self.assertEqual(len(result.files), 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0][0], "aaa")
        self.assertIn("network", result.errors[0][1])


if __name__ == "__main__":
    unittest.main()