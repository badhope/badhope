# -*- coding: utf-8 -*-
"""主题系统：多套配色预设 + 逐账号选择 + 自定义覆盖。

移植自 github-readme-stats 的 75 套主题与 github-profile-trophy 的 25 套主题：
本仓库只需要把它们的 5 个槽位（title/icon/text/bg/border）映射到我们的
12 个槽位（bg0/bg1/panel/panel2/gold/gold_bright/ink/muted/faint/star/
deep_blue/indigo/teal），映射规则写死在 `_expand()` 里，保证任何一套 GRS
主题搬进来都能得到协调的整套配色。

使用方式（accounts.py）：
    ACCOUNTS["gitcode_badhope"]["theme"] = "radical"       # 用预设
    ACCOUNTS["gitcode_badhope"]["theme_custom"] = {
        "gold": "#ff0000",                                  # 覆盖个别槽位
    }

不带 theme 字段 = 默认「星夜极光」，与历史产物完全一致（黄金测试锁定）。
"""

import accounts as A

# 与 GRS 完全同源的预设（title/icon/text/bg 四槽来自 themes/index.js）
_GRS = {
    "radical":    ("fe428e", "f8d847", "a9fef7", "141321"),
    "dracula":    ("ff6e96", "79dafa", "f8f8f2", "282a36"),
    "tokyonight": ("70a5fd", "bf91f3", "38bdae", "1a1b27"),
    "nord":       ("81a1c1", "88c0d0", "d8dee9", "2e3440"),
    "onedark":    ("e4bf7a", "8eb573", "df6d74", "282c34"),
    "gruvbox":    ("fabd2f", "fe8019", "8ec07c", "282828"),
    "monokai":    ("eb1f6a", "e28905", "f1f1eb", "272822"),
    "github_dark": ("58a6ff", "1f6feb", "c3d1d9", "0d1117"),
    "synthwave":  ("e5289e", "ef8539", "e2e9ec", "2b213a"),
    "highcontrast": ("e7f216", "00ffff", "ffffff", "000000"),
    "merko":      ("abd200", "b7d364", "68b587", "0a0f0b"),
    "calm":       ("e07a5f", "edae49", "ebcfb2", "373f51"),
    "aura_dark":  ("ff7372", "6cffd0", "dbdbdb", "252334"),
}


def _shade(hex_color, factor):
    """factor>1 提亮，<1 压暗；输入 #rrggbb，输出 #rrggbb。"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(ch * 2 for ch in hex_color)
    if len(hex_color) != 6:
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    clamped = lambda v: max(0, min(255, int(v)))
    return "#{:02x}{:02x}{:02x}".format(
        clamped(r * factor), clamped(g * factor), clamped(b * factor))


def _expand(title, icon, text, bg):
    """把 GRS 的 5 槽位扩展为 kit 的 12 槽位。"""
    panel = _shade(bg, 1.35)
    return {
        "bg0": _shade(bg, 0.75),
        "bg1": bg,
        "panel": panel,
        "panel2": _shade(panel, 1.25),
        "gold": title,
        "gold_bright": icon,
        "ink": text,
        "muted": _shade(text, 0.72),
        "faint": _shade(text, 0.45),
        "star": _shade(text, 1.0),
        "deep_blue": _shade(bg, 1.6),
        "indigo": icon,
        "teal": title,
    }


DEFAULT_NAME = "aurora"

#: 预设名 → 12 槽位。默认「星夜极光」保持历史字节不变。
THEMES = {DEFAULT_NAME: dict(A.THEME)}
for _name, (_title, _icon, _text, _bg) in _GRS.items():
    THEMES[_name] = _expand(_title, _icon, _text, _bg)

#: 兼容别名（GRS 原名）
ALIASES = {"default": DEFAULT_NAME, "ambient_gradient": DEFAULT_NAME}


def resolve(acct):
    """按账号解析最终主题 dict。

    优先级：theme_custom 覆盖 > 预设 > 默认。
    未知预设名回退默认（与 trophy 的 parseParams 行为一致）。
    """
    name = (acct.get("theme") or "").strip()
    base = THEMES.get(ALIASES.get(name, name), THEMES[DEFAULT_NAME])
    custom = acct.get("theme_custom") or {}
    if custom:
        merged = dict(base)
        for key, value in custom.items():
            if key in merged:
                merged[key] = value
        return merged
    return base


def available():
    return sorted(THEMES)
