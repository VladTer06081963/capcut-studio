"""Tests for py.search.matcher + py.assemble.concat_exporter — fully mocked."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from py.assemble import concat_exporter
from py.episode.spec_writer import EpisodeSpec, SceneSpec, SCHEMA_VERSION
from py.index import embedder
from py.search import matcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(*, n_scenes: int = 3, with_audio: bool = True) -> EpisodeSpec:
    """Build a minimal valid EpisodeSpec for tests."""
    scenes: list[SceneSpec] = []
    for i in range(1, n_scenes + 1):
        if i == n_scenes and with_audio:
            scenes.append(SceneSpec(
                n=i, type="voiceover", query="",
                preferred_source="any", track="audio",
                duration_sec=3, voiceover="Some thoughts.",
            ))
        else:
            scenes.append(SceneSpec(
                n=i, type="establishing", query=f"scene {i} forest fog",
                preferred_source="ai", track="video",
                duration_sec=5,
            ))
    return EpisodeSpec(
        schema=SCHEMA_VERSION, id="ep-test", show="test",
        title="Test", summary="Test",
        scenes=scenes,
        provider={"text": "qwen/qwen3-max"},
        model="qwen/qwen3-max",
        created_at="2026-10-09T21:00:00Z",
        brief_sha256="a" * 64, bible_sha256="b" * 64,
    )


# ---------------------------------------------------------------------------
# Matcher tests
# ---------------------------------------------------------------------------

class SourcePriorityTest(unittest.TestCase):
    def test_ai_priority(self) -> None:
        chain = matcher._resolve_source_filter("ai")
        self.assertEqual(chain, ["ai", "stock", None])

    def test_stock_priority(self) -> None:
        chain = matcher._resolve_source_filter("stock")
        self.assertEqual(chain, ["stock", "ai", None])

    def test_any_priority(self) -> None:
        chain = matcher._resolve_source_filter("any")
        self.assertEqual(chain, [None])

    def test_unknown_defaults_to_any(self) -> None:
        chain = matcher._resolve_source_filter("garbage")
        self.assertEqual(chain, [None])


class MatchEpisodeTest(unittest.TestCase):
    def test_lm_studio_down_raises(self) -> None:
        spec = _make_spec()
        with patch.object(embedder, "lm_studio_alive", return_value=False):
            with self.assertRaises(RuntimeError):
                matcher.match_episode(spec)

    def test_skips_audio_scenes(self) -> None:
        """Audio tracks get scene_match with clip_id=None (visual search not relevant)."""
        spec = _make_spec(with_audio=True)
        with patch.object(embedder, "lm_studio_alive", return_value=True), \
             patch.object(embedder, "embed_text", return_value=[0.1] * 384), \
             patch.object(embedder, "search_by_text", return_value=[
                 ("ai:test:clip", 0.85),
             ]), \
             patch.object(embedder, "get_clip_by_id", return_value={
                 "id": "ai:test:clip", "path": "ai/test/clip.mp4",
                 "source": "ai", "duration_sec": 5.0,
                 "sha256": "a" * 64, "caption": "", "embedding": None,
                 "tags": [], "width": 1920, "height": 1080, "fps": 24.0,
                 "indexed_at": "2026-10-09T20:00:00Z",
             }):
            matched = matcher.match_episode(spec)

        # Last scene is audio — should have no match
        self.assertIsNone(matched.scenes[-1].clip_id)
        self.assertEqual(matched.scenes[-1].source, "none")

    def test_matches_video_scenes(self) -> None:
        spec = _make_spec(n_scenes=2, with_audio=False)
        with patch.object(embedder, "lm_studio_alive", return_value=True), \
             patch.object(embedder, "embed_text", return_value=[0.1] * 384), \
             patch.object(embedder, "search_by_text", return_value=[
                 ("ai:test:clip", 0.85),
             ]), \
             patch.object(embedder, "get_clip_by_id", return_value={
                 "id": "ai:test:clip", "path": "ai/test/clip.mp4",
                 "source": "ai", "duration_sec": 5.0,
                 "sha256": "a" * 64, "caption": "", "embedding": None,
                 "tags": [], "width": 1920, "height": 1080, "fps": 24.0,
                 "indexed_at": "2026-10-09T20:00:00Z",
             }):
            matched = matcher.match_episode(spec)

        for scene_match in matched.scenes:
            self.assertIsNotNone(scene_match.clip_id)
            self.assertEqual(scene_match.source, "ai")
            self.assertGreater(scene_match.score, 0)

    def test_no_match_keeps_scene_with_warning(self) -> None:
        spec = _make_spec(n_scenes=1, with_audio=False)
        with patch.object(embedder, "lm_studio_alive", return_value=True), \
             patch.object(embedder, "embed_text", return_value=[0.1] * 384), \
             patch.object(embedder, "search_by_text", return_value=[]):
            matched = matcher.match_episode(spec)

        self.assertIsNone(matched.scenes[0].clip_id)
        self.assertTrue(any("no candidate" in w for w in matched.scenes[0].warnings))
        self.assertEqual(matched.unmatched_scenes(), [1])

    def test_low_score_skipped(self) -> None:
        spec = _make_spec(n_scenes=1, with_audio=False)
        with patch.object(embedder, "lm_studio_alive", return_value=True), \
             patch.object(embedder, "embed_text", return_value=[0.1] * 384), \
             patch.object(embedder, "search_by_text", return_value=[
                 ("ai:bad", 0.05),  # below 0.1 threshold
             ]):
            matched = matcher.match_episode(spec)

        self.assertIsNone(matched.scenes[0].clip_id)


class MatchedPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_write_load_roundtrip(self) -> None:
        spec = _make_spec(n_scenes=1, with_audio=False)
        with patch.object(embedder, "lm_studio_alive", return_value=True), \
             patch.object(embedder, "embed_text", return_value=[0.1] * 384), \
             patch.object(embedder, "search_by_text", return_value=[
                 ("ai:test:clip", 0.85),
             ]), \
             patch.object(embedder, "get_clip_by_id", return_value={
                 "id": "ai:test:clip", "path": "ai/test/clip.mp4",
                 "source": "ai", "duration_sec": 5.0,
                 "sha256": "a" * 64, "caption": "", "embedding": None,
                 "tags": [], "width": 1920, "height": 1080, "fps": 24.0,
                 "indexed_at": "2026-10-09T20:00:00Z",
             }):
            matched = matcher.match_episode(spec)

        path = Path(self._tmp) / "matched.json"
        matcher.write_matched(matched, path)
        loaded = matcher.load_matched(path)
        self.assertEqual(loaded.spec_id, spec.id)
        self.assertEqual(len(loaded.scenes), 1)


# ---------------------------------------------------------------------------
# Concat assembler tests
# ---------------------------------------------------------------------------

class ConcatAssemblerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        # Create fake library with two mp4s that can be resolved
        self.lib_root = Path(self._tmp) / "library"
        (self.lib_root / "ai" / "reznik").mkdir(parents=True)
        (self.lib_root / "ai" / "reznik" / "walk.mp4").write_bytes(b"\x00" * 100)
        (self.lib_root / "ai" / "reznik" / "talk.mp4").write_bytes(b"\x00" * 100)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _matched_with_clips(self, n: int, paths: list[str]) -> matcher.MatchedEpisode:
        return matcher.MatchedEpisode(
            spec_id="ep-test", spec_sha256="x" * 64,
            matched_at="2026-10-09T21:00:00Z",
            embed_model="bge-large-en-v1.5",
            scenes=[
                matcher.SceneMatch(
                    n=i + 1, clip_id=f"ai:reznik:{paths[i].split('/')[-1].replace('.mp4','')}",
                    score=0.85, source="ai", clip_path=paths[i],
                    duration_sec=5.0,
                )
                for i in range(n)
            ],
        )

    def test_assemble_video_tracks(self) -> None:
        spec = _make_spec(n_scenes=2, with_audio=False)
        matched = self._matched_with_clips(2, ["ai/reznik/walk.mp4", "ai/reznik/talk.mp4"])

        timeline = concat_exporter.assemble_timeline(spec, matched, library_root=self.lib_root)

        video_tracks = [t for t in timeline.tracks if t.type == "video"]
        self.assertEqual(len(video_tracks), 1)
        self.assertEqual(len(video_tracks[0].clips), 2)
        self.assertEqual(video_tracks[0].clips[0].start_sec, 0.0)
        self.assertEqual(video_tracks[0].clips[1].start_sec, 5.0)
        # First scene has fade-in, last scene has fade-out
        self.assertEqual(video_tracks[0].clips[0].transition_in, "fade")
        self.assertEqual(video_tracks[0].clips[0].transition_out, "cut")
        self.assertEqual(video_tracks[0].clips[1].transition_in, "cut")
        self.assertEqual(video_tracks[0].clips[1].transition_out, "fade")

    def test_assemble_audio_track_with_voiceover(self) -> None:
        spec = _make_spec(n_scenes=2, with_audio=True)  # last scene is audio
        matched = self._matched_with_clips(1, ["ai/reznik/walk.mp4"])

        timeline = concat_exporter.assemble_timeline(spec, matched, library_root=self.lib_root)

        audio_tracks = [t for t in timeline.tracks if t.type == "audio"]
        self.assertEqual(len(audio_tracks), 1)
        self.assertEqual(audio_tracks[0].clips[0].voiceover, "Some thoughts.")
        self.assertIsNone(audio_tracks[0].clips[0].src)  # TTS later

    def test_unmatched_video_scene_records_warning(self) -> None:
        spec = _make_spec(n_scenes=1, with_audio=False)
        matched = matcher.MatchedEpisode(
            spec_id="ep", spec_sha256="x" * 64,
            matched_at="2026-10-09T21:00:00Z",
            embed_model="bge",
            scenes=[matcher.SceneMatch(n=1, clip_id=None, score=0.0, source="none")],
        )
        timeline = concat_exporter.assemble_timeline(spec, matched, library_root=self.lib_root)

        self.assertEqual(timeline.unmatched_scenes, [1])
        self.assertTrue(any("scene 1" in w for w in timeline.warnings))

    def test_write_load_concat_roundtrip(self) -> None:
        spec = _make_spec(n_scenes=1, with_audio=False)
        matched = self._matched_with_clips(1, ["ai/reznik/walk.mp4"])

        timeline = concat_exporter.assemble_timeline(spec, matched, library_root=self.lib_root)
        path = Path(self._tmp) / "draft.json"
        concat_exporter.write_concat_timeline(timeline, path)

        self.assertTrue(path.exists())
        loaded = concat_exporter.load_concat_timeline(path)
        self.assertEqual(loaded.project.name, f"{spec.show}-{spec.id}")
        self.assertEqual(len(loaded.tracks), 1)


if __name__ == "__main__":
    unittest.main()