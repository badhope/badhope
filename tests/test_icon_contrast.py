# -*- coding: utf-8 -*-
"""图标配色：深色底上的可辨识度。

彩色图标（devicon 等）自带配色，其中 Vue 的 #35495e、深绿 #090 在星夜底色
上几乎看不见。这组断言保证「过暗就提亮、够亮就不动、不碰 none/url()」，
同时确认提亮是确定性的（同色同果），不破坏字节级可复现。
"""

import unittest

from kit.icons import _lighten, _luma, brighten_for_dark


class LumaTests(unittest.TestCase):
    def test_known_luminance(self):
        self.assertAlmostEqual(_luma("#000000"), 0.0, places=3)
        self.assertAlmostEqual(_luma("#ffffff"), 1.0, places=3)
        self.assertAlmostEqual(_luma("#fff"), 1.0, places=3)

    def test_invalid_color_returns_none(self):
        self.assertIsNone(_luma("#zzzzzz"))


class LightenTests(unittest.TestCase):
    def test_dark_color_is_lifted_above_floor(self):
        lifted = _lighten("#35495e")
        self.assertNotEqual(lifted, "#35495e")
        self.assertGreaterEqual(_luma(lifted), 0.42)

    def test_bright_color_is_unchanged(self):
        self.assertEqual(_lighten("#41b883"), "#41b883")
        self.assertEqual(_lighten("#DFE8FF"), "#DFE8FF")

    def test_lighten_is_deterministic(self):
        self.assertEqual(_lighten("#35495e"), _lighten("#35495e"))


class BrightenBodyTests(unittest.TestCase):
    def test_dark_fills_and_strokes_are_lifted(self):
        body = '<path fill="#35495e"/><circle stroke="#090"/>'
        out = brighten_for_dark(body)
        self.assertNotIn("#35495e", out)
        self.assertNotIn("#090", out)

    def test_none_and_url_are_untouched(self):
        body = '<path fill="none" stroke="url(#g)"/>'
        self.assertEqual(brighten_for_dark(body), body)

    def test_same_color_maps_to_same_output(self):
        out = brighten_for_dark('<path fill="#35495e"/><path fill="#35495e"/>')
        first = out.split('fill="')[1].split('"')[0]
        second = out.split('fill="')[2].split('"')[0]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
