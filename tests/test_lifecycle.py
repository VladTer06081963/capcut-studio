"""Tests for py.lib.lifecycle — episode state machine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from py.lib import lifecycle


class LifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self._patch = patch.object(lifecycle, "SERIALS_ROOT", Path(self._tmp))
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        import shutil

        shutil.rmtree(self._tmp)

    def _make_episode(self, show: str = "test", ep_id: str = "ep-01") -> lifecycle.Episode:
        ep = lifecycle.Episode.locate(show, ep_id)
        ep.path.mkdir(parents=True)
        (ep.path / "brief.md").write_text("# test")
        (ep.path / "spec.json").write_text('{"foo": "bar"}')
        return ep

    def test_initial_state_is_draft(self) -> None:
        ep = self._make_episode()
        self.assertEqual(lifecycle.current_state(ep), lifecycle.State.DRAFT)
        self.assertTrue(lifecycle.is_draft(ep))

    def test_approve_creates_sentinel(self) -> None:
        ep = self._make_episode()
        lifecycle.approve(ep)
        self.assertTrue((ep.path / ".approved").exists())
        self.assertEqual(lifecycle.current_state(ep), lifecycle.State.APPROVED)

    def test_approve_idempotent(self) -> None:
        ep = self._make_episode()
        lifecycle.approve(ep)
        lifecycle.approve(ep)  # second call should not raise
        self.assertEqual(lifecycle.current_state(ep), lifecycle.State.APPROVED)

    def test_approve_requires_spec(self) -> None:
        ep = lifecycle.Episode.locate("test", "ep-no-spec")
        ep.path.mkdir(parents=True)
        with self.assertRaises(FileNotFoundError):
            lifecycle.approve(ep)

    def test_revise_drops_back_to_draft(self) -> None:
        ep = self._make_episode()
        lifecycle.approve(ep)
        lifecycle.revise(ep)
        self.assertFalse((ep.path / ".approved").exists())
        self.assertEqual(lifecycle.current_state(ep), lifecycle.State.DRAFT)

    def test_mark_rendered_requires_final_mp4(self) -> None:
        ep = self._make_episode()
        with self.assertRaises(FileNotFoundError):
            lifecycle.mark_rendered(ep)

    def test_mark_rendered_with_empty_file(self) -> None:
        ep = self._make_episode()
        rendered = ep.path / "rendered"
        rendered.mkdir()
        (rendered / "final.mp4").write_bytes(b"")
        with self.assertRaises(FileNotFoundError):
            lifecycle.mark_rendered(ep)

    def test_mark_rendered_success(self) -> None:
        ep = self._make_episode()
        rendered = ep.path / "rendered"
        rendered.mkdir()
        (rendered / "final.mp4").write_bytes(b"\x00" * 100)
        lifecycle.mark_rendered(ep)
        self.assertEqual(lifecycle.current_state(ep), lifecycle.State.RENDERED)

    def test_sha256_spec_idempotent(self) -> None:
        ep = self._make_episode()
        sha1 = lifecycle.sha256_spec(ep)
        sha2 = lifecycle.sha256_spec(ep)
        self.assertEqual(sha1, sha2)
        self.assertEqual(len(sha1), 64)  # sha256 hex length

    def test_is_idempotent_render_requires_both_files(self) -> None:
        ep = self._make_episode()
        # No rendered/ dir
        self.assertFalse(lifecycle.is_idempotent_render(ep))

    def test_write_spec_sha_then_idempotent(self) -> None:
        ep = self._make_episode()
        rendered = ep.path / "rendered"
        rendered.mkdir()
        (rendered / "final.mp4").write_bytes(b"\x00" * 100)
        lifecycle.write_spec_sha(ep)
        self.assertTrue(lifecycle.is_idempotent_render(ep))

        # Mutating spec.json breaks idempotency
        (ep.path / "spec.json").write_text('{"foo": "baz"}')
        self.assertFalse(lifecycle.is_idempotent_render(ep))

    def test_publish_appends_log(self) -> None:
        ep = self._make_episode()
        rendered = ep.path / "rendered"
        rendered.mkdir()
        (rendered / "final.mp4").write_bytes(b"\x00" * 100)

        show_root = lifecycle.SERIALS_ROOT / "test"
        log = show_root / "episode-log.md"
        log.write_text("# Episode log\n")

        lifecycle.publish(ep, log=log)
        content = log.read_text()
        self.assertIn("ep-01", content)
        self.assertIn("status=published", content)

    def test_publish_requires_log(self) -> None:
        ep = self._make_episode()
        with self.assertRaises(FileNotFoundError):
            lifecycle.publish(ep)

    def test_list_episodes_sorted(self) -> None:
        for ep_id in ("ep-03", "ep-01", "ep-02"):
            self._make_episode(ep_id=ep_id)
        eps = lifecycle.list_episodes("test")
        self.assertEqual([e.ep_id for e in eps], ["ep-01", "ep-02", "ep-03"])


if __name__ == "__main__":
    unittest.main()