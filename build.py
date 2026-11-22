#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Profile page generator — one data source, three platforms, three languages.

Design language: warm paper, cobalt + vermilion accents, oversized type,
layered "3D" cards. Everything is local SVG; no third-party badges, no
external stats services, no image hosts.

Entry points used by CI and the mirror:
    python3 scripts/generate.py --here
    python3 scripts/verify.py
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

THEMES = {
    "light": {
        "bg": "#F7F2E7",
        "bg2": "#EDF1FF",
        "panel": "#FFFFFF",
        "panel2": "#FBF7EE",
        "ink": "#15171C",
        "muted": "#5F6673",
        "faint": "#8B919C",
        "line": "#E2DACB",
        "chip": "#F2ECDD",
        "chipLine": "#DED4C1",
        "accent": "#F0502E",
        "accent2": "#2A5BFF",
        "accent3": "#0E9F6E",
        "accent4": "#7C3AED",
        "grid": "#15171C",
        "shadow": "#15171C",
    },
    "dark": {
        "bg": "#0A0C10",
        "bg2": "#111528",
        "panel": "#14171D",
        "panel2": "#181C24",
        "ink": "#F2F0EA",
        "muted": "#A6ADBA",
        "faint": "#737B88",
        "line": "#2A2F39",
        "chip": "#1D222B",
        "chipLine": "#333A46",
        "accent": "#FF6A4D",
        "accent2": "#6E9BFF",
        "accent3": "#35D39A",
        "accent4": "#A78BFA",
        "grid": "#F2F0EA",
        "shadow": "#000000",
    },
}

ACCENTS = ("accent", "accent2", "accent3", "accent4")

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

