import unittest

import accounts as A
from kit.readme import render_readme


class LocaleExpansionTests(unittest.TestCase):
    def test_language_navigation_uses_configured_locales(self):
        acct = dict(A.ACCOUNTS["gitcode_badhope"])
        acct["locales"] = {"md": "English", "zh-CN": "中文", "ja": "日本語", "ko": "한국어"}
        text = render_readme(acct, "gitcode_badhope", "md",
                             {"as_of": "", "accounts": {}}, discovered={"accounts": {}})
        self.assertIn("한국어", text)
        self.assertIn("README.ko.md", text)

    def test_default_locale_navigation_unchanged(self):
        text = render_readme(A.ACCOUNTS["gitcode_badhope"], "gitcode_badhope", "md",
                             {"as_of": "", "accounts": {}}, discovered={"accounts": {}})
        self.assertIn("[English](README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md)", text)
