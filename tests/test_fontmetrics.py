import unittest

from kit.fontmetrics import char_width, text_width


class FontMetricsTests(unittest.TestCase):
    def test_verdana_widths_are_available(self):
        self.assertIsNotNone(char_width("A"))
        self.assertIsNotNone(char_width("i"))
        self.assertNotEqual(char_width("A"), char_width("i"))

    def test_cjk_width_is_full_em(self):
        self.assertEqual(char_width("中"), 1.0)

    def test_unknown_symbol_falls_back(self):
        self.assertIsNone(char_width("\u2603"))

    def test_text_width_scales_with_size(self):
        self.assertAlmostEqual(text_width("ABC", 10) * 2, text_width("ABC", 20))