COPY = {
    "gh_badhope": {
        "platform": "github",
        "handle": "badhope",
        "home_display": "github.com/badhope",
        "role": {
            "en": "Agent developer · local-first software",
            "zh-CN": "Agent 开发者 · 本地优先软件",
            "ja": "エージェント開発者 · ローカルファースト",
        },
        "tagline": {
            "en": "I build agents that live on your own machine: small, auditable, and a little stubborn about the cloud.",
            "zh-CN": "把 Agent 装进自己的电脑：小、可复核，对云保持一点固执。",
            "ja": "自分のマシンに住むエージェントを作る。小さく、検証でき、クラウドに少し頑固に。",
        },
        "status": {
            "en": [("BUILDING", "moneyhelper · workbench"), ("PUBLISHING", "CSDN · Juejin"), ("OPEN TO", "Agent / full-stack roles"), ("TIMEZONE", "UTC+8")],
            "zh-CN": [("在做", "moneyhelper · workbench"), ("在写", "CSDN · 掘金"), ("在看", "Agent / 全栈机会"), ("时区", "UTC+8")],
            "ja": [("製作中", "moneyhelper · workbench"), ("執筆", "CSDN · Juejin"), ("募集中", "エージェント / フルスタック"), ("タイムゾーン", "UTC+8")],
        },
        "now": {
            "en": [
                "**moneyhelper** — a chat-first personal finance agent; local-first, every number auditable",
                "**workbench** — a Tauri 2 + React desktop workbench that keeps the daily grind in one window",
                "**Publishing line** — CSDN long-form and Juejin notes, automated; these two channels only",
            ],
            "zh-CN": [
                "**moneyhelper** —— 对话优先的个人理财 Agent，本地优先，每个数字都能复核",
                "**workbench** —— Tauri 2 + React 的桌面工作台，把日常琐事收进一个窗口",
                "**发布管线** —— CSDN 长文与掘金沸点自动发布，只保留这两条通道",
            ],
            "ja": [
                "**moneyhelper** —— 対話型の家計エージェント。ローカル完結、数値は検証可能",
                "**workbench** —— Tauri 2 + React のデスクトップ作業台",
                "**配信ライン** —— CSDN 長文と Juejin の短文を自動投稿。この二経路だけ",
            ],
        },
        "more_intro": {"en": "Also on the shelf", "zh-CN": "架子上还有", "ja": "棚の続き"},
    },
    "gh_morningstar": {
        "platform": "github",
        "handle": "Morningstar202604",
        "home_display": "github.com/Morningstar202604",
        "role": {
            "en": "Long-horizon projects · upstream contributor",
            "zh-CN": "长线项目 · 上游贡献者",
            "ja": "長期プロジェクト · 上流コントリビュータ",
        },
        "tagline": {
            "en": "Slow, compounding work: a few projects carried for years, and fixes that stay upstream.",
            "zh-CN": "做能复利的长线事：几个养了多年的项目，和一批留在上游的修复。",
            "ja": "ゆっくり複利で積み上げる。何年も育てるプロジェクトと、上流に残る修正。",
        },
        "status": {
            "en": [("BUILDING", "moneyhelper · sciflow"), ("PUBLISHING", "CSDN · Juejin"), ("OPEN TO", "Long-term collaboration"), ("TIMEZONE", "UTC+8")],
            "zh-CN": [("在做", "moneyhelper · sciflow"), ("在写", "CSDN · 掘金"), ("在看", "长期合作"), ("时区", "UTC+8")],
            "ja": [("製作中", "moneyhelper · sciflow"), ("執筆", "CSDN · Juejin"), ("募集中", "長期コラボ"), ("タイムゾーン", "UTC+8")],
        },
        "now": {
            "en": [
                "Carrying **moneyhelper**, **spark** and **sciflow** over the long haul",
                "Keeping upstream fixes alive: ohmyzsh, icalendar, apache/airflow",
                "Writing engineering notes on agents and local-first AI",
            ],
            "zh-CN": [
                "长线养护 **moneyhelper**、**spark**、**sciflow**",
                "把上游修复养住：ohmyzsh、icalendar、apache/airflow",
                "写工程手记：Agent 与本地优先 AI",
            ],
            "ja": [
                "**moneyhelper**、**spark**、**sciflow** を長期で育てる",
                "上流の修正を維持：ohmyzsh、icalendar、apache/airflow",
                "エージェントとローカルファースト AI の工程記録を執筆",
            ],
        },
        "more_intro": {"en": "Also on the shelf", "zh-CN": "架子上还有", "ja": "棚の続き"},
    },
    "gh_x33834": {
        "platform": "github",
        "handle": "X33834",
        "home_display": "github.com/X33834",
        "role": {
            "en": "Upstream fixes · small sharp tools",
            "zh-CN": "上游修复 · 小而锋利的工具",
            "ja": "上流修正 · 小さな道具",
        },
        "tagline": {
            "en": "I find bugs in other people's software and send the fix upstream. Small tools between the big ones.",
            "zh-CN": "在别人的软件里找 bug，把修复送回上游。大工具之间，放几件小工具。",
            "ja": "他人のソフトウェアのバグを見つけ、修正を上流へ。大きな道具の間に小さな道具を。",
        },
        "status": {
            "en": [("BUILDING", "world-walker · harbor"), ("PUBLISHING", "CSDN · Juejin"), ("OPEN TO", "Upstream / tooling"), ("TIMEZONE", "UTC+8")],
            "zh-CN": [("在做", "world-walker · harbor"), ("在写", "CSDN · 掘金"), ("在看", "上游 / 工具链"), ("时区", "UTC+8")],
            "ja": [("製作中", "world-walker · harbor"), ("執筆", "CSDN · Juejin"), ("募集中", "上流 / ツール"), ("タイムゾーン", "UTC+8")],
        },
        "now": {
            "en": [
                "Merged in **apache/airflow**; betterleaks and lefthook fixes under review",
                "Maintaining **world-walker**, **harbor** and offline mobile tools",
                "Reading codebases for a living and for fun",
            ],
            "zh-CN": [
                "已合入 **apache/airflow**；betterleaks 与 lefthook 的修复在审",
                "维护 **world-walker**、**harbor** 与离线移动工具",
                "以读代码为业，也以此为乐",
            ],
            "ja": [
                "**apache/airflow** はマージ済み。betterleaks と lefthook はレビュー中",
                "**world-walker**、**harbor** とオフライン mobile ツールを維持",
                "コードを読むのが仕事であり趣味",
            ],
        },
        "more_intro": {"en": "Also on the shelf", "zh-CN": "架子上还有", "ja": "棚の続き"},
    },
    "gitcode_badhope": {
        "platform": "gitcode",
        "handle": "badhope",
        "home_display": "gitcode.com/badhope",
        "role": {"zh-CN": "移动端开发 · 离线工具"},
        "tagline": {"zh-CN": "离线优先的移动端实验场：能装进口袋的软件，不绕云。"},
        "status": {"zh-CN": [("在做", "mashang · pocketmind"), ("在写", "CSDN · 掘金"), ("镜像", "GitHub → GitCode"), ("时区", "UTC+8")]},
        "now": {
            "zh-CN": [
                "**mashang** —— 赛博朋克风离线编程终端，内置 CPython 3.13",
                "**pocketmind** —— 住进 Android 的常驻 Agent，一个 APK 独立运行",
                "**发布管线** —— CSDN 长文与掘金沸点自动发布",
            ]
        },
        "more_intro": {"zh-CN": "架子上还有"},
    },
    "gitee_badhope": {
        "platform": "gitee",
        "handle": "badhope",
        "home_display": "gitee.com/badhope",
        "role": {"zh-CN": "作品镜像 · 小程序"},
        "tagline": {"zh-CN": "作品另一处安放：精选项目与小型实验，保持同一套骨架。"},
        "status": {"zh-CN": [("在做", "shopcash · quiz-chest"), ("在写", "CSDN · 掘金"), ("镜像", "GitHub → Gitee"), ("时区", "UTC+8")]},
        "now": {
            "zh-CN": [
                "**shopcash** —— 单机门店收银与记账，资金零介入",
                "**quiz-chest** —— 本地优先的自有题库练习",
                "**发布管线** —— CSDN 长文与掘金沸点自动发布",
            ]
        },
        "more_intro": {"zh-CN": "架子上还有"},
    },
}

