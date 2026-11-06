#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Profile page generator — one data source, three platforms, three languages.

Replaces the old kit/ pipeline (30 modules). Everything lives here:

  * DATA        — copy, works catalogue, upstream record, writing (per language)
  * svg_hero    — one adaptive hero banner
  * svg_work    — featured project cards (adaptive light/dark)
  * render      — README per account: github gets en/zh-CN/ja, mirrors get zh-CN

Deterministic: no wall-clock in output; numbers come from data/stats.json
(committed snapshot, refreshed by scripts/refresh_sections.py).

Entry points used by CI and the mirror:
    python3 scripts/generate.py --here
    python3 scripts/verify.py
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

ACCENT_LIGHT = "#4F46E5"
ACCENT_DARK = "#A5B4FC"

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

COPY = {
    "gh_badhope": {
        "platform": "github",
        "handle": "badhope",
        "home_display": "github.com/badhope",
        "role": {
            "en": "Full-stack developer · local-first tools",
            "zh-CN": "全栈开发者 · 本地优先工具",
            "ja": "フルスタック開発者 · ローカルファーストな道具",
        },
        "tagline": {
            "en": "I build small, honest software that runs on your own machine — no cloud required.",
            "zh-CN": "做小而扎实的软件，装在自己机器上就能跑——不依赖云。",
            "ja": "小さくて誠実な、自分のマシンで動くソフトウェアを作っています。",
        },
        "now": {
            "en": [
                "**moneyhelper** — chat-first personal finance agent, local-first, numbers you can audit",
                "**workbench** — a desktop workbench (Tauri 2 + React) for daily driver tasks",
                "Upstream fixes: ohmyzsh, lefthook, betterleaks, scrapy",
            ],
            "zh-CN": [
                "**moneyhelper** —— 对话优先的个人理财智能体，本地优先、数字可复核",
                "**workbench** —— 日常驾驶舱级桌面工作台（Tauri 2 + React）",
                "上游修复进行中：ohmyzsh、lefthook、betterleaks、scrapy",
            ],
            "ja": [
                "**moneyhelper** —— 対話型の家計エージェント。ローカル完結、数値は検証可能",
                "**workbench** —— デスクトップ作業台（Tauri 2 + React）",
                "アップストリーム修正：ohmyzsh、lefthook、betterleaks、scrapy",
            ],
        },
        "more_intro": {
            "en": "More on the shelf",
            "zh-CN": "架子上还有",
            "ja": "その他の作品",
        },
    },
    "gitcode_badhope": {
        "platform": "gitcode",
        "handle": "badhope",
        "home_display": "gitcode.com/badhope",
        "role": {
            "zh-CN": "移动端开发 · 离线工具",
        },
        "tagline": {
            "zh-CN": "把软件做成离线也能跑的东西。这里放国内镜像和移动端实验场。",
        },
        "now": {
            "zh-CN": [
                "**mashang** —— 赛博朋克风离线编程学习终端，内置 CPython 3.13",
                "**pocketmind** —— 住进 Android 手机的常驻 AI Agent，一个 APK 独立运行",
                "**CodePocket** —— 离线优先的安卓 Python IDE",
            ],
        },
        "more_intro": {"zh-CN": "架子上还有"},
    },
    "gitee_badhope": {
        "platform": "gitee",
        "handle": "badhope",
        "home_display": "gitee.com/badhope",
        "role": {
            "zh-CN": "作品镜像 · 小程序",
        },
        "tagline": {
            "zh-CN": "镜像站：作品另一处安放。精选项目与小型微信小程序实验。",
        },
        "now": {
            "zh-CN": [
                "**quiz-chest** —— 本地优先的自有题库练习应用",
                "**shopcash** —— 单机门店收银与收款记账，资金零介入",
                "**mashang** —— 离线编程学习终端",
            ],
        },
        "more_intro": {"zh-CN": "架子上还有"},
    },
}

