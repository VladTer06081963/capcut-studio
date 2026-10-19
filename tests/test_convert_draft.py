import json
import tempfile
import unittest
from pathlib import Path

from scripts.convert_draft import convert


class ConvertDraftTest(unittest.TestCase):
    def test_converts_clips_and_ignores_clips_without_sources(self):
        draft = {
            "project": {"name": "fixture"},
            "tracks": [
                {
                    "clips": [
                        {"src": "/tmp/clip-a.mp4", "duration_sec": 2.5, "start_sec": 0},
                        {"duration_sec": 1, "start_sec": 2.5},
                        {"src": "/tmp/clip-b.mp4", "duration_sec": 3, "start_sec": 2.5},
                    ]
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            draft_path = Path(temp_dir) / "draft.json"
            concat_path = Path(temp_dir) / "concat.json"
            draft_path.write_text(json.dumps(draft), encoding="utf-8")

            convert(draft_path, concat_path)

            result = json.loads(concat_path.read_text(encoding="utf-8"))

        self.assertEqual(result["name"], "fixture")
        self.assertEqual(
            result["media"],
            [
                {"id": "m1", "path": "/tmp/clip-a.mp4"},
                {"id": "m2", "path": "/tmp/clip-b.mp4"},
            ],
        )
        self.assertEqual(
            [(clip["duration"], clip["start"], clip["mediaId"]) for clip in result["clips"]],
            [(2.5, 0.0, "m1"), (3.0, 2.5, "m2")],
        )
        self.assertEqual(result["timelines"][0]["clips"], result["clips"])

    def test_fps_24_propagates_to_root_and_timeline_video(self):
        draft = {
            "project": {"name": "fixture-24", "fps": 24.0},
            "tracks": [
                {
                    "clips": [
                        {"src": "/tmp/clip-a.mp4", "duration_sec": 2.0, "start_sec": 0},
                    ]
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            draft_path = Path(temp_dir) / "draft.json"
            concat_path = Path(temp_dir) / "concat.json"
            draft_path.write_text(json.dumps(draft), encoding="utf-8")

            convert(draft_path, concat_path)

            result = json.loads(concat_path.read_text(encoding="utf-8"))

        expected_video = {"width": 1920, "height": 1080, "rateNum": 24, "rateDen": 1}
        self.assertEqual(result["video"], expected_video)
        self.assertEqual(result["timelines"][0]["video"], expected_video)

    def test_fps_missing_falls_back_to_30_1(self):
        draft = {
            "project": {"name": "fixture-no-fps"},
            "tracks": [
                {
                    "clips": [
                        {"src": "/tmp/clip-a.mp4", "duration_sec": 2.0, "start_sec": 0},
                    ]
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            draft_path = Path(temp_dir) / "draft.json"
            concat_path = Path(temp_dir) / "concat.json"
            draft_path.write_text(json.dumps(draft), encoding="utf-8")

            convert(draft_path, concat_path)

            result = json.loads(concat_path.read_text(encoding="utf-8"))

        expected_video = {"width": 1920, "height": 1080, "rateNum": 30, "rateDen": 1}
        self.assertEqual(result["video"], expected_video)
        self.assertEqual(result["timelines"][0]["video"], expected_video)


if __name__ == "__main__":
    unittest.main()
