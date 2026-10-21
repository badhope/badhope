#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主页面 kit 生成器 —— 纯 stdlib、离线可跑、输出确定。

用法：
  python scripts/generate.py --all --out dist         # 五个账号全量生成
  python scripts/generate.py --account gh_badhope --out dist
  python scripts/generate.py --pack gh_badhope --out pack/gh_badhope
  python scripts/generate.py --here                   # 在已部署仓库内原地重建
  python scripts/generate.py --preview                # 生成 dist/ 与 preview/index.html

约定：
- README 里的 <img> 只指向仓库内 ./assets/*.svg（自包含，各平台渲染一致）。
- 星域坐标由 CRC32(账号 key) 固定种子生成 —— 同一输入两次运行字节一致。
- 数字来自 data/stats.json（由 scripts/refresh.py 刷新）；本脚本从不联网。
"""

import argparse
import datetime
import json
import pathlib
import random
import re
import shutil
import sys
import xml.sax.saxutils as xu
import zlib
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import accounts as A  # noqa: E402

STAT_FIELDS = ("repos", "stars", "followers", "merged")
PLATFORM_LABEL = {"github": "GitHub", "gitcode": "GitCode", "gitee": "Gitee"}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def esc(text):
    return xu.escape(str(text), {'"': "&quot;"})


def seed_of(acct):
    return zlib.crc32(acct["home_display"].encode("utf-8"))


def rng(acct, salt=""):
    return random.Random(seed_of(acct) ^ zlib.crc32(salt.encode("utf-8")))


def fmt_num(v):
    try:
        return format(int(v), ",")
    except (TypeError, ValueError):
        return str(v)


def text_w(text, size):
    """估算文本宽度：拉丁/符号按 0.6em，CJK 按 1.0em（等宽标签用）。"""
    total = 0.0
    for ch in text:
        total += size if ord(ch) > 0x2E80 else size * 0.6
    return total


def clip_w(text, max_w, size):
    """按估算像素宽度裁剪文本（CJK 1.0em / 拉丁 0.6em），超出以 … 结尾。"""
    out, used = [], 0.0
    for ch in text:
        cw = size if ord(ch) > 0x2E80 else size * 0.6
        if used + cw > max_w:
            return "".join(out).rstrip() + "…"
        out.append(ch)
        used += cw
    return "".join(out)


def live_badges(acct, lang):
    """实时数字徽章行（shields.io，国内实测可达）：repos / followers。

    平台公开 API（未认证可读，实测 200）：
      GitHub  https://api.github.com/users/<handle>    -> public_repos, followers
      GitCode https://api.gitcode.com/api/v5/users/<handle> -> followers
    实测限制（2026-10-18）：
      - Gitee：shields.io 服务器无法访问 gitee.com（动态徽章返回 invalid），
        故 Gitee 不输出徽章，数字仍由定时任务刷新。
      - GitHub 原生 github/followers 徽章带 label 参数会失效，统一走 dynamic/json。
      - GitCode 用户端点不含仓库数。
    stars/merged 无公开实时聚合接口，这两个数字仍由定时任务刷新（data/stats.json）。
    """
    plat = acct.get("platform")
    handle = acct.get("handle")
    if not handle or plat == "gitee":
        return None
    labels = A.LABELS[lang]
    lc, co = "0E1630", "D9B876"          # label 底=面板深蓝, 数值=主题金
    style = "flat"
    badges = []

    def dyn(url, query, label):
        inner = ("https://img.shields.io/badge/dynamic/json?url=%s&query=%s&style=%s"
                 "&label=%s&labelColor=%s&color=%s"
                 % (quote(url, safe=""), quote(query, safe=""), style,
                    quote(label, safe=""), lc, co))
        return '<img src="%s" alt="%s" />' % (inner, esc("%s: %s" % (label, handle)))

    if plat == "github":
        badges.append(dyn("https://api.github.com/users/%s" % handle,
                          "public_repos", labels["badge_repos"]))
        badges.append(dyn("https://api.github.com/users/%s" % handle,
                          "followers", labels["badge_followers"]))
    elif plat == "gitcode":
        badges.append(dyn("https://api.gitcode.com/api/v5/users/%s" % handle,
                          "followers", labels["badge_followers"]))
    if not badges:
        return None
    return '<p align="center">\n  %s\n</p>' % "\n  ".join(badges)


def copy_icon_light(src, dst, color):
    """拷贝图标并确保其在深色底上可见。

    simple-icons 的 SVG 不带 fill（默认黑色），在深色 README 上不可见；
    这里给根元素补一个浅色 fill（仅当图标自身未指定）。
    """
    text = src.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"<svg\b[^>]*>", text)
    if m and "fill=" not in m.group(0):
        text = text.replace(m.group(0), m.group(0)[:-1] + ' fill="%s">' % color, 1)
    dst.write_text(text, encoding="utf-8", newline="\n")


def icon_svg_body(name, size, color=None):
    """取 vendored 图标的内部图形（path/circle/...），返回可直接内联的片段。

    图标来源 devicon / simple-icons（纯几何元素，无 <style>/<class>），
    以嵌套 <svg> 承载：外层给尺寸与配色，内层保留原始 viewBox 与路径。
    color 为 None 时保留图标自身配色；否则以单色填充覆盖（外层 fill 继承）。

    个别图标（dev-go）带 xlink:href 引用，内联时须补命名空间声明，
    否则整份 SVG 会因 unbound prefix 解析失败。
    """
    path = None
    for prefix in A.ICON_PREFIXES:
        cand = ROOT / "data" / "icons" / ("%s-%s.svg" % (prefix, name))
        if cand.is_file():
            path = cand
            break
    if path is None:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<svg[^>]*viewBox=\"([^\"]+)\"[^>]*>(.*)</svg>", text, re.S)
    if not m:
        return None
    viewbox, body = m.group(1), m.group(2).strip()
    ns = ' xmlns:xlink="http://www.w3.org/1999/xlink"' if "xlink:" in body else ""
    style = ' fill="%s"' % color if color else ""
    return ('<svg x="0" y="0" width="%s" height="%s" viewBox="%s"%s%s>%s</svg>'
            % (size, size, viewbox, ns, style, body))


def skills_svg(acct, lang):
    """技能跑马灯：一行不同大小的图标从左向右连续划过（SMIL 无缝循环，边缘淡入淡出）。

    参考常见 portfolio 的 icon marquee：图标尺寸 20–60px 随机、
    基线上下轻微浮动、少量旋转与透明度变化；内容复制两份首尾相接，
    外层 <animateTransform> 以 strip 宽度平移实现无缝循环。
    """
    t = A.THEME
    labels = A.LABELS[lang]
    names = [s for s in acct.get("skills", []) if s in A.SKILL_LABELS]
    entries = []
    for name in names:
        # simple-icons 是单色图标且不带 fill（默认黑），深色底上不可见 → 指定浅色
        mono = (ROOT / "data" / "icons" / ("si-%s.svg" % name)).is_file()
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


def works_svg(acct, key, lang):
    """作品面板：每件作品一张卡片（图标瓷片 + 名称 + 说明 + 标签胶囊），网格排布。"""
    t = A.THEME
    labels = A.LABELS[lang]
    items = []
    for wid in acct["works"]:
        work = A.WORKS[wid]
        icon_name = A.WORK_ICONS.get(wid, "markdown")
        body = icon_svg_body(icon_name, 26, A.THEME["gold_bright"])
        if body is None:
            body = icon_svg_body("github", 26, A.THEME["gold_bright"])
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


def activity_svg(acct, key, lang, stats):
    """活跃度条：把统计数字画成横向条形图（视觉化替代纯数字堆叠）。"""
    t = A.THEME
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


def load_stats(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"as_of": "", "accounts": {}}


def acct_stats(stats, key):
    return (stats.get("accounts") or {}).get(key) or {}


SNAKE_NAMES = ("github-contribution-grid-snake.svg", "github-contribution-grid-snake-dark.svg")
CARD_NAMES = {
    "stats": "cards/stats-%s.svg",
    "langs": "cards/langs-%s.svg",
    "pin": "cards/pin-%s.svg",
}


def load_card_seed(key, kind, lang, base=None):
    """官方卡片种子（data/cards/<key>/<kind>-<locale>.svg，由 scripts/render_cards.mjs 产出）。

    缺失时返回 None —— README 渲染随之降级，绝不产生裂图或外链（R7/S7.2）。
    base 允许在部署仓库内（--here）从该目录的 data/cards 读取。
    """
    name = CARD_NAMES[kind] % A.CARD_LOCALE[lang]
    roots = [ROOT] if base is None else [base, ROOT]
    for root in roots:
        p = root / "data" / "cards" / key / pathlib.Path(name).name
        if p.is_file():
            return p
    return None


def cards_dir_for(key, base):
    """卡片种子目录：优先部署仓库内的一份（--here 自包含），否则用 kit 源。"""
    if base:
        local = pathlib.Path(base) / "data" / "cards" / key
        if local.is_dir():
            return local
    return ROOT / "data" / "cards" / key


def load_writing_items():
    """读取 data/writing.json（refresh.py 维护）。缺失/损坏时返回空列表。"""
    try:
        data = json.loads((ROOT / "data" / "writing.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [it for it in (data.get("items") or []) if it.get("title") and it.get("url")]


# --------------------------------------------------------------------------
# SVG assets
# --------------------------------------------------------------------------
def starfield(acct, w, h, n, salt="hero"):
    r = rng(acct, salt)
    t = A.THEME
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


DIPPER = [(0.075, 0.62), (0.130, 0.46), (0.190, 0.365), (0.285, 0.42),
          (0.415, 0.27), (0.520, 0.225), (0.635, 0.30)]


def dipper(acct, w, h, salt="dipper"):
    r = rng(acct, salt)
    pts = []
    for px, py in DIPPER:
        jx = px + r.uniform(-0.012, 0.012)
        jy = py + r.uniform(-0.02, 0.02)
        pts.append((round(jx * w, 1), round(jy * h, 1)))
    poly = " ".join("%s,%s" % p for p in pts)
    dots = "\n  ".join(
        '<circle cx="%s" cy="%s" r="2.1" fill="%s"><title>·</title></circle>' % (x, y, A.THEME["star"])
        for x, y in pts
    )
    return poly, dots


def hero_svg(acct):
    w, h = 1200, 430
    poly, dots = dipper(acct, w, h)
    handle = acct["handle"]
    fs = 60 if len(handle) <= 12 else 46
    ls = 8 if len(handle) <= 12 else 6
    t = A.THEME
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
        fs=fs, ls=ls, stars=starfield(acct, w, h, 110), poly=poly, dots=dots, grid=grid,
    )


def stats_svg(acct, key, stats, lang):
    t = A.THEME
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
    parts = []
    for i, (val, label) in enumerate(cells):
        cx = round(1000 * (i + 0.5) / n, 1)
        parts.append(
            '<text x="%s" y="96" text-anchor="middle" font-family="%s" font-size="46" fill="url(#num)">%s</text>'
            % (cx, A.SERIF, esc(val))
        )
        parts.append(
            '<text x="%s" y="132" text-anchor="middle" font-family="%s" font-size="12.5" letter-spacing="2.5" fill="%s">%s</text>'
            % (cx, A.MONO, t["muted"], esc(label.upper()))
        )
    for i in range(1, n):
        x = round(1000 * i / n, 1)
        parts.append(
            '<line x1="%s" y1="48" x2="%s" y2="150" stroke="%s" stroke-opacity="0.14"/>'
            % (x, x, t["gold"])
        )
    as_of = stats.get("as_of") or ""
    foot_left = esc(acct["handle"])
    foot_right = ("%s %s" % (labels["as_of"], as_of)).strip()
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 190" width="1000" height="190" role="img" aria-label="{alt}">
<defs>
  <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{panel}"/>
    <stop offset="100%" stop-color="{bg1}"/>
  </linearGradient>
  <linearGradient id="num" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{gold_bright}"/>
    <stop offset="100%" stop-color="{gold}"/>
  </linearGradient>
</defs>
<rect x="0.75" y="0.75" width="998.5" height="188.5" rx="16" fill="url(#panel)" stroke="{gold}" stroke-opacity="0.30" stroke-width="1.5"/>
{parts}
<text x="26" y="172" font-family="{mono}" font-size="12" letter-spacing="2.5" fill="{faint}">{left}</text>
<text x="974" y="172" text-anchor="end" font-family="{mono}" font-size="12" letter-spacing="1.5" fill="{faint}">{right}</text>
</svg>
""".format(
        alt=esc(" · ".join("%s %s" % (v, l) for v, l in cells)),
        panel=t["panel"], bg1=t["bg1"], gold=t["gold"], gold_bright=t["gold_bright"], faint=t["faint"],
        sans=A.SANS, mono=A.MONO, parts="\n".join(parts), left=foot_left, right=esc(foot_right),
    )


def footer_svg(acct):
    t = A.THEME
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


# --------------------------------------------------------------------------
# README rendering
# --------------------------------------------------------------------------
def pr_links(repo_url, nums):
    return " · ".join("[#%s](%s/pull/%s)" % (n, repo_url, n) for n in nums)


def render_contrib(acct, key, lang):
    labels = A.LABELS[lang]
    kind = acct["contrib"]
    if kind == "shared":
        links = " · ".join("[%s](%s)" % (h, u) for h, u in A.GITHUB_ACCOUNTS_FOR_SHARED)
        return "%s: %s" % (labels["shared_line"], links)
    block = A.CONTRIB["own"][key]
    out = ["**%s**" % labels["merged_heading"]]
    for repo, url, nums, note in block["merged"]:
        out.append("- [%s](%s) — %s — %s" % (repo, url, pr_links(url, nums), note))
    out.append("")
    out.append("**%s**" % labels["review_heading"])
    for repo, url, nums, note in block["review"]:
        out.append("- [%s](%s) — %s — %s" % (repo, url, pr_links(url, nums), note))
    return "\n".join(out)


def clip_text(text, max_em):
    """按保守字宽（拉丁 0.55em / CJK 1.0em）裁剪文本，超出以 … 结尾。"""
    out, used = [], 0.0
    for ch in text:
        w = 1.0 if ord(ch) > 0x2E80 else 0.55
        if used + w > max_em:
            return "".join(out).rstrip() + "…"
        out.append(ch)
        used += w
    return text


def render_readme(acct, key, lang, stats, base=None):
    labels = A.LABELS[lang]
    tagline = acct["tagline"][lang]
    lines = []
    lines.append("[English](README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md)")
    lines.append("")
    lines.append('<p align="center">')
    # hero 用 <picture> 提供 PNG 兜底：GitHub camo / GitCode raw 对 SVG 的支持不稳定，
    # PNG 是位图，各平台渲染策略一致，优先使用。
    lines.append('  <picture>')
    lines.append('  <source type="image/png" srcset="./assets/png/hero.png" />')
    lines.append('  <img src="./assets/hero.svg" alt="%s · %s" width="100%%" />'
                 % (esc(acct["handle"]), esc(acct["home_display"])))
    lines.append('  </picture>')
    lines.append("</p>")
    lines.append("")
    lines.append("<p align=\"center\"><i>%s</i></p>" % tagline)
    lines.append("")
    quote = A.QUOTES[(datetime.date.today().month - 1) % len(A.QUOTES)]
    quote_text = quote["zh"] if lang == "zh-CN" else quote["en"]
    author = quote.get("author") or ""
    suffix = "" if author in ("", "—") else " — %s" % author
    lines.append('<p align="center"><sub>%s%s</sub></p>' % (quote_text, suffix))
    lines.append("")

    # ---- 两栏面板：About | Now（结构化排版，避免长文堆叠） ----
    lines.append('<table border="0">')
    lines.append("<tr>")
    lines.append('<td valign="top" width="58%">')
    lines.append("")
    lines.append("### %s" % labels["about"])
    lines.append("")
    lines.append(acct["about"][lang])
    lines.append("")
    lines.append("</td>")
    lines.append('<td valign="top" width="42%">')
    lines.append("")
    lines.append("### %s" % labels["now"])
    lines.append("")
    for item in acct["now"][lang]:
        lines.append("- %s" % item)
    lines.append("")
    lines.append("</td>")
    lines.append("</tr>")
    lines.append("</table>")
    lines.append("")

    # ---- 技能矩阵（图标网格，本地资产） ----
    lines.append("## %s" % labels["skills"])
    lines.append("")
    lines.append('<p align="center">')
    lines.append('  <img src="./assets/skills-%s.svg" alt="%s" width="100%%" />' % (lang, esc(labels["skills"])))
    lines.append("</p>")
    lines.append("")

    # ---- 作品卡片网格 ----
    lines.append("## %s" % labels["works"])
    lines.append("")
    lines.append('<p align="center">')
    lines.append('  <img src="./assets/works-%s.svg" alt="%s" width="100%%" />' % (lang, esc(labels["works"])))
    lines.append("</p>")
    lines.append("")
    links_row = " · ".join(
        '<a href="%s">%s</a>' % (esc(A.work_url(wid, acct)), esc(A.WORKS[wid]["title"]))
        for wid in acct["works"]
    )
    lines.append('<p align="center"><sub>%s</sub></p>' % links_row)
    lines.append("")
    lines.append("%s [%s](%s)" % (labels["all_repos"], acct["home_display"], acct["home"]))
    lines.append("")

    # ---- 数据面板：官方卡片（有种子时）否则自绘统计卡 ----
    lines.append("## %s" % labels["numbers"])
    lines.append("")
    # 实时徽章行（shields.io）：repos / followers 每次加载即时刷新
    badge_row = live_badges(acct, lang)
    if badge_row:
        lines.append(badge_row)
        lines.append("")
    data = acct_stats(stats, key)
    alt_bits = []
    for field in STAT_FIELDS:
        val = data.get(field)
        if val is not None:
            alt_bits.append("%s %s" % (fmt_num(val), labels["stat_%s" % field]))
    alt = " · ".join(alt_bits) if alt_bits else labels["numbers"]
    card_stats = load_card_seed(key, "stats", lang, base)
    card_langs = load_card_seed(key, "langs", lang, base)
    lines.append('<p align="center">')
    if card_stats and card_langs:
        lines.append('  <img src="./assets/cards/stats-%s.svg" alt="GitHub stats" width="49%%" />'
                     % A.CARD_LOCALE[lang])
        lines.append('  <img src="./assets/cards/langs-%s.svg" alt="Top languages" width="49%%" />'
                     % A.CARD_LOCALE[lang])
    elif card_stats:
        lines.append('  <img src="./assets/cards/stats-%s.svg" alt="GitHub stats" width="70%%" />'
                     % A.CARD_LOCALE[lang])
    else:
        lines.append('  <img src="./assets/%s" alt="%s" width="80%%" />' % (A.STATS_NAME[lang], esc(alt)))
    lines.append("</p>")
    lines.append("")
    # 活跃度条与官方 stats 卡展示同一批数字 → 有官方卡时不再重复（避免冗余堆叠）
    if not card_stats:
        lines.append('<p align="center">')
        lines.append('  <img src="./assets/activity-%s.svg" alt="%s" width="100%%" />' % (lang, esc(alt)))
        lines.append("</p>")
        lines.append("")

    # ---- 置顶作品（官方 pin 卡；仅有种子时出现） ----
    pin_rows = []
    for slot in range(1, 4):
        cand = (pathlib.Path(base) if base else ROOT) / "data" / "cards" / key / ("pin-%d-%s.svg" % (slot, A.CARD_LOCALE[lang]))
        if cand.is_file():
            pin_rows.append(cand.name)
    if pin_rows:
        lines.append("## %s" % labels["pinned"])
        lines.append("")
        lines.append('<p align="center">')
        for name in pin_rows:
            lines.append('  <img src="./assets/cards/%s" alt="pinned work" width="32%%" />' % name)
        lines.append("</p>")
        lines.append("")

    if acct.get("contrib_graph"):
        lines.append("## %s" % labels["contrib_graph"])
        lines.append("")
        lines.append('<p align="center">')
        lines.append('  <picture>')
        # 缩进不得超过 3 空格：HTML 块内 4 空格缩进在部分 Markdown 解析器会被当成代码文本
        lines.append('  <source media="(prefers-color-scheme: dark)" srcset="./assets/github-contribution-grid-snake-dark.svg" />')
        lines.append('  <img src="./assets/github-contribution-grid-snake.svg" alt="contribution snake" width="100%" />')
        lines.append('  </picture>')
        lines.append("</p>")
        lines.append("")

    # ---- 开源足迹（表格式，非散文） ----
    lines.append("## %s" % labels["contrib"])
    lines.append("")
    lines.append(render_contrib(acct, key, lang))
    lines.append("")

    # ---- 写作（日期 | 文章 两列表） ----
    lines.append("## %s" % labels["writing"])
    lines.append("")
    writing_items = load_writing_items()
    if writing_items:
        lines.append("| %s | %s |" % (labels["date"], labels["article"]))
        lines.append("|---|---|")
        for item in writing_items[:5]:
            lines.append("| %s | [%s](%s) |"
                         % (item.get("date") or "—", item["title"], item["url"]))
        lines.append("")
    platform_bits = " · ".join(
        '<img src="./assets/icons/%s" width="15" alt="%s" /> <a href="%s">%s</a>'
        % (icon, esc(name), esc(url), esc(name))
        for name, url, icon in A.WRITING
    )
    lines.append("<sub>%s %s</sub>" % (esc(labels["also_on"]), platform_bits))
    lines.append("")

    # ---- 在别处（宽表格，窄屏可横向滑动） ----
    lines.append("## %s" % labels["elsewhere"])
    lines.append("")
    lines.append("> %s" % labels["mirror_note"])
    lines.append("")
    lines.append("| | %s | %s | %s |" % (labels["platform"], labels["account"], labels["role"]))
    lines.append("|---|---|---|---|")
    for other_key in A.ACCOUNT_ORDER:
        other = A.ACCOUNTS[other_key]
        icon = A.PLATFORM_ICON[other["platform"]]
        marker = " ◆ *%s*" % labels["here"] if other_key == key else ""
        lines.append('| <img src="./assets/icons/%s" width="18" alt="%s" /> | %s | **[%s](%s)** | %s%s |'
                     % (icon, PLATFORM_LABEL[other["platform"]], PLATFORM_LABEL[other["platform"]],
                        other["handle"], other["home"], other["role"][lang], marker))
    lines.append("")
    lines.append('<p align="center">')
    lines.append('  <img src="./assets/footer.svg" alt="" width="100%" />')
    lines.append("</p>")
    lines.append("")
    lines.append('<p align="center"><sub>© %s</sub></p>' % acct["handle"])
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# writing / packing
# --------------------------------------------------------------------------
def write_account_files(acct, key, out_dir, stats, base=None):
    out = pathlib.Path(out_dir)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "icons").mkdir(parents=True, exist_ok=True)
    (assets / "cards").mkdir(parents=True, exist_ok=True)
    lang_assets = {"skills-%s.svg", "works-%s.svg", "activity-%s.svg"}
    wanted = {"hero.svg", "footer.svg"}
    wanted |= {A.STATS_NAME[l] for l in A.LANGS}
    for l in A.LANGS:
        wanted |= {t % l for t in lang_assets}
    if acct.get("contrib_graph"):
        wanted |= set(SNAKE_NAMES)
    for stale in assets.glob("*.svg"):
        if stale.name not in wanted:
            stale.unlink()
    for stale in (assets / "icons").glob("*.svg"):
        stale.unlink()
    for stale in (assets / "cards").glob("*.svg"):
        stale.unlink()
    for lang in A.LANGS:
        (out / A.README_NAME[lang]).write_text(
            render_readme(acct, key, lang, stats), encoding="utf-8", newline="\n"
        )
        (assets / A.STATS_NAME[lang]).write_text(
            stats_svg(acct, key, stats, lang), encoding="utf-8", newline="\n"
        )
        for svg, fn in ((skills_svg(acct, lang), "skills-%s.svg"),
                        (works_svg(acct, key, lang), "works-%s.svg"),
                        (activity_svg(acct, key, lang, stats), "activity-%s.svg")):
            if svg:
                (assets / (fn % lang)).write_text(svg, encoding="utf-8", newline="\n")
    (assets / "hero.svg").write_text(hero_svg(acct), encoding="utf-8", newline="\n")
    # hero 的 PNG 兜底（由 scripts/rasterize.py 预先生成；缺失时 <picture> 自动回落 SVG）
    png_dir = assets / "png"
    png_dir.mkdir(parents=True, exist_ok=True)
    hero_png_dst = png_dir / "hero.png"
    # 每个账号的 hero 都不同，PNG 必须按账号生成（src/assets/png/<key>/hero.png）；
    # 缺失时 <picture> 自动回落到同目录的 hero.svg，不影响显示。
    hero_png_src = ROOT / "assets" / "png" / key / "hero.png"
    if hero_png_src.is_file() and hero_png_src.resolve() != hero_png_dst.resolve():
        shutil.copyfile(hero_png_src, hero_png_dst)
    (assets / "footer.svg").write_text(footer_svg(acct), encoding="utf-8", newline="\n")
    # README 引用的图标（平台徽标 + 写作平台），只拷贝用到的那几个
    icon_roots = [pathlib.Path(base) / "data" / "icons", ROOT / "data" / "icons"] if base else [ROOT / "data" / "icons"]
    used_icons = sorted({A.PLATFORM_ICON[p] for p in
                         {a["platform"] for a in A.ACCOUNTS.values()}})
    used_icons += [icon for _name, _url, icon in A.WRITING]
    for name in used_icons:
        for root in icon_roots:
            src = root / name
            if src.is_file():
                if name.startswith("si-"):
                    # simple-icons 默认黑色，深色底上不可见 → 补浅色填充
                    copy_icon_light(src, assets / "icons" / name, A.THEME["muted"])
                else:
                    shutil.copyfile(src, assets / "icons" / name)
                break
    # 官方卡片种子（存在才拷贝 —— 缺失即 README 自动降级，见 load_card_seed）
    card_dir = cards_dir_for(key, base)
    if card_dir.is_dir():
        for f in sorted(card_dir.glob("*.svg")):
            shutil.copyfile(f, assets / "cards" / f.name)
    if acct.get("contrib_graph"):
        seed_dir = ROOT / "data" / "contrib" / key
        for src_name, dst_name in (("snake.svg", SNAKE_NAMES[0]), ("snake-dark.svg", SNAKE_NAMES[1])):
            src = seed_dir / src_name
            if src.is_file():
                shutil.copyfile(src, assets / dst_name)


PACK_EXTRAS = ("scripts/generate.py", "scripts/refresh.py", "scripts/refresh_sections.py",
                "accounts.py", "data/stats.json", "data/writing.json")
PACK_GITIGNORE = ".gitignore"


def _has_mirror(key):
    """该账号是否在 GitCode / Gitee 另有主页（需要镜像作业）。

    目前仅 github/badhope 在 GitCode、Gitee 均有同名主页；其余账号只在 GitHub。
    """
    acct = A.ACCOUNTS.get(key, {})
    return acct.get("platform") == "github" and acct.get("handle") == "badhope"


def pack(key, out_dir):
    acct = A.ACCOUNTS[key]
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stats_path = ROOT / "data" / "stats.json"
    stats = load_stats(stats_path)
    write_account_files(acct, key, out, stats)
    for rel in PACK_EXTRAS:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)
    if acct.get("contrib_graph"):
        seed_src = ROOT / "data" / "contrib" / key
        if seed_src.is_dir():
            dst_dir = out / "data" / "contrib" / key
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in sorted(seed_src.glob("*.svg")):
                shutil.copyfile(f, dst_dir / f.name)
    # 图标库与卡片种子随包携带（目标仓库内可 --here 重建 / 由 workflow 刷新卡片）
    icon_src = ROOT / "data" / "icons"
    if icon_src.is_dir():
        dst_icons = out / "data" / "icons"
        dst_icons.mkdir(parents=True, exist_ok=True)
        for f in sorted(icon_src.glob("*.svg")):
            shutil.copyfile(f, dst_icons / f.name)
    card_src = ROOT / "data" / "cards" / key
    if card_src.is_dir():
        dst_cards = out / "data" / "cards" / key
        dst_cards.mkdir(parents=True, exist_ok=True)
        for f in sorted(card_src.glob("*.svg")):
            shutil.copyfile(f, dst_cards / f.name)
    (out / "profile.json").write_text(
        json.dumps({"kit_version": A.KIT_VERSION, "account": key}, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    if acct["platform"] == "github":
        # CI 的 test job 需要 tests/，不打进包就等于门禁必然失败
        if (ROOT / "tests").is_dir():
            shutil.copytree(ROOT / "tests", out / "tests",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
        wf_dir = out / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        # 动态刷新工作流（分区刷新、变更闸门、配额安全）
        shutil.copyfile(ROOT / "workflows" / "refresh.yml", wf_dir / "refresh.yml")
        # 仅 badhope 需在 GitCode / Gitee 镜像（其余账号只在 GitHub）
        if _has_mirror(key):
            shutil.copyfile(ROOT / "workflows" / "mirror.yml", wf_dir / "mirror.yml")
            shutil.copyfile(ROOT / "workflows" / "mirror-shared.sh", out / "scripts" / "mirror-shared.sh")
        # 分支保护把 "Scan for secrets (gitleaks)" 列为必需检查，缺失会导致 main 无法推送
        shutil.copyfile(ROOT / "workflows" / "gitleaks.yml", wf_dir / "gitleaks.yml")
        shutil.copyfile(ROOT / ".gitleaks.toml", out / ".gitleaks.toml")
        (out / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "scripts" / "refresh_sections.py", out / "scripts" / "refresh_sections.py")
        shutil.copyfile(ROOT / "scripts" / "render_cards.mjs", out / "scripts" / "render_cards.mjs")
        # node 依赖清单与锁文件：cards 作业的 npm ci 需要（仅 GitHub 账号带 Actions）
        shutil.copyfile(ROOT / "package.json", out / "package.json")
        shutil.copyfile(ROOT / "package-lock.json", out / "package-lock.json")
        # 动态刷新说明文档（docs/ 下全部 .md 随包携带）
        doc_src_dir = ROOT / "docs"
        if doc_src_dir.is_dir():
            doc_dir = out / "docs"
            doc_dir.mkdir(parents=True, exist_ok=True)
            for d in sorted(doc_src_dir.glob("*.md")):
                shutil.copyfile(d, doc_dir / d.name)
    (out / PACK_GITIGNORE).write_text(
        (ROOT / PACK_GITIGNORE).read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
    )
    return out


def here(cwd):
    cwd = pathlib.Path(cwd)
    prof = json.loads((cwd / "profile.json").read_text(encoding="utf-8"))
    key = prof["account"]
    stats = load_stats(cwd / "data" / "stats.json")
    write_account_files(A.ACCOUNTS[key], key, cwd, stats, base=cwd)
    return key


# --------------------------------------------------------------------------
# preview
# --------------------------------------------------------------------------
def md_line_html(text):
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def md_to_html(md):
    out, in_ul, in_table = [], False, False

    def is_sep_row(line):
        return bool(re.fullmatch(r"\s*\|[\s:|-]*\|\s*", line)) and "-" in line

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
        if stripped.startswith("## "):
            out.append("<h2>%s</h2>" % md_line_html(stripped[3:]))
        elif stripped.startswith("### "):
            out.append("<h3>%s</h3>" % md_line_html(stripped[4:]))
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
            tds = "".join("<%s>%s</%s>" % (tag, md_line_html(c), tag) for c in cells)
            out.append("<tr>%s</tr>" % tds)
        elif stripped.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>%s</li>" % md_line_html(stripped[2:]))
        elif stripped.startswith("> "):
            out.append("<blockquote>%s</blockquote>" % md_line_html(stripped[2:]))
        elif line.startswith("<") or (line[:1] == " " and stripped.startswith("<")):
            out.append(line)  # 原生 HTML（含缩进的 img/picture 等），按原样输出
        elif not line:
            out.append("")
        else:
            out.append("<p>%s</p>" % md_line_html(line))
    if in_ul:
        out.append("</ul>")
    if in_table:
        out.append("</table></div>")
    return "\n".join(out)


PREVIEW_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>主页面 kit · 预览</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin:0; background:#04060E; color:#F4F7FF;
         font:16px/1.65 "Helvetica Neue",Helvetica,Arial,"PingFang SC","Microsoft YaHei",sans-serif; }}
  .page {{ max-width:900px; margin:0 auto; padding:48px 28px 96px; }}
  .badge {{ display:inline-block; padding:2px 10px; border:1px solid rgba(217,184,118,.5);
            border-radius:999px; color:#D9B876; font-size:12px; letter-spacing:2px; }}
  .kit {{ font-size:13px; color:#5C6A94; letter-spacing:2px; }}
  .account {{ margin-top:72px; border-top:1px solid rgba(217,184,118,.22); padding-top:40px; }}
  .account h1 {{ font-family:Georgia,"Times New Roman",serif; font-weight:600;
                 letter-spacing:1px; font-size:26px; }}
  .account img.hero {{ width:100%; border-radius:14px; border:1px solid rgba(217,184,118,.25); }}
  .readme {{ margin-top:28px; }}
  .readme h2 {{ font-family:Georgia,serif; font-size:21px; border-bottom:1px solid rgba(217,184,118,.2);
                padding-bottom:8px; margin-top:44px; }}
  .readme h3 {{ font-size:17px; color:#D9B876; margin-top:28px; }}
  .readme a {{ color:#F2DC9E; text-decoration:none; }}
  .readme code {{ background:#131D3D; border:1px solid rgba(217,184,118,.18);
                  border-radius:6px; padding:1px 6px; font-size:13px; color:#9AA8CC; }}
  .readme blockquote {{ border-left:3px solid rgba(217,184,118,.5); margin-left:0;
                        padding-left:16px; color:#9AA8CC; }}
  .readme img {{ max-width:100%; }}
  .readme ul {{ padding-left:22px; }}
  .readme table {{ border-collapse:collapse; margin:8px 0; }}
  .readme th, .readme td {{ padding:6px 12px; border:1px solid rgba(217,184,118,.18); text-align:left; vertical-align:middle; }}
  .readme th {{ color:#D9B876; font-weight:600; }}
  .tscroll {{ overflow-x:auto; }}
  .readme .tscroll table {{ min-width:520px; }}
  .meta {{ color:#5C6A94; font-size:13px; margin-top:6px; }}
</style>
</head>
<body>
<div class="page">
  <span class="badge">主页面 KIT · 预览</span>
  <p class="kit">GENERATED PREVIEW · {count} ACCOUNTS · {langs} LANGUAGES · SELF-CONTAINED SVG</p>
{body}
</div>
</body>
</html>
"""


def LOCALIZE_BADGES(md):
    """把 shields.io 动态徽章替换为本地静态文本块（预览页专用，不改动部署产物）。"""
    def repl(m):
        label = m.group(1) or ""
        value = m.group(2) or ""
        return ('<span class="staticbadge"><b>%s</b>%s</span>'
                % (esc(label.replace("+", " ")), esc(value.replace("+", " "))))
    # 形如 https://img.shields.io/badge/dynamic/json?...&label=xxx  → 用 label 文本占位
    md = re.sub(r'<img[^>]*src="https://img\.shields\.io[^"]*label=([^"&]*)[^"]*"[^>]*/?>',
                lambda m: repl_static(m.group(1)), md)
    return md