# Featured works. `url` is per platform; mirrors reuse the repo name.
WORKS = {
    "moneyhelper": {
        "stack": {"en": "FastAPI · LangGraph · React", "zh-CN": "FastAPI · LangGraph · React", "ja": "FastAPI · LangGraph · React"},
        "line": {
            "en": "Chat-first personal finance agent. Bookkeeping by sentence, portfolio risk, earnings research — local-first, every number auditable.",
            "zh-CN": "对话优先的个人理财智能体：一句话记账、持仓风控、财报分析——本地优先，每个数字都可复核。",
            "ja": "対話型の家計エージェント。記帳は一言で、リスク管理も決算分析も。ローカル完結、数値はすべて検証可能。",
        },
        "urls": {
            "github": "https://github.com/badhope/moneyhelper",
            "gitcode": "https://gitcode.com/badhope/moneyhelper",
            "gitee": "https://gitee.com/badhope/moneyhelper",
        },
    },
    "workbench": {
        "stack": {"en": "Tauri 2 · React 19 · TypeScript", "zh-CN": "Tauri 2 · React 19 · TypeScript", "ja": "Tauri 2 · React 19 · TypeScript"},
        "line": {
            "en": "A local-first desktop workbench for the daily grind: clipboard, snippets, windows, quick launch — one quiet app.",
            "zh-CN": "本地优先的桌面工作台：剪贴板、片段、窗口、快速启动——一个安静的应用全包。",
            "ja": "ローカルファーストなデスクトップ作業台。クリップボード、スニペット、起動をひとつに。",
        },
        "urls": {
            "github": "https://github.com/badhope/workbench",
            "gitcode": "https://gitcode.com/badhope/workbench",
            "gitee": "https://gitee.com/badhope/workbench",
        },
    },
    "spark": {
        "stack": {"en": "Python · React · self-hosted", "zh-CN": "Python · React · 自托管", "ja": "Python · React · セルフホスト"},
        "line": {
            "en": "A self-hosted coding agent harness: cockpit UI, sandboxed runs, MCP tools — your own agent, your own rules.",
            "zh-CN": "自托管的编码智能体底座：驾驶舱 UI、沙箱执行、MCP 工具——自己的 agent 自己定规矩。",
            "ja": "セルフホストのコーディングエージェント基盤。コックピット UI、サンドボックス実行、MCP ツール。",
        },
        "urls": {
            "github": "https://github.com/badhope/spark",
            "gitcode": "https://gitcode.com/badhope/spark",
            "gitee": "https://gitee.com/badhope/spark",
        },
    },
    "world-walker": {
        "stack": {"en": "Python stdlib · MCP", "zh-CN": "Python 标准库 · MCP", "ja": "Python 標準ライブラリ · MCP"},
        "line": {
            "en": "The rules layer for AI-driven interactive fiction: deterministic engine, 64 MCP tools, save library.",
            "zh-CN": "AI 互动小说的规则层：确定性引擎、64 个 MCP 工具、存档库。",
            "ja": "AI 対話フィクションのルール層。決定論エンジン、64 の MCP ツール、セーブ管理。",
        },
        "urls": {
            "github": "https://github.com/badhope/world-walker",
            "gitcode": "https://gitcode.com/badhope/world-walker",
            "gitee": "https://gitee.com/badhope/world-walker",
        },
    },
    "mashang": {
        "stack": {"en": "Kotlin · CPython 3.13 · offline", "zh-CN": "Kotlin · CPython 3.13 · 离线", "ja": "Kotlin · CPython 3.13 · オフライン"},
        "line": {
            "en": "A cyberpunk-styled offline programming learning terminal: built-in CPython and JS, quests, assert grading.",
            "zh-CN": "赛博朋克风离线编程学习终端：内置 CPython 与 JS，关卡制、assert 判题。",
            "ja": "サイバーパンクなオフライン学習ターミナル。CPython と JS を内蔵、クエスト制。",
        },
        "urls": {
            "github": "https://github.com/badhope/mashang",
            "gitcode": "https://gitcode.com/badhope/mashang",
            "gitee": "https://gitee.com/badhope/mashang",
        },
    },
    "pocketmind": {
        "stack": {"en": "Android · on-device AI", "zh-CN": "Android · 端侧 AI", "ja": "Android · 端側 AI"},
        "line": {
            "en": "A resident AI agent that lives in your Android phone: one APK, on-device tools, no cloud round-trips.",
            "zh-CN": "住进 Android 手机的常驻 AI Agent：一个 APK 独立运行，端侧工具，不绕云。",
            "ja": "Android に住む常駐 AI エージェント。APK ひとつで完結、端側で動く。",
        },
        "urls": {
            "github": "https://github.com/badhope/pocketmind",
            "gitcode": "https://gitcode.com/badhope/pocketmind",
            "gitee": "https://gitee.com/badhope/pocketmind",
        },
    },
    "quiz-chest": {
        "stack": {"en": "Local-first · question bank", "zh-CN": "本地优先 · 自有题库", "ja": "ローカルファースト · 問題バンク"},
        "line": {
            "en": "Practice your own question bank, offline. Import, tag, drill — your data stays yours.",
            "zh-CN": "练自己的题库：导入、打标、刷题——数据始终是自己的。",
            "ja": "自分の問題バンクを練習。取り込み、タグ付け、ドリル。",
        },
        "urls": {
            "github": "https://github.com/badhope/quiz-chest",
            "gitcode": "https://gitcode.com/badhope/quiz-chest",
            "gitee": "https://gitee.com/badhope/quiz-chest",
        },
    },
    "shopcash": {
        "stack": {"en": "Desktop · payments-free", "zh-CN": "桌面应用 · 零资金介入", "ja": "デスクトップ · 決済非介入"},
        "line": {
            "en": "Cashier and bookkeeping for small shops. Money only ever lands in the merchant's own account.",
            "zh-CN": "单机门店收银与记账，钱只进商家自己的商户号，软件零资金介入。",
            "ja": "小規模店舗向けレジと記帳。売上は常に店舗自身の口座へ。",
        },
        "urls": {
            "github": "https://github.com/badhope/shopcash",
            "gitcode": "https://gitcode.com/badhope/shopcash",
            "gitee": "https://gitee.com/badhope/shopcash",
        },
    },
}

