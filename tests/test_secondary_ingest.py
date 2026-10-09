"""Tests for py.ingest.{coverr, mixkit, archive} — mocked, no live calls."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from py.ingest import archive, coverr, mixkit


SAMPLE_COVERR_RESPONSE = {
    "videos": [
        {
            "id": "foggy-mountain",
            "name": "Foggy Mountain Dawn",
            "duration": 12,
            "video_url": "https://cdn.coverr.co/foggy.mp4",
            "poster": "https://cdn.coverr.co/foggy.jpg",
            "tags": ["fog", "mountain", "nature"],
        },
        {
            "id": "city-night",
            "name": "City Night Lights",
            "duration": 8,
            "video_url": "https://cdn.coverr.co/city.mp4",
            "poster": "https://cdn.coverr.co/city.jpg",
            "tags": ["city", "night"],
        },
    ]
}


SAMPLE_MIXKIT_HTML = """
<html><body>
<article data-href="https://mixkit.co/free-stock-video/misty-forest-12345/">
  <h3>Misty Forest</h3>
  <img src="https://mixkit.co/thumbs/misty.jpg">
  <span class="duration">0:45</span>
</article>
<article data-href="https://mixkit.co/free-stock-video/sunset-desert-67890/">
  <h3>Sunset Desert</h3>
  <img src="https://mixkit.co/thumbs/sunset.jpg">
  <span class="duration">1:23</span>
</article>
</body></html>
"""


SAMPLE_MIXKIT_VIDEO_PAGE = """
<html><body>
<video>
  <source src="https://cdn.mixkit.co/videos/preview/mixkit-misty-forest-12345-medium.mp4" type="video/mp4">
