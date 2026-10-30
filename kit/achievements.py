# -*- coding: utf-8 -*-
"""成就/奖杯卡（trophy + metrics achievements 的合并移植）。

布局参考 trophy 的 110x110 面板网格：
- 面板 rx=4.5，标题在上，奖杯图形居中，rank 字母覆盖杯身
- 到下一档的进度条：track 80x3.2 at (15,101)，fill 宽度 = progress*80
- abridgeScore：<1 → "0pt"，>999 → "x.xkpt"

与 trophy 的差别：数据来自 data/stats.json + works.json（构建期快照），
而不是 GraphQL —— 因此面板集合由数据可用性决定。
"""

import accounts as A

from .cards import _bg_fill
from .emoji import parse_emojis
from .textutil import esc
from .rank import (ACHIEVEMENT_COLORS, achievements, derive_profile,
                   fmt_compact, trophies)

PANEL_W, PANEL_H = 110, 110
COLS = 4

_LAUREL = (
    "M22 26c-4-6-3-13 2-18-6 2-10 8-9 15-3-2-5-5-6-9-1 7 2 13 8 16z"
)


def _cup(rank, theme):
    """奖杯图形 + rank 字母（trophy getTrophyIcon 的简化移植）。"""
    colors = ACHIEVEMENT_COLORS.get(rank[0] if len(rank) > 1 else rank, ACHIEVEMENT_COLORS["A"])
    if rank in ("SECRET", "SSS", "SS"):
        base, text = ACHIEVEMENT_COLORS["$"][0], "#ffffff"
    elif rank.startswith("S"):
        base = colors[0]
        text = "#ffffff"
    else:
        base = colors[0]
        text = "#ffffff"
    letter = rank[0] if rank != "C" else "C"
    return (
        '<g transform="translate(33,28)">'
        '<path d="M4 2h28v10c0 10-7 16-14 16S4 22 4 12z" fill="%s"/>'
        '<path d="M32 6h8c0 7-4 11-9 12z" fill="%s" opacity="0.85"/>'
        '<path d="M4 6h-8c0 7 4 11 9 12z" fill="%s" opacity="0.85"/>'
        '<rect x="14" y="27" width="8" height="6" fill="%s" opacity="0.8"/>'
        '<rect x="9" y="33" width="18" height="3" rx="1.5" fill="%s"/>'
        '<text x="18" y="16" text-anchor="middle" font-family="Courier,Monospace" '
        'font-size="11" font-weight="bold" fill="%s">%s</text>'
        '</g>'
        % (base, _shade(base, 1.2), _shade(base, 0.8), _shade(base, 0.9), _shade(base, 1.3), text, letter)
    )


def _shade(hex_color, factor):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(ch * 2 for ch in hex_color)
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    clamped = lambda v: max(0, min(255, int(v)))
    return "#{:02x}{:02x}{:02x}".format(clamped(r * factor), clamped(g * factor), clamped(b * factor))


def _panel(item, x, y, theme):
    colors = ACHIEVEMENT_COLORS.get(item["rank"], ACHIEVEMENT_COLORS["A"])
    bar_color = theme.get("teal", "#4FE3C1")
    return (
        '<g transform="translate(%d,%d)">'
        '<rect width="110" height="110" rx="4.5" fill="%s" stroke="%s" stroke-opacity="0.35"/>'
        '<text x="55" y="20" text-anchor="middle" font-family="%s" font-size="12.5" '
        'font-weight="bold" fill="%s">%s</text>'
        '%s'
        '<text x="55" y="82" text-anchor="middle" font-family="%s" font-size="10.5" '
        'fill="%s">%s</text>'
        '<text x="55" y="96" text-anchor="middle" font-family="%s" font-size="9.5" '
        'fill="%s">%s</text>'
        '<rect x="15" y="101" width="80" height="3.2" rx="1" fill="%s" opacity="0.25"/>'
        '<rect x="15" y="101" width="%.1f" height="3.2" rx="1" fill="%s"/>'
        '</g>'
        % (x, y, theme["panel"], theme["deep_blue"], A.SANS, colors[0],
           esc(parse_emojis(item["name"])), _cup(item["rank"], theme), A.SANS, theme["gold_bright"],
           esc(fmt_compact(item["value"])), A.MONO, theme["muted"],
           esc(item["rank"]), theme["faint"], 80 * item["progress"], bar_color)
    )


def achievements_svg(acct, key, stats, lang, discovered=None, theme=None, years=None):
    """成就面板网格：trophy 阈值表 + metrics 成就，数据不足时返回 None。"""
    t = theme or A.THEME
    # stats 是整个 stats.json；成就只看本账号的 block
    block = ((discovered or {}).get("accounts") or {}).get(key) or {}
    derived = derive_profile((stats or {}).get("accounts", {}).get(key) or {},
                             block.get("repos") or [])
    stats = (stats or {}).get("accounts", {}).get(key) or {}
    # 成就卡先取；奖杯卡（trophy 阈值表）只保留成就表没覆盖的字段，
    # 避免同一统计出现两块面板（如 Stars 与 Maintainer 同源）。
    ach_items = achievements(stats, languages=derived["languages"])
    covered = {item["field"] for item in ach_items}
    trophy_items = [x for x in trophies(stats) if x["field"] not in covered]
    items = ach_items + trophy_items
    if not items:
        return None
    cols = min(COLS, len(items))
    rows = (len(items) + cols - 1) // cols
    width = PANEL_W * cols + 20 * (cols - 1) + 40
    height = PANEL_H * rows + 16 * (rows - 1) + 30
    parts = []
    for i, item in enumerate(items):
        x = 20 + (i % cols) * (PANEL_W + 20)
        y = 20 + (i // cols) * (PANEL_H + 16)
        parts.append(_panel(item, x, y, t))
    labels = A.LABELS[lang]
    # 渐变背景与 stats/langs 卡同源（theme_custom["bg1"] 支持 "angle,c1,c2,..."）
    panel_grad, _fill = _bg_fill(t, "bg1", t["bg1"])
    if panel_grad:
        panel_def = panel_grad
        bg_attr = 'fill="url(#grad-bg1)"'
    else:
        panel_def = ""
        bg_attr = 'fill="none"'
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{alt}">
<defs>{panel_def}</defs>
<rect width="{w}" height="{h}" {bg_attr}/>
{parts}
</svg>
""".format(
        w=width, h=height, panel_def=panel_def, bg_attr=bg_attr, parts="\n".join(parts),
        alt=esc(labels["achievements"] if "achievements" in labels else "Achievements"),
    )
