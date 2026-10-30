# -*- coding: utf-8 -*-
"""SVG 卡片渲染：hero / 统计 / 活跃度 / 技能跑马灯 / 作品 / 页脚 / 实时徽章。"""

import math
import re
from urllib.parse import quote

import accounts as A

from .config import STAT_FIELDS
from .data import acct_stats
from .icons import icon_exists, icon_svg_body
from .paths import ROOT
from .textutil import clip_w, esc, fmt_num, rng, seed_of, text_w

def live_badges(acct, lang):
    """实时数字徽章（shields.io）。数字在浏览器渲染时才向 API 取值，仓库不存写死数字。

    实测（2026-10-21）：
      原生徽章  github/stars/<u>、github/followers/<u>        —— 稳定，优先用
      动态徽章  dynamic/json + /users/<u>?query=...           —— GitHub/Gitee/GitCode 均可用
      GitHub 的 repos 走 dynamic/json（原生 repos 端点已下线）。
    """
    plat = acct.get("platform")
    handle = acct.get("handle")
    if not handle:
        return None
    labels = A.LABELS[lang]
    lc, co = "0E1630", "D9B876"          # label 底=面板深蓝, 数值=主题金
    badges = []

    def raw(spec, alt):
        inner = "https://img.shields.io/%s?style=flat&labelColor=%s&color=%s" % (spec, lc, co)
        return '<img src="%s" alt="%s" />' % (inner, esc(alt))

    def dyn(api, query, label, alt):
        inner = ("https://img.shields.io/badge/dynamic/json?url=%s&query=%s&style=flat"
                 "&label=%s&labelColor=%s&color=%s"
                 % (quote(api, safe=""), quote(query, safe=""),
                    quote(label, safe=""), lc, co))
        return '<img src="%s" alt="%s" />' % (inner, esc(alt))

    if plat == "github":
        badges.append(dyn("https://api.github.com/users/%s" % handle, "public_repos",
                          labels["badge_repos"], "%s: %s" % (labels["badge_repos"], handle)))
        badges.append(raw("github/stars/%s" % handle,
                          "%s: %s" % (labels.get("stat_stars", "stars"), handle)))
        badges.append(raw("github/followers/%s" % handle,
                          "%s: %s" % (labels["badge_followers"], handle)))
    # Gitee / GitCode：shields 没有原生端点，dynamic/json 实测稳定返回 invalid
    # （shields 侧访问被拒）。宁可不显示徽章，也不要挂一个 "invalid" 出去；
    # 这两个平台的数字由定时任务刷新进 stats.json，再由统计卡呈现。
    if not badges:
        return None
    joined = "\n  ".join(badges)
    return '<p align="center">\n  %s\n</p>' % joined

def skills_svg(acct, lang, theme=None):
    """技能跑马灯：一行不同大小的图标从左向右连续划过（SMIL 无缝循环，边缘淡入淡出）。

    参考常见 portfolio 的 icon marquee：图标尺寸 20–60px 随机、
    基线上下轻微浮动、少量旋转与透明度变化；内容复制两份首尾相接，
    外层 <animateTransform> 以 strip 宽度平移实现无缝循环。
    """
    t = theme or A.THEME
    labels = A.LABELS[lang]
    names = [s for s in acct.get("skills", []) if s in A.SKILL_LABELS]
    entries = []
    for name in names:
        # simple-icons 是单色图标且不带 fill（默认黑），深色底上不可见 → 指定浅色
        mono = icon_exists(name, prefix="si")
        if icon_svg_body(name, 8) is None:
            continue
        entries.append((name, mono))
    if not entries:
        return None

    W, H = 1200, 206
    r = rng(acct, "skills-marquee-v2")
    sizes = (20, 24, 30, 36, 42, 50, 60)
    baseline = 122
    items = []
    x = 84.0
    for name, mono in entries:
        size = r.choice(sizes)
        dy = r.uniform(-14, 14)          # 上下轻微浮动
        gap = r.uniform(38, 70)
        items.append((name, mono, round(x, 1), round(baseline - size + dy, 1),
                      size, round(r.uniform(0.60, 1.0), 2), round(r.uniform(-5, 5), 1)))
        x += size + gap
    strip = int(x) + 80

    def copy(offset):
        parts = []
        for (name, mono, ix, iy, size, op, rot) in items:
            body = icon_svg_body(name, size, t["star"] if mono else None)
            cx = cy = size / 2.0
            parts.append(
                '<g transform="translate(%.1f,%.1f)" opacity="%.2f">'
                '<g transform="rotate(%.1f %.1f %.1f)">%s</g></g>'
                % (offset + ix, iy, op, rot, cx, cy, body))
        return "".join(parts)

    dur = max(18, round(strip / 30.0, 1))
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{alt}">
<defs>
  <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{panel}"/>
    <stop offset="100%" stop-color="{bg1}"/>
  </linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#fff" stop-opacity="0"/>
    <stop offset="6%" stop-color="#fff" stop-opacity="1"/>
    <stop offset="94%" stop-color="#fff" stop-opacity="1"/>
    <stop offset="100%" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <mask id="fade"><rect x="0" y="0" width="{w}" height="{h}" fill="url(#edge)"/></mask>
