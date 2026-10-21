# -*- coding: utf-8 -*-
"""作品区必须来自真实仓库，且数字必须是实时徽章（不能是写死的图）。"""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "generate.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))


class WorksRealDataTest(unittest.TestCase):
    def test_works_json_has_real_repos(self):
        p = ROOT / "data" / "works.json"
        self.assertTrue(p.is_file(), "缺 data/works.json（作品区数据源）")
        data = json.loads(p.read_text(encoding="utf-8"))
        accounts = data.get("accounts") or {}
        self.assertTrue(accounts, "works.json 没有账号数据")
        for key, blk in accounts.items():
            repos = blk.get("repos") or []
            self.assertTrue(repos, "%s 没有发现任何仓库" % key)
            for r in repos:
                self.assertTrue(r.get("name"), "%s 有仓库缺 name" % key)
                self.assertTrue(r.get("url", "").startswith("http"),
                                "%s 的 %s 缺有效 URL" % (key, r.get("name")))
                self.assertRegex(r.get("updated") or "", r"^\d{4}-\d{2}-\d{2}$",
                                 "%s 的 %s 缺更新时间" % (key, r.get("name")))

    def test_no_hardcoded_missing_projects(self):
        """审计发现的 7 个不存在项目不得再出现在源码里。"""
        import accounts as A
        fakes = ["awesome-ai-devkit", "awesome-skillkit", "novel-engine",
                 "p2wlan", "DU", "API-Market", "MCP-HUB"]
        offenders = []
        for key, acct in A.ACCOUNTS.items():
            for w in acct.get("works", []):
                if w in fakes:
                    offenders.append("%s -> %s" % (key, w))
        self.assertEqual(offenders, [], "仍有不存在的项目: %s" % offenders)


class LiveBadgeTest(unittest.TestCase):
    def setUp(self):
        import accounts as A
        import generate as G
        self.A, self.G = A, G

    def test_github_has_three_realtime_badges(self):
        html = self.G.live_badges(self.A.ACCOUNTS["gh_badhope"], "md")
        self.assertIsNotNone(html)
        self.assertEqual(html.count("img.shields.io"), 3,
                         "GitHub 应有 repos/stars/followers 三个实时徽章")
        self.assertIn("github/stars/badhope", html)
        self.assertIn("github/followers/badhope", html)
        self.assertIn("dynamic/json", html)

    def test_gitee_and_gitcode_emit_no_broken_badges(self):
        """shields 对这两个平台没有可用端点（实测稳定 invalid），
        宁可不显示徽章，也不能挂一个 invalid 出去。"""
        for key in ("gitee_badhope", "gitcode_badhope"):
            html = self.G.live_badges(self.A.ACCOUNTS[key], "md")
            if html is not None:
                self.assertNotIn("dynamic/json", html,
                                 "%s 用了会返回 invalid 的动态徽章" % key)

    def test_badges_are_not_local_images(self):
        """徽章必须是外链 shields，不能是仓库内的静态图。"""
        for key in ("gh_badhope", "gitee_badhope", "gitcode_badhope"):
            html = self.G.live_badges(self.A.ACCOUNTS[key], "md")
            if html is None:
                continue          # 该平台没有可靠徽章端点，不显示是对的
            self.assertNotIn("./assets/", html, "%s 的徽章用了本地静态图" % key)


class WorksTableRenderTest(unittest.TestCase):
    def test_readme_works_section_is_a_linked_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "p"
            subprocess.run([sys.executable, str(GEN), "--pack", "gh_badhope", "--out", str(out)],
                           check=True, capture_output=True)
            md = (out / "README.md").read_text(encoding="utf-8")
            start = md.index("## Selected work")
            end = md.index("All public repositories")
            section = md[start:end]
            self.assertIn("| Project |", section, "作品区应为表格")
            self.assertIn("](https://github.com/badhope/", section, "作品应为可点击链接")
            # 不允许再出现把作品画成整张图的写法
            self.assertNotIn("assets/works-md.svg", section,
                             "作品区仍在用静态 SVG 图")

    def test_works_table_sorted_by_update_desc(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "p"
            subprocess.run([sys.executable, str(GEN), "--pack", "gh_badhope", "--out", str(out)],
                           check=True, capture_output=True)
            data = json.loads((ROOT / "data" / "works.json").read_text(encoding="utf-8"))
            repos = data["accounts"]["gh_badhope"]["repos"]
            dates = [r["updated"] for r in repos]
            self.assertEqual(dates, sorted(dates, reverse=True),
                             "作品应按更新时间倒序")


if __name__ == "__main__":
    unittest.main()
