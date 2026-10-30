# -*- coding: utf-8 -*-
"""自渲染徽章（badges/shields `badge-maker` 的移植子集）。

为什么自渲染：shields.io 是运行期第三方依赖，GitCode/Gitee 的 camo 代理
也不总能访问它。这里在构建期把徽章画成本地 SVG —— 数字来自 data 快照，
与统计卡永远同源，且离线可用。

移植范围（flat + flat-square 两种最常用风格）：
- 字宽用 `text_w` 估算（shields 用 anafanafo 预计算 Verdana 11px 表；
  我们的栈里没有该字体表，用与卡片一致的估算器保持视觉统一）
- **textLength 技巧**：text 以 font-size=110 + scale(.1) 输出并声明
  `textLength`，这样即使查看端没有对应字体，文字宽度也严格等于测量值
- 命名色与别名（brightgreen/green/.../blue + gray→grey 等）
- 文字对比度：亮度 = (299R+587G+114B)/255000，阈值 0.69 决定白字/黑字
- 错误徽章语义：not found → red，invalid/inaccessible → lightgray
"""

import functools
import xml.sax.saxutils as xu

from .textutil import text_w

STYLE_HEIGHT = {"flat": 20, "flat-square": 20}
HORIZ_PADDING = 5
FONT_STACK = "Verdana,Geneva,DejaVu Sans,sans-serif"

NAMED_COLORS = {
    "brightgreen": "#4c0", "green": "#67ac09", "yellow": "#d8b800",
    "yellowgreen": "#95991a", "orange": "#ea7233", "red": "#dd4343",
    "blue": "#007ec6", "grey": "#555", "gray": "#555",
    "lightgrey": "#939393", "lightgray": "#939393",
    "critical": "#dd4343", "important": "#ea7233", "success": "#4c0",
    "informational": "#007ec6", "inactive": "#939393",
}


@functools.lru_cache(maxsize=256)
def _color(value, default="#555"):
    value = (value or "").strip()
    if value.lower() in NAMED_COLORS:
        return NAMED_COLORS[value.lower()]
    stripped = value.lstrip("#")
    if len(stripped) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in stripped):
        return "#" + stripped
    return default


@functools.lru_cache(maxsize=256)
def _brightness(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (299 * r + 587 * g + 114 * b) / 255000.0


@functools.lru_cache(maxsize=256)
def _text_width(text):
    return text_w(text, 10) / 10.0  # 归一化到 1px 字号，渲染时再乘


def _emit_text(x, y, content, text_width, fill, bold=False):
    """textLength 技巧：font-size=110 + scale(.1)，宽度严格等于测量值。"""
    weight = ' font-weight="bold"' if bold else ""
    return ('<text transform="scale(.1)" x="%d" y="%d" textLength="%d" '
            'fill="%s"%s>%s</text>'
            % (int(x * 10), int(y * 10), int(text_width * 10), fill, weight,
               xu.escape(content)))


def _emit_group(fill, bold, inner):
    weight = ' font-weight="bold"' if bold else ""
    return ('<g fill="%s" text-anchor="middle" font-family="%s" '
            'font-size="10"%s>%s</g>' % (fill, FONT_STACK, weight, inner))


def make_badge(label, message, style="flat", color="blue",
               label_color="#555"):
    """渲染一枚 flat / flat-square 徽章。返回 SVG 字符串。"""
    from .emoji import parse_emojis
    label, message = parse_emojis(str(label or "")), parse_emojis(str(message or ""))
    if style not in STYLE_HEIGHT:
        style = "flat"
    height = STYLE_HEIGHT[style]
    label_color = _color(label_color)
    color = _color(color, "#4c0")
    label_w = int(round(_text_width(label))) if label else 0
    message_w = int(round(_text_width(message)))
    left = label_w + 2 * HORIZ_PADDING if label else 0
    right = message_w + 2 * HORIZ_PADDING
    total = left + right
    has_label = bool(label)
    text_color = "#fff" if _brightness(color) <= 0.69 else "#333"
    label_text_color = "#fff" if _brightness(label_color) <= 0.69 else "#333"
    center_l = left / 2.0 if has_label else 0
    center_r = left + right / 2.0
    y = (height - 1)

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'role="img" aria-label="%s: %s"><title>%s: %s</title>'
             % (total, height, xu.escape(label), xu.escape(message),
                xu.escape(label), xu.escape(message))]

    if style == "flat":
        parts.append('<linearGradient id="s" x2="0" y2="100%">'
                     '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
                     '<stop offset="1" stop-color="#000" stop-opacity=".1"/></linearGradient>')
        parts.append('<clipPath id="r"><rect width="%d" height="%d" rx="3"/></clipPath>' % (total, height))
    parts.append('<g clip-path="url(#r)" shape-rendering="%s">'
                 % ("crispEdges" if style == "flat-square" else "auto"))
    if has_label:
        parts.append('<rect width="%d" height="%d" fill="%s"/>' % (left, height, label_color))
    parts.append('<rect x="%d" width="%d" height="%d" fill="%s"/>' % (left, right, height, color))
    if style == "flat":
        parts.append('<rect width="%d" height="%d" fill="url(#s)"/>' % (total, height))
    parts.append('</g>')

    label_texts = ""
    if has_label:
        label_texts = _emit_text(center_l, y, label, label_w, label_text_color)
    message_texts = _emit_text(center_r, y, message, message_w, text_color, bold=True)
    if has_label:
        parts.append(_emit_group(label_text_color, False, label_texts))
    parts.append(_emit_group(text_color, True, message_texts))
    parts.append('</svg>')
    return "".join(parts)
