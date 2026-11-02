import pathlib
import tempfile
import unittest
from unittest.mock import patch

import scripts.rasterize as rasterize


class RasterizeTargetTests(unittest.TestCase):
    def test_targets_are_selected_from_explicit_build_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "assets").mkdir()
            (root / "assets" / "hero.svg").write_text('<svg width="30" height="20"/>')
            (root / "assets" / "stats.svg").write_text('<svg width="20" height="10"/>')
            targets = rasterize.discover_targets("gitcode_badhope", root)
            self.assertEqual({p.name for p in targets}, {"hero.svg", "stats.svg"})

    def test_missing_account_returns_empty(self):
        self.assertEqual(rasterize.discover_targets("no-such-account"), [])

    def test_raster_dimensions_come_from_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            svg = pathlib.Path(tmp) / "test.svg"
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 125"/>')
            self.assertEqual(rasterize.svg_dimensions(svg), (320, 125))
