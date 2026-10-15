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
    """技能矩阵：图标 + 名称的网格卡片（本地资产，无外链）。"""
    t = A.THEME
    labels = A.LABELS[lang]
    names = [s for s in acct.get("skills", []) if s in A.SKILL_LABELS]
    tiles = []
    for name in names:
        body = icon_svg_body(name, 34)
        if body is None:
            continue
        tiles.append((A.SKILL_LABELS[name], body))
    if not tiles:
        return None
    cols = min(5, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    cell_w, cell_h = 196, 92
    pad_x, pad_top = 34, 48
    width = pad_x * 2 + cell_w * cols
    height = pad_top + cell_h * rows + 24
    parts = []
    for i, (label, body) in enumerate(tiles):
        cx = pad_x + (i % cols) * cell_w
        cy = pad_top + (i // cols) * cell_h
        parts.append(
            '<g transform="translate(%s,%s)">'
            '<rect x="0" y="0" width="%s" height="%s" rx="12" fill="%s" fill-opacity="0.55" '
            'stroke="%s" stroke-opacity="0.22"/>'
            '<g transform="translate(%s,20)">%s</g>'
            '<text x="%s" y="76" text-anchor="middle" font-family="%s" font-size="13.5" fill="%s">%s</text>'
            '</g>'
            % (cx, cy, cell_w - 16, cell_h - 16, t["bg1"], t["gold"],
               (cell_w - 16 - 34) / 2, body, (cell_w - 16) / 2, A.SANS, t["muted"], esc(label))
        )
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{alt}">
<defs>
  <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{panel}"/>
    <stop offset="100%" stop-color="{bg1}"/>
  </linearGradient>
</defs>
<rect x="0.75" y="0.75" width="{rw}" height="{rh}" rx="16" fill="url(#panel)" stroke="{gold}" stroke-opacity="0.28" stroke-width="1.5"/>
<text x="{rx}" y="30" text-anchor="end" font-family="{sans}" font-size="12" fill="{faint}">{note}</text>
{parts}
</svg>
""".format(
        w=width, h=height, rw=width - 1.5, rh=height - 1.5,
        panel=t["panel"], bg1=t["bg1"], gold=t["gold"], faint=t["faint"],
        sans=A.SANS, rx=width - pad_x, note=esc(labels["skills_note"]),
        parts="\n".join(parts), alt=esc(labels["skills"] + " · " + ", ".join(n for n, _ in tiles)),
    )


def works_svg(acct, key, lang):
    """作品面板：每件作品一张卡片（图标 + 名称 + 说明 + 标签），网格排布。"""
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
    cell_w, cell_h = 470, 118
    pad_x, pad_top = 34, 24
    width = pad_x * 2 + cell_w * cols
    height = pad_top + cell_h * rows + 24
    parts = []
    for i, (title, desc, tags, body) in enumerate(items):
        cx = pad_x + (i % cols) * cell_w
        cy = pad_top + (i // cols) * cell_h
        desc_short = desc if len(esc(desc)) <= 58 else esc(desc)[:56].rstrip() + "…"
        parts.append(
            '<g transform="translate(%s,%s)">'
            '<rect x="0" y="0" width="%s" height="%s" rx="12" fill="%s" fill-opacity="0.55" '
            'stroke="%s" stroke-opacity="0.22"/>'
            '<rect x="0" y="0" width="3" height="%s" rx="1.5" fill="%s" fill-opacity="0.9"/>'
            '<g transform="translate(22,22)">%s</g>'
            '<text x="60" y="34" font-family="%s" font-size="16.5" fill="%s">%s</text>'
            '<text x="60" y="58" font-family="%s" font-size="12.8" fill="%s">%s</text>'
            '<text x="60" y="82" font-family="%s" font-size="11.5" letter-spacing="1.2" fill="%s">%s</text>'
            '</g>'
            % (cx, cy, cell_w - 18, cell_h - 16, t["bg1"], t["gold"], cell_h - 16, t["gold"],
               body, A.SANS, t["ink"], esc(title), A.SANS, t["muted"], desc_short,
               A.SANS, t["gold"], esc(tags.upper()))
        )
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{alt}">
<defs>
  <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{panel}"/>
    <stop offset="100%" stop-color="{bg1}"/>
  </linearGradient>
</defs>
<rect x="0.75" y="0.75" width="{rw}" height="{rh}" rx="16" fill="url(#panel)" stroke="{gold}" stroke-opacity="0.28" stroke-width="1.5"/>
{parts}
</svg>
""".format(
        w=width, h=height, rw=width - 1.5, rh=height - 1.5,
        panel=t["panel"], bg1=t["bg1"], gold=t["gold"], ink=t["ink"],
        serif=A.SERIF, sans=A.SANS, pad=pad_x, rx=width - pad_x,
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
            '<text x="%s" y="%s" text-anchor="end" font-family="%s" font-size="14" fill="%s">%s</text>'
            % (bar_x - 18, y + 15, A.SANS, t["muted"], esc(label))
        )
        parts.append(
            '<rect x="%s" y="%s" width="%s" height="14" rx="7" fill="%s" fill-opacity="0.55"/>'
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
    <stop offset="0%" stop-color="{gold}" stop-opacity="0.55"/>
    <stop offset="100%" stop-color="{gold_bright}" stop-opacity="0.95"/>
  </linearGradient>
</defs>
<rect x="0.75" y="0.75" width="{rw}" height="{rh}" rx="16" fill="url(#panel)" stroke="{gold}" stroke-opacity="0.28" stroke-width="1.5"/>
<text x="{rx}" y="30" text-anchor="end" font-family="{sans}" font-size="12" fill="{faint}">{asof}</text>
{parts}
</svg>
""".format(
        w=width, h=height, rw=width - 1.5, rh=height - 1.5,
        panel=t["panel"], bg1=t["bg1"], gold=t["gold"], gold_bright=t["gold_bright"],
        faint=t["faint"], sans=A.SANS, rx=width - pad_x,
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
    out = []
    for _ in range(n):
        x = round(r.uniform(10, w - 10), 1)
        y = round(r.uniform(8, h - 8), 1)
        rr = round(r.uniform(0.6, 1.7), 1)
        op = round(r.uniform(0.22, 0.9), 2)
        fill = A.THEME["gold"] if r.random() < 0.14 else A.THEME["star"]
        out.append(
            '<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="%s"/>'
            % (x, y, rr, fill, op)
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
    w, h = 1200, 360
    poly, dots = dipper(acct, w, h)
    handle = acct["handle"]
    fs = 58 if len(handle) <= 12 else 46
    ls = 6 if len(handle) <= 12 else 8
    t = A.THEME
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" width="1200" height="360" role="img" aria-label="{handle} — {home}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#05070F"/>
    <stop offset="55%" stop-color="{bg0}"/>
    <stop offset="100%" stop-color="{bg1}"/>
  </linearGradient>
  <radialGradient id="glow-warm" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{gold}" stop-opacity="0.10"/>
    <stop offset="100%" stop-color="{gold}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glow-cool" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{deep}" stop-opacity="0.22"/>
    <stop offset="100%" stop-color="{deep}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{gold}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{gold}" stop-opacity="0.55"/>
    <stop offset="100%" stop-color="{gold}" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect width="1200" height="360" fill="url(#sky)"/>
<ellipse cx="880" cy="80" rx="430" ry="200" fill="url(#glow-warm)"/>
<ellipse cx="240" cy="300" rx="470" ry="220" fill="url(#glow-cool)"/>
<g>
  {stars}
</g>
<polyline points="{poly}" fill="none" stroke="{gold}" stroke-opacity="0.30" stroke-width="1.1"/>
<g>
  {dots}
</g>
<text x="600" y="205" text-anchor="middle" font-family="{serif}" font-size="{fs}" letter-spacing="{ls}" fill="{ink}">{handle}</text>
<text x="600" y="252" text-anchor="middle" font-family="{sans}" font-size="19" letter-spacing="4" fill="{gold}">{home}</text>
<rect x="260" y="296" width="680" height="1.5" fill="url(#rule)"/>
<rect x="592" y="288" width="14" height="14" fill="none" stroke="{gold}" stroke-opacity="0.8" stroke-width="1.2" transform="rotate(45 599 295)"/>
</svg>
""".format(
        handle=esc(handle), home=esc(acct["home_display"]),
        bg0=t["bg0"], bg1=t["bg1"], gold=t["gold"], ink=t["ink"],
        deep=t["deep_blue"], serif=A.SERIF, sans=A.SANS,
        fs=fs, ls=ls, stars=starfield(acct, w, h, 84), poly=poly, dots=dots,
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
            '<text x="%s" y="92" text-anchor="middle" font-family="%s" font-size="44" fill="%s">%s</text>'
            % (cx, A.SERIF, t["gold_bright"], esc(val))
        )
        parts.append(
            '<text x="%s" y="126" text-anchor="middle" font-family="%s" font-size="16" letter-spacing="1.5" fill="%s">%s</text>'
            % (cx, A.SANS, t["muted"], esc(label))
        )
    for i in range(1, n):
        x = round(1000 * i / n, 1)
        parts.append(
            '<line x1="%s" y1="46" x2="%s" y2="146" stroke="%s" stroke-opacity="0.16"/>'
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
</defs>
<rect x="0.75" y="0.75" width="998.5" height="188.5" rx="16" fill="url(#panel)" stroke="{gold}" stroke-opacity="0.28" stroke-width="1.5"/>
{parts}
<text x="26" y="172" font-family="{sans}" font-size="13" letter-spacing="2" fill="{faint}">{left}</text>
<text x="974" y="172" text-anchor="end" font-family="{sans}" font-size="13" letter-spacing="1" fill="{faint}">{right}</text>
</svg>
""".format(
        alt=esc(" · ".join("%s %s" % (v, l) for v, l in cells)),
        panel=t["panel"], bg1=t["bg1"], gold=t["gold"], faint=t["faint"],
        sans=A.SANS, parts="\n".join(parts), left=foot_left, right=esc(foot_right),
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
    lines.append('  <img src="./assets/hero.svg" alt="%s · %s" width="100%%" />'
                 % (esc(acct["handle"]), esc(acct["home_display"])))
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
        "[%s](%s)" % (A.WORKS[wid]["title"], A.work_url(wid, acct)) for wid in acct["works"]
    )
    lines.append('<p align="center"><sub>%s</sub></p>' % links_row)
    lines.append("")
    lines.append("%s [%s](%s)" % (labels["all_repos"], acct["home_display"], acct["home"]))
    lines.append("")

    # ---- 数据面板：官方卡片（有种子时）否则自绘统计卡 ----
    lines.append("## %s" % labels["numbers"])
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
        lines.append('    <source media="(prefers-color-scheme: dark)" srcset="./assets/github-contribution-grid-snake-dark.svg" />')
        lines.append('    <img src="./assets/github-contribution-grid-snake.svg" alt="contribution snake" width="100%" />')
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
    lines.append("<sub>%s <img src=\"./assets/icons/si-csdn.svg\" width=\"15\" alt=\"CSDN\" /> [CSDN](%s) · <img src=\"./assets/icons/si-juejin.svg\" width=\"15\" alt=\"Juejin\" /> [Juejin](%s)</sub>"
                 % (labels["also_on"], A.WRITING[0][1], A.WRITING[1][1]))
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
    (assets / "footer.svg").write_text(footer_svg(acct), encoding="utf-8", newline="\n")
    # README 引用的图标（平台徽标 + 写作平台），只拷贝用到的那几个
    icon_roots = [pathlib.Path(base) / "data" / "icons", ROOT / "data" / "icons"] if base else [ROOT / "data" / "icons"]
    used_icons = sorted({A.PLATFORM_ICON[p] for p in
                         {a["platform"] for a in A.ACCOUNTS.values()}})
    used_icons += ["si-csdn.svg", "si-juejin.svg"]
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


PACK_EXTRAS = ("scripts/generate.py", "scripts/refresh.py", "accounts.py", "data/stats.json", "data/writing.json",
               "package.json", "package-lock.json")
PACK_GITIGNORE = ".gitignore"


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
        wf_dir = out / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "workflows" / "refresh.yml", wf_dir / "refresh.yml")
        if acct.get("contrib_graph"):
            shutil.copyfile(ROOT / "workflows" / "contrib.yml", wf_dir / "contrib.yml")
        shutil.copyfile(ROOT / "workflows" / "cards.yml", wf_dir / "cards.yml")
        (out / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "scripts" / "render_cards.mjs", out / "scripts" / "render_cards.mjs")
        shutil.copyfile(ROOT / "package.json", out / "package.json")
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
  body {{ margin:0; background:#070A13; color:#E9EDF6;
         font:16px/1.65 "Helvetica Neue",Helvetica,Arial,"PingFang SC","Microsoft YaHei",sans-serif; }}
  .page {{ max-width:900px; margin:0 auto; padding:48px 28px 96px; }}
  .badge {{ display:inline-block; padding:2px 10px; border:1px solid rgba(201,168,106,.5);
            border-radius:999px; color:#C9A86A; font-size:12px; letter-spacing:2px; }}
  .kit {{ font-size:13px; color:#6B7A9B; letter-spacing:2px; }}
  .account {{ margin-top:72px; border-top:1px solid rgba(201,168,106,.22); padding-top:40px; }}
  .account h1 {{ font-family:Georgia,"Times New Roman",serif; font-weight:600;
                 letter-spacing:1px; font-size:26px; }}
  .account img.hero {{ width:100%; border-radius:14px; border:1px solid rgba(201,168,106,.25); }}
  .readme {{ margin-top:28px; }}
  .readme h2 {{ font-family:Georgia,serif; font-size:21px; border-bottom:1px solid rgba(201,168,106,.2);
                padding-bottom:8px; margin-top:44px; }}
  .readme h3 {{ font-size:17px; color:#C9A86A; margin-top:28px; }}
  .readme a {{ color:#E8CD92; text-decoration:none; }}
  .readme code {{ background:#121A2E; border:1px solid rgba(201,168,106,.18);
                  border-radius:6px; padding:1px 6px; font-size:13px; color:#A9B4CC; }}
  .readme blockquote {{ border-left:3px solid rgba(201,168,106,.5); margin-left:0;
                        padding-left:16px; color:#A9B4CC; }}
  .readme img {{ max-width:100%; }}
  .readme ul {{ padding-left:22px; }}
  .readme table {{ border-collapse:collapse; margin:8px 0; }}
  .readme th, .readme td {{ padding:6px 12px; border:1px solid rgba(201,168,106,.18); text-align:left; vertical-align:middle; }}
  .readme th {{ color:#C9A86A; font-weight:600; }}
  .tscroll {{ overflow-x:auto; }}
  .readme .tscroll table {{ min-width:520px; }}
  .meta {{ color:#6B7A9B; font-size:13px; margin-top:6px; }}
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


def build_preview(out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dist = ROOT / "dist"
    stats = load_stats(ROOT / "data" / "stats.json")
    blocks = []
    for key in A.ACCOUNT_ORDER:
        acct = A.ACCOUNTS[key]
        generate_to(dist / key, key, stats)
        rel = "../dist/%s/assets" % key
        hero = ('<img class="hero" src="%s/hero.svg" alt="%s" />' % (rel, esc(acct["handle"])))
        md = (dist / key / "README.md").read_text(encoding="utf-8")
        md = md.replace("./assets/", rel + "/")
        blocks.append(
            '<section class="account" id="%s">\n<h1>%s · %s</h1>\n'
            '<p class="meta">%s</p>\n%s\n<div class="readme">\n%s\n</div>\n</section>'
            % (key, esc(acct["handle"]), PLATFORM_LABEL[acct["platform"]],
               esc(acct["home"]), hero, md_to_html(md))
        )
    html = PREVIEW_TPL.format(count=len(A.ACCOUNT_ORDER), langs=len(A.LANGS), body="\n".join(blocks))
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
