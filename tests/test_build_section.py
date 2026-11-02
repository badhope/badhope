# -*- coding: utf-8 -*-
"""README 的 Build 区块：只在配置了 build_files 的账号出现。

这个仓库本身是生成器，主页需要说明「它是什么、怎么跑」而不只是展示成品。
同时保证未配置的账号不会凭空多出一个空区块。
"""

import unittest

import accounts as A
from kit.readme import render_readme


def _render(key, lang="md"):
    return render_readme(A.ACCOUNTS[key], key, lang, {"accounts": {}}, base=None,
                         discovered={"accounts": {key: {"repos": []}}}, hero_png=False)


class BuildSectionTests(unittest.TestCase):
    def test_configured_account_renders_build_block(self):
        html = _render("gitcode_badhope")
        self.assertIn("## Build", html)
        self.assertIn("make gen", html)
        self.assertIn("make verify", html)

    def test_section_follows_language(self):
        self.assertIn("## 构建", _render("gitcode_badhope", "zh-CN"))
        self.assertIn("## ビルド", _render("gitcode_badhope", "ja"))

    def test_unconfigured_account_omits_build_block(self):
        html = _render("gh_x33834")
        self.assertNotIn("## Build", html)
        self.assertNotIn("make verify", html)

    def test_layout_table_lists_data_source(self):
        html = _render("gitcode_badhope")
        self.assertIn("`accounts.py`", html)
        self.assertIn("`kit/`", html)


if __name__ == "__main__":
    unittest.main()