</defs>
<rect x="0.75" y="0.75" width="{rw}" height="{rh}" rx="16" fill="url(#panel)" stroke="{gold}" stroke-opacity="0.30" stroke-width="1.5"/>
<text x="{tx}" y="30" text-anchor="end" font-family="{mono}" font-size="11.5" letter-spacing="1.5" fill="{faint}">{note}</text>
<g mask="url(#fade)">
  <g>
    <animateTransform attributeName="transform" type="translate" from="0 0" to="-{strip} 0" dur="{dur}s" repeatCount="indefinite"/>
    {c0}{c1}
  </g>
</g>
</svg>
""".format(
        w=W, h=H, rw=W - 1.5, rh=H - 1.5,
        panel=t["panel"], bg1=t["bg1"], gold=t["gold"], faint=t["faint"],
        mono=A.MONO, tx=W - 34, note=esc(labels["skills_note"]),
        strip=strip, dur=dur, c0=copy(0), c1=copy(strip),
        alt=esc(labels["skills"] + " · " + ", ".join(n for n, _ in entries)),
    )

def works_svg(acct, key, lang, theme=None):
    """作品面板：每件作品一张卡片（图标瓷片 + 名称 + 说明 + 标签胶囊），网格排布。"""
    t = theme or A.THEME
    labels = A.LABELS[lang]
    items = []
    for wid in acct["works"]:
        work = A.WORKS[wid]
        icon_name = A.WORK_ICONS.get(wid, "markdown")
        body = icon_svg_body(icon_name, 26, t["gold_bright"])
        if body is None:
            body = icon_svg_body("github", 26, t["gold_bright"])
        items.append((work["title"], work["desc"][lang], work["tags"][lang], body))
    if not items:
        return None
    cols = 2
    rows = (len(items) + cols - 1) // cols
    cell_w, cell_h = 474, 126
    pad_x, pad_top = 30, 26
    width = pad_x * 2 + cell_w * cols
    height = pad_top + cell_h * rows + 26
    parts = []
    for i, (title, desc, tags, body) in enumerate(items):
        cx = pad_x + (i % cols) * cell_w
        cy = pad_top + (i // cols) * cell_h
        desc_short = clip_w(desc, 356, 12.5)
        inner_w = cell_w - 18
        chips = []
        tx = 80
        for tg in [x.strip() for x in tags.split("·") if x.strip()][:2]:
            cw = round(text_w(tg, 10.5) + 20, 1)
            if tx + cw > inner_w - 12:
                break
            chips.append(
                '<g transform="translate(%s,82)">'
                '<rect x="0" y="0" width="%s" height="20" rx="10" fill="none" stroke="%s" stroke-opacity="0.5"/>'
                '<text x="%s" y="13.5" text-anchor="middle" font-family="%s" font-size="10.5" '
                'letter-spacing="1.6" fill="%s">%s</text>'
                '</g>'
                % (tx, cw, t["gold"], cw / 2, A.MONO, t["gold"], esc(tg.upper()))
            )
            tx += cw + 8
        parts.append(
            '<g transform="translate(%s,%s)">'
            '<rect x="0" y="0" width="%s" height="%s" rx="14" fill="%s" fill-opacity="0.6" '
            'stroke="%s" stroke-opacity="0.30"/>'
            '<rect x="0" y="0" width="4" height="%s" rx="2" fill="url(#accent)"/>'
            '<rect x="20" y="20" width="44" height="44" rx="12" fill="%s" stroke="%s" stroke-opacity="0.4"/>'
            '<g transform="translate(29,29)">%s</g>'
            '<text x="80" y="38" font-family="%s" font-size="16.5" fill="%s">%s</text>'
            '<text x="80" y="63" font-family="%s" font-size="12.5" fill="%s">%s</text>'
            '%s'
            '</g>'
            % (cx, cy, inner_w, cell_h - 16, t["panel2"], t["gold"],
               cell_h - 16, t["bg0"], t["gold"],
               body, A.SERIF, t["ink"], esc(title), A.SANS, t["muted"], desc_short,
               "\n".join(chips))
        )
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{alt}">
<defs>
  <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{panel}"/>
    <stop offset="100%" stop-color="{bg1}"/>
  </linearGradient>
  <linearGradient id="accent" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{indigo}"/>
    <stop offset="100%" stop-color="{teal}"/>
  </linearGradient>
</defs>
<rect x="0.75" y="0.75" width="{rw}" height="{rh}" rx="16" fill="url(#panel)" stroke="{gold}" stroke-opacity="0.30" stroke-width="1.5"/>
{parts}
</svg>
""".format(
        w=width, h=height, rw=width - 1.5, rh=height - 1.5,
        panel=t["panel"], bg1=t["bg1"], gold=t["gold"], ink=t["ink"],
        indigo=t["indigo"], teal=t["teal"],
        serif=A.SERIF, sans=A.SANS,
        parts="\n".join(parts),
        alt=esc(labels["works"] + " · " + ", ".join(x[0] for x in items)),
    )