FEATURED = {
    "gh_badhope": ["moneyhelper", "workbench", "spark", "world-walker"],
    "gitcode_badhope": ["mashang", "pocketmind", "quiz-chest", "workbench"],
    "gitee_badhope": ["shopcash", "quiz-chest", "mashang", "moneyhelper"],
}

MORE = {
    "gh_badhope": [
        ("DU", "11★", "https://github.com/badhope/DU"),
        ("mashang", "9★", "https://github.com/badhope/mashang"),
        ("digilegacy", "7★", "https://github.com/badhope/digilegacy"),
        ("harbor", "11★", "https://github.com/badhope/harbor"),
        ("sciflow", "12★", "https://github.com/badhope/sciflow"),
        ("pocketmind", "3★", "https://github.com/badhope/pocketmind"),
        ("aquapilot", "—", "https://github.com/badhope/aquapilot"),
        ("melee", "3★", "https://github.com/badhope/melee"),
    ],
    "gitcode_badhope": [
        ("CodePocket", "—", "https://gitcode.com/badhope/CodePocket"),
        ("moneyhelper", "—", "https://gitcode.com/badhope/moneyhelper"),
        ("spark", "—", "https://gitcode.com/badhope/spark"),
        ("workbench", "—", "https://gitcode.com/badhope/workbench"),
    ],
    "gitee_badhope": [
        ("mashang", "—", "https://gitee.com/badhope/mashang"),
        ("moneyhelper", "—", "https://gitee.com/badhope/moneyhelper"),
        ("spark", "—", "https://gitee.com/badhope/spark"),
        ("world-walker", "—", "https://gitee.com/badhope/world-walker"),
    ],
}

# Upstream open-source record (verified 2026-11-07).
UPSTREAM = [
    ("ohmyzsh", "3 merged · 3 under review", "https://github.com/ohmyzsh/ohmyzsh"),
    ("renovate-operator", "1 merged · 1 under review", "https://github.com/mogenius/renovate-operator"),
    ("icalendar", "3 merged", "https://github.com/python-icalendar/icalendar"),
    ("apache/airflow", "1 merged", "https://github.com/apache/airflow"),
    ("betterleaks · lefthook · scrapy", "under review", "https://github.com/betterleaks/betterleaks"),
]