WORKS = {
    "moneyhelper": {
        "title": {"en": "moneyhelper", "zh-CN": "moneyhelper", "ja": "moneyhelper"},
        "stack": {"en": "FastAPI · LangGraph · React", "zh-CN": "FastAPI · LangGraph · React", "ja": "FastAPI · LangGraph · React"},
        "line": {
            "en": "A chat-first finance agent that keeps the books on your machine. Sentence-level bookkeeping, portfolio risk, earnings research.",
            "zh-CN": "对话优先的个人理财 Agent：一句话记账、持仓风控、财报分析，账本留在自己机器上。",
            "ja": "対話型の家計エージェント。一文で記帳、リスク管理、決算分析。家計簿は自分のマシンに。",
        },
    },
    "workbench": {
        "title": {"en": "workbench", "zh-CN": "workbench", "ja": "workbench"},
        "stack": {"en": "Tauri 2 · React 19 · TypeScript", "zh-CN": "Tauri 2 · React 19 · TypeScript", "ja": "Tauri 2 · React 19 · TypeScript"},
        "line": {
            "en": "A quiet desktop workbench: clipboard, snippets, windows, quick launch — the daily grind in one app.",
            "zh-CN": "安静的桌面工作台：剪贴板、片段、窗口、快速启动，把日常琐事收进一个应用。",
            "ja": "静かなデスクトップ作業台。クリップボード、スニペット、起動をひとつに。",
        },
    },
    "spark": {
        "title": {"en": "spark", "zh-CN": "spark", "ja": "spark"},
        "stack": {"en": "Python · React · self-hosted", "zh-CN": "Python · React · 自托管", "ja": "Python · React · セルフホスト"},
        "line": {
            "en": "A self-hosted coding-agent harness: cockpit UI, sandboxed runs, MCP tools. Your agent, your rules.",
            "zh-CN": "自托管的编码智能体底座：驾驶舱界面、沙箱执行、MCP 工具，自己的 Agent 自己定规矩。",
            "ja": "セルフホストのコーディングエージェント基盤。コックピット UI、サンドボックス実行、MCP ツール。",
        },
    },
    "world-walker": {
        "title": {"en": "world-walker", "zh-CN": "world-walker", "ja": "world-walker"},
        "stack": {"en": "Python stdlib · MCP", "zh-CN": "Python 标准库 · MCP", "ja": "Python 標準ライブラリ · MCP"},
        "line": {
            "en": "A deterministic rules layer for AI interactive fiction: 64 MCP tools, a save library, no cloud.",
            "zh-CN": "AI 互动小说的确定性规则层：64 个 MCP 工具、存档库，不依赖云。",
            "ja": "AI 対話フィクションの決定論ルール層。64 の MCP ツール、セーブ管理。",
        },
    },
    "mashang": {
        "title": {"en": "mashang", "zh-CN": "mashang", "ja": "mashang"},
        "stack": {"en": "Kotlin · CPython 3.13 · offline", "zh-CN": "Kotlin · CPython 3.13 · 离线", "ja": "Kotlin · CPython 3.13 · オフライン"},
        "line": {
            "en": "A cyberpunk offline programming terminal: built-in CPython and JS, quests, assert grading.",
            "zh-CN": "赛博朋克风离线编程学习终端：内置 CPython 与 JS，关卡制、assert 判题。",
            "ja": "サイバーパンクなオフライン学習ターミナル。CPython と JS を内蔵、クエスト制。",
        },
    },
    "pocketmind": {
        "title": {"en": "pocketmind", "zh-CN": "pocketmind", "ja": "pocketmind"},
        "stack": {"en": "Android · on-device AI", "zh-CN": "Android · 端侧 AI", "ja": "Android · 端側 AI"},
        "line": {
            "en": "A resident agent inside an Android phone: one APK, on-device tools, no round trips.",
            "zh-CN": "住进 Android 手机的常驻 Agent：一个 APK 独立运行，端侧工具，不绕云。",
            "ja": "Android に住む常駐エージェント。APK ひとつ、端側で動く。",
        },
    },
    "quiz-chest": {
        "title": {"en": "quiz-chest", "zh-CN": "quiz-chest", "ja": "quiz-chest"},
        "stack": {"en": "Local-first · question bank", "zh-CN": "本地优先 · 自有题库", "ja": "ローカルファースト · 問題バンク"},
        "line": {
            "en": "Your own question bank, offline: import, tag, drill — the data stays yours.",
            "zh-CN": "练自己的题库：导入、打标、刷题，数据始终是自己的。",
            "ja": "自分の問題バンクを練習。取り込み、タグ付け、ドリル。",
        },
    },
    "shopcash": {
        "title": {"en": "shopcash", "zh-CN": "shopcash", "ja": "shopcash"},
        "stack": {"en": "Desktop · payments-free", "zh-CN": "桌面应用 · 无资金介入", "ja": "デスクトップ · 決済非介入"},
        "line": {
            "en": "Single-machine cashier and books for small shops; money never touches the software.",
            "zh-CN": "单机门店收银与记账，钱只进商家自己的账户，软件零资金介入。",
            "ja": "小規模店舗向けレジと記帳。売上は常に店舗自身の口座へ。",
        },
    },
    "sciflow": {
        "title": {"en": "sciflow", "zh-CN": "sciflow", "ja": "sciflow"},
        "stack": {"en": "Python · research workbench", "zh-CN": "Python · 科研工作台", "ja": "Python · 研究ワークベンチ"},
        "line": {
            "en": "From a topic to a submittable manuscript: literature triage, experiment log, structured drafting.",
            "zh-CN": "从一个题目到一份可投稿的稿件：文献分诊、实验记录、结构化写作。",
            "ja": "テーマから投稿可能な原稿まで。文献整理、実験記録、構造化執筆。",
        },
    },
    "harbor": {
        "title": {"en": "harbor", "zh-CN": "harbor", "ja": "harbor"},
        "stack": {"en": "Publishing hub · 15 platforms", "zh-CN": "发布枢纽 · 15 个平台", "ja": "配信ハブ · 15 プラットフォーム"},
        "line": {
            "en": "Write once, ship to fifteen platforms: a self-hosted publishing hub with per-channel typesetting.",
            "zh-CN": "写一次，发十五处：自托管的发布枢纽，按渠道各自排版。",
            "ja": "一度書いて 15 箇所へ。チャネル別に整形する配信ハブ。",
        },
    },
    "CodePocket": {
        "title": {"en": "CodePocket", "zh-CN": "CodePocket", "ja": "CodePocket"},
        "stack": {"en": "Android · offline Python IDE", "zh-CN": "Android · 离线 Python IDE", "ja": "Android · オフライン Python IDE"},
        "line": {
            "en": "An offline-first Python IDE for Android: native CPython 3.13 in your pocket, no cloud.",
            "zh-CN": "离线优先的安卓 Python IDE：兜里装着原生 CPython 3.13，不靠云。",
            "ja": "オフラインファーストの Android 用 Python IDE。ネイティブ CPython 3.13 をポケットに。",
        },
    },
}

