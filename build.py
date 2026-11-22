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
import math
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

THEMES = {
    "light": {
        "bg": "#F8F2E4",
        "bg2": "#E7EDFB",
        "panel": "#FFFDF7",
        "panel2": "#F7F0DF",
        "ink": "#141A2A",
        "muted": "#5D6478",
        "faint": "#8A8FA3",
        "line": "#DDD2BD",
        "chip": "#F1E8D6",
        "chipLine": "#D8CCB4",
        "accent": "#E14B2B",
        "accent2": "#2E5BC7",
        "accent3": "#0E8E77",
        "accent4": "#7A4FD6",
        "grid": "#141A2A",
        "shadow": "#141A2A",
        "star": "#8C5A10",
        "constellation": "#214FC4",
        "nebulaA": "#F3B49B",
        "nebulaB": "#A9BFF2",
        "gold": "#B57712",
    },
    "dark": {
        "bg": "#05070E",
        "bg2": "#0A1124",
        "panel": "#0D121D",
        "panel2": "#111827",
        "ink": "#F4F1E7",
        "muted": "#A8B1C3",
        "faint": "#6E788E",
        "line": "#283145",
        "chip": "#171F30",
        "chipLine": "#303A50",
        "accent": "#FF7455",
        "accent2": "#7FA5FF",
        "accent3": "#3DDAAA",
        "accent4": "#B79BFF",
        "grid": "#F4F1E7",
        "shadow": "#000000",
        "star": "#FFE3A0",
        "constellation": "#9DB8FF",
        "nebulaA": "#FF6B4D",
        "nebulaB": "#5D7CFF",
        "gold": "#EDBD62",
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
            "en": "Self-hosted agents, local-first tools, and upstream fixes.",
            "zh-CN": "自托管 Agent、本地优先工具与上游修复。",
            "ja": "セルフホストのエージェント、ローカルファーストの道具、上流の修正。",
        },
        "status": {
            "en": [("BUILDING", "moneyhelper · workbench"), ("PUBLISHING", "4 channels"), ("OPEN TO", "Agent / full-stack roles"), ("TIMEZONE", "UTC+8")],
            "zh-CN": [("在做", "moneyhelper · workbench"), ("在写", "四通道"), ("在看", "Agent / 全栈机会"), ("时区", "UTC+8")],
            "ja": [("製作中", "moneyhelper · workbench"), ("執筆", "4チャネル"), ("募集中", "エージェント / フルスタック"), ("タイムゾーン", "UTC+8")],
        },
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
            "en": "Long-horizon projects and upstream fixes; notes on CSDN, Juejin, Zhihu and Cnblogs.",
            "zh-CN": "长线项目与上游修复；工程手记发在 CSDN、掘金、知乎与博客园。",
            "ja": "長期プロジェクトと上流の修正。記録は CSDN、Juejin、Zhihu、Cnblogs に。",
        },
        "status": {
            "en": [("BUILDING", "moneyhelper · sciflow"), ("PUBLISHING", "4 channels"), ("OPEN TO", "Long-term collaboration"), ("TIMEZONE", "UTC+8")],
            "zh-CN": [("在做", "moneyhelper · sciflow"), ("在写", "四通道"), ("在看", "长期合作"), ("时区", "UTC+8")],
            "ja": [("製作中", "moneyhelper · sciflow"), ("執筆", "4チャネル"), ("募集中", "長期コラボ"), ("タイムゾーン", "UTC+8")],
        },
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
            "en": "Upstream fixes and small tools; read the code, send the fix back.",
            "zh-CN": "上游修复与小工具；读代码，把修复送回上游。",
            "ja": "上流の修正と小さな道具。コードを読み、修正を返す。",
        },
        "status": {
            "en": [("BUILDING", "world-walker · harbor"), ("PUBLISHING", "4 channels"), ("OPEN TO", "Upstream / tooling"), ("TIMEZONE", "UTC+8")],
            "zh-CN": [("在做", "world-walker · harbor"), ("在写", "四通道"), ("在看", "上游 / 工具链"), ("时区", "UTC+8")],
            "ja": [("製作中", "world-walker · harbor"), ("執筆", "4チャネル"), ("募集中", "上流 / ツール"), ("タイムゾーン", "UTC+8")],
        },
    },
    "gitcode_badhope": {
        "platform": "gitcode",
        "handle": "badhope",
        "home_display": "gitcode.com/badhope",
        "role": {"zh-CN": "移动端开发 · 离线工具"},
        "tagline": {"zh-CN": "移动端与离线工具；同一套生成器的 GitCode 镜像。"},
        "status": {"zh-CN": [("在做", "mashang · pocketmind"), ("在写", "四通道"), ("镜像", "GitHub → GitCode"), ("时区", "UTC+8")]},
    },
    "gitee_badhope": {
        "platform": "gitee",
        "handle": "badhope",
        "home_display": "gitee.com/badhope",
        "role": {"zh-CN": "主页镜像 · 小程序"},
        "tagline": {"zh-CN": "主页镜像；项目与小型实验共用同一套生成器。"},
        "status": {"zh-CN": [("在做", "CodePocket · quiz-chest"), ("在写", "四通道"), ("镜像", "GitHub → Gitee"), ("时区", "UTC+8")]},
    },
}