def activity_svg(acct, key, lang, stats, theme=None):
    """活跃度条：把统计数字画成横向条形图（视觉化替代纯数字堆叠）。"""
    t = theme or A.THEME
    labels = A.LABELS[lang]
    data = acct_stats(stats, key)
    rows = []
    for field in STAT_FIELDS:
        val = data.get(field)
        if val is None:
            continue
        rows.append((labels["stat_%s" % field], int(val)))
    if not rows:
        return None
    top = max(v for _, v in rows) or 1
    width, pad_x = 1000, 34
    bar_x, bar_w = 300, 600
    row_h, pad_top = 46, 48
    height = pad_top + row_h * len(rows) + 26
    parts = []
    for i, (label, val) in enumerate(rows):
        y = pad_top + i * row_h
        frac = max(val / top, 0.012)
        fw = round(bar_w * frac, 1)
        parts.append(
            '<text x="%s" y="%s" text-anchor="end" font-family="%s" font-size="13.5" fill="%s">%s</text>'
            % (bar_x - 18, y + 15, A.MONO, t["muted"], esc(label))
        )
        parts.append(
            '<rect x="%s" y="%s" width="%s" height="14" rx="7" fill="%s"/>'
            % (bar_x, y, bar_w, t["bg1"])
        )
        parts.append(
            '<rect x="%s" y="%s" width="%s" height="14" rx="7" fill="url(#bar)"/>'
            % (bar_x, y, fw)
        )
        parts.append(
            '<text x="%s" y="%s" font-family="%s" font-size="14.5" fill="%s">%s</text>'
            % (bar_x + bar_w + 16, y + 13, A.SERIF, t["gold_bright"], esc(fmt_num(val)))
        )
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{alt}">
<defs>
  <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{panel}"/>
    <stop offset="100%" stop-color="{bg1}"/>
  </linearGradient>
  <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{indigo}" stop-opacity="0.85"/>
    <stop offset="100%" stop-color="{teal}" stop-opacity="0.95"/>
  </linearGradient>
