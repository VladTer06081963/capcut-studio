"""Tests for py.episode.spec_writer — mocked, no live LLM calls."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from py.episode import spec_writer


SAMPLE_BIBLE = """# Show — stalker-reznik

## Visual style

Stalker Pripyat 1986, atmospheric realism.

## Frozen video prompt suffix (H3.0 / H3 Max)

cinematic anamorphic, atmospheric realism, hyper-detailed

## Cast

- `bible/character-reznik.md` — stalker veteran (lead)

## Locations

- `bible/scene-pripyat-riverbank.md` — campfire scenes
"""

SAMPLE_BRIEF = """# Episode: Reznik at the riverbank

Reznik approaches the campfire at dusk. Sees a figure across the river.
Returns to camp without engaging. Voice-over: "Some things aren't worth
the ammo."
"""

SAMPLE_LLM_RESPONSE = {
    "choices": [{
        "message": {
            "content": json.dumps({
                "id": "ep-01-pilot",
                "show": "stalker-reznik",
                "title": "Reznik at the Riverbank",
                "summary": "Reznik sees a figure across the river, returns to camp.",
                "scenes": [
                    {
                        "n": 1,
                        "type": "establishing",
                        "query": "Wide shot of campfire by Pripyat riverbank at dusk, fog",
                        "preferred_source": "ai",
                        "track": "video",
                        "duration_sec": 6,
                        "character_ref": None,
                        "scene_ref": "ai:pripyat-riverbank:wide",
                        "caption": None,
                        "voiceover": None,
                        "tags": ["establishing", "evening"]
                    },
                    {
                        "n": 2,
                        "type": "dialogue",
                        "query": "Reznik standing by campfire, looking across river",
                        "preferred_source": "ai",
                        "track": "video",
                        "duration_sec": 5,
                        "character_ref": "ai:reznik:reference.png",
                        "scene_ref": None,
                        "caption": None,
                        "voiceover": None,
                        "tags": ["reznik", "dialogue"]
                    },
                    {
                        "n": 3,
                        "type": "voiceover",
                        "query": "",
                        "preferred_source": "any",
                        "track": "audio",
                        "duration_sec": 3,
                        "character_ref": None,
                        "scene_ref": None,
                        "caption": None,
                        "voiceover": "Some things aren't worth the ammo.",
                        "tags": ["voiceover"]
                    },
                ],
                "provider": {"text": "qwen/qwen3-max"}
            })
        }
    }]
}


class ValidateSpecTest(unittest.TestCase):
    def _valid_scene(self, n: int = 1) -> spec_writer.SceneSpec:
        return spec_writer.SceneSpec(
            n=n, type="establishing",
            query="forest scene", preferred_source="ai",
            track="video", duration_sec=5,
        )

    def _valid_spec(self) -> spec_writer.EpisodeSpec:
        return spec_writer.EpisodeSpec(
            schema=spec_writer.SCHEMA_VERSION,
            id="ep-01-pilot", show="stalker-reznik",
            title="Test", summary="Test summary",
            scenes=[self._valid_scene()],
            provider={"text": "qwen/qwen3-max"},
            model="qwen/qwen3-max",
            created_at="2026-10-09T19:00:00Z",
            brief_sha256="a" * 64, bible_sha256="b" * 64,
        )

    def test_valid_spec_passes(self) -> None:
        self.assertEqual(spec_writer.validate_spec(self._valid_spec()), [])

    def test_invalid_id_rejected(self) -> None:
        spec = self._valid_spec()
        spec.id = "Bad ID!"
        issues = spec_writer.validate_spec(spec)
        self.assertTrue(any("id invalid" in i for i in issues))

    def test_scene_n_must_be_sequential(self) -> None:
        spec = self._valid_spec()
        spec.scenes = [self._valid_scene(n=1), self._valid_scene(n=3)]
        issues = spec_writer.validate_spec(spec)
        self.assertTrue(any("scene[1].n" in i for i in issues))

    def test_scene_type_validated(self) -> None:
        spec = self._valid_spec()
        spec.scenes[0].type = "explosion"
        self.assertTrue(any("type invalid" in i for i in spec_writer.validate_spec(spec)))

    def test_empty_scenes_rejected(self) -> None:
        spec = self._valid_spec()
        spec.scenes = []
        self.assertTrue(any("scenes list is empty" in i for i in spec_writer.validate_spec(spec)))

    def test_query_required_for_video(self) -> None:
        spec = self._valid_spec()
        spec.scenes[0].query = ""
        self.assertTrue(any("query required" in i for i in spec_writer.validate_spec(spec)))

    def test_duration_bounds(self) -> None:
        spec = self._valid_spec()
        spec.scenes[0].duration_sec = 200
        self.assertTrue(any("duration_sec out of range" in i for i in spec_writer.validate_spec(spec)))


class ExtractBibleExcerptTest(unittest.TestCase):
    def test_picks_known_sections(self) -> None:
        excerpt = spec_writer.extract_bible_excerpt(SAMPLE_BIBLE)
        self.assertIn("Visual style", excerpt)
        self.assertIn("Frozen video prompt suffix", excerpt)
        self.assertIn("Cast", excerpt)
        self.assertIn("Locations", excerpt)

    def test_skips_unknown_sections(self) -> None:
        excerpt = spec_writer.extract_bible_excerpt(SAMPLE_BIBLE)
        # "Editing style" is in _BIBLE_KEY_SECTIONS but not in SAMPLE_BIBLE
        self.assertNotIn("Editing style", excerpt)

    def test_fallback_to_full_text(self) -> None:
        excerpt = spec_writer.extract_bible_excerpt("# Just a title\n\nnothing else")
        self.assertIn("Just a title", excerpt)


class WriteSpecFromBriefTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.brief = Path(self._tmp) / "brief.md"
        self.brief.write_text(SAMPLE_BRIEF, encoding="utf-8")
        self.bible = Path(self._tmp) / "bible.md"
        self.bible.write_text(SAMPLE_BIBLE, encoding="utf-8")
        self.output = Path(self._tmp) / "spec.json"

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_dry_run_writes_minimal_stub(self) -> None:
        spec = spec_writer.write_spec_from_brief(
            brief_path=self.brief,
            bible_path=self.bible,
            output_path=self.output,
            dry_run=True,
        )
        self.assertEqual(spec.scenes, [])
        self.assertTrue(self.output.exists())

    def test_live_call_parses_llm_response(self) -> None:
        with patch.object(spec_writer, "call_openrouter", return_value=SAMPLE_LLM_RESPONSE):
            spec = spec_writer.write_spec_from_brief(
                brief_path=self.brief,
                bible_path=self.bible,
                output_path=self.output,
            )

        self.assertEqual(spec.id, "ep-01-pilot")
        self.assertEqual(spec.show, "stalker-reznik")
        self.assertEqual(len(spec.scenes), 3)
        self.assertEqual(spec.scenes[0].type, "establishing")
        self.assertEqual(spec.scenes[1].character_ref, "ai:reznik:reference.png")
        self.assertEqual(spec.scenes[2].track, "audio")
        # Metadata we control
        self.assertEqual(spec.schema, spec_writer.SCHEMA_VERSION)
        self.assertEqual(len(spec.brief_sha256), 64)
        # Output file written
        self.assertTrue(self.output.exists())

    def test_invalid_llm_json_raises(self) -> None:
        bad_response = {"choices": [{"message": {"content": "not json"}}]}
        with patch.object(spec_writer, "call_openrouter", return_value=bad_response):
            with self.assertRaises(RuntimeError) as ctx:
                spec_writer.write_spec_from_brief(
                    brief_path=self.brief, bible_path=self.bible, output_path=self.output,
                )
            self.assertIn("invalid JSON", str(ctx.exception))

    def test_validation_failure_raises(self) -> None:
        bad_spec = SAMPLE_LLM_RESPONSE.copy()
        bad_spec["choices"][0]["message"]["content"] = json.dumps({
            "id": "ep-01",
            "show": "x",
            "title": "",
            "summary": "",
            "scenes": [],  # empty
            "provider": {},
        })
        with patch.object(spec_writer, "call_openrouter", return_value=bad_spec):
            with self.assertRaises(ValueError) as ctx:
                spec_writer.write_spec_from_brief(
                    brief_path=self.brief, bible_path=self.bible, output_path=self.output,
                )
            self.assertIn("validation failed", str(ctx.exception))

    def test_load_spec_roundtrip(self) -> None:
        with patch.object(spec_writer, "call_openrouter", return_value=SAMPLE_LLM_RESPONSE):
            spec_writer.write_spec_from_brief(
                brief_path=self.brief, bible_path=self.bible, output_path=self.output,
            )
        loaded = spec_writer.load_spec(self.output)
        self.assertEqual(loaded.id, "ep-01-pilot")
        self.assertEqual(len(loaded.scenes), 3)


if __name__ == "__main__":
    unittest.main()