WRITING = [
    ("2026-11-04", "把 AI Agent 接进业务系统，我踩了 3 个挺蠢的坑", "https://blog.csdn.net/weixin_56622231/article/details/170051167"),
    ("2026-10-18", "Gemini 4 Argon 全面开放：谷歌憋了半年的旗舰大招，到底行不行？", "https://blog.csdn.net/weixin_56622231/article/details/168251657"),
]

CHANNELS = [
    {
        "key": "csdn",
        "name": {"en": "CSDN", "zh-CN": "CSDN", "ja": "CSDN"},
        "initial": "C",
        "accent_key": "accent",
        "url": "https://blog.csdn.net/weixin_56622231",
        "display": "badhope.blog.csdn.net",
        "tag": {"en": "MANUAL", "zh-CN": "手动归档", "ja": "手動"},
        "note": {
            "en": "Engineering notes and post-mortems, archived and published by hand.",
            "zh-CN": "工程手记与踩坑复盘，整理后归档发布。",
            "ja": "工程メモと失敗談を整理して公開。",
        },
    },
    {
        "key": "juejin",
        "name": {"en": "Juejin", "zh-CN": "稀土掘金", "ja": "Juejin"},
        "initial": "J",
        "accent_key": "accent2",
        "url": "https://juejin.cn/user/2350111542479753",
        "display": "juejin.cn/user/2350111542479753",
        "tag": {"en": "AUTO · DAILY", "zh-CN": "自动运营 · 日更", "ja": "自動運用 · 毎日"},
        "note": {
            "en": "Short daily notes and boiling points, run by the automation line.",
            "zh-CN": "短平快的日常与沸点，由自动化管线运营。",
            "ja": "短い日常メモ、自動化ラインで運用。",
        },
    },
    {
        "key": "zhihu",
        "name": {"en": "Zhihu", "zh-CN": "知乎", "ja": "知乎"},
        "initial": "Z",
        "accent_key": "accent4",
        "url": "https://www.zhihu.com/people/e7c851hd",
        "display": "zhihu.com/people/e7c851hd",
        "tag": {"en": "AUTO · DAILY", "zh-CN": "自动运营 · 日更", "ja": "自動運用 · 毎日"},
        "note": {
            "en": "Long-form answers and daily notes, run by the automation line.",
            "zh-CN": "长文回答与日常，由自动化管线运营。",
            "ja": "長文回答と日常メモ、自動化ラインで運用。",
        },
    },
    {
        "key": "cnblogs",
        "name": {"en": "Cnblogs", "zh-CN": "博客园", "ja": "博客园"},
        "initial": "B",
        "accent_key": "accent3",
        "url": "https://www.cnblogs.com/badhope",
        "display": "cnblogs.com/badhope",
        "tag": {"en": "AUTO · DAILY", "zh-CN": "自动 · 巡场", "ja": "自動 · 巡回"},
        "note": {
            "en": "Engineering notes and a daily field check, run by the automation line.",
            "zh-CN": "工程手记与每日巡场，由自动化管线运营。",
            "ja": "工程メモと毎日の巡回、自動化ラインで運用。",
        },
    },
]

PIPELINE_NOTE = {
    "en": "Four publishing accounts: CSDN is archived by hand; Juejin, Zhihu and Cnblogs run on the automation line.",
    "zh-CN": "四个发布账号：CSDN 手动归档；掘金、知乎、博客园由自动化管线运营。",
    "ja": "四つの配信アカウント。CSDN は手動アーカイブ、Juejin・知乎・博客园 は自動化ラインで運用。",
}

LATEST_LABEL = {"en": "Latest on CSDN", "zh-CN": "CSDN 最近", "ja": "CSDN 最新"}

TOOLBOX = {
    "en": ["Python", "TypeScript", "Kotlin", "Tauri", "MCP"],
    "zh-CN": ["Python", "TypeScript", "Kotlin", "Tauri", "MCP"],
    "ja": ["Python", "TypeScript", "Kotlin", "Tauri", "MCP"],
}