</defs>
<rect x="0.75" y="0.75" width="{rw}" height="{rh}" rx="16" fill="url(#panel)" stroke="{gold}" stroke-opacity="0.30" stroke-width="1.5"/>
<text x="{rx}" y="30" text-anchor="end" font-family="{mono}" font-size="11.5" letter-spacing="1.5" fill="{faint}">{asof}</text>
{parts}
</svg>
""".format(
        w=width, h=height, rw=width - 1.5, rh=height - 1.5,
        panel=t["panel"], bg1=t["bg1"], gold=t["gold"], gold_bright=t["gold_bright"],
        indigo=t["indigo"], teal=t["teal"],
        faint=t["faint"], sans=A.SANS, mono=A.MONO, rx=width - pad_x,
        asof=esc("%s %s" % (labels["as_of"], stats.get("as_of") or "")),
        parts="\n".join(parts), alt=esc(" · ".join("%s: %s" % (l, fmt_num(v)) for l, v in rows)),
    )

def starfield(acct, w, h, n, salt="hero", theme=None):
    r = rng(acct, salt)
    t = theme or A.THEME
    out = []
    for _ in range(n):
        x = round(r.uniform(10, w - 10), 1)
        y = round(r.uniform(8, h - 8), 1)
        rr = round(r.uniform(0.5, 1.5), 1)
        op = round(r.uniform(0.18, 0.95), 2)
        fill = t["gold"] if r.random() < 0.13 else t["star"]
        out.append(
            '<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="%s"/>'
            % (x, y, rr, fill, op)
        )
        # 少量四芒星光（十字亮线），增加层次
        if r.random() < 0.14:
            s = round(r.uniform(3.0, 6.5), 1)
            sp = round(r.uniform(0.35, 0.8), 2)
            out.append(
                '<path d="M%s %s L%s %s M%s %s L%s %s" stroke="%s" stroke-width="0.7" '
                'stroke-linecap="round" opacity="%s"/>'
                % (x, y - s, x, y + s, x - s, y, x + s, y, fill, sp)
            )
    return "\n  ".join(out)

def dipper(acct, w, h, salt="dipper", theme=None):
    r = rng(acct, salt)
    pts = []
    for px, py in DIPPER:
        jx = px + r.uniform(-0.012, 0.012)
        jy = py + r.uniform(-0.02, 0.02)
        pts.append((round(jx * w, 1), round(jy * h, 1)))
    poly = " ".join("%s,%s" % p for p in pts)
    dots = "\n  ".join(
        '<circle cx="%s" cy="%s" r="2.1" fill="%s"><title>·</title></circle>' % (x, y, (theme or A.THEME)["star"])
        for x, y in pts
    )
    return poly, dots

def hero_svg(acct, theme=None):
    w, h = 1200, 430
    poly, dots = dipper(acct, w, h, theme=theme)
    handle = acct["handle"]
    fs = 60 if len(handle) <= 12 else 46
    ls = 8 if len(handle) <= 12 else 6
    t = theme or A.THEME
    grid = "\n  ".join(
        ['<line x1="0" y1="%s" x2="1200" y2="%s" stroke="%s" stroke-opacity="0.045" stroke-width="1"/>' % (y, y, t["star"])
         for y in range(80, h, 70)]
        + ['<line x1="%s" y1="0" x2="%s" y2="%s" stroke="%s" stroke-opacity="0.04" stroke-width="1"/>' % (x, x, h, t["star"])
           for x in range(120, w, 120)]
    )
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 430" width="1200" height="430" role="img" aria-label="{handle} — {home}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#03050C"/>
    <stop offset="52%" stop-color="{bg0}"/>
    <stop offset="100%" stop-color="{bg1}"/>
  </linearGradient>
  <radialGradient id="glow-indigo" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{indigo}" stop-opacity="0.20"/>
    <stop offset="100%" stop-color="{indigo}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glow-teal" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{teal}" stop-opacity="0.14"/>
    <stop offset="100%" stop-color="{teal}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glow-gold" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{gold}" stop-opacity="0.10"/>
    <stop offset="100%" stop-color="{gold}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="name-grad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{gold_bright}"/>
    <stop offset="50%" stop-color="{ink}"/>
    <stop offset="100%" stop-color="{gold}"/>
  </linearGradient>
  <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{gold}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{gold}" stop-opacity="0.6"/>
    <stop offset="100%" stop-color="{gold}" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect width="1200" height="430" fill="url(#sky)"/>
<g>
  {grid}
</g>
<ellipse cx="190" cy="95" rx="420" ry="220" fill="url(#glow-indigo)"/>
<ellipse cx="1010" cy="120" rx="380" ry="210" fill="url(#glow-teal)"/>
<ellipse cx="600" cy="235" rx="520" ry="200" fill="url(#glow-gold)"/>
<g>
  {stars}
</g>
<polyline points="{poly}" fill="none" stroke="{gold}" stroke-opacity="0.32" stroke-width="1.1"/>
<g>
  {dots}
</g>
<text x="600" y="218" text-anchor="middle" font-family="{serif}" font-size="{fs}" letter-spacing="{ls}" fill="url(#name-grad)">{handle}</text>
<text x="600" y="268" text-anchor="middle" font-family="{mono}" font-size="17" letter-spacing="5" fill="{gold}">{home}</text>
<rect x="260" y="318" width="680" height="1.5" fill="url(#rule)"/>
<rect x="592" y="308" width="15" height="15" fill="none" stroke="{gold}" stroke-opacity="0.85" stroke-width="1.3" transform="rotate(45 599 315)"/>
<circle cx="600" cy="346" r="2.2" fill="{gold_bright}" opacity="0.9"/>
<circle cx="571" cy="340" r="1.4" fill="{star}" opacity="0.6"/>
<circle cx="629" cy="340" r="1.4" fill="{star}" opacity="0.6"/>
</svg>
""".format(
        handle=esc(handle), home=esc(acct["home_display"]),
        bg0=t["bg0"], bg1=t["bg1"], gold=t["gold"], gold_bright=t["gold_bright"],
        ink=t["ink"], indigo=t["indigo"], teal=t["teal"], star=t["star"],
        serif=A.SERIF, sans=A.SANS, mono=A.MONO,
        fs=fs, ls=ls, stars=starfield(acct, w, h, 110, theme=theme), poly=poly, dots=dots, grid=grid,
    )