def repl_static(label):
    from urllib.parse import unquote_plus
    return '<span class="staticbadge">%s</span>' % esc(unquote_plus(label))


def strip_preview_dupes(md):
    """预览页自带语言 tab 与 hero，剥离 README 里重复的那两段。"""
    lines = md.split("\n")
    out = []
    i = 0
    while i < len(lines):
        st = lines[i].strip()
        # 顶部语言导航行：[English](...) | [中文](...) | [日本語](...)
        if ("README.md)" in st and "README.zh-CN.md)" in st and "README.ja.md)" in st
                and st.startswith("[")):
            i += 1
            continue
        # hero 块：<p ...> 起始，内部含 hero.svg（可能包在 <picture>/<source> 里），直到 </p>
        if st.startswith("<p"):
            # 向后看最多 6 行，找到 </p>
            j = i
            block = []
            while j < len(lines) and j < i + 6:
                block.append(lines[j])
                if "</p>" in lines[j]:
                    break
                j += 1
            joined = "\n".join(block)
            if 'assets/hero.svg' in joined and "</p>" in joined:
                i = j + 1
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def build_preview(out_dir):
    """构建多账号、多语言、可导航的预览界面（单文件 + 相对路径资产）。"""
    import brand
    import preview as P

    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dist = ROOT / "dist"
    stats = load_stats(ROOT / "data" / "stats.json")

    brand_dir = dist / "brand"
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / "mark.svg").write_text(brand.logo_mark(64, with_wordmark=False), encoding="utf-8", newline="\n")
    (brand_dir / "logo.svg").write_text(brand.logo_mark(64, with_wordmark=True), encoding="utf-8", newline="\n")
    (brand_dir / "favicon.svg").write_text(brand.favicon_svg(), encoding="utf-8", newline="\n")
    (brand_dir / "mark-light.svg").write_text(brand.logo_light(), encoding="utf-8", newline="\n")

    lang_labels = {"md": "English", "zh-CN": "中文", "ja": "日本語"}
    accent = {"gh_x33834": "#7C9CFF", "gh_morningstar": "#C9A0FF",
              "gh_badhope": "#D9B876", "gitcode_badhope": "#3FD9C0", "gitee_badhope": "#FF8FA3"}

    nav, panels = [], []
    for key in A.ACCOUNT_ORDER:
        acct = A.ACCOUNTS[key]
        generate_to(dist / key, key, stats)
        rel = "../dist/%s/assets" % key
        langs_data = {}
        for lang in A.LANGS:
            md = (dist / key / A.README_NAME[lang]).read_text(encoding="utf-8")
            md = strip_preview_dupes(md)
            md = md.replace("./assets/", rel + "/")
            # 预览页必须离线可开：把实时 shields 徽章换成等价的本地静态条，
            # 否则内网/离线环境下 <img> 永不加载完成，整页卡在 loading。
            md = LOCALIZE_BADGES(md)
            langs_data[lang] = {
                "label": lang_labels.get(lang, lang),
                "labels": A.LABELS[lang],
                "html": md_to_html(md),
                "hero": rel + "/hero.svg",
            }
        block = (stats.get("accounts") or {}).get(key) or {}
        panels.append(P._account_panel(key, acct, langs_data, block, accent.get(key, "#D9B876")))
        nav.append(
            '<li><button class="navitem%s" data-target="%s" style="--accent:%s">'
            '<span class="dot"></span><span>%s</span>'
            '<span class="nav-plat">%s</span></button></li>'
            % (" is-active" if key == A.ACCOUNT_ORDER[0] else "", key,
               accent.get(key, "#D9B876"), esc(acct["handle"]),
               esc(PLATFORM_LABEL[acct["platform"]]))
        )

    html = P.TEMPLATE.format(count=len(A.ACCOUNT_ORDER), langs=len(A.LANGS),
                             nav="".join(nav), panels="".join(panels))
    (out_dir / "index.html").write_text(html, encoding="utf-8", newline="\n")
    return out_dir / "index.html"