FEATURED = {
    "gh_badhope": ["moneyhelper", "spark", "workbench", "world-walker"],
    "gitcode_badhope": ["mashang", "pocketmind", "CodePocket", "workbench"],
    "gitee_badhope": ["shopcash", "quiz-chest", "mashang", "moneyhelper"],
    "gh_morningstar": ["moneyhelper", "spark", "sciflow", "workbench"],
    "gh_x33834": ["world-walker", "harbor", "CodePocket", "mashang"],
}

MORE = {
    "gh_badhope": [
        ("DU", "https://github.com/badhope/DU"),
        ("mashang", "https://github.com/badhope/mashang"),
        ("digilegacy", "https://github.com/badhope/digilegacy"),
        ("harbor", "https://github.com/badhope/harbor"),
        ("sciflow", "https://github.com/badhope/sciflow"),
        ("pocketmind", "https://github.com/badhope/pocketmind"),
        ("aquapilot", "https://github.com/badhope/aquapilot"),
        ("melee", "https://github.com/badhope/melee"),
    ],
    "gitcode_badhope": [
        ("CodePocket", "https://gitcode.com/badhope/CodePocket"),
        ("moneyhelper", "https://gitcode.com/badhope/moneyhelper"),
        ("spark", "https://gitcode.com/badhope/spark"),
        ("workbench", "https://gitcode.com/badhope/workbench"),
    ],
    "gitee_badhope": [
        ("mashang", "https://gitee.com/badhope/mashang"),
        ("moneyhelper", "https://gitee.com/badhope/moneyhelper"),
        ("spark", "https://gitee.com/badhope/spark"),
        ("world-walker", "https://gitee.com/badhope/world-walker"),
    ],
    "gh_morningstar": [
        ("sciflow", "https://github.com/Morningstar202604/sciflow"),
        ("world-walker", "https://github.com/Morningstar202604/world-walker"),
        ("digilegacy", "https://github.com/Morningstar202604/digilegacy"),
        ("harbor", "https://github.com/Morningstar202604/harbor"),
        ("creator-studio", "https://github.com/Morningstar202604/creator-studio"),
    ],
    "gh_x33834": [
        ("harbor", "https://github.com/X33834/harbor"),
        ("CodePocket", "https://github.com/X33834/CodePocket"),
        ("moneyhelper", "https://github.com/X33834/moneyhelper"),
        ("digilegacy", "https://github.com/X33834/digilegacy"),
    ],
}

UPSTREAM = [
    ("ohmyzsh", "https://github.com/ohmyzsh/ohmyzsh"),
    ("icalendar", "https://github.com/python-icalendar/icalendar"),
    ("apache/airflow", "https://github.com/apache/airflow"),
    ("renovate-operator", "https://github.com/mogenius/renovate-operator"),
]

WRITING = [
    ("2026-11-04", "把 AI Agent 接进业务系统，我踩了 3 个挺蠢的坑", "https://blog.csdn.net/weixin_56622231/article/details/170051167"),
    ("2026-10-18", "Gemini 4 Argon 全面开放：谷歌憋了半年的旗舰大招，到底行不行？", "https://blog.csdn.net/weixin_56622231/article/details/168251657"),
]

CHANNELS = [
    {
        "key": "csdn",
        "name": {"en": "CSDN", "zh-CN": "CSDN", "ja": "CSDN"},
        "initial": "C",
        "url": "https://blog.csdn.net/weixin_56622231",
        "display": "badhope.blog.csdn.net",
        "tag": {"en": "AUTO · LONG FORM", "zh-CN": "自动发布 · 长文", "ja": "自動公開 · 長文"},
        "note": {
            "en": "Engineering notes and post-mortems, published on a schedule.",
            "zh-CN": "工程手记与踩坑复盘，按计划自动发布。",
            "ja": "工程メモと失敗談を定期公開。",
        },
    },
    {
        "key": "juejin",
        "name": {"en": "Juejin", "zh-CN": "稀土掘金", "ja": "Juejin"},
        "initial": "J",
        "url": "https://juejin.cn/user/2350111542479753",
        "display": "juejin.cn/user/2350111542479753",
        "tag": {"en": "AUTO · DAILY", "zh-CN": "自动运营 · 日更", "ja": "自動運用 · 毎日"},
        "note": {
            "en": "Short daily notes and boiling points, run by the automation line.",
            "zh-CN": "短平快的日常与沸点，由自动化管线运营。",
            "ja": "短い日常メモ、自動化ラインで運用。",
        },
    },
]

TOOLBOX = {
    "en": ["Python", "TypeScript", "Kotlin", "Tauri", "MCP"],
    "zh-CN": ["Python", "TypeScript", "Kotlin", "Tauri", "MCP"],
    "ja": ["Python", "TypeScript", "Kotlin", "Tauri", "MCP"],
}

