import pathlib
import unittest
from unittest.mock import patch

import scripts.rasterize as rasterize


class RasterizeTargetTests(unittest.TestCase):
    def test_svg_files_are_discovered_per_account(self):
        with patch.object(rasterize, "find_browser", return_value=None):
            targets = rasterize.discover_targets("gitcode_badhope")
        self.assertTrue(targets)
        self.assertTrue(all(p.suffix == ".svg" for p in targets))

    def test_missing_account_returns_empty(self):
        with patch.object(rasterize, "find_browser", return_value=None):
            self.assertEqual(rasterize.discover_targets("no-such-account"), [])
