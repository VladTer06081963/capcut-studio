"""Tests for py.index.embedder — mocked, no LM Studio calls."""

from __future__ import annotations

import json
import sqlite3
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from py.index import embedder


SAMPLE_CAPTION_RESPONSE = {
    "choices": [{
        "message": {"content": "A campfire burns in a foggy forest at dusk."}
    }]
}

SAMPLE_EMBED_RESPONSE = {
    "data": [{"embedding": [0.1] * 384}]
}

SAMPLE_MODELS_RESPONSE = {
    "data": [{"id": "bge-large-en-v1.5"}, {"id": "blip-2"}]
}


class EmbeddingPackTest(unittest.TestCase):
    def test_pack_unpack_roundtrip(self) -> None:
        vec = [0.1, 0.2, 0.3, -0.5]
        blob = embedder.pack_embedding(vec)
        self.assertEqual(len(blob), 4 * 4)  # 4 floats * 4 bytes
        unpacked = embedder.unpack_embedding(blob)
        for a, b in zip(vec, unpacked):
            self.assertAlmostEqual(a, b, places=5)


class InitDbTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_init_db_creates_tables(self) -> None:
        db = Path(self._tmp) / "test.sqlite"
        conn = embedder.init_db(db)
        # Verify tables exist
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clips'"
        )
        self.assertIsNotNone(cur.fetchone())
        conn.close()

    def test_init_db_idempotent(self) -> None:
        db = Path(self._tmp) / "test.sqlite"
        embedder.init_db(db).close()
        # Second call should not raise
        embedder.init_db(db).close()


class LmStudioClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        # Create a fake image
        self.img = Path(self._tmp) / "fake.png"
        self.img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_caption_image_parses_response(self) -> None:
        with patch.object(embedder, "requests") as mock_requests:
            mock_requests.post.return_value.json.return_value = SAMPLE_CAPTION_RESPONSE
            mock_requests.post.return_value.raise_for_status.return_value = None

            caption = embedder.caption_image(self.img)

        self.assertEqual(caption, "A campfire burns in a foggy forest at dusk.")

    def test_embed_text_parses_response(self) -> None:
        with patch.object(embedder, "requests") as mock_requests:
            mock_requests.post.return_value.json.return_value = SAMPLE_EMBED_RESPONSE
            mock_requests.post.return_value.raise_for_status.return_value = None

            vec = embedder.embed_text("forest fog")

        self.assertEqual(len(vec), 384)

    def test_lm_studio_alive_when_200(self) -> None:
        with patch.object(embedder, "requests") as mock_requests:
            mock_requests.get.return_value.status_code = 200
            self.assertTrue(embedder.lm_studio_alive())

    def test_lm_studio_alive_when_500(self) -> None:
        with patch.object(embedder, "requests") as mock_requests:
            mock_requests.get.return_value.status_code = 500
            self.assertFalse(embedder.lm_studio_alive())

    def test_lm_studio_alive_when_unreachable(self) -> None:
        import requests as _r
        with patch.object(embedder, "requests") as mock_requests:
            mock_requests.get.side_effect = _r.ConnectionError("refused")
            self.assertFalse(embedder.lm_studio_alive())


class IndexClipTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        # Fake mp4 + metadata
        self.mp4 = Path(self._tmp) / "abc.mp4"
        self.mp4.write_bytes(b"\x00" * 200)
        meta = {
            "id": "test:abc",
            "source": "youtube",
            "tags": ["fog", "forest"],
            "prompt": "Test Title",
            "duration_sec": 5.0,
        }
        (self.mp4.with_suffix(self.mp4.suffix + ".metadata.json")).write_text(
            json.dumps(meta), encoding="utf-8"
        )
        # Fake library_root parent
        self.lib_root = Path(self._tmp) / "lib"
        self.lib_root.mkdir()
        # Move mp4 inside lib_root
        self.target = self.lib_root / "abc.mp4"
        self.mp4.rename(self.target)
        meta_target = self.target.with_suffix(self.target.suffix + ".metadata.json")
        (mp4_meta := self.mp4.with_suffix(self.mp4.suffix + ".metadata.json")).rename(meta_target)

        self.db = Path(self._tmp) / "index.sqlite"
        self.conn = embedder.init_db(self.db)

    def tearDown(self) -> None:
        self.conn.close()
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_index_clip_inserts_row(self) -> None:
        with patch.object(embedder, "_probe_for_indexing", return_value={
            "duration_sec": 5.0, "width": 1280, "height": 720, "fps": 24.0,
        }), \
             patch.object(embedder, "lm_studio_alive", return_value=False):
            added = embedder.index_clip(self.conn, self.target, self.lib_root)

        self.assertTrue(added)
        row = self.conn.execute("SELECT id, source, caption FROM clips").fetchone()
        self.assertEqual(row[0], "test:abc")
        self.assertEqual(row[1], "youtube")

    def test_index_clip_idempotent_on_same_sha256(self) -> None:
        with patch.object(embedder, "_probe_for_indexing", return_value={
            "duration_sec": 5.0, "width": 1280, "height": 720, "fps": 24.0,
        }), \
             patch.object(embedder, "lm_studio_alive", return_value=False):
            embedder.index_clip(self.conn, self.target, self.lib_root)
            added2 = embedder.index_clip(self.conn, self.target, self.lib_root)

        self.assertTrue(added2 is False)  # second call should skip
        count = self.conn.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
        self.assertEqual(count, 1)

    def test_index_clip_skips_zero_duration(self) -> None:
        with patch.object(embedder, "_probe_for_indexing", return_value={
            "duration_sec": 0, "width": 0, "height": 0, "fps": 0,
        }), \
             patch.object(embedder, "lm_studio_alive", return_value=False):
            added = embedder.index_clip(self.conn, self.target, self.lib_root)

        self.assertFalse(added)
        count = self.conn.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
        self.assertEqual(count, 0)


class SearchByTextTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.db = Path(self._tmp) / "index.sqlite"
        self.conn = embedder.init_db(self.db)

    def tearDown(self) -> None:
        self.conn.close()
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _insert_clip(self, clip_id: str, vec: list[float], source: str = "ai") -> None:
        self.conn.execute(
            "INSERT INTO clips (id, path, sha256, source, embedding, indexed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (clip_id, f"path/{clip_id}.mp4", "a" * 64, source, embedder.pack_embedding(vec), "2026-10-09T20:00Z"),
        )
        self.conn.commit()

    def test_search_returns_top_match(self) -> None:
        # Three clips with orthogonal-ish vectors
        v1 = [1.0, 0.0, 0.0] + [0.0] * 381
        v2 = [0.0, 1.0, 0.0] + [0.0] * 381
        v3 = [0.9, 0.1, 0.0] + [0.0] * 381   # closer to v1
        self._insert_clip("a", v1)
        self._insert_clip("b", v2)
        self._insert_clip("c", v3)

        query = [1.0, 0.0, 0.0] + [0.0] * 381
        results = embedder.search_by_text(self.db, query, limit=3)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0][0], "a")  # exact match first
        self.assertGreater(results[0][1], results[1][1])  # scores descending

    def test_search_filters_by_source(self) -> None:
        v = [1.0] + [0.0] * 383
        self._insert_clip("ai-1", v, source="ai")
        self._insert_clip("stock-1", v, source="stock")

        query = [1.0] + [0.0] * 383
        results = embedder.search_by_text(self.db, query, source_filter="ai")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "ai-1")


if __name__ == "__main__":
    unittest.main()