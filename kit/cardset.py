# -*- coding: utf-8 -*-
"""内置卡片注册：把 cards.py 的各个渲染函数登记进插件表。

新增卡片只需要在这里加一个 `@card(...)`，`build.py` 完全不需要改。
`when` 回调让"有种子才渲染"这类条件也变成声明式配置。
"""

import accounts as A

from . import cards
from .rank import derive_profile
from .textutil import esc
from .achievements import achievements_svg as _achievements_svg
from .badge import make_badge
from .data import _snake_available
from .emoji import parse_emojis
from .plugins import card
from .snake import generate as snake_generate
from .typing import typing_svg
from .wakatime import fetch_stats as _wakatime_fetch, wakatime_svg as _wakatime_svg


@card("hero", "hero.svg", per_lang=False, priority=10)
def _hero(acct, key, lang, ctx):
    return cards.hero_svg(acct, theme=ctx["theme"])


@card("footer", "footer.svg", per_lang=False, priority=20)
def _footer(acct, key, lang, ctx):
    return cards.footer_svg(acct, theme=ctx["theme"])


@card("stats", "stats-{lang}.svg", priority=30, slug=True)
def _stats(acct, key, lang, ctx):
    # Rank 环数据：统一走 rank.derive_profile（与成就卡同源）
    block = (ctx["stats"].get("accounts") or {}).get(key) or {}
    repos_block = (ctx.get("discovered") or {}).get("accounts", {}).get(key) or {}
    derived = derive_profile(block, repos_block.get("repos") or [])
    rank_icon = (acct.get("cards") or {}).get("rank_icon", "default")
    return cards.stats_svg(acct, key, ctx["stats"], lang, theme=ctx["theme"],
                           rank=derived["rank"], rank_icon=rank_icon)


@card("skills", "skills-{lang}.svg", priority=40)
def _skills(acct, key, lang, ctx):
    return cards.skills_svg(acct, lang, theme=ctx["theme"])


@card("works", "works-{lang}.svg", priority=50)
def _works(acct, key, lang, ctx):
    return cards.works_svg(acct, key, lang, theme=ctx["theme"])


@card("activity", "activity-{lang}.svg", priority=60)
def _activity(acct, key, lang, ctx):
    return cards.activity_svg(acct, key, lang, ctx["stats"], theme=ctx["theme"])


@card("langs", "langs-{lang}.svg", priority=70,
      when=lambda acct, ctx: bool((ctx.get("discovered") or {}).get("accounts", {})
                                  .get(ctx["key"], {}).get("repos")))
def _langs(acct, key, lang, ctx):
    layout = (acct.get("cards") or {}).get("langs_layout", "bar")
    return cards.langs_svg(key, lang, ctx.get("discovered"), theme=ctx["theme"],
                           layout=layout if layout in ("bar", "donut", "compact", "pie") else "bar")


@card("achievements", "achievements-{lang}.svg", priority=80, slug=True,
      when=lambda acct, ctx: bool(ctx["stats"].get("accounts", {}).get(ctx["key"])))
def _achievements(acct, key, lang, ctx):
    return _achievements_svg(acct, key, ctx["stats"], lang,
                             discovered=ctx.get("discovered"), theme=ctx["theme"])


@card("typing", "typing-{lang}.svg", priority=90)
def _typing(acct, key, lang, ctx):
    """打字机格言卡（readme-typing-svg 移植）。颜色由 typing 内部取 theme。"""
    lines = [parse_emojis(acct["tagline"][lang])]
    return typing_svg(lines, lang=lang, theme=ctx["theme"],
                      options={"background": "#00000000",
                               "width": 600, "height": 60})


@card("statbadges", "badges-{lang}.svg", priority=95, slug=True,
      when=lambda acct, ctx: acct.get("platform") in ("gitcode", "gitee"))
def _stat_badges(acct, key, lang, ctx):
    """自渲染徽章行（shields 移植）：GitCode/Gitee 没有 shields 端点可用。"""
    block = (ctx["stats"].get("accounts") or {}).get(key) or {}
    labels = A.LABELS[lang]
    svgs = []
    for field, label in (
        ("repos", labels["badge_repos"]),
        ("stars", labels.get("stat_stars", "stars")),
        ("followers", labels["badge_followers"]),
    ):
        value = block.get(field)
        if value is None:
            continue
        color = {"repos": "blue", "stars": "yellow", "followers": "green"}.get(field, "blue")
        svgs.append(make_badge(label, str(value), style="flat", color=color))
    if not svgs:
        return None
    gap = 8
    total = sum(int(s.split('width="', 1)[1].split('"')[0]) for s in svgs) + gap * (len(svgs) - 1)
    x = 0
    parts = []
    for svg in svgs:
        w = int(svg.split('width="', 1)[1].split('"')[0])
        inner = svg.split('>', 1)[1].rsplit('</svg>', 1)[0]
        parts.append('<g transform="translate(%d,0)">%s</g>' % (x, inner))
        x += w + gap
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="20" '
            'role="img" aria-label="badges">%s</svg>' % (total, "".join(parts)))


@card("snake", "snake-{lang}.svg", priority=85,
      when=lambda acct, ctx: acct.get("platform") == "github"
      and (acct.get("snake") is not False))
def _snake(acct, key, lang, ctx):
    """贡献蛇动画（Platane/snk 移植，tokenless HTML 抓取）。"""
    try:
        svg, _grid = snake_generate(acct["handle"], palette=acct.get("snake_palette", "aurora"),
                                    theme=ctx["theme"])
        return svg
    except (OSError, ValueError):
        return None


@card("wakatime", "wakatime-{lang}.svg", priority=100,
      when=lambda acct, ctx: bool(acct.get("wakatime")))
def _wakatime(acct, key, lang, ctx):
    stats = _wakatime_fetch()
    return _wakatime_svg((stats or {}).get("data") and stats, lang=lang, theme=ctx["theme"])
