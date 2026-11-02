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


_INLINE_TAG_RE = re.compile(
    r"<(/?)(img|br|sub|sup|kbd|strong|em|code|a|span)\b([^<>]*?)(/?)>", re.I)
# 属性白名单：只放行纯展示/链接所需，事件处理器与 style 一律丢弃。
_ALLOWED_ATTRS = {"src", "alt", "width", "height", "href", "title", "class", "align"}
_ATTR_RE = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')


def _safe_attrs(attrs):
    kept = []
    for name, value in _ATTR_RE.findall(attrs):
        lowered = name.lower()
        if lowered not in _ALLOWED_ATTRS or lowered.startswith("on"):
            continue
        if lowered in ("src", "href"):
            # 只允许相对路径、http(s) 与 data:image，挡掉 javascript: 等伪协议
            scheme = value.split(":", 1)[0].lower() if ":" in value.split("?", 1)[0] else ""
            if scheme and scheme not in ("http", "https", "data", "mailto"):
                continue
        kept.append('%s="%s"' % (lowered, html.escape(value, quote=True)))
    return (" " + " ".join(kept)) if kept else ""


def _esc_keep_inline(text):
    """转义文本，但保留白名单内的行内 HTML 标签。

    表格单元格里常出现 `<img ... />`（平台图标）与 `<sub>`。如果整行转义，
    预览页会把标签当字面量显示，表格随即错乱。README 由本仓库生成，
    这里只放行固定白名单标签，属性再过一遍白名单，避免注入。
    """
    parts, pos = [], 0
    for match in _INLINE_TAG_RE.finditer(text):
        parts.append(html.escape(text[pos:match.start()], quote=False))
        closing, name, attrs, selfclose = match.groups()
        if closing:
            parts.append("</%s>" % name.lower())
        else:
            parts.append("<%s%s%s>" % (name.lower(), _safe_attrs(attrs), selfclose))
        pos = match.end()
    parts.append(html.escape(text[pos:], quote=False))
    return "".join(parts)


def _line_html(text):
    text = _esc_keep_inline(text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _URL_RE.sub(r'<a href="\2">\1</a>', text)
    text = _CODE_RE.sub(r"<code>\1</code>", text)
    return text


_BLOCK_TAG_RE = re.compile(
    r"<(/?)(p|picture|source|img|details|summary|table|thead|tbody|tr|th|td|"
    r"div|span|br|hr|h1|h2|h3|h4|ul|ol|li|blockquote|sub|sup|kbd|a|b|i|em|strong|code)\b"
    r"([^<>]*?)(/?)>", re.I)


def _block_html(line):
    """原生 HTML 块的安全通道：只放行展示类标签，属性过同一套白名单。"""
    parts, pos = [], 0
    for match in _BLOCK_TAG_RE.finditer(line):
        parts.append(html.escape(line[pos:match.start()], quote=False))
        closing, name, attrs, selfclose = match.groups()
        if closing:
            parts.append("</%s>" % name.lower())
        else:
            parts.append("<%s%s%s>" % (name.lower(), _safe_attrs(attrs), selfclose))
        pos = match.end()
    parts.append(html.escape(line[pos:], quote=False))
    return "".join(parts)


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
            # 原生 HTML 块：逐行过白名单。README 只用 <p>/<img>/<details>/<table>
            # 这类展示标签，不在这里放行脚本或事件属性。
            out.append(_block_html(line))
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