def _bg_fill(theme, key, default):
    """读取背景槽位；值为 "angle,c1,c2,..." 时返回 (gradient_def, url_ref)。"""
    value = theme.get(key) or default
    parts = [x.strip() for x in str(value).split(",")]
    if len(parts) >= 3 and all(x.replace("#", "").isalnum() for x in parts[1:]):
        try:
            angle = float(parts[0])
        except ValueError:
            angle = 35
        import math
        rad = math.radians(angle)
        x2 = round(50 + 50 * math.cos(rad), 1)
        y2 = round(50 + 50 * math.sin(rad), 1)
        stops = "".join('<stop offset="%d%%" stop-color="%s"/>' % (
            round(100 * i / (len(parts) - 2)), c) for i, c in enumerate(parts[1:]))
        gid = "grad-%s" % key
        return ('<linearGradient id="%s" x1="50%%" y1="50%%" x2="%s%%" y2="%s%%">%s</linearGradient>'
                % (gid, x2, y2, stops)), "url(#%s)" % gid
    return "", value

#: GRS rank_icon 三模式（default/github/percentile）
def _rank_icon(mode, level, percentile, t):
    if mode == "github":
        # GitHub Octocat mark（GRS icons.js rankIcon("github") 的 path）
        return ('<svg x="-38" y="-30" height="66" width="66" viewBox="0 0 16 16">'
                '<path fill="%s" d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59'
                'c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48'
                ' 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08'
                '-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27'
                '-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28'
                '-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21'
                '-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19'
                '.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45'
                '-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path></svg>'
                % t["ink"])
    if mode == "percentile":
        return ('<text x="-5" y="-12" text-anchor="middle" font-family="%s" '
                'font-size="11" fill="%s">Top</text>'
                '<text x="-5" y="12" text-anchor="middle" font-family="%s" '
                'font-size="13" fill="%s">%.1f%%</text>'
                % (A.SANS, t["gold_bright"], A.MONO, t["ink"], percentile))
    return ('<text x="-5" y="3" text-anchor="middle" font-family="%s" '
            'font-size="24" font-weight="bold" fill="%s">%s</text>'
            % (A.SANS, t["ink"], esc(level)))