HEADINGS = {
    "en": {"now": "Now", "work": "Selected work", "numbers": "Numbers", "publish": "Publishing line", "more": "Also on the shelf"},
    "zh-CN": {"now": "现在", "work": "代表作品", "numbers": "数据", "publish": "发布管线", "more": "架子上还有"},
    "ja": {"now": "いま", "work": "代表作", "numbers": "数字", "publish": "配信ライン", "more": "棚の続き"},
}

METRIC_LABELS = {
    "commits": {"en": "COMMITS", "zh-CN": "提交", "ja": "コミット"},
    "prs": {"en": "PULL REQUESTS", "zh-CN": "PR", "ja": "PR"},
    "merged": {"en": "MERGED", "zh-CN": "已合并", "ja": "マージ済み"},
    "followers": {"en": "FOLLOWERS", "zh-CN": "关注者", "ja": "フォロワー"},
    "repos": {"en": "REPOSITORIES", "zh-CN": "仓库", "ja": "リポジトリ"},
    "stars": {"en": "STARS", "zh-CN": "星标", "ja": "スター"},
    "works": {"en": "FEATURED", "zh-CN": "精选作品", "ja": "代表作"},
}

SIGNAL_TITLE = {
    "en": "Signal · last 12 months",
    "zh-CN": "信号 · 过去 12 个月",
    "ja": "シグナル · 直近 12 か月",
}

LANG_NAMES = {"en": "English", "zh-CN": "中文", "ja": "日本語"}

WRITING_MORE = {"en": "All posts on CSDN →", "zh-CN": "CSDN 全部文章 →", "ja": "CSDN の全記事 →"}

MORE_LINK_TEXT = {
    "en": "All public repositories",
    "zh-CN": "全部仓库",
    "ja": "すべてのリポジトリ",
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


def stat_metrics(account):
    stats = load_stats()
    acc = stats.get("accounts", {}).get(account, {})
    platform = COPY[account]["platform"]
    if platform == "github":
        keys = ["commits", "prs", "merged", "followers"]
    else:
        keys = ["repos", "stars", "followers", "works"]
    values = []
    for key in keys:
        if key == "works":
            values.append(len(FEATURED[account]))
        else:
            values.append(acc.get(key))
    return keys, values, stats.get("as_of", "")


def work_stars(account, slug):
    stats = load_stats()
    acc = stats.get("accounts", {}).get(account, {})
    return acc.get("works", {}).get(slug, {}).get("stars")


def fmt_num(value):
    if value is None:
        return "—"
    try:
        return "{:,}".format(int(value))
    except (TypeError, ValueError):
        return str(value)

# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def wrap_text(text, limit, lang):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if lang in ("zh-CN", "ja"):
        # Prefer punctuation boundaries; never split a katakana / Latin run
        # if a natural break is available.
        segments = [seg for seg in re.split(r"(?<=[。！？；、，,：:])", text) if seg]
        lines, cur = [], ""
        for seg in segments:
            if len(cur) + len(seg) > limit and cur:
                lines.append(cur)
                cur = seg
            else:
                cur += seg
        if cur:
            lines.append(cur)
        return [line for line in lines if line]
    words, lines, cur = text.split(" "), [], ""
    for word in words:
        candidate = (cur + " " + word).strip()
        if len(candidate) > limit and cur:
            lines.append(cur)
            cur = word
        else:
            cur = candidate
    if cur:
        lines.append(cur)
    return lines


def svg_head(width, height, label, theme):
    t = THEMES[theme]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}">\n'
        "<style>\n"
        "  text { font-family: -apple-system, 'Segoe UI', 'PingFang SC', 'Hiragino Sans', 'Noto Sans SC', 'Microsoft YaHei', sans-serif; }\n"
        "  .mono { font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace; }\n"
        f"  .ink {{ fill: {t['ink']}; }}\n"
        f"  .muted {{ fill: {t['muted']}; }}\n"
        f"  .faint {{ fill: {t['faint']}; }}\n"
        f"  .accent {{ fill: {t['accent']}; }}\n"
        f"  .accent2 {{ fill: {t['accent2']}; }}\n"
        f"  .accent3 {{ fill: {t['accent3']}; }}\n"
        f"  .accent4 {{ fill: {t['accent4']}; }}\n"
        f"  .line {{ stroke: {t['line']}; stroke-width: 1; }}\n"
        "</style>\n"
    )


def chip_row(x, y, items, theme, lang):
    t = THEMES[theme]
    out = []
    cx = x
    for item in items:
        width = int(len(item) * 6.8 + 20)
        out.append(
            f'<rect x="{cx}" y="{y}" width="{width}" height="24" rx="12" '
            f'fill="{t["chip"]}" stroke="{t["chipLine"]}"/>'
        )
        out.append(
            f'<text x="{cx + width / 2}" y="{y + 16}" text-anchor="middle" '
            f'class="mono muted" font-size="10.5">{esc(item)}</text>'
        )
        cx += width + 8
    return out


