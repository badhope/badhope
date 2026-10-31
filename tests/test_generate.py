# -*- coding: utf-8 -*-
"""离线单元测试：生成器核心行为（stdlib unittest，无第三方依赖）。

运行：
  python -m unittest discover -s tests -v
"""

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import accounts as A  # noqa: E402
import generate as G  # noqa: E402
import refresh as R  # noqa: E402
import discover_works as D  # noqa: E402


class EscapeTests(unittest.TestCase):
    def test_esc_quotes_and_ampersand(self):
        self.assertEqual(G.esc('a & "b"'), "a &amp; &quot;b&quot;")

    def test_clip_w_adds_ellipsis(self):
        out = G.clip_w("abcdefghij", 30, 10)
        self.assertTrue(out.endswith("…"))
        # 省略号本身不参与预算：去掉 … 后必须落在 max_w 内
        self.assertLessEqual(G.text_w(out[:-1], 10), 30)

    def test_clip_w_keeps_text_that_fits(self):
        self.assertEqual(G.clip_w("abc", 30, 10), "abc")

    def test_clip_text_keeps_short_strings(self):
        self.assertEqual(G.clip_text("short", 20), "short")


class IconTests(unittest.TestCase):
    def test_known_icon_renders(self):
        body = G.icon_svg_body("github", 24)
        self.assertIsNotNone(body)
        self.assertIn("viewBox", body)

    def test_missing_icon_returns_none(self):
        self.assertIsNone(G.icon_svg_body("does-not-exist", 24))


class WorkUrlTests(unittest.TestCase):
    def test_prefers_account_platform(self):
        url = A.work_url("zhike", A.ACCOUNTS["gitcode_badhope"])
        self.assertTrue(url.startswith("https://gitcode.com/badhope/"))

    def test_falls_back_to_github(self):
        url = A.work_url("DU", A.ACCOUNTS["gitee_badhope"])
        self.assertEqual(url, "https://github.com/badhope/DU")

    def test_every_account_work_resolves(self):
        for key, acct in A.ACCOUNTS.items():
            for wid in acct["works"]:
                url = A.work_url(wid, acct)
                self.assertTrue(url.startswith("http"), "%s/%s -> %s" % (key, wid, url))


class ReadmeCopyTests(unittest.TestCase):
    def test_japanese_quote_is_localized(self):
        quote = A.QUOTES[0]
        self.assertIn("ja", quote)
        self.assertNotEqual(quote["ja"], quote["en"])

    def test_japanese_work_label_omits_incompatible_description(self):
        from kit.readme import _work_label
        label = _work_label({"title": "demo", "desc": "A local-first tool"}, "ja")
        self.assertEqual(label, "demo")

    def test_chinese_work_label_keeps_cjk_description(self):
        from kit.readme import _work_label
        label = _work_label({"title": "演示", "desc": "本地工具"}, "zh-CN")
        self.assertIn("本地工具", label)

    def test_wakatime_card_renders_with_stats(self):
        from kit.wakatime import wakatime_svg
        svg = wakatime_svg({"data": {"range": "last_7_days", "categories": [{"text": "1 hr"}],
                                      "languages": [{"name": "Python", "text": "1 hr", "percent": 100}]}},
                            theme=A.THEME)
        self.assertIn("WakaTime", svg)
        self.assertNotIn("card failed", svg)

    def test_writing_title_is_localized(self):
        from kit.readme import render_readme
        text = render_readme(A.ACCOUNTS["gitcode_badhope"], "gitcode_badhope", "ja",
                             {"as_of": "", "accounts": {}}, discovered={"accounts": {}})
        self.assertIn("ローカルファースト AI", text)
        self.assertNotIn("本地优先 AI", text)

    def test_chinese_badge_uses_internal_language_key(self):
        from kit.readme import render_readme
        assets = pathlib.Path(tempfile.mkdtemp())
        (assets / "badges-zh-CN.svg").write_text("<svg/>", encoding="utf-8")
        text = render_readme(A.ACCOUNTS["gitcode_badhope"], "gitcode_badhope", "zh-CN",
                             {"as_of": "", "accounts": {}}, discovered={"accounts": {}},
                             assets_dir=assets)
        self.assertIn("./assets/badges-zh-CN.svg", text)
        self.assertNotIn("badges-cn.svg", text)

    def test_wakatime_localized_range_label(self):
        from kit.wakatime import wakatime_svg
        svg = wakatime_svg({"data": {"range": "last_7_days", "categories": [{"text": "1 hr"}],
                                      "languages": [{"name": "Python", "text": "1 hr", "percent": 100}]}},
                            lang="ja", theme=A.THEME)
        self.assertIn("過去7日間", svg)


class GenerateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.stats = G.load_stats(ROOT / "data" / "stats.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_output_is_deterministic(self):
        key = "gitcode_badhope"
        a = self.root / "a"
        b = self.root / "b"
        G.write_account_files(A.ACCOUNTS[key], key, a, self.stats)
        G.write_account_files(A.ACCOUNTS[key], key, b, self.stats)
        for path in a.rglob("*"):
            if path.is_file():
                twin = b / path.relative_to(a)
                self.assertEqual(path.read_bytes(), twin.read_bytes(), str(path))

    def test_all_readme_asset_refs_exist(self):
        for key in A.ACCOUNT_ORDER:
            out = self.root / key
            G.write_account_files(A.ACCOUNTS[key], key, out, self.stats)
            for lang in A.LANGS:
                text = (out / A.README_NAME[lang]).read_text(encoding="utf-8")
                for ref in set(__import__("re").findall(r'(?:src|srcset)="(\./[^"]+)"', text)):
                    self.assertTrue((out / ref[2:]).is_file(), "%s %s: %s" % (key, lang, ref))

    def test_hero_uses_own_account(self):
        for key in A.ACCOUNT_ORDER:
            out = self.root / key
            G.write_account_files(A.ACCOUNTS[key], key, out, self.stats)
            hero = (out / "assets" / "hero.svg").read_text(encoding="utf-8")
            self.assertIn(A.ACCOUNTS[key]["home_display"], hero)

    def test_assets_only_keeps_readme(self):
        key = "gitcode_badhope"
        out = self.root / "repo"
        G.write_account_files(A.ACCOUNTS[key], key, out, self.stats)
        readme = out / "README.md"
        readme.write_text("sentinel", encoding="utf-8")
        G.write_account_files(A.ACCOUNTS[key], key, out, self.stats, assets_only=True)
        self.assertEqual(readme.read_text(encoding="utf-8"), "sentinel")


class WritingMergeTests(unittest.TestCase):
    def test_curated_wins_and_dedupes(self):
        curated = [{"title": "c", "url": "https://x/1", "date": "2026-01-02"}]
        rss = [{"title": "r", "url": "https://x/1", "date": "2026-01-01"},
               {"title": "r2", "url": "https://x/2", "date": "2026-01-03"}]
        merged = R.merge_writing(rss, curated)
        self.assertEqual([m["title"] for m in merged], ["r2", "c"])

    def test_old_items_survive_rss_failure(self):
        old = [{"title": "old", "url": "https://x/9", "date": "2025-12-01"}]
        merged = R.merge_writing([], [], old)
        self.assertEqual(merged[0]["title"], "old")


class DiscoverTests(unittest.TestCase):
    def test_gitee_title_strips_owner_prefix(self):
        repo = {"name": "知客 Zhike", "path": "zhike", "human_name": "badhope/zhike",
                "html_url": "https://gitee.com/badhope/zhike.git"}
        norm = D._norm(repo, "gitee")
        self.assertEqual(norm["title"], "zhike")
        self.assertEqual(norm["url"], "https://gitee.com/badhope/zhike")

    def test_gitcode_uses_web_url(self):
        repo = {"name": "zhike", "path": "zhike", "human_name": "badhope / zhike",
                "web_url": "https://gitcode.com/badhope/zhike"}
        norm = D._norm(repo, "gitcode")
        self.assertEqual(norm["url"], "https://gitcode.com/badhope/zhike")
        self.assertEqual(norm["title"], "zhike")

    def test_forks_and_profile_repo_excluded(self):
        class FakeRefresh:
            pass
        # fetch_repos 需要网络；这里只验证过滤规则的纯函数部分
        repo = {"name": "badhope", "path": "badhope"}
        self.assertEqual(D._repo_ident(repo, "github"), "badhope")


class StatsTests(unittest.TestCase):
    def test_empty_stats_falls_back_to_placeholder(self):
        svg = G.stats_svg(A.ACCOUNTS["gitcode_badhope"], "gitcode_badhope",
                          {"as_of": "", "accounts": {}}, "md")
        self.assertIn("—", svg)

    def test_activity_uses_stats_values(self):
        stats = {"as_of": "2026-10-01", "accounts": {"gitcode_badhope": {"repos": 7}}}
        svg = G.activity_svg(A.ACCOUNTS["gitcode_badhope"], "gitcode_badhope", "md", stats)
        self.assertIn(">7<", svg)


if __name__ == "__main__":
    unittest.main()