def generate_to(out_dir, key, stats):
    write_account_files(A.ACCOUNTS[key], key, out_dir, stats)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description="主页面 kit generator")
    parser.add_argument("--all", action="store_true", help="generate all accounts")
    parser.add_argument("--account", metavar="KEY", help="generate one account")
    parser.add_argument("--pack", metavar="KEY", help="write a deployable repo tree")
    parser.add_argument("--here", action="store_true", help="regenerate in current dir (needs profile.json)")
    parser.add_argument("--preview", action="store_true", help="build dist/ + preview/index.html")
    parser.add_argument("--out", metavar="DIR", help="output directory")
    args = parser.parse_args(argv)

    try:
        if args.pack:
            if args.pack not in A.ACCOUNTS:
                print("unknown account: %s (available: %s)"
                      % (args.pack, ", ".join(A.ACCOUNT_ORDER)), file=sys.stderr)
                return 1
            out = args.out or (ROOT / "pack" / args.pack)
            path = pack(args.pack, out)
            print("packed %s -> %s" % (args.pack, path))
            return 0
        if args.here:
            key = here(pathlib.Path.cwd())
            print("regenerated in place: %s" % key)
            return 0
        if args.preview:
            index = build_preview(args.out or (ROOT / "preview"))
            print("preview -> %s" % index)
            return 0
        stats = load_stats(ROOT / "data" / "stats.json")
        keys = list(A.ACCOUNT_ORDER)
        if args.account:
            if args.account not in A.ACCOUNTS:
                print("unknown account: %s (available: %s)"
                      % (args.account, ", ".join(keys)), file=sys.stderr)
                return 1
            keys = [args.account]
        elif not args.all:
            parser.print_help()
            return 1
        base = pathlib.Path(args.out) if args.out else (ROOT / "dist")
        for key in keys:
            target = base / key
            generate_to(target, key, stats)
            print("generated %s -> %s" % (key, target))
        return 0
    except (OSError, KeyError, ValueError) as err:
        print("generation failed: %r" % (err,), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
