# -*- coding: utf-8 -*-
"""refresh_sections 的变更闸门与 fail-soft 契约。

这些用例针对审计发现的真实缺陷：
  - as_of 每天变化会让"无变化不写盘"永远失效
  - 刷新函数内部吞掉异常时，外层会打印假 ok
"""

import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import refresh_sections as RS  # noqa: E402


def write_stats(path, accounts, as_of="2026-10-01"):
    path.write_text(json.dumps({"as_of": as_of, "source": "old", "accounts": accounts},
                               indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


BASE = {
    "gh_x33834": {"repos": 10, "stars": 1, "followers": 2, "merged": 0},
    "gh_morningstar": {"repos": 20, "stars": 2, "followers": 3, "merged": 1},
    "gh_badhope": {"repos": 30, "stars": 3, "followers": 4, "merged": 2},
    "gitcode_badhope": {"repos": 5, "stars": 1, "followers": None, "merged": None},
    "gitee_badhope": {"repos": 4, "stars": 0, "followers": None, "merged": None},
}


class ChangeGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / "stats.json"
        p = mock.patch.object(RS, "STATS_PATH", self.path)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_only_as_of_changing_does_not_write(self):
        """数值完全相同、仅日期不同 → 不应写盘（审计发现的核心缺陷）。"""
        write_stats(self.path, BASE, as_of="2026-10-01")
        before = self.path.read_bytes()
        with mock.patch.object(RS.R, "refresh_github", lambda h, b: None), \
             mock.patch.object(RS.R, "refresh_gitee", lambda h, b: None), \
             mock.patch.object(RS.R, "refresh_gitcode", lambda h, b: None):
            changed = RS.refresh_stats()
        self.assertFalse(changed, "仅时间戳变化不应判定为变更")
        self.assertEqual(self.path.read_bytes(), before, "文件不应被重写")

    def test_real_number_change_writes(self):
        write_stats(self.path, BASE, as_of="2026-10-01")

        def bump(handle, block):
            block["repos"] = block.get("repos", 0) + 1

        with mock.patch.object(RS.R, "refresh_github", bump), \
             mock.patch.object(RS.R, "refresh_gitee", bump), \
             mock.patch.object(RS.R, "refresh_gitcode", bump):
            changed = RS.refresh_stats()
        self.assertTrue(changed)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["accounts"]["gh_badhope"]["repos"], 31)

    def test_failure_keeps_old_values(self):
        """抓取抛异常时，该账号必须保留旧值且不被清空。"""
        write_stats(self.path, BASE, as_of="2026-10-01")
        before = json.loads(self.path.read_text(encoding="utf-8"))["accounts"]

        def boom(handle, block):
            block.clear()
            raise RuntimeError("network down")

        with mock.patch.object(RS.R, "refresh_github", boom), \
             mock.patch.object(RS.R, "refresh_gitee", lambda h, b: None), \
             mock.patch.object(RS.R, "refresh_gitcode", lambda h, b: None):
            RS.refresh_stats()

        after = json.loads(self.path.read_text(encoding="utf-8"))["accounts"]
        self.assertEqual(after["gh_badhope"], before["gh_badhope"], "失败账号的旧值必须保留")
        self.assertNotEqual(after["gh_badhope"], {}, "旧值不能被清空")


class WritingGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / "writing.json"
        p = mock.patch.object(RS, "WRITING_PATH", self.path)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_only_fetched_date_changing_does_not_write(self):
        items = {"items": [{"title": "a", "url": "https://x/1", "date": "2026-01-01"}]}
        self.path.write_text(json.dumps({"fetched": "2026-10-01", **items}) + "\n", encoding="utf-8")
        before = self.path.read_bytes()

        # build_writing 只返回数据、不落盘；只有内容变化时 refresh_writing 才写
        with mock.patch.object(RS.R, "build_writing",
                               lambda: {"fetched": "2026-10-02", **items}):
            changed = RS.refresh_writing()
        self.assertFalse(changed, "仅 fetched 日期变化不算内容变更")
        self.assertEqual(self.path.read_bytes(), before,
                         "仅时间戳变化时磁盘文件必须逐字节不变")

    def test_new_item_writes(self):
        self.path.write_text(json.dumps({"fetched": "2026-10-01", "items": []}) + "\n", encoding="utf-8")

        with mock.patch.object(RS.R, "build_writing",
                               lambda: {"fetched": "2026-10-01",
                                        "items": [{"title": "new", "url": "https://x/2"}]}):
            self.assertTrue(RS.refresh_writing())
        on_disk = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(len(on_disk["items"]), 1, "新条目必须真的落盘")


if __name__ == "__main__":
    unittest.main()
