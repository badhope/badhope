# -*- coding: utf-8 -*-
"""Markdown → HTML：优先用 markdown-it-py，缺失时退回内置精简解析器。

为什么不是"必须装库"：这个仓库要在 GitHub Actions、GitCode Actions 和
任意本地 checkout 里都能直接跑，多一个运行时依赖就多一处失败点。所以
这里把 `markdown-it-py` 当作**可选加速器**：

- 装了：完整 CommonMark + 表格 + 删除线，生成的预览页与 GitHub 渲染一致；
- 没装：退回 `_fallback_render`，覆盖本项目实际用到的子集
  （标题/表格/列表/引用/行内链接/粗体/行内码/原生 HTML 块）。

两条路径的输出都经过同一层「本地资产路径重写」，页面结构不受影响。
"""

import html
import re

try:  # 可选依赖
    from markdown_it import MarkdownIt as _MarkdownIt
except ImportError:  # pragma: no cover - 环境相关
    _MarkdownIt = None

_URL_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_CODE_RE = re.compile(r"`([^`]+)`")
_SEP_ROW_RE = re.compile(r"\s*\|[\s:|-]*\|\s*")


def has_markdown_it():
    return _MarkdownIt is not None


def _line_html(text):
    text = html.escape(text, quote=False)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _URL_RE.sub(r'<a href="\2">\1</a>', text)
    text = _CODE_RE.sub(r"<code>\1</code>", text)
    return text


def _fallback_render(md):
    out, in_ul, in_table = [], False, False

    def is_sep_row(line):
        return bool(_SEP_ROW_RE.fullmatch(line)) and "-" in line

    for raw in md.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if in_ul and not stripped.startswith("- "):
            out.append("</ul>")
            in_ul = False
        is_table_row = stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2
        if in_table and not is_table_row:
            out.append("</table></div>")
            in_table = False
        if stripped.startswith("# ") and not stripped.startswith("## "):
            out.append("<h1>%s</h1>" % _line_html(stripped[2:]))
        elif stripped.startswith("## "):
            out.append("<h2>%s</h2>" % _line_html(stripped[3:]))
        elif stripped.startswith("### "):
            out.append("<h3>%s</h3>" % _line_html(stripped[4:]))
        elif is_table_row:
            if is_sep_row(stripped):
                continue
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            if not in_table:
                out.append('<div class="tscroll"><table>')
                in_table = True
                tag = "th"
            else:
                tag = "td"
            tds = "".join("<%s>%s</%s>" % (tag, _line_html(c), tag) for c in cells)
            out.append("<tr>%s</tr>" % tds)
        elif stripped.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>%s</li>" % _line_html(stripped[2:]))
        elif stripped.startswith("> "):
            out.append("<blockquote>%s</blockquote>" % _line_html(stripped[2:]))
        elif line.startswith("<") or (line[:1] == " " and stripped.startswith("<")):
            out.append(line)
        elif not line:
            out.append("")
        else:
            out.append("<p>%s</p>" % _line_html(line))
    if in_ul:
        out.append("</ul>")
    if in_table:
        out.append("</table></div>")
    return "\n".join(out)


def _markdown_it_render(md):
    parser = _MarkdownIt("commonmark", {"html": True, "linkify": False, "typographer": False})
    parser.enable("table")
    parser.enable("strikethrough")
    html_out = parser.render(md)
    # 与内置解析器保持同一套布局钩子：宽表格套一层横向滚动容器
    return html_out.replace("<table>", '<div class="tscroll"><table>').replace(
        "</table>", "</table></div>")


def render(md):
    """Markdown → HTML。返回 (html, engine_name)。"""
    if _MarkdownIt is not None:
        return _markdown_it_render(md), "markdown-it-py"
    return _fallback_render(md), "builtin"
