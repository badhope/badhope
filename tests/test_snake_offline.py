# -*- coding: utf-8 -*-
"""贡献蛇卡：构建期必须离线、确定、可复现。

这些断言守住项目定位——产物是构建物，不是服务响应。若有人把网络抓取
重新塞回渲染路径，这里会先失败。
"""

import unittest
from unittest import mock

from kit import cardset
from kit import snake


SAMPLE_DAYS = [
    {"date": "2026-01-01", "count": 0},
    {"date": "2026-01-02", "count": 3},
    {"date": "2026-01-03", "count": 12},
    {"date": "2026-01-04", "count": 0},
    {"date": "2026-01-05", "count": 1},
]


class CellsFromDaysTests(unittest.TestCase):
    def test_levels_are_bucketed(self):
        cells = snake.cells_from_days([
            {"date": "2026-01-01", "count": 0},
            {"date": "2026-01-02", "count": 2},
            {"date": "2026-01-03", "count": 5},
            {"date": "2026-01-04", "count": 9},
            {"date": "2026-01-05", "count": 10},
        ])
        self.assertEqual([c["level"] for c in cells], [0, 1, 2, 3, 4])

    def test_malformed_entries_are_skipped(self):
        cells = snake.cells_from_days([
            {"date": "not-a-date", "count": 3},
            {"count": 1},
            {"date": "2026-01-02", "count": 4},
            "not-a-dict",
        ])
        self.assertEqual(len(cells), 1)

    def test_empty_input_yields_no_cells(self):
        self.assertEqual(snake.cells_from_days([]), [])
        self.assertEqual(snake.cells_from_days(None), [])


class OfflineRenderTests(unittest.TestCase):
    def test_render_is_deterministic(self):
        cells = snake.cells_from_days(SAMPLE_DAYS)
        first, _ = snake.render_from_cells(cells)
        second, _ = snake.render_from_cells(cells)
        self.assertIsNotNone(first)
        self.assertEqual(first, second)

    def test_render_never_touches_the_network(self):
        cells = snake.cells_from_days(SAMPLE_DAYS)
        with mock.patch.object(snake, "fetch_contribution_cells",
                               side_effect=AssertionError("render must not fetch")):
            svg, grid = snake.render_from_cells(cells)
        self.assertIsNotNone(svg)
        self.assertIsNotNone(grid)

    def test_empty_cells_render_to_none(self):
        self.assertEqual(snake.render_from_cells([]), (None, None))

    def test_snake_card_requires_snapshot(self):
        from kit.plugins import REGISTRY
        acct = {"platform": "github", "handle": "someone"}
        ctx = {"key": "gh_test", "base": None}
        spec = next(s for s in REGISTRY if s.name == "snake")
        with mock.patch.object(cardset, "load_extras", return_value={}):
            self.assertFalse(spec.enabled(acct, ctx))
        with mock.patch.object(cardset, "load_extras",
                               return_value={"contribution_days": SAMPLE_DAYS}):
            self.assertTrue(spec.enabled(acct, ctx))


if __name__ == "__main__":
    unittest.main()