UPSTREAM_NOTE = {
    "en": "Tracked across this account and [X33834](https://github.com/X33834) / [Morningstar202604](https://github.com/Morningstar202604).",
    "zh-CN": "记录横跨本账号与 [X33834](https://github.com/X33834) / [Morningstar202604](https://github.com/Morningstar202604)。",
    "ja": "このアカウントと [X33834](https://github.com/X33834) / [Morningstar202604](https://github.com/Morningstar202604) にまたがる記録。",
}

WRITING = [
    ("2026-11-04", "把 AI Agent 接进业务系统，我踩了3 个挺蠢的坑", "https://blog.csdn.net/weixin_56622231/article/details/170051167"),
    ("2026-10-18", "Gemini 4 Argon 全面开放：谷歌憋了半年的旗舰大招，到底行不行？", "https://blog.csdn.net/weixin_56622231/article/details/168251657"),
    ("2026-10-16", "MCP 落地一年，我总结了 6 个没人告诉你的工程真相", "https://zhuanlan.zhihu.com/p/2094232145015453253"),
    ("2026-10-16", "本地优先 AI：当所有人都在上云，我为什么把 AI 装回自己电脑", "https://zhuanlan.zhihu.com/p/2094233605513991576"),
    ("2026-10-16", "AI Agent 上线前必须过的 5 道关：一个真实项目的工程手记", "https://zhuanlan.zhihu.com/p/2094218858789856836"),
]

TOOLBOX = {
    "en": "Python · TypeScript / React · Kotlin · Tauri · FastAPI · Docker · SQLite",
    "zh-CN": "Python · TypeScript / React · Kotlin · Tauri · FastAPI · Docker · SQLite",
    "ja": "Python · TypeScript / React · Kotlin · Tauri · FastAPI · Docker · SQLite",
}

SECTION_HEADINGS = {
    "en": {"now": "Now", "work": "Featured work", "oss": "Open source", "writing": "Writing", "toolbox": "Toolbox", "about": "About this page"},
    "zh-CN": {"now": "最近在做", "work": "代表作品", "oss": "开源贡献", "writing": "写作", "toolbox": "工具箱", "about": "关于本页"},
    "ja": {"now": "いま", "work": "代表作", "oss": "オープンソース", "writing": "書きもの", "toolbox": "道具箱", "about": "このページについて"},
}

MORE_LINK = {
    "github": "All public repositories: [github.com/badhope](https://github.com/badhope)",
    "gitcode": "全部仓库：[gitcode.com/badhope](https://gitcode.com/badhope)",
    "gitee": "全部仓库：[gitee.com/badhope](https://gitee.com/badhope)",
}

# ---------------------------------------------------------------------------
# Stats snapshot
# ---------------------------------------------------------------------------

def load_stats():
    path = ROOT / "data" / "stats.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"as_of": "", "accounts": {}}


def statTriple(stats, account):
    acc = stats.get("accounts", {}).get(account, {})
    return acc.get("stars"), acc.get("repos"), acc.get("followers")


def workStars(stats, account, slug):
    acc = stats.get("accounts", {}).get(account, {})
    works = acc.get("works", {})
    return works.get(slug, {}).get("stars")


def fmtStars(value):
    if value is None:
        return ""
    if value >= 1000:
        return "%.1fk" % (value / 1000.0)
    return str(value)

# ---------------------------------------------------------------------------
# SVG helpers — adaptive light/dark, hairline editorial style
# ---------------------------------------------------------------------------

def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def svgHead(width, height, label):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">\n'
        "<style>\n"
        "  text { font-family: -apple-system, 'Segoe UI', 'PingFang SC', 'Hiragino Sans', 'Noto Sans SC', 'Microsoft YaHei', sans-serif; }\n"
        "  .mono { font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace; }\n"
        "  .fg { fill: #1F2328; } .muted { fill: #59636E; } .accent { fill: %s; }\n"
        "  .line { stroke: #D1D9E0; stroke-width: 1; }\n"
        "  .chip { fill: rgba(79,70,229,0.08); }\n"
        "  @media (prefers-color-scheme: dark) {\n"
        "    .fg { fill: #E6EDF3; } .muted { fill: #8B949E; } .accent { fill: %s; }\n"
        "    .line { stroke: #30363D; } .chip { fill: rgba(165,180,252,0.14); }\n"
        "  }\n"
        "</style>\n" % (width, height, width, height, esc(label), ACCENT_LIGHT, ACCENT_DARK)
    )


