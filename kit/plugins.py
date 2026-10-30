# -*- coding: utf-8 -*-
"""卡片插件注册表。

参考 lowlighter/metrics 的插件模型：新增一种卡片 = 新增一个注册项，
`build.py` 不再认识任何具体卡片。每个插件用声明式元数据描述自己：

    @card("stats", "stats-{lang}.svg", per_lang=True)
    def stats_card(acct, key, lang, ctx): ...

- `per_lang`：是否为每种语言各出一份（文件名里的 `{lang}` 会被替换）
- `when`：启用条件（例如只有存在贡献图种子时才生成 snake）
- `priority`：渲染顺序，仅影响日志，不影响产物

`REGISTRY` 是有序列表；`describe()` 供 `verify.py` 与文档生成使用。
"""

import dataclasses
from typing import Callable, Optional


@dataclasses.dataclass(frozen=True)
class CardSpec:
    name: str
    filename: str
    producer: Callable
    per_lang: bool = True
    when: Optional[Callable] = None
    priority: int = 100
    # True 时文件名里的 {lang} 用 A.STATS_NAME 的英文 slug（md→en）；
    # 其余卡片沿用内部语言键（skills-md.svg），与 README 引用保持一致。
    slug: bool = False

    def enabled(self, acct, ctx):
        # 逐卡开关：ACCOUNTS[key]["cards"]["<name>"] = False 时跳过该卡
        cards_cfg = acct.get("cards") or {}
        if cards_cfg.get(self.name) is False:
            return False
        return True if self.when is None else bool(self.when(acct, ctx))


# 产物文件名里的语言段：README 用 stats-en.svg，但内部语言键是 md
_LANG_SLUG = {"md": "en", "zh-CN": "zh-CN", "ja": "ja"}

REGISTRY = []


def _ensure_loaded():
    """导入内置卡片集（幂等）。放在这里而不是模块顶层，避免与 cards 循环依赖。"""
    if not REGISTRY:
        from . import cardset  # noqa: F401


def card(name, filename, per_lang=True, when=None, priority=100, slug=False):
    def deco(fn):
        REGISTRY.append(CardSpec(name, filename, fn, per_lang, when, priority, slug))
        REGISTRY.sort(key=lambda spec: (spec.priority, spec.name))
        return fn
    return deco


def describe():
    _ensure_loaded()
    return [{"name": s.name, "filename": s.filename, "per_lang": s.per_lang,
             "priority": s.priority} for s in REGISTRY]


def filenames(acct, ctx):
    """该账号应产出的卡片文件名集合（用于清理过期文件）。"""
    _ensure_loaded()
    names = set()
    for spec in REGISTRY:
        if not spec.enabled(acct, ctx):
            continue
        if spec.per_lang:
            names.update(spec.filename.format(lang=_LANG_SLUG.get(lang, lang) if spec.slug else lang)
                         for lang in ("md", "zh-CN", "ja"))
        else:
            names.add(spec.filename)
    return names


def _error_svg(name, err):
    """GRS renderError 的移植：单卡失败时渲染占位卡而不是炸掉整个构建。"""
    import xml.sax.saxutils as xu
    message = xu.escape(str(err), {'"': "&quot;"})
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="120" '
            'role="img"><rect width="480" height="120" rx="4.5" fill="#0E1630"/>'
            '<text x="24" y="45" font-family="Segoe UI,Ubuntu,sans-serif" font-size="16" '
            'fill="#F2DC9E">card failed: %s</text>'
            '<text x="24" y="75" font-family="Segoe UI,Ubuntu,sans-serif" font-size="11" '
            'fill="#9AA8CC">%s</text></svg>' % (name, message))


def render_all(acct, key, lang, ctx):
    """按 lang 渲染全部 per_lang 插件，返回 [(filename, svg)]。

    `{lang}` 会被替换成输出文件名里的语言段（md→en，其余原样），
    与 README 的 `assets/stats-en.svg` 等引用保持一致。
    """
    _ensure_loaded()
    out = []
    for spec in REGISTRY:
        if not spec.per_lang or not spec.enabled(acct, ctx):
            continue
        try:
            svg = spec.producer(acct, key, lang, ctx)
        except Exception as err:  # noqa: BLE001 —— 单卡失败降级为占位卡（metrics 模式）
            svg = _error_svg(spec.name, err)
        if svg:
            name = spec.filename.format(lang=_LANG_SLUG.get(lang, lang) if spec.slug else lang)
            out.append((name, svg))
    return out


def render_static(acct, key, ctx):
    """渲染非 per_lang 插件（hero / footer / snake 等），返回 [(filename, svg)]。"""
    _ensure_loaded()
    out = []
    for spec in REGISTRY:
        if spec.per_lang or not spec.enabled(acct, ctx):
            continue
        try:
            svg = spec.producer(acct, key, None, ctx)
        except Exception as err:  # noqa: BLE001
            svg = _error_svg(spec.name, err)
        if svg:
            out.append((spec.filename, svg))
    return out