def svg_hero(account, lang, theme):
    copy = COPY[account]
    t = THEMES[theme]
    role = copy["role"][lang]
    tagline = copy["tagline"][lang]
    handle = copy["handle"]
    size = 72 if len(handle) <= 8 else 50 if len(handle) <= 12 else 38
    w, h = 1240, 320
    out = [svg_head(w, h, f"{handle} — {role}", theme)]
    out.append("<defs>")
    out.append(
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{t["bg"]}"/><stop offset="0.55" stop-color="{t["bg"]}"/>'
        f'<stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>'
    )
    out.append(
        f'<radialGradient id="orbA"><stop stop-color="{t["accent"]}" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></radialGradient>'
    )
    out.append(
        f'<radialGradient id="orbB"><stop stop-color="{t["accent2"]}" stop-opacity="0.50"/>'
        f'<stop offset="1" stop-color="{t["accent2"]}" stop-opacity="0"/></radialGradient>'
    )
    out.append(
        f'<radialGradient id="sphere" cx="35%" cy="26%" r="78%">'
        f'<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.95"/>'
        f'<stop offset="0.28" stop-color="{t["accent2"]}"/>'
        f'<stop offset="0.72" stop-color="{t["accent"]}"/>'
        f'<stop offset="1" stop-color="{t["ink"]}"/></radialGradient>'
    )
    out.append(
        f'<pattern id="grid" width="44" height="44" patternUnits="userSpaceOnUse">'
        f'<path d="M44 0H0V44" fill="none" stroke="{t["grid"]}" stroke-opacity="0.06" stroke-width="1"/>'
        f'</pattern>'
    )
    out.append('<filter id="blur"><feGaussianBlur stdDeviation="34"/></filter>')
    out.append(
        f'<filter id="soft" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{t["shadow"]}" flood-opacity="0.16"/>'
        f'</filter>'
    )
    out.append("</defs>")
    out.append(f'<rect width="{w}" height="{h}" rx="26" fill="url(#bg)"/>')
    out.append(f'<rect width="{w}" height="{h}" rx="26" fill="url(#grid)"/>')
    out.append(f'<circle cx="1090" cy="10" r="210" fill="url(#orbA)" filter="url(#blur)" opacity="0.75"/>')
    out.append(f'<circle cx="880" cy="330" r="220" fill="url(#orbB)" filter="url(#blur)" opacity="0.65"/>')
    out.append(f'<circle cx="1164" cy="268" r="40" fill="url(#sphere)" filter="url(#soft)"/>')
    out.append(f'<ellipse cx="1152" cy="252" rx="12" ry="7" fill="#FFFFFF" opacity="0.55"/>')

    # identity block
    out.append(f'<rect x="56" y="46" width="4" height="14" rx="2" fill="{t["accent"]}"/>')
    out.append('<text x="70" y="58" class="mono muted" font-size="11" letter-spacing="2.2">PROFILE / 2026</text>')
    out.append(
        f'<text x="54" y="132" class="ink" font-size="{size}" font-weight="750" '
        f'letter-spacing="-{2.2 if size >= 60 else 1.2}">{esc(handle)}</text>'
    )
    out.append(f'<text x="58" y="168" class="muted" font-size="19">{esc(role)}</text>')
    for i, line in enumerate(wrap_text(tagline, 62 if lang == "en" else 31 if lang == "zh-CN" else 37, lang)[:2]):
        out.append(f'<text x="58" y="{200 + i * 24}" class="muted" font-size="15.5" opacity="0.92">{esc(line)}</text>')
    for item in chip_row(58, 246, TOOLBOX[lang], theme, lang):
        out.append(item)

    # status card
    out.append(
        f'<rect x="856" y="42" width="328" height="164" rx="20" fill="{t["panel"]}" '
        f'fill-opacity="0.86" stroke="{t["line"]}" filter="url(#soft)"/>'
    )
    out.append(f'<text x="882" y="70" class="mono faint" font-size="9.5" letter-spacing="1.8">STATUS</text>')
    rows = copy["status"][lang]
    for i, (label, value) in enumerate(rows):
        y = 94 + i * 32
        out.append(f'<circle cx="884" cy="{y - 4}" r="3.5" fill="{t[ACCENTS[i % 4]]}"/>')
        out.append(f'<text x="898" y="{y}" class="mono muted" font-size="10.5" letter-spacing="1.1">{esc(label)}</text>')
        out.append(f'<text x="1160" y="{y}" text-anchor="end" class="ink" font-size="13.5">{esc(value)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def svg_work(account, lang, slug, index, theme):
    work = WORKS[slug]
    t = THEMES[theme]
    accent = t[ACCENTS[(index - 1) % 4]]
    title = work["title"][lang]
    line = work["line"][lang]
    stack = work["stack"][lang]
    url = work_url(account, slug)
    stars = work_stars(account, slug)
    w, h = 608, 246
    out = [svg_head(w, h, f"{title} — {stack}", theme)]
    out.append(
        f'<filter id="soft" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="{t["shadow"]}" flood-opacity="0.14"/>'
        f'</filter>'
    )
    out.append(f'<rect x="12" y="14" width="584" height="218" rx="20" fill="{accent}" opacity="0.11"/>')
    out.append(
        f'<rect x="4" y="4" width="584" height="200" rx="20" fill="{t["panel"]}" '
        f'stroke="{t["line"]}" filter="url(#soft)"/>'
    )
    out.append(f'<rect x="4" y="4" width="584" height="6" rx="3" fill="{accent}"/>')
    out.append(f'<text x="28" y="38" class="mono faint" font-size="10.5" letter-spacing="1.5">FEATURED / {index:02d}</text>')
    if stars:
        out.append(
            f'<rect x="486" y="20" width="76" height="24" rx="12" fill="{t["chip"]}" stroke="{t["chipLine"]}"/>'
        )
        out.append(f'<text x="524" y="36" text-anchor="middle" class="mono muted" font-size="11">★ {esc(fmt_num(stars))}</text>')
    out.append(f'<text x="28" y="82" class="ink" font-size="29" font-weight="720" letter-spacing="-0.6">{esc(title)}</text>')
    for i, part in enumerate(wrap_text(line, 52 if lang == "en" else 25 if lang == "zh-CN" else 31, lang)[:3]):
        out.append(f'<text x="28" y="{110 + i * 21}" class="muted" font-size="14.2" opacity="0.92">{esc(part)}</text>')
    for item in chip_row(28, 170, [s.strip() for s in stack.split("·")][:3], theme, lang):
        out.append(item)
    out.append(f'<text x="28" y="214" class="mono" font-size="10.5" fill="{accent}">{esc(url.replace("https://", ""))}</text>')
    out.append(f'<text x="556" y="214" text-anchor="end" class="mono" font-size="12" fill="{accent}">↗</text>')
    out.append("</svg>")
    return "\n".join(out)


def svg_numbers(account, lang, theme):
    keys, values, as_of = stat_metrics(account)
    t = THEMES[theme]
    w, h = 1240, 156
    out = [svg_head(w, h, "numbers", theme)]
    out.append(
        f'<filter id="soft" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="{t["shadow"]}" flood-opacity="0.12"/>'
        f'</filter>'
    )
    out.append(
        f'<rect x="4" y="4" width="1232" height="160" rx="24" fill="{t["panel"]}" '
        f'stroke="{t["line"]}" filter="url(#soft)"/>'
    )
    out.append(f'<rect x="4" y="4" width="6" height="136" rx="3" fill="{t["accent"]}"/>')
    out.append(f'<text x="40" y="46" class="mono" font-size="10" letter-spacing="2" fill="{t["accent"]}">SIGNAL / 03</text>')
    out.append(f'<text x="40" y="80" class="ink" font-size="21" font-weight="650">{esc(SIGNAL_TITLE[lang])}</text>')
    out.append(f'<text x="40" y="106" class="mono faint" font-size="11.2">as of {esc(as_of)}</text>')
    start = 360
    step = 206
    for i, (key, value) in enumerate(zip(keys, values)):
        x = start + i * step
        out.append(f'<line x1="{x - 28}" y1="34" x2="{x - 28}" y2="116" stroke="{t["line"]}"/>')
        out.append(f'<text x="{x}" y="66" class="ink" font-size="38" font-weight="750" letter-spacing="-1.2">{esc(fmt_num(value))}</text>')
        out.append(f'<text x="{x}" y="98" class="mono muted" font-size="11.2" letter-spacing="1.3">{esc(METRIC_LABELS[key][lang])}</text>')
        out.append(f'<rect x="{x}" y="110" width="38" height="3" rx="1.5" fill="{t[ACCENTS[i % 4]]}"/>')
    out.append("</svg>")
    return "\n".join(out)


def svg_channel(channel, lang, theme):
    t = THEMES[theme]
    accent = t["accent"] if channel["key"] == "csdn" else t["accent2"]
    w, h = 608, 156
    out = [svg_head(w, h, channel["name"][lang], theme)]
    out.append(
        f'<filter id="soft" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="9" stdDeviation="13" flood-color="{t["shadow"]}" flood-opacity="0.13"/>'
        f'</filter>'
    )
    out.append(f'<rect x="12" y="14" width="584" height="128" rx="18" fill="{accent}" opacity="0.10"/>')
    out.append(
        f'<rect x="4" y="4" width="584" height="128" rx="18" fill="{t["panel"]}" '
        f'stroke="{t["line"]}" filter="url(#soft)"/>'
    )
    out.append(f'<rect x="28" y="28" width="52" height="52" rx="16" fill="{accent}" opacity="0.13"/>')
    out.append(f'<text x="54" y="64" text-anchor="middle" font-size="24" font-weight="750" fill="{accent}">{esc(channel["initial"])}</text>')
    out.append(f'<text x="98" y="50" class="ink" font-size="23" font-weight="700">{esc(channel["name"][lang])}</text>')
    out.append(f'<rect x="452" y="24" width="108" height="22" rx="11" fill="{accent}" opacity="0.12"/>')
    out.append(f'<text x="506" y="39" text-anchor="middle" class="mono" font-size="9.2" letter-spacing="1" fill="{accent}">{esc(channel["tag"][lang])}</text>')
    out.append(f'<text x="98" y="78" class="muted" font-size="13.5" opacity="0.92">{esc(channel["note"][lang])}</text>')
    out.append(f'<text x="98" y="110" class="mono faint" font-size="10.5">{esc(channel["display"])}</text>')
    out.append(f'<text x="556" y="110" text-anchor="end" class="mono" font-size="12" fill="{accent}">↗</text>')
    out.append("</svg>")
    return "\n".join(out)

# ---------------------------------------------------------------------------
# README rendering
# ---------------------------------------------------------------------------


def work_url(account, slug):
    entry = WORKS[slug]
    platform = COPY[account]["platform"]
    override = (entry.get("account_urls") or {}).get(account)
    if override:
        return override
    base = {"github": "https://github.com", "gitcode": "https://gitcode.com", "gitee": "https://gitee.com"}[platform]
    repo = entry.get("repo", slug)
    return f"{base}/{COPY[account]['handle']}/{repo}"


def picture(light, dark, alt, width="100%"):
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="{dark}" />'
        f'<img src="{light}" alt="{esc(alt)}" width="{width}" /></picture>'
    )


