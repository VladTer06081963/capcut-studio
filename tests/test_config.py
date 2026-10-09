"""Tests for py.lib.config — env loading and defaults."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch


class ConfigTest(unittest.TestCase):
    def test_defaults_when_no_env(self) -> None:
        # Force a clean env for this test (no .env loaded either)
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to pick up clean state
            import importlib

            from py.lib import config

            importlib.reload(config)
            self.assertEqual(config.DEFAULT_VIDEO_PROVIDER, "minimax-h3-max")
            self.assertEqual(config.DEFAULT_TEXT_PROVIDER, "qwen3-max")
            self.assertEqual(config.DEFAULT_IMAGE_PROVIDER, "qwen-image")
            self.assertFalse(config.has_minimax())
            self.assertFalse(config.has_openrouter())
            self.assertFalse(config.has_youtube())
            self.assertFalse(config.has_coverr())

    def test_helpers_with_keys(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MINIMAX_API_KEY": "sk-test",
                "OPENROUTER_API_KEY": "sk-or-test",
                "YOUTUBE_API_KEY": "AIza-test",
                "COVERR_API_KEY": "cov-test",
            },
            clear=True,
        ):
            import importlib

            from py.lib import config

            importlib.reload(config)
            self.assertTrue(config.has_minimax())
            self.assertTrue(config.has_openrouter())
            self.assertTrue(config.has_youtube())
            self.assertTrue(config.has_coverr())

    def test_paths_resolve_under_project_root(self) -> None:
        from py.lib import config

        # LIBRARY_ROOT should be inside PROJECT_ROOT unless explicitly overridden
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            importlib.reload(config)
            self.assertTrue(
                str(config.LIBRARY_ROOT).startswith(str(config.PROJECT_ROOT)),
                f"LIBRARY_ROOT {config.LIBRARY_ROOT} should be under PROJECT_ROOT {config.PROJECT_ROOT}",
            )

    def test_ensure_dirs_creates_tree(self) -> None:
        from py.lib import config

        with patch.dict(os.environ, {"LIBRARY_ROOT": "/tmp/_capcut_test_lib"}, clear=True):
            import importlib
            import shutil

            importlib.reload(config)
            shutil.rmtree("/tmp/_capcut_test_lib", ignore_errors=True)
            config.ensure_dirs()
            self.assertTrue(config.LIBRARY_ROOT.exists())
            self.assertTrue(config.AI_DIR.exists())
            self.assertTrue(config.STOCK_DIR.exists())
            shutil.rmtree("/tmp/_capcut_test_lib", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()