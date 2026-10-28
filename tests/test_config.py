"""Tests for capcut.lib.config — env loading and defaults."""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


def _no_dotenv():
    """Stop config reload from re-reading the developer's real .env."""
    return patch("dotenv.load_dotenv", lambda *a, **k: False)


@contextmanager
def _clean_config_env(**env: str):
    """Reload capcut.lib.config under a controlled environment.

    The module-level constants are computed at import time, so a reload
    inside `patch.dict(os.environ, ..., clear=True)` leaves the module
    holding the patched values *after* the patch has exited. Without the
    reload in the `finally` block this module leaks its test values into
    every test that runs after it — order-dependent, and invisible.
    """
    import importlib

    from capcut.lib import config

    try:
        with patch.dict(os.environ, env, clear=True), _no_dotenv():
            importlib.reload(config)
            yield config
    finally:
        # Put the module back in sync with the real environment.
        importlib.reload(config)


class ConfigTest(unittest.TestCase):
    def test_defaults_when_no_env(self) -> None:
        with _clean_config_env() as config:
            self.assertEqual(config.DEFAULT_VIDEO_PROVIDER, "kie/veo-3-1")
            self.assertEqual(config.DEFAULT_TEXT_PROVIDER, "qwen3-max")
            self.assertEqual(config.DEFAULT_IMAGE_PROVIDER, "qwen-image")
            self.assertFalse(config.has_minimax())
            self.assertFalse(config.has_openrouter())
            self.assertFalse(config.has_youtube())
            self.assertFalse(config.has_coverr())

    def test_helpers_with_keys(self) -> None:
        with _clean_config_env(
            MINIMAX_API_KEY="sk-test",
            OPENROUTER_API_KEY="sk-or-test",
            YOUTUBE_API_KEY="AIza-test",
            COVERR_API_KEY="cov-test",
        ) as config:
            self.assertTrue(config.has_minimax())
            self.assertTrue(config.has_openrouter())
            self.assertTrue(config.has_youtube())
            self.assertTrue(config.has_coverr())

    def test_paths_resolve_under_project_root(self) -> None:
        with _clean_config_env() as config:
            # LIBRARY_ROOT should be inside PROJECT_ROOT unless explicitly overridden
            self.assertTrue(
                str(config.LIBRARY_ROOT).startswith(str(config.PROJECT_ROOT)),
                f"LIBRARY_ROOT {config.LIBRARY_ROOT} should be under PROJECT_ROOT {config.PROJECT_ROOT}",
            )

    def test_ensure_dirs_creates_tree(self) -> None:
        with _clean_config_env(LIBRARY_ROOT="/tmp/_capcut_test_lib") as config:
            import shutil

            shutil.rmtree("/tmp/_capcut_test_lib", ignore_errors=True)
            config.ensure_dirs()
            self.assertTrue(config.LIBRARY_ROOT.exists())
            self.assertTrue(config.AI_DIR.exists())
            self.assertTrue(config.STOCK_DIR.exists())
            shutil.rmtree("/tmp/_capcut_test_lib", ignore_errors=True)

    def test_patched_reload_does_not_leak_into_the_module(self) -> None:
        """The module must be back in sync once the patch has exited."""
        from capcut.lib import config

        with _clean_config_env(LIBRARY_ROOT="/tmp/_capcut_leak_probe") as patched:
            self.assertEqual(str(patched.LIBRARY_ROOT), "/tmp/_capcut_leak_probe")

        # Outside the patch: the patched value must be gone.
        self.assertNotEqual(str(config.LIBRARY_ROOT), "/tmp/_capcut_leak_probe")


if __name__ == "__main__":
    unittest.main()