def asset(name, lang, theme):
    return f"assets/{name}-{lang}-{theme}.svg"


def render_readme(account, lang):
    copy = COPY[account]
    stats = load_stats()
    platform = copy["platform"]
    head = HEADINGS[lang]
    featured = FEATURED[account]
    more = MORE[account]
    out = []

    if platform == "github":
        parts = []
        for other in ("en", "zh-CN", "ja"):
            if other == lang:
                parts.append(f"<b>{LANG_NAMES[other]}</b>")
            else:
                target = {"en": "README.md", "zh-CN": "README.zh-CN.md", "ja": "README.ja.md"}[other]
                parts.append(f'<a href="{target}">{LANG_NAMES[other]}</a>')
        out.append(f'<p align="right"><sub>{" · ".join(parts)}</sub></p>')
        out.append("")

    out.append('<p align="center">')
    out.append(picture(asset("hero", lang, "light"), asset("hero", lang, "dark"), f"{copy['handle']} · {copy['home_display']}"))
    out.append("</p>")
    out.append("")

    out.append(f"## 01 · {head['now']}")
    out.append("")
    for item in copy["now"][lang]:
        out.append(f"- {item}")
    out.append("")

    out.append(f"## 02 · {head['work']}")
    out.append("")
    for row in range(0, len(featured), 2):
        cards = []
        for offset, slug in enumerate(featured[row:row + 2]):
            index = row + offset + 1
            cards.append(
                f'<a href="{work_url(account, slug)}">'
                + picture(
                    asset(f"work-{index}", lang, "light"),
                    asset(f"work-{index}", lang, "dark"),
                    slug,
                    "49.2%",
                )
                + "</a>"
            )
        out.append(f'<p align="center">{" ".join(cards)}</p>')
        out.append("")

    out.append(f"## 03 · {head['numbers']}")
    out.append("")
    out.append('<p align="center">')
    out.append(picture(asset("numbers", lang, "light"), asset("numbers", lang, "dark"), "numbers", "100%"))
    out.append("</p>")
    out.append("")

    out.append(f"## 04 · {head['publish']}")
    out.append("")
    cards = []
    for channel in CHANNELS:
        cards.append(
            f'<a href="{channel["url"]}">'
            + picture(
                asset(f"channel-{channel['key']}", lang, "light"),
                asset(f"channel-{channel['key']}", lang, "dark"),
                channel["name"][lang],
                "49.2%",
            )
            + "</a>"
        )
    out.append(f'<p align="center">{" ".join(cards)}</p>')
    out.append("")
    for date, title, url in WRITING:
        out.append(f"- {date} — [{title}]({url})")
    out.append("")
    out.append(f'<sub><a href="{CHANNELS[0]["url"]}">{WRITING_MORE[lang]}</a></sub>')
    out.append("")

    out.append(f"## 05 · {head['more']}")
    out.append("")
    more_line = " · ".join(f"[{name}]({url})" for name, url in more)
    out.append(f"> {more_line}")
    out.append("")

    if platform == "github":
        upstream = " · ".join(f"[{name}]({url})" for name, url in UPSTREAM)
        out.append(f'<sub>Upstream: {upstream}</sub>')
        out.append("")
    out.append('<sub>One source, five profiles · numbers from a local snapshot</sub>')
    out.append("")
    home = copy["home_display"]
    out.append(f"{MORE_LINK_TEXT[lang]}: [{home}](https://{home})")
    out.append("")
    return "\n".join(out)

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