</video>
</body></html>
"""


SAMPLE_ARCHIVE_SEARCH = {
    "response": {
        "numFound": 2,
        "docs": [
            {
                "identifier": "Prelinger_DayPlanner_Ad_1958",
                "title": "Day Planner Ad (1958)",
                "year": "1958",
                "mediatype": "movies",
                "licenseurl": "https://creativecommons.org/publicdomain/",
            },
            {
                "identifier": "Prelinger_Coca_Cola_1958",
                "title": "Coca Cola (1958)",
                "year": "1958",
                "mediatype": "movies",
                "licenseurl": "https://creativecommons.org/publicdomain/",
            },
        ],
    }
}


SAMPLE_ARCHIVE_METADATA = {
    "files": [
        {"name": "Prelinger_DayPlanner_Ad_1958.mp4", "format": "h.264"},
        {"name": "Prelinger_DayPlanner_Ad_1958.xml", "format": "metadata"},
    ],
}


SAMPLE_FFPROBE_OUTPUT = json.dumps({
    "streams": [{"width": 1920, "height": 1080, "r_frame_rate": "24/1"}],
    "format": {"duration": "12.5"},
}).encode()


# ---------------------------------------------------------------------------
# Coverr tests
# ---------------------------------------------------------------------------

class CoverrIngestTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_search_no_api_key_raises(self) -> None:
        with patch.object(coverr, "has_coverr", return_value=False):
            with self.assertRaises(RuntimeError):
                coverr.search_videos("test")

    def test_search_parses_response(self) -> None:
        with patch.object(coverr, "has_coverr", return_value=True), \
             patch.object(coverr, "requests") as mock_requests:
            mock_requests.get.return_value.json.return_value = SAMPLE_COVERR_RESPONSE
            mock_requests.get.return_value.raise_for_status.return_value = None

            metas = coverr.search_videos("fog", max_results=2)

        self.assertEqual(len(metas), 2)
        self.assertEqual(metas[0].id, "foggy-mountain")
        self.assertEqual(metas[0].duration_sec, 12)
        self.assertEqual(metas[0].download_url, "https://cdn.coverr.co/foggy.mp4")
        self.assertIn("fog", metas[0].tags)

    def test_write_metadata_creates_sibling(self) -> None:
        mp4 = Path(self._tmp) / "foggy-mountain.mp4"
        mp4.write_bytes(b"\x00" * 100)

        vm = coverr.VideoMeta(
            id="foggy-mountain", title="Foggy Mountain Dawn",
            duration_sec=12, download_url="https://x", thumbnail_url="",
            tags=("fog", "mountain"),
        )
        probe = coverr.ProbeResult(12.5, 1920, 1080, 24.0)
        meta_path = coverr.write_metadata(mp4, video_meta=vm, probe=probe)

        self.assertTrue(meta_path.exists())
        data = json.loads(meta_path.read_text())
        self.assertEqual(data["source"], "coverr")
        self.assertEqual(data["license"], "coverr")
        self.assertIn("Coverr", data["attribution"])


# ---------------------------------------------------------------------------
# Mixkit tests
# ---------------------------------------------------------------------------

class MixkitIngestTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_find_video_cards(self) -> None:
        cards = mixkit._find_video_cards(SAMPLE_MIXKIT_HTML)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["id"], "misty-forest-12345")
        self.assertEqual(cards[0]["title"], "Misty Forest")
        self.assertEqual(cards[0]["duration_text"], "0:45")
        self.assertEqual(cards[1]["id"], "sunset-desert-67890")

    def test_parse_duration_to_seconds(self) -> None:
        self.assertEqual(mixkit._parse_duration_to_seconds("0:45"), 45)
        self.assertEqual(mixkit._parse_duration_to_seconds("1:23"), 83)
        self.assertEqual(mixkit._parse_duration_to_seconds("12:34"), 754)
        self.assertEqual(mixkit._parse_duration_to_seconds("garbage"), 0)

    def test_search_uses_polite_delay(self) -> None:
        with patch.object(mixkit, "requests") as mock_requests, \
             patch.object(mixkit.time, "sleep") as mock_sleep:
            mock_requests.get.return_value.text = SAMPLE_MIXKIT_HTML
            mock_requests.get.return_value.raise_for_status.return_value = None

            metas = mixkit.search_videos("forest", max_results=5, polite_delay_sec=0.5)

        mock_sleep.assert_called_once_with(0.5)
        self.assertEqual(len(metas), 2)
        self.assertEqual(metas[0].duration_sec, 45)

    def test_resolve_download_url(self) -> None:
        with patch.object(mixkit, "requests") as mock_requests, \
             patch.object(mixkit.time, "sleep"):
            mock_requests.get.return_value.text = SAMPLE_MIXKIT_VIDEO_PAGE
            mock_requests.get.return_value.raise_for_status.return_value = None

            url = mixkit._resolve_download_url("https://mixkit.co/whatever/", 0.0)
            self.assertIn(".mp4", url)
            self.assertIn("misty-forest", url)


# ---------------------------------------------------------------------------
# Archive.org tests
# ---------------------------------------------------------------------------

class ArchiveIngestTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_search_parses_response(self) -> None:
        with patch.object(archive, "requests") as mock_requests:
            mock_requests.get.return_value.json.return_value = SAMPLE_ARCHIVE_SEARCH
            mock_requests.get.return_value.raise_for_status.return_value = None

            metas = archive.search_videos("prelinger", max_results=2)

        self.assertEqual(len(metas), 2)
        self.assertEqual(metas[0].identifier, "Prelinger_DayPlanner_Ad_1958")
        self.assertEqual(metas[0].year, 1958)
        self.assertEqual(metas[0].license, "publicdomain")

    def test_search_quotes_query_for_lucene_safety(self) -> None:
        with patch.object(archive, "requests") as mock_requests:
            mock_requests.get.return_value.json.return_value = {"response": {"docs": []}}
            mock_requests.get.return_value.raise_for_status.return_value = None

            archive.search_videos('hello "world"', max_results=1)

        # Verify query was quoted (passed via params= keyword)
        call_args = mock_requests.get.call_args
        params = call_args.kwargs.get("params", {})
        self.assertIn('"hello', params.get("q", ""))

    def test_resolve_mp4_url_prefers_h264(self) -> None:
        with patch.object(archive, "requests") as mock_requests:
            mock_requests.get.return_value.json.return_value = SAMPLE_ARCHIVE_METADATA
            mock_requests.get.return_value.raise_for_status.return_value = None

            url = archive._resolve_mp4_url("Prelinger_DayPlanner_Ad_1958")
            self.assertIn(".mp4", url)
            self.assertIn("Prelinger_DayPlanner", url)

    def test_resolve_mp4_url_no_video_raises(self) -> None:
        with patch.object(archive, "requests") as mock_requests:
            mock_requests.get.return_value.json.return_value = {"files": [
                {"name": "readme.txt", "format": "text"},
            ]}
            mock_requests.get.return_value.raise_for_status.return_value = None

            with self.assertRaises(RuntimeError):
                archive._resolve_mp4_url("nothing-here")

    def test_write_metadata(self) -> None:
        mp4 = Path(self._tmp) / "test.mp4"
        mp4.write_bytes(b"\x00" * 100)

        vm = archive.VideoMeta(
            identifier="test", title="Test Film", year=1958,
            mediatype="movies", download_url="https://x",
            license="publicdomain",
        )
        probe = archive.ProbeResult(60.0, 1280, 720, 24.0)
        meta_path = archive.write_metadata(mp4, video_meta=vm, probe=probe)

        data = json.loads(meta_path.read_text())
        self.assertEqual(data["source"], "archive")
        self.assertEqual(data["license"], "publicdomain")
        self.assertEqual(data["archive_year"], 1958)
        self.assertIn("Internet Archive", data["attribution"])


if __name__ == "__main__":
    unittest.main()