def clip(text, limit):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def svg_hero(account, lang, stats):
    copy = COPY[account]
    role = copy["role"][lang]
    tagline = copy["tagline"][lang]
    stars, repos, followers = statTriple(stats, account)
    statsText = " · ".join(
        part
        for part in (
            ("★ %s" % fmtStars(stars)) if stars is not None else "",
            ("%d repos" % repos) if repos is not None else "",
            ("%d followers" % followers) if followers is not None else "",
        )
        if part
    )

    w, h = 1240, 176
    out = [svgHead(w, h, "%s — %s" % (copy["handle"], role))]
    out.append('<g transform="translate(0,10)">')
    # accent tick + handle
    out.append('  <rect x="4" y="26" width="4" height="46" rx="2" class="accent"/>')
    out.append('  <text x="22" y="62" class="mono fg" font-size="40" font-weight="650" letter-spacing="0.5">%s</text>' % esc(copy["handle"]))
    out.append('  <text x="24" y="94" class="muted" font-size="15">%s</text>' % esc(role))
    out.append('  <text x="24" y="122" class="muted" font-size="14" opacity="0.92">%s</text>' % esc(clip(tagline, 88)))
    # stats cluster, right aligned
    if statsText:
        out.append('  <text x="1236" y="52" text-anchor="end" class="mono muted" font-size="14">%s</text>' % esc(statsText))
    out.append('  <text x="1236" y="76" text-anchor="end" class="mono muted" font-size="12" opacity="0.8">%s</text>' % esc(copy["home_display"]))
    # bottom hairline
    out.append('  <line x1="4" y1="%d" x2="1236" y2="%d" class="line"/>' % (h - 26, h - 26))
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def svg_work(account, lang, slug, index, stats):
    work = WORKS[slug]
    line = work["line"][lang]
    stack = work["stack"][lang]
    url = work["urls"].get(COPY[account]["platform"], work["urls"]["github"])
    stars = workStars(stats, account, slug)
    w, h = 608, 152
    out = [svgHead(w, h, "%s — %s" % (slug, stack))]
    out.append('<g transform="translate(0,6)">')
    out.append('  <line x1="2" y1="10" x2="606" y2="10" class="line"/>')
    out.append('  <text x="2" y="42" class="mono fg" font-size="21" font-weight="600">%s</text>' % esc(slug))
    if stars is not None:
        out.append('  <text x="606" y="42" text-anchor="end" class="mono muted" font-size="14">★ %s</text>' % esc(fmtStars(stars)))
    out.append('  <text x="2" y="72" class="muted" font-size="13.5">%s</text>' % esc(clip(line, 76)))
    out.append('  <text x="2" y="102" class="muted" font-size="12" opacity="0.85">%s</text>' % esc(clip(stack, 60)))
    out.append('  <a href="%s"><rect x="0" y="0" width="%d" height="%d" fill="transparent"><title>%s</title></rect></a>' % (esc(url), w, h, esc(url)))
    out.append('  <text x="2" y="132" class="accent mono" font-size="12">%s</text>' % esc(url.replace("https://", "")))
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)

# ---------------------------------------------------------------------------
# README rendering
# ---------------------------------------------------------------------------

def heroRef(lang):
    tag = {"en": "en", "zh-CN": "zh-CN", "ja": "ja"}[lang]
    return "assets/hero-%s.svg" % tag


def workRef(lang, index):
    tag = {"en": "en", "zh-CN": "zh-CN", "ja": "ja"}[lang]
    return "assets/work-%d-%s.svg" % (index, tag)


def render_readme(account, lang):
    copy = COPY[account]
    stats = load_stats()
    platform = copy["platform"]
    head = SECTION_HEADINGS[lang]
    featured = FEATURED[account]
    more = MORE[account]

    out = []
    out.append('<p align="center"><img src="%s" alt="%s · %s" width="100%%" /></p>' % (heroRef(lang), copy["handle"], esc(copy["home_display"])))
    out.append("")

    # Now
    out.append("## %s" % head["now"])
    out.append("")
    for item in copy["now"][lang]:
        out.append("- %s" % item)
    out.append("")

    # Featured work — SVG card grid, two cards per row in one paragraph
    out.append("## %s" % head["work"])
    out.append("")
    for row in range(0, len(featured), 2):
        pair = featured[row:row + 2]
        imgs = []
        for offset, slug in enumerate(pair):
            url = WORKS[slug]["urls"].get(platform, WORKS[slug]["urls"]["github"])
            imgs.append('<a href="%s"><img src="%s" alt="%s" width="49.2%%" /></a>' % (
                url, workRef(lang, row + offset + 1), esc(slug)))
        out.append('<p align="center">%s</p>' % " ".join(imgs))
        out.append("")
    moreTitle = copy["more_intro"][lang]
    moreLine = " · ".join("[%s](%s)" % (name, url) for name, _stars, url in more)
    out.append("> %s：%s" % (moreTitle, moreLine) if lang != "en" else "> %s: %s" % (moreTitle, moreLine))
    out.append("")

    # Open source (github only — mirror audiences care about the works)
    if platform == "github":
        out.append("## %s" % head["oss"])
        out.append("")
        out.append("| Upstream | Record |")
        out.append("| --- | --- |")
        for name, record, url in UPSTREAM:
            out.append("| [%s](%s) | %s |" % (name, url, record))
        out.append("")
        out.append("<sub>%s</sub>" % UPSTREAM_NOTE[lang])
        out.append("")

    # Writing (github only)
    if platform == "github":
        out.append("## %s" % head["writing"])
        out.append("")
        for date, title, url in WRITING[:3]:
            out.append("- %s — [%s](%s)" % (date, title, url))
        out.append("")
        out.append('<sub>CSDN · Juejin · Zhihu — <a href="https://blog.csdn.net/weixin_56622231">blog</a> · <a href="https://juejin.cn/user/2350111542479753">juejin</a> · <a href="https://www.zhihu.com/people/e7c851hd">zhihu</a></sub>')
        out.append("")

    # Toolbox
    out.append("**%s** — %s" % (head["toolbox"], TOOLBOX[lang]))
    out.append("")

    out.append("---")
    out.append("")
    out.append("<details>")
    out.append("<summary>%s</summary>" % head["about"])
    out.append("")
    out.append("This page is generated by `build.py` from one data source — `make gen` rebuilds every byte, `make verify` proves it offline.")
    out.append("")
    out.append("</details>")
    out.append("")
    out.append(MORE_LINK[platform])
    out.append("")
    return "\n".join(out)

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

LANGS = ("en", "zh-CN", "ja")


def render_assets(account):
    stats = load_stats()
    langs = ("en", "zh-CN", "ja") if COPY[account]["platform"] == "github" else ("zh-CN",)
    written = []
    for lang in langs:
        hero = ASSETS / ("hero-%s.svg" % {"en": "en", "zh-CN": "zh-CN", "ja": "ja"}[lang])
        hero.write_text(svg_hero(account, lang, stats), encoding="utf-8")
        written.append(hero)
        for i, slug in enumerate(FEATURED[account], 1):
            path = ASSETS / ("work-%d-%s.svg" % (i, {"en": "en", "zh-CN": "zh-CN", "ja": "ja"}[lang]))
            path.write_text(svg_work(account, lang, slug, i, stats), encoding="utf-8")
            written.append(path)
    return written


def current_account():
    return json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))["account"]


def build(account=None):
    if account is None:
        account = current_account()
    ASSETS.mkdir(exist_ok=True)
    render_assets(account)
    outputs = {}
    if COPY[account]["platform"] == "github":
        outputs["README.md"] = render_readme(account, "en")
        outputs["README.zh-CN.md"] = render_readme(account, "zh-CN")
        outputs["README.ja.md"] = render_readme(account, "ja")
    else:
        outputs["README.md"] = render_readme(account, "zh-CN")
    for name, content in outputs.items():
        (ROOT / name).write_text(content, encoding="utf-8")
    return sorted(outputs)


def main():
    build()


if __name__ == "__main__":
    main()