LANGS = ("en", "zh-CN", "ja")
THEME_NAMES = ("light", "dark")


def render_assets(account):
    langs = LANGS if COPY[account]["platform"] == "github" else ("zh-CN",)
    written = []
    for theme in THEME_NAMES:
        for lang in langs:
            hero = ASSETS / f"hero-{lang}-{theme}.svg"
            hero.write_text(svg_hero(account, lang, theme), encoding="utf-8")
            written.append(hero)
            numbers = ASSETS / f"numbers-{lang}-{theme}.svg"
            numbers.write_text(svg_numbers(account, lang, theme), encoding="utf-8")
            written.append(numbers)
            for i, slug in enumerate(FEATURED[account], 1):
                path = ASSETS / f"work-{i}-{lang}-{theme}.svg"
                path.write_text(svg_work(account, lang, slug, i, theme), encoding="utf-8")
                written.append(path)
            for channel in CHANNELS:
                path = ASSETS / f"channel-{channel['key']}-{lang}-{theme}.svg"
                path.write_text(svg_channel(channel, lang, theme), encoding="utf-8")
                written.append(path)
    return written


def current_account():
    return json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))["account"]


def build(account=None):
    if account is None:
        account = current_account()
    ASSETS.mkdir(exist_ok=True)
    # Drop assets from the previous design so stale files never linger.
    for path in ASSETS.glob("*.svg"):
        path.unlink()
    render_assets(account)
    outputs = {}
    if COPY[account]["platform"] == "github":
        outputs["README.md"] = render_readme(account, "en")
        outputs["README.zh-CN.md"] = render_readme(account, "zh-CN")
        outputs["README.ja.md"] = render_readme(account, "ja")
    else:
        outputs["README.md"] = render_readme(account, "zh-CN")
        # Mirrors keep a single Chinese README; drop stale multilingual copies
        # left by the previous pipeline so verify never sees foreign links.
        for stale in ("README.zh-CN.md", "README.ja.md"):
            path = ROOT / stale
            if path.exists():
                path.unlink()
    for name, content in outputs.items():
        (ROOT / name).write_text(content, encoding="utf-8")
    return sorted(outputs)


def main():
    build()


if __name__ == "__main__":
    main()
