# -*- coding: utf-8 -*-
"""profile kit —— 静态个人主页资产编译器。

分层：textutil（纯函数）→ icons → cards → readme → build → pack/preview → cli。
所有子模块按需加载；包级属性使用 PEP 562 惰性导出，import kit 不会触发渲染。
"""

import importlib

__version__ = "2.0.0"

_EXPORTS = {
    "esc": ("textutil", "esc"),
    "clip_w": ("textutil", "clip_w"),
    "clip_text": ("textutil", "clip_text"),
    "fmt_num": ("textutil", "fmt_num"),
    "icon_svg_body": ("icons", "icon_svg_body"),
    "hero_svg": ("cards", "hero_svg"),
    "stats_svg": ("cards", "stats_svg"),
    "activity_svg": ("cards", "activity_svg"),
    "skills_svg": ("cards", "skills_svg"),
    "works_svg": ("cards", "works_svg"),
    "footer_svg": ("cards", "footer_svg"),
    "render_readme": ("readme", "render_readme"),
    "write_account_files": ("build", "write_account_files"),
    "pack": ("pack", "pack"),
    "build_preview": ("preview", "build_preview"),
}


def __getattr__(name):
    if name in _EXPORTS:
        module, attr = _EXPORTS[name]
        mod = importlib.import_module("." + module, __name__)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(name)