def stats_svg(acct, key, stats, lang, theme=None, rank=None, rank_icon="default"):
    """统计卡：四格数字 + 可选 Rank 进度环（GRS 移植）。

    rank: {"level","percentile"}（kit.rank.calculate_rank 的输出）；None 时不画环。
    rank_icon: "default"（等级字母）| "github"（Octocat）| "percentile"（Top x.x%）。
    """
    t = theme or A.THEME
    labels = A.LABELS[lang]
    data = acct_stats(stats, key)
    cells = []
    for field in STAT_FIELDS:
        val = data.get(field)
        if val is None:
            continue
        label = labels["stat_%s" % field]
        cells.append((fmt_num(val), label))
    if not cells:
        cells = [("—", labels["numbers"])]
    n = len(cells)
    chart_right = 870 if rank else 1000  # rank 环占右侧 130px
    parts = []
    for i, (val, label) in enumerate(cells):
        cx = round(chart_right * (i + 0.5) / n, 1)
        parts.append(
            '<text x="%s" y="96" text-anchor="middle" font-family="%s" font-size="46" fill="url(#num)">%s</text>'
            % (cx, A.SERIF, esc(val))
        )
        parts.append(
            '<text x="%s" y="132" text-anchor="middle" font-family="%s" font-size="12.5" letter-spacing="2.5" fill="%s">%s</text>'
            % (cx, A.MONO, t["muted"], esc(label.upper()))
        )
    for i in range(1, n):
        x = round(chart_right * i / n, 1)
        parts.append(
            '<line x1="%s" y1="48" x2="%s" y2="150" stroke="%s" stroke-opacity="0.14"/>'
            % (x, x, t["gold"])
        )
    as_of = stats.get("as_of") or ""
    foot_left = esc(acct["handle"])
    foot_right = ("%s %s" % (labels["as_of"], as_of)).strip()

    # Rank 环（GRS getStyles + rankCircle 移植）：r=40，进度沿圆周
    rank_svg = ""
    if rank:
        percentile = min(100.0, max(0.0, float(rank.get("percentile", 100))))
        progress = 100 - percentile  # 百分位越低越好
        radius = 40.0
        circumference = math.pi * (radius * 2)
        dash_offset = circumference * (1 - progress / 100.0)
        ring_color = t["teal"]
        rank_svg = (
            '<g transform="translate(%d,%d)">'
            '<circle class="rank-rim" cx="-10" cy="8" r="40" fill="none" '
            'stroke="%s" stroke-width="6" opacity="0.2"/>'
            '<circle class="rank-ring" cx="-10" cy="8" r="40" fill="none" '
            'stroke="%s" stroke-width="6" stroke-linecap="round" opacity="0.8" '
            'stroke-dasharray="%.1f" stroke-dashoffset="%.1f" '
            'transform="rotate(-90 -10 8)"/>'
            '<g class="rank-text">%s</g></g>'
            % (935, 95, ring_color, ring_color, circumference, dash_offset,
               _rank_icon(rank_icon, rank.get("level"), percentile, t))
        )
    # 面板填充：theme_custom 的 bg1 支持渐变（"angle,c1,c2,..."），否则双色 panel→bg1
    panel_grad, panel_fill = _bg_fill(t, "bg1", t["bg1"])
    if panel_grad:
        panel_def = panel_grad
        panel_fill = "url(#grad-bg1)"
    else:
        panel_def = ('<linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">'
                     '<stop offset="0%" stop-color="{}"/>'
                     '<stop offset="100%" stop-color="{}"/></linearGradient>'.format(t["panel"], t["bg1"]))
        panel_fill = "url(#panel)"
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 190" width="1000" height="190" role="img" aria-label="{alt}">
<defs>
  {panel_def}
  <linearGradient id="num" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{gold_bright}"/>
    <stop offset="100%" stop-color="{gold}"/>
  </linearGradient>