HEADINGS = {
    "en": {"now": "Now", "contrib": "Upstream pull requests", "projects": "Other projects", "numbers": "Numbers", "publish": "Publishing line"},
    "zh-CN": {"now": "现在", "contrib": "外部 PR", "projects": "参与项目", "numbers": "数据", "publish": "发布管线"},
    "ja": {"now": "いま", "contrib": "外部 PR", "projects": "参加プロジェクト", "numbers": "数字", "publish": "配信ライン"},
}

PR_STATUS = {
    "merged": {"en": "merged", "zh-CN": "已合并", "ja": "マージ済み"},
    "open": {"en": "open", "zh-CN": "开放中", "ja": "オープン"},
    "closed": {"en": "closed", "zh-CN": "已关闭", "ja": "クローズ"},
}

PROJECT_TABLE = {
    "en": ("Project", "Stack", "Scope"),
    "zh-CN": ("项目", "技术栈", "方向"),
    "ja": ("プロジェクト", "スタック", "方向"),
}

PR_SUMMARY = {
    "en": "{n} selected · {merged} merged · {open} open · {closed} closed · +{adds}/−{dels} · {files} files · {comments} comments",
    "zh-CN": "{n} 条 · 已合并 {merged} · 开放中 {open} · 已关闭 {closed} · +{adds}/−{dels} · {files} 个文件 · {comments} 条评论",
    "ja": "{n} 件 · マージ済み {merged} · オープン {open} · クローズ {closed} · +{adds}/−{dels} · {files} ファイル · {comments} コメント",
}

PR_WHEN = {
    "merged": {"en": "merged", "zh-CN": "合并于", "ja": "マージ"},
    "open": {"en": "opened", "zh-CN": "开启于", "ja": "提出"},
    "closed": {"en": "opened", "zh-CN": "开启于", "ja": "提出"},
}

PR_META = {
    "en": {"file": "file", "files": "files", "comment": "comment", "comments": "comments", "snapshot": "PR snapshot"},
    "zh-CN": {"file": "个文件", "files": "个文件", "comment": "条评论", "comments": "条评论", "snapshot": "PR 快照"},
    "ja": {"file": "ファイル", "files": "ファイル", "comment": "コメント", "comments": "コメント", "snapshot": "PR スナップショット"},
}

NOW_COPY = {
    "en": {
        "repos": "Personal repositories",
        "repo_note": "{n} · personal namespace, forks excluded",
        "prs": "Upstream pull requests",
        "pr_note": "{n} selected: {merged} merged, {open} open, {closed} closed",
        "publish": "Publishing",
        "publish_note": "CSDN archive; Juejin, Zhihu and Cnblogs automation",
    },
    "zh-CN": {
        "repos": "个人仓库",
        "repo_note": "{n} 个 · 个人命名空间，不含 fork",
        "prs": "外部 PR",
        "pr_note": "{n} 条：已合并 {merged}，开放中 {open}，已关闭 {closed}",
        "publish": "发布",
        "publish_note": "CSDN 长文归档；掘金、知乎、博客园自动运营",
    },
    "ja": {
        "repos": "個人リポジトリ",
        "repo_note": "{n} 件 · 個人名前空間、fork を除く",
        "prs": "外部 PR",
        "pr_note": "{n} 件：マージ {merged}、オープン {open}、クローズ {closed}",
        "publish": "配信",
        "publish_note": "CSDN 長文アーカイブ、Juejin・知乎・博客园 は自動運用",
    },
}

METRIC_LABELS = {
    "commits": {"en": "COMMITS", "zh-CN": "提交", "ja": "コミット"},
    "prs": {"en": "PULL REQUESTS", "zh-CN": "PR", "ja": "PR"},
    "merged": {"en": "MERGED", "zh-CN": "已合并", "ja": "マージ済み"},
    "followers": {"en": "FOLLOWERS", "zh-CN": "关注者", "ja": "フォロワー"},
    "repos": {"en": "REPOSITORIES", "zh-CN": "仓库", "ja": "リポジトリ"},
    "stars": {"en": "STARS", "zh-CN": "星标", "ja": "スター"},
    "projects": {"en": "PROJECTS", "zh-CN": "项目", "ja": "プロジェクト"},
}

SIGNAL_TITLE = {
    "en": "Signal · current snapshot",
    "zh-CN": "信号 · 当前快照",
    "ja": "シグナル · 現在のスナップショット",
}

