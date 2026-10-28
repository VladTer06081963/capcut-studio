"""Tests for capcut.lib.atomic — atomic writes of state files.

A state file is read back later by another process. If a write is
interrupted half-way, the next reader fails on truncated content — and that
failure is indistinguishable from real corruption. Atomic writes make the
reader see either the old file or the new one, never a half-written one.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from capcut.lib.atomic import atomic_write_json, atomic_write_text


class AtomicWriteTextTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _leftovers(self) -> list[str]:
        return sorted(p.name for p in self.tmp.iterdir() if p.name != "state.json")

    def test_writes_content(self) -> None:
        target = self.tmp / "state.json"
        atomic_write_text(target, "hello")
        self.assertEqual(target.read_text(), "hello")

    def test_creates_missing_parent_directory(self) -> None:
        target = self.tmp / "deep" / "nested" / "state.json"
        atomic_write_text(target, "hello")
        self.assertTrue(target.exists())

    def test_leaves_no_temp_file_behind(self) -> None:
        target = self.tmp / "state.json"
        atomic_write_text(target, "hello")
        self.assertEqual(self._leftovers(), [])

    def test_overwrite_replaces_content(self) -> None:
        target = self.tmp / "state.json"
        atomic_write_text(target, "one")
        atomic_write_text(target, "two")
        self.assertEqual(target.read_text(), "two")

    def test_failed_write_leaves_previous_file_intact(self) -> None:
        target = self.tmp / "state.json"
        target.write_text("original")

        class _Unserializable:
            pass

        with self.assertRaises(TypeError):
            atomic_write_json(target, {"bad": _Unserializable()})

        self.assertEqual(target.read_text(), "original")
        self.assertEqual(self._leftovers(), [])


class AtomicWriteJsonTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_roundtrip(self) -> None:
        target = self.tmp / "state.json"
        payload = {"a": 1, "b": ["x", "y"], "c": {"d": None}, "e": 2.5}
        atomic_write_json(target, payload)
        self.assertEqual(json.loads(target.read_text()), payload)

    def test_unicode_is_not_escaped(self) -> None:
        target = self.tmp / "state.json"
        atomic_write_json(target, {"k": "Припять"})
        self.assertIn("Припять", target.read_text())

    def test_indent_two_by_default(self) -> None:
        target = self.tmp / "state.json"
        atomic_write_json(target, {"k": "v"})
        self.assertIn('\n  "k"', target.read_text())


if __name__ == "__main__":
    unittest.main()
