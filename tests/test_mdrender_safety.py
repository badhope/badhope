# -*- coding: utf-8 -*-
"""预览页 Markdown 渲染：行内 HTML 白名单与注入防护。

README 的平台表格里嵌了 `<img>` 图标。若整行转义，预览页会把标签当字面量
显示，表格随即错乱；若整行放行，外部仓库名就能注入脚本。这组断言同时守住
「图标要渲染」与「脚本要转义」两侧。
"""

import unittest

from kit.mdrender import render


class InlineHtmlTests(unittest.TestCase):
    def test_table_keeps_platform_icon(self):
        md = ("| | Platform |\n|---|---|\n"
              '| <img src="./assets/icons/si-github.svg" width="18" alt="GitHub" /> | GitHub |')
        html, _engine = render(md)
        self.assertIn('<img src="./assets/icons/si-github.svg"', html)
        self.assertNotIn("&lt;img", html)

    def test_script_tag_is_escaped(self):
        html, _engine = render("text with <script>alert(1)</script> here")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_event_handler_attribute_is_escaped(self):
        html, _engine = render('<img src="x" onerror="alert(1)">')
        self.assertNotIn('onerror="alert(1)"', html)

    def test_unknown_tag_is_escaped(self):
        html, _engine = render("<iframe src=\"https://evil.example\"></iframe>")
        self.assertNotIn("<iframe", html)
        self.assertIn("&lt;iframe", html)


class FencedCodeTests(unittest.TestCase):
    def test_fenced_block_renders_as_pre_code(self):
        html, _engine = render("text\n\n```bash\nmake gen\n```\n\nafter")
        self.assertIn("<pre><code>", html)
        self.assertIn("make gen", html)
        self.assertNotIn("```", html)

    def test_code_content_is_escaped(self):
        html, _engine = render("```html\n<script>alert(1)</script>\n```")
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_unclosed_fence_still_renders(self):
        html, _engine = render("```bash\nmake gen")
        self.assertIn("<pre><code>", html)
        self.assertIn("make gen", html)

    def test_markup_inside_fence_is_not_parsed(self):
        html, _engine = render("```\n| a | b |\n|---|---|\n```")
        self.assertNotIn("<table>", html)
        self.assertIn("| a | b |", html)


if __name__ == "__main__":
    unittest.main()