STARCHART_NOTE = {
    "en": "A slow sky · one turn every three minutes",
    "zh-CN": "缓慢旋转的星图 · 一圈三分钟",
    "ja": "ゆっくり回る星図 · 一周三分",
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


CONTRIB_PATH = ROOT / "data" / "contributions.json"


def load_contributions():
    try:
        return json.loads(CONTRIB_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"as_of": "", "projects": {}, "accounts": {}}


def contribution_account(account):
    return load_contributions().get("accounts", {}).get(account, {})


def project_url(account, slug):
    catalog = load_contributions().get("projects", {}).get(slug, {})
    platform = COPY[account]["platform"]
    base = {"github": "https://github.com", "gitcode": "https://gitcode.com", "gitee": "https://gitee.com"}[platform]
    repo = catalog.get("repo") or catalog.get("name") or slug
    return f"{base}/{COPY[account]['handle']}/{repo}"


def stat_metrics(account):
    stats = load_stats()
    acc = stats.get("accounts", {}).get(account, {})
    platform = COPY[account]["platform"]
    if platform == "github":
        keys = ["repos", "prs", "merged", "followers"]
    else:
        keys = ["repos", "stars", "followers", "projects"]
    values = []
    for key in keys:
        if key == "projects":
            values.append(len(contribution_account(account).get("projects", [])))
        else:
            values.append(acc.get(key))
    return keys, values, stats.get("as_of", "")


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


def sparkle(cx, cy, r, color, opacity=0.7):
    """A four-point star drawn as two hairlines plus a small core."""
    return (
        f'<g opacity="{opacity}">'
        f'<line x1="{cx - r}" y1="{cy}" x2="{cx + r}" y2="{cy}" stroke="{color}" stroke-width="1"/>'
        f'<line x1="{cx}" y1="{cy - r}" x2="{cx}" y2="{cy + r}" stroke="{color}" stroke-width="1"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{max(0.6, r / 3)}" fill="{color}"/>'
        f'</g>'
    )


def star_field(width, height, theme, count=40, seed=7, opacity=0.4):
    """Deterministic star field. Ratio and seed keep every build byte-identical."""
    t = THEMES[theme]
    rng = random.Random(seed)
    out = []
    for i in range(count):
        x = round(rng.uniform(4, width - 4), 1)
        y = round(rng.uniform(4, height - 4), 1)
        r = rng.choice((0.6, 0.9, 1.2, 1.7, 2.2))
        alpha = round(rng.uniform(0.18, opacity), 2)
        color = t["star"] if i % 6 else t["constellation"]
        out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="{alpha}"/>')
        if i % 23 == 0:
            out.append(sparkle(x, y, 4.5, color, min(0.8, alpha + 0.15)))
    return out


def star_field_radius(cx, cy, radius, theme, count=40, seed=11, opacity=0.5):
    t = THEMES[theme]
    rng = random.Random(seed)
    out = []
    made = 0
    while made < count:
        x = rng.uniform(-radius, radius)
        y = rng.uniform(-radius, radius)
        if x * x + y * y > radius * radius:
            continue
        r = rng.choice((0.6, 0.9, 1.2, 1.7, 2.3))
        alpha = round(rng.uniform(0.2, opacity), 2)
        color = t["star"] if made % 5 else t["constellation"]
        out.append(f'<circle cx="{round(cx + x, 1)}" cy="{round(cy + y, 1)}" r="{r}" fill="{color}" opacity="{alpha}"/>')
        if made % 19 == 0:
            out.append(sparkle(round(cx + x, 1), round(cy + y, 1), 5, color, min(0.85, alpha + 0.2)))
        made += 1
    return out


def constellation(points, theme, opacity=0.18, stroke_width=1):
    """Connect a small set of stars, like a hand-drawn constellation."""
    t = THEMES[theme]
    color = t["constellation"]
    out = [f'<g opacity="{opacity}">']
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{stroke_width}"/>')
    for x, y in points:
        out.append(f'<circle cx="{x}" cy="{y}" r="2.2" fill="{t["star"]}"/>')
        out.append(f'<circle cx="{x}" cy="{y}" r="5.5" fill="none" stroke="{color}" stroke-width="1" opacity="0.45"/>')
    out.append('</g>')
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
    out.append('<filter id="blur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="34"/></filter>')
    out.append(
        f'<filter id="soft" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{t["shadow"]}" flood-opacity="0.16"/>'
        f'</filter>'
    )
    out.append("</defs>")
    out.append(f'<rect width="{w}" height="{h}" rx="26" fill="url(#bg)"/>')
    out.append(f'<rect width="{w}" height="{h}" rx="26" fill="url(#grid)"/>')
    out.extend(star_field(w, h, theme, count=54, seed=5, opacity=0.38))
    out.extend(constellation([(212, 22), (256, 52), (318, 30), (366, 66), (414, 40)], theme, opacity=0.13))
    out.extend(constellation([(780, 24), (812, 58), (862, 44), (902, 78)], theme, opacity=0.12))
    out.append(f'<circle cx="1090" cy="10" r="210" fill="url(#orbA)" filter="url(#blur)" opacity="0.75"/>')
    out.append(f'<circle cx="880" cy="330" r="220" fill="url(#orbB)" filter="url(#blur)" opacity="0.65"/>')
    out.append(f'<ellipse cx="1164" cy="268" rx="72" ry="17" fill="none" stroke="{t["gold"]}" stroke-width="1.2" opacity="0.38" transform="rotate(-18 1164 268)"/>')
    out.append(f'<circle cx="1164" cy="268" r="40" fill="url(#sphere)" filter="url(#soft)"/>')
    out.append(f'<ellipse cx="1152" cy="252" rx="12" ry="7" fill="#FFFFFF" opacity="0.55"/>')
    out.append(sparkle(1072, 196, 9, t["star"], 0.55))
    out.append(sparkle(1188, 338, 7, t["star"], 0.45))

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
    out.extend(star_field(w, h, theme, count=26, seed=23, opacity=0.17))
    out.append(f'<circle cx="1138" cy="76" r="62" fill="none" stroke="{t["constellation"]}" stroke-width="1" opacity="0.12"/>')
    out.append(f'<circle cx="1138" cy="76" r="47" fill="none" stroke="{t["constellation"]}" stroke-width="1" opacity="0.10"/>')
    out.append(f'<circle cx="1138" cy="76" r="3.2" fill="{t["gold"]}" opacity="0.85"/>')
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
    accent = t[channel.get("accent_key", "accent2")]
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
    out.extend(star_field(w, h, theme, count=10, seed=31, opacity=0.13))
    out.append(f'<ellipse cx="54" cy="54" rx="40" ry="14" fill="none" stroke="{accent}" stroke-width="1" opacity="0.30" transform="rotate(-18 54 54)"/>')
    out.append(f'<text x="54" y="64" text-anchor="middle" font-size="24" font-weight="750" fill="{accent}">{esc(channel["initial"])}</text>')
    out.append(f'<text x="98" y="50" class="ink" font-size="23" font-weight="700">{esc(channel["name"][lang])}</text>')
    out.append(f'<rect x="404" y="24" width="156" height="22" rx="11" fill="{accent}" opacity="0.12"/>')
    out.append(f'<text x="482" y="39" text-anchor="middle" class="mono" font-size="10.4" letter-spacing="0.3" fill="{accent}">{esc(channel["tag"][lang])}</text>')
    out.append(f'<text x="98" y="78" class="muted" font-size="13.5" opacity="0.92">{esc(channel["note"][lang])}</text>')
    out.append(f'<text x="98" y="110" class="mono faint" font-size="10.5">{esc(channel["display"])}</text>')
    out.append(f'<text x="556" y="110" text-anchor="end" class="mono" font-size="12" fill="{accent}">↗</text>')
    out.append("</svg>")
    return "\n".join(out)

def svg_starchart(lang, theme):
    """A slowly turning celestial plate. SMIL keeps it alive even as a plain <img>."""
    t = THEMES[theme]
    w, h = 640, 640
    c = 320
    outer = 252
    disc = 226
    title = {"zh-CN": "星辰图谱", "en": "CELESTIAL CHART", "ja": "星図"}[lang]
    out = [svg_head(w, h, f"{title} — slow rotation", theme)]
    out.append("<defs>")
    out.append(
        f'<radialGradient id="halo"><stop stop-color="{t["star"]}" stop-opacity="0.18"/>'
        f'<stop offset="0.55" stop-color="{t["constellation"]}" stop-opacity="0.10"/>'
        f'<stop offset="1" stop-color="{t["constellation"]}" stop-opacity="0"/></radialGradient>'
    )
    out.append(
        f'<radialGradient id="disc" cx="42%" cy="36%" r="72%">'
        f'<stop offset="0" stop-color="{t["panel"]}" stop-opacity="0.92"/>'
        f'<stop offset="0.72" stop-color="{t["panel2"]}" stop-opacity="0.82"/>'
        f'<stop offset="1" stop-color="{t["panel"]}" stop-opacity="0.64"/></radialGradient>'
    )
    out.append("</defs>")
    out.append(f'<circle cx="{c}" cy="{c}" r="310" fill="url(#halo)"/>')
    out.extend(star_field(w, h, theme, count=72, seed=43, opacity=0.72))

    # outer rim and 72 ticks; every sixth tick is longer
    out.append(f'<circle cx="{c}" cy="{c}" r="{outer}" fill="none" stroke="{t["gold"]}" stroke-width="2.3" opacity="0.95"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{outer - 6}" fill="none" stroke="{t["gold"]}" stroke-width="1.4" opacity="0.68"/>')
    for i in range(72):
        a = 2 * math.pi * i / 72
        major = i % 6 == 0
        r1 = outer - 10 if major else outer - 4
        r2 = outer + 7
        x1 = round(c + r1 * math.sin(a), 2)
        y1 = round(c - r1 * math.cos(a), 2)
        x2 = round(c + r2 * math.sin(a), 2)
        y2 = round(c - r2 * math.cos(a), 2)
        out.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["gold"]}" '
            f'stroke-width="{2.0 if major else 1.15}" opacity="{0.92 if major else 0.55}"/>'
        )

    # cardinal letters, kept just outside the rim
    out.append(f'<text x="{c}" y="54" text-anchor="middle" class="mono muted" font-size="10" letter-spacing="2">N</text>')
    out.append(f'<text x="{c}" y="602" text-anchor="middle" class="mono muted" font-size="10" letter-spacing="2">S</text>')
    out.append(f'<text x="598" y="324" text-anchor="middle" class="mono muted" font-size="10" letter-spacing="2">E</text>')
    out.append(f'<text x="42" y="324" text-anchor="middle" class="mono muted" font-size="10" letter-spacing="2">W</text>')
    out.append(f'<text x="24" y="28" class="mono faint" font-size="8.5" letter-spacing="1.8">CELESTIAL ATLAS</text>')
    out.append(f'<text x="616" y="28" text-anchor="end" class="mono faint" font-size="8.5" letter-spacing="1.8">EPOCH / 2026</text>')

    out.append("<g>")
    out.append('<animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 320 320" to="360 320 320" dur="180s" repeatCount="indefinite"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{disc}" fill="{t["bg2"]}" opacity="0.62"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{disc}" fill="url(#disc)" stroke="{t["gold"]}" stroke-width="1.8" opacity="0.96"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{disc - 14}" fill="none" stroke="{t["constellation"]}" stroke-width="1.6" opacity="0.66"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="150" fill="none" stroke="{t["constellation"]}" stroke-width="1.6" opacity="0.56"/>')
    out.append(f'<ellipse cx="{c}" cy="{c}" rx="214" ry="118" fill="none" stroke="{t["constellation"]}" stroke-width="1.8" opacity="0.50" transform="rotate(-18 320 320)"/>')

    # twelve faint spokes, as on an armillary plate
    for i in range(12):
        a = 2 * math.pi * i / 12
        x1 = round(c + 64 * math.sin(a), 1)
        y1 = round(c - 64 * math.cos(a), 1)
        x2 = round(c + (disc - 4) * math.sin(a), 1)
        y2 = round(c - (disc - 4) * math.cos(a), 1)
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["constellation"]}" stroke-width="1.25" opacity="0.36"/>')

    out.extend(star_field_radius(c, c, 210, theme, count=56, seed=17, opacity=0.80))
    out.extend(constellation([(416, 248), (452, 302), (432, 368), (368, 412), (298, 398)], theme, opacity=0.80, stroke_width=1.5))
    out.extend(constellation([(222, 252), (196, 286), (214, 328), (250, 348)], theme, opacity=0.64, stroke_width=1.4))
    out.append(f'<circle cx="412" cy="354" r="4" fill="{t["star"]}" opacity="1"/>')
    out.append(f'<circle cx="412" cy="354" r="10" fill="none" stroke="{t["gold"]}" stroke-width="1.4" opacity="0.50"/>')
    out.append(f'<circle cx="228" cy="290" r="3.2" fill="{t["constellation"]}" opacity="1"/>')

    # A bright comet sweeps faster than the plate; its asymmetry makes the
    # rotation obvious even at a glance. The plate itself remains slow.
    out.append('<g>')
    out.append('<animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 320 320" to="360 320 320" dur="45s" repeatCount="indefinite"/>')
    out.append(f'<line x1="320" y1="96" x2="320" y2="132" stroke="{t["gold"]}" stroke-width="3.0" opacity="0.92"/>')
    out.append(f'<line x1="320" y1="112" x2="320" y2="150" stroke="{t["constellation"]}" stroke-width="1.7" opacity="0.48"/>')
    out.append(f'<circle cx="320" cy="94" r="15" fill="{t["star"]}" opacity="0.18"/>')
    out.append(f'<circle cx="320" cy="94" r="6.2" fill="{t["star"]}" opacity="0.99"/>')
    out.append('</g>')

    # A smaller blue moon counter-rotates at a different speed, so the chart
    # never looks like one static dial with a single moving hand.
    out.append('<g>')
    out.append('<animateTransform attributeName="transform" attributeType="XML" type="rotate" from="360 320 320" to="0 320 320" dur="90s" repeatCount="indefinite"/>')
    out.append(f'<circle cx="320" cy="144" r="5.5" fill="{t["constellation"]}" opacity="0.99"/>')
    out.append(f'<circle cx="320" cy="144" r="13" fill="none" stroke="{t["constellation"]}" stroke-width="1.4" opacity="0.42"/>')
    out.append('</g>')

    # a long hour hand so the rotation is legible at a glance
    out.append(f'<line x1="{c}" y1="{c}" x2="{c}" y2="96" stroke="{t["star"]}" stroke-width="2.4" opacity="0.86"/>')
    out.append(f'<line x1="{c}" y1="{c}" x2="{c}" y2="376" stroke="{t["gold"]}" stroke-width="1.8" opacity="0.62"/>')
    out.append(f'<circle cx="{c}" cy="96" r="5.5" fill="{t["star"]}" opacity="0.96"/>')

    # centre: a quiet gold star on a dark coin
    out.append(f'<circle cx="{c}" cy="{c}" r="64" fill="{t["panel"]}" stroke="{t["gold"]}" stroke-width="1.7" opacity="0.96"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="54" fill="none" stroke="{t["line"]}" stroke-width="1.1" opacity="0.55"/>')
    out.append(sparkle(c, c, 31, t["star"], 0.92))
    out.append(f'<circle cx="{c}" cy="{c}" r="7" fill="{t["panel"]}" stroke="{t["gold"]}" stroke-width="1.2"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="3" fill="{t["star"]}"/>')
    out.append("</g>")

    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# README rendering
