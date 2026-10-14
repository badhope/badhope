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


def load_stats(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"as_of": "", "accounts": {}}


def acct_stats(stats, key):
    return (stats.get("accounts") or {}).get(key) or {}


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


def render_readme(acct, key, lang, stats):
    labels = A.LABELS[lang]
    role = acct["role"][lang]
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
    lines.append("## %s" % labels["about"])
    lines.append("")
    lines.append(acct["about"][lang])
    lines.append("")
    lines.append("### %s" % labels["now"])
    lines.append("")
    for item in acct["now"][lang]:
        lines.append("- %s" % item)
    lines.append("")
    lines.append("## %s" % labels["works"])
    lines.append("")
    for wid in acct["works"]:
        work = A.WORKS[wid]
        url = A.work_url(wid, acct)
        lines.append("- **[%s](%s)** — %s · `%s`"
                     % (work["title"], url, work["desc"][lang], work["tags"][lang]))
    lines.append("")
    lines.append("%s [%s](%s)" % (labels["all_repos"], acct["home_display"], acct["home"]))
    lines.append("")
    lines.append("## %s" % labels["contrib"])
    lines.append("")
    lines.append(render_contrib(acct, key, lang))
    lines.append("")
    lines.append("## %s" % labels["numbers"])
    lines.append("")
    data = acct_stats(stats, key)
    alt_bits = []
    for field in STAT_FIELDS:
        val = data.get(field)
        if val is not None:
            alt_bits.append("%s %s" % (fmt_num(val), labels["stat_%s" % field]))
    alt = " · ".join(alt_bits) if alt_bits else labels["numbers"]
    lines.append('<p align="center">')
    lines.append('  <img src="./assets/%s" alt="%s" width="80%%" />' % (A.STATS_NAME[lang], esc(alt)))
    lines.append("</p>")
    lines.append("")
    lines.append("## %s" % labels["writing"])
    lines.append("")
    lines.append("- " + " · ".join("[%s](%s)" % w for w in A.WRITING))
    lines.append("")
    lines.append("## %s" % labels["elsewhere"])
    lines.append("")
    lines.append("> %s" % labels["mirror_note"])
    lines.append("")
    for other_key in A.ACCOUNT_ORDER:
        other = A.ACCOUNTS[other_key]
        marker = " ◆ %s" % labels["here"] if other_key == key else ""
        lines.append("- **%s · [%s](%s)** — %s%s"
                     % (PLATFORM_LABEL[other["platform"]], other["handle"], other["home"],
                        other["role"][lang], marker))
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
def write_account_files(acct, key, out_dir, stats):
    out = pathlib.Path(out_dir)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    wanted = {"hero.svg", "footer.svg"} | {A.STATS_NAME[l] for l in A.LANGS}
    for stale in assets.glob("*.svg"):
        if stale.name not in wanted:
            stale.unlink()
    for lang in A.LANGS:
        (out / A.README_NAME[lang]).write_text(
            render_readme(acct, key, lang, stats), encoding="utf-8", newline="\n"
        )
        (assets / A.STATS_NAME[lang]).write_text(
            stats_svg(acct, key, stats, lang), encoding="utf-8", newline="\n"
        )
    (assets / "hero.svg").write_text(hero_svg(acct), encoding="utf-8", newline="\n")
    (assets / "footer.svg").write_text(footer_svg(acct), encoding="utf-8", newline="\n")


PACK_EXTRAS = ("scripts/generate.py", "scripts/refresh.py", "accounts.py", "data/stats.json")
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
    (out / "profile.json").write_text(
        json.dumps({"kit_version": A.KIT_VERSION, "account": key}, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    if acct["platform"] == "github":
        wf = out / ".github" / "workflows" / "refresh.yml"
        wf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "workflows" / "refresh.yml", wf)
    (out / PACK_GITIGNORE).write_text(
        (ROOT / PACK_GITIGNORE).read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
    )
    return out


def here(cwd):
    cwd = pathlib.Path(cwd)
    prof = json.loads((cwd / "profile.json").read_text(encoding="utf-8"))
    key = prof["account"]
    stats = load_stats(cwd / "data" / "stats.json")
    write_account_files(A.ACCOUNTS[key], key, cwd, stats)
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
    out, in_ul = [], False
    for raw in md.split("\n"):
        line = raw.rstrip()
        if in_ul and not line.startswith("- "):
            out.append("</ul>")
            in_ul = False
        if line.startswith("## "):
            out.append("<h2>%s</h2>" % md_line_html(line[3:]))
        elif line.startswith("### "):
            out.append("<h3>%s</h3>" % md_line_html(line[4:]))
        elif line.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>%s</li>" % md_line_html(line[2:]))
        elif line.startswith("> "):
            out.append("<blockquote>%s</blockquote>" % md_line_html(line[2:]))
        elif line.startswith("<"):
            out.append(line)
        elif not line:
            out.append("")
        else:
            out.append("<p>%s</p>" % md_line_html(line))
    if in_ul:
        out.append("</ul>")
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