</defs>
<rect x="0.75" y="0.75" width="998.5" height="188.5" rx="16" fill="{panel_fill}" stroke="{gold}" stroke-opacity="0.30" stroke-width="1.5"/>
{parts}
{rank_svg}
<text x="26" y="172" font-family="{mono}" font-size="12" letter-spacing="2.5" fill="{faint}">{left}</text>
<text x="974" y="172" text-anchor="end" font-family="{mono}" font-size="12" letter-spacing="1.5" fill="{faint}">{right}</text>
</svg>
""".format(
        alt=esc(" · ".join("%s %s" % (v, l) for v, l in cells)),
        panel_def=panel_def, panel_fill=panel_fill,
        gold=t["gold"], gold_bright=t["gold_bright"], faint=t["faint"],
        sans=A.SANS, mono=A.MONO, parts="\n".join(parts), rank_svg=rank_svg,
        left=foot_left, right=esc(foot_right),
    )

def _lang_color(name, theme):
    """GitHub Linguist 官方色（649 语言，kit/linguist.py）；未知回退主题 indigo。"""
    from .linguist import color_of
    return color_of(name, fallback=theme["indigo"])


def _langs_aggregate(key, discovered):
    """聚合 works.json 的语言分布。返回 (top 列表, total) 或 (None, 0)。"""
    block = ((discovered or {}).get("accounts") or {}).get(key) or {}
    repos = block.get("repos") or []
    counts = {}
    for repo in repos:
        language = (repo.get("language") or "").strip()
        if language:
            counts[language] = counts.get(language, 0) + 1
    if not counts:
        return None, 0
    total = sum(counts.values())
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    return top, total


def _donut_arc(cx, cy, r, start_angle, end_angle):
    """极坐标 → 圆弧 path（GRS polarToCartesian + describeArc 同源）。"""
    import math
    start_rad = math.radians(start_angle - 90)
    end_rad = math.radians(end_angle - 90)
    x1 = cx + r * math.cos(start_rad)
    y1 = cy + r * math.sin(start_rad)
    x2 = cx + r * math.cos(end_rad)
    y2 = cy + r * math.sin(end_rad)
    large = 1 if (end_angle - start_angle) > 180 else 0
    return "M %.2f %.2f A %.2f %.2f 0 %d 1 %.2f %.2f" % (x1, y1, r, r, large, x2, y2)


def _legend_items(top, total, t, start_y, col_gap=232, row_gap=30, start_x=26):
    """两列图例（compact 风格：色点 + 名称 + 百分比）。"""
    items = []
    for i, (name, count) in enumerate(top):
        col, row = i % 2, i // 2
        cx, cy = start_x + col * col_gap, start_y + row * row_gap
        pct = 100.0 * count / total
        items.append(
            '<circle cx="%d" cy="%d" r="4.5" fill="%s"/>'
            '<text x="%d" y="%d" font-family="%s" font-size="12.5" fill="%s">%s</text>'
            '<text x="%d" y="%d" text-anchor="end" font-family="%s" font-size="12" fill="%s">%.1f%%</text>'
            % (cx, cy, _lang_color(name, t),
               cx + 12, cy + 4, A.SANS, t["ink"], esc(name),
               cx + col_gap - 22, cy + 4, A.MONO, t["muted"], pct)
        )
    return items


def langs_svg(key, lang, discovered, theme=None, layout="bar"):
    """语言构成卡：由 works.json 聚合，支持 bar / donut / compact / pie 四布局。

    layout:
      - "bar"（默认）：顶部堆叠条 + 两列图例（历史样式）
      - "donut"：左侧环形图 + 右侧图例（GRS donut-vertical 风格）
      - "compact"：单条堆叠条 + 两列图例（GRS compact 风格）
      - "pie"：左侧扇形图 + 下方图例（GRS pie 风格）
    """
    top, total = _langs_aggregate(key, discovered)
    if not top:
        return None
    t = theme or A.THEME
    labels = A.LABELS[lang]

    if layout == "donut":
        width, height = 500, 230
        cx, cy, r, stroke = 130, 125, 72, 25
        import math as _math
        circumference = 2 * _math.pi * r
        indent = 0.0
        arcs = []
        for name, count in top:
            frac = count / total
            arc_len = circumference * frac
            arcs.append(
                '<circle cx="%d" cy="%d" r="%d" fill="transparent" stroke="%s" '
                'stroke-width="%d" stroke-dasharray="%.2f" stroke-dashoffset="%.2f" '
                'transform="rotate(-90 %d %d)"/>'
                % (cx, cy, r, _lang_color(name, t), stroke, circumference, -indent, cx, cy))
            indent += arc_len
        legend = _legend_items(top, total, t, 60, col_gap=250, start_x=260)
        body = "".join(arcs)
        legend_svg = "\n".join(legend)
    elif layout == "pie":
        width, height = 500, 300
        cx, cy, r = 150, 125, 90
        start = 0.0
        paths = []
        for i, (name, count) in enumerate(top):
            frac = count / total
            if len(top) == 1:
                paths.append('<circle cx="%d" cy="%d" r="%d" fill="%s"/>'
                             % (cx, cy, r, _lang_color(name, t)))
                break
            angle = frac * 360
            end = start + angle
            large = 1 if angle > 180 else 0
            import math as _math
            s_rad = _math.radians(start - 90)
            e_rad = _math.radians(end - 90)
            sx, sy = cx + r * _math.cos(s_rad), cy + r * _math.sin(s_rad)
            ex, ey = cx + r * _math.cos(e_rad), cy + r * _math.sin(e_rad)
            paths.append('<path d="M %.2f %.2f L %.2f %.2f A %.2f %.2f 0 %d 1 %.2f %.2f Z" fill="%s"/>'
                         % (cx, cy, sx, sy, r, r, large, ex, ey, _lang_color(name, t)))
            start = end
        legend = _legend_items(top, total, t, 235, col_gap=232)
        body = "".join(paths)
        legend_svg = "\n".join(legend)
    elif layout == "compact":
        width, height = 500, 180
        bar_x, bar_w, bar_y = 26, width - 52, 62
        segs, x = [], float(bar_x)
        for name, count in top:
            w = (bar_w * count) / total
            segs.append('<rect x="%.1f" y="%d" width="%.1f" height="12" fill="%s"/>'
                        % (x, bar_y, w, _lang_color(name, t)))
            x += w
        legend = _legend_items(top, total, t, 100)
        body = '<mask id="lang-mask"><rect x="%d" y="%d" width="%d" height="12" rx="5" fill="white"/></mask>%s' % (
            bar_x, bar_y, bar_w, "".join(segs))
        legend_svg = "\n".join(legend)
    else:  # bar（默认，历史样式）
        width, height = 500, 220
        bar_x, bar_w, bar_y = 26, width - 52, 62
        segs, x = [], float(bar_x)
        for name, count in top:
            w = (bar_w * count) / total
            segs.append('<rect x="%.1f" y="%d" width="%.1f" height="12" rx="3" fill="%s"/>'
                        % (x, bar_y, max(w - 2, 2), _lang_color(name, t)))
            x += w
        legend = _legend_items(top, total, t, 104)
        body = "\n".join(segs)
        legend_svg = "\n".join(legend)

    panel_grad, panel_fill = _bg_fill(t, "bg1", t["bg1"])
    if panel_grad:
        panel_def = panel_grad
        panel_fill = "url(#grad-bg1)"
    else:
        panel_def = ('<linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">'
                     '<stop offset="0%" stop-color="{}"/>'
                     '<stop offset="100%" stop-color="{}"/></linearGradient>'.format(t["panel"], t["bg1"]))
        panel_fill = "url(#panel)"
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{alt}">
<defs>
  {panel_def}
</defs>
<rect x="0.75" y="0.75" width="{rw}" height="{rh}" rx="16" fill="{panel_fill}" stroke="{gold}" stroke-opacity="0.30" stroke-width="1.5"/>
<text x="26" y="38" font-family="{serif}" font-size="15" fill="{ink}">{title}</text>
<text x="{rx}" y="38" text-anchor="end" font-family="{mono}" font-size="11" letter-spacing="1.2" fill="{faint}">{total} repos</text>
{body}
{legend}
</svg>
""".format(
        w=width, h=height, rw=width - 1.5, rh=height - 1.5,
        panel_def=panel_def, panel_fill=panel_fill,
        gold=t["gold"], ink=t["ink"], faint=t["faint"],
        serif=A.SERIF, mono=A.MONO, rx=width - 26,
        title=esc(labels["langs"]), total=total,
        body=body, legend=legend_svg,
        alt=esc(labels["langs"] + " · " + ", ".join("%s %d" % kv for kv in top)),
    )