# ---------------------------------------------------------------------------


def picture(light, dark, alt, width="100%"):
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="{dark}" />'
        f'<img src="{light}" alt="{esc(alt)}" width="{width}" /></picture>'
    )


REMOTE_ASSET_BASE = {
    # GitCode rewrites relative README images to raw.gitcode.com, whose WAF
    # returns 418 to anonymous readers. Serve the same committed SVG files
    # through jsDelivr so the public GitCode page can actually render them.
    "gitcode": "https://cdn.jsdelivr.net/gh/badhope/badhope@main/assets",
}


def asset(account, name, lang, theme):
    filename = f"{name}-{lang}-{theme}.svg"
    base = REMOTE_ASSET_BASE.get(COPY[account]["platform"])
    return f"{base}/{filename}" if base else f"assets/{filename}"


def image_tag(account, name, lang, alt, width="100%"):
    """GitHub gets theme-aware <picture>; mirrors get a plain <img>.

    Gitee / GitCode README renderers do not reliably keep <picture>/<source>,
    so the domestic mirrors use the light SVG directly. The layout is identical.
    GitCode additionally needs an absolute CDN URL because its raw file host
    rejects anonymous image requests.
    """
    light = asset(account, name, lang, "light")
    if COPY[account]["platform"] == "github":
        return picture(light, asset(account, name, lang, "dark"), alt, width)
    return f'<img src="{light}" alt="{esc(alt)}" width="{width}" />'


