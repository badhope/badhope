# -*- coding: utf-8 -*-
"""GitHub Linguist 语言色表（github-readme-stats 的 languageColors.json 全量移植）。

来源：github/linguist `lib/linguist/languages.yml` 的颜色字段，
经 GRS `scripts/generate-langs-json.js` 提炼成 649 语言的 JSON。
本模块加载 `data/linguist_colors.json`，未知语言回退主题 indigo。
"""

import functools
import json

from .paths import ROOT

_FALLBACK = "#858585"  # GRS 的默认语言色

_COLORS = None


def _load():
    global _COLORS
    if _COLORS is None:
        try:
            _COLORS = json.loads(
                (ROOT / "data" / "linguist_colors.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _COLORS = {}
    return _COLORS


@functools.lru_cache(maxsize=512)
def color_of(language, fallback=None):
    """查询语言官方色。language 大小写不敏感。"""
    if not language:
        return fallback or _FALLBACK
    colors = _load()
    if language in colors:
        return colors[language]
    lowered = language.lower()
    for name, hex_color in colors.items():
        if name.lower() == lowered:
            return hex_color
    return fallback or _FALLBACK