def footer_svg(acct, theme=None):
    t = theme or A.THEME
    r = rng(acct, "footer")
    xs = [260, 380, 520, 660, 800, 940]
    ys = [66, 54, 60, 50, 62, 56]
    pts = [(x + round(r.uniform(-6, 6), 1), y + round(r.uniform(-4, 4), 1)) for x, y in zip(xs, ys)]
    poly = " ".join("%s,%s" % p for p in pts)
    dots = "\n  ".join('<circle cx="%s" cy="%s" r="1.8" fill="%s" opacity="0.85"/>' % (x, y, t["star"]) for x, y in pts)
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 130" width="1200" height="130" role="img" aria-label="·">
<defs>
  <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{gold}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{gold}" stop-opacity="0.45"/>
    <stop offset="100%" stop-color="{gold}" stop-opacity="0"/>
  </linearGradient>
</defs>
<line x1="120" y1="18" x2="1080" y2="18" stroke="url(#rule)" stroke-width="1.2"/>
<polyline points="{poly}" fill="none" stroke="{gold}" stroke-opacity="0.22" stroke-width="1"/>
<g>
  {dots}
</g>
<rect x="593" y="92" width="12" height="12" fill="none" stroke="{gold}" stroke-opacity="0.7" stroke-width="1.1" transform="rotate(45 599 98)"/>
<line x1="120" y1="112" x2="1080" y2="112" stroke="url(#rule)" stroke-width="1.2"/>
</svg>
""".format(gold=t["gold"], poly=poly, dots=dots)

DIPPER = [(0.075, 0.62), (0.130, 0.46), (0.190, 0.365), (0.285, 0.42),
          (0.415, 0.27), (0.520, 0.225), (0.635, 0.30)]