def render_readme(account, lang):
    copy = COPY[account]
    stats = load_stats()
    platform = copy["platform"]
    head = HEADINGS[lang]
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
    out.append(image_tag(account, "hero", lang, f"{copy['handle']} · {copy['home_display']}"))
    out.append("</p>")
    out.append("")
    out.append('<p align="center">')
    out.append(image_tag(account, "starchart", lang, "slow celestial chart", "58%"))
    out.append("</p>")
    out.append(f'<p align="center"><sub>{STARCHART_NOTE[lang]}</sub></p>')
    out.append("")

    contrib = load_contributions()
    cacc = contribution_account(account)
    prs = cacc.get("pull_requests", [])
    merged = sum(1 for pr in prs if pr.get("status") == "merged")
    opened = sum(1 for pr in prs if pr.get("status") == "open")
    closed = sum(1 for pr in prs if pr.get("status") == "closed")
    adds = sum(pr.get("additions", 0) for pr in prs)
    dels = sum(pr.get("deletions", 0) for pr in prs)
    files = sum(pr.get("files", 0) for pr in prs)
    comments = sum(pr.get("comments", 0) for pr in prs)
    repo_count = stats.get("accounts", {}).get(account, {}).get("repos", 0)
    now = NOW_COPY[lang]

    out.append(f"## 01 · {head['now']}")
    out.append("")
    out.append(f"- **{now['repos']}** — {now['repo_note'].format(n=repo_count)}")
    out.append(
        f"- **{now['prs']}** — "
        + now["pr_note"].format(n=len(prs), merged=merged, open=opened, closed=closed)
    )
    out.append(f"- **{now['publish']}** — {now['publish_note']}")
    out.append("")

    out.append(f"## 02 · {head['contrib']}")
    out.append("")
    out.append(
        "<sub>"
        + PR_SUMMARY[lang].format(
            n=len(prs), merged=merged, open=opened, closed=closed,
            adds=adds, dels=dels, files=files, comments=comments,
        )
        + "</sub>"
    )
    out.append("")
    for pr in prs:
        status = pr.get("status", "closed")
        when_label = PR_WHEN.get(status, PR_WHEN["closed"])[lang]
        when = f"{when_label} {pr['merged_at']}" if status == "merged" and pr.get("merged_at") else f"{when_label} {pr.get('opened', '')}"
        files = pr.get("files", 0)
        comments = pr.get("comments", 0)
        meta = PR_META[lang]
        file_unit = meta["file"] if files == 1 else meta["files"]
        comment_unit = meta["comment"] if comments == 1 else meta["comments"]
        line = (
            f"- [{pr['repo']}#{pr['number']}](https://github.com/{pr['repo']}/pull/{pr['number']})"
            f" — {pr['title']} · **{PR_STATUS.get(status, PR_STATUS['closed'])[lang]}**"
            f" · {when} · +{pr.get('additions', 0)}/−{pr.get('deletions', 0)}"
            f" · {files} {file_unit} · {comments} {comment_unit}"
        )
        out.append(line)
    out.append("")
    out.append(f"<sub>{PR_META[lang]['snapshot']} {contrib.get('as_of', '')} · GitHub Search / pulls API</sub>")
    out.append("")

    out.append(f"## 03 · {head['projects']}")
    out.append("")
    heads = PROJECT_TABLE[lang]
    out.append(f"| {heads[0]} | {heads[1]} | {heads[2]} |")
    out.append("|---|---|---|")
    for slug in cacc.get("projects", []):
        entry = contrib.get("projects", {}).get(slug, {})
        name = entry.get("name", slug)
        if lang == "zh-CN":
            note = entry.get("note_zh", entry.get("note", ""))
        elif lang == "ja":
            note = entry.get("note_ja", entry.get("note", ""))
        else:
            note = entry.get("note", "")
        out.append(f"| [{name}]({project_url(account, slug)}) | {entry.get('stack', '')} | {note} |")
    out.append("")

    out.append(f"## 04 · {head['numbers']}")
    out.append("")
    out.append('<p align="center">')
    out.append(image_tag(account, "numbers", lang, "numbers"))
    out.append("</p>")
    out.append("")

    out.append(f"## 05 · {head['publish']}")
    out.append("")
    cards = []
    for channel in CHANNELS:
        cards.append(
            f'<a href="{channel["url"]}">'
            + image_tag(account, f"channel-{channel['key']}", lang, channel["name"][lang], "49.2%")
            + "</a>"
        )
    for i in range(0, len(cards), 2):
        out.append(f'<p align="center">{" ".join(cards[i:i + 2])}</p>')
        out.append("")
    out.append(f"<sub>{PIPELINE_NOTE[lang]}</sub>")
    out.append("")
    out.append(f"<sub>{LATEST_LABEL[lang]}</sub>")
    out.append("")
    for date, title, url in WRITING:
        out.append(f"- {date} — [{title}]({url})")
    out.append("")
    out.append(f'<sub><a href="{CHANNELS[0]["url"]}">{WRITING_MORE[lang]}</a></sub>')
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
    themes = THEME_NAMES if COPY[account]["platform"] == "github" else ("light",)
    for theme in themes:
        for lang in langs:
            hero = ASSETS / f"hero-{lang}-{theme}.svg"
            hero.write_text(svg_hero(account, lang, theme), encoding="utf-8")
            written.append(hero)
            numbers = ASSETS / f"numbers-{lang}-{theme}.svg"
            numbers.write_text(svg_numbers(account, lang, theme), encoding="utf-8")
            written.append(numbers)
            starchart = ASSETS / f"starchart-{lang}-{theme}.svg"
            starchart.write_text(svg_starchart(lang, theme), encoding="utf-8")
            written.append(starchart)
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
