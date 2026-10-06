#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于原模板(249cb56)重建四平台主页 README。

- 顶部语言切换链接（EN/中/日）保留，并加四平台镜像说明
- 统计: 聚合四平台；项目以 GitCode 现有项目为主；stars 取两个 GitHub 中较大者
- 项目区块: 以 GitCode 现有 14 个为准
- 开源贡献: 四平台全部展现（GitHub X33834 / Morningstar202604 / GitCode / Gitee）
- 其余区块(banner/关于/streak/3D/snake/技术栈/博客/雷达/在别处/footer)原样继承
"""
import os
import re
import sys

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------- 数据（2026-09-18 实测） ----------
# 项目精选：只放高含金量代表项目（GitCode 为主）
GC_PROJECTS = [
    ("bot4cj", "基于仓颉语言的硬件机器人控制框架", 6, "硬件 · 机器人"),
    ("mobilecode", "Android 端 AI 编程助手（BYOK 离线运行）", 1, "移动端 · Kotlin"),
    ("dev-terminal", "完全离线的安卓编程终端 — 手机上的现代 IDE", 0, "移动端 · 离线"),
    ("awesome-skillkit", "Agent Skills 场景包 · 27 packs / 11 分类", 3, "AI 工具链"),
    ("scholarhub", "学术期刊与预印本多租户平台", 1, "SaaS"),
    ("FinHub", "AI 投资研究 Agent 平台", 0, "量化 · 金融"),
    ("VerdictAI", "多智能体法庭辩论系统", 0, "多智能体"),
    ("mashang-python", "码上 Python · PY//NOW 赛博朋克风学习终端", 0, "教育"),
    ("KeBaiPay", "科佰支付 · 自托管开源支付中台", 0, "支付"),
]

# 开源贡献（以高 star 项目为重，卡片式高亮）
CONTRIB = {
    "zh": {
        "intro": "代码已合入多个高知名度的开源上游项目——**GitHub 两账号合计 16 个 PR 被合并**，其中不乏 **_ohmyzsh（189k★）_、_tldr-pages（64k★）_** 这样的明星项目。",
        "cards_title": "⭐ 高含金量 · 已合并",
        "review_title": "🚧 评审中",
        "cards": [
            {
                "repo": "ohmyzsh/ohmyzsh", "stars": "189k", "url": "https://github.com/ohmyzsh/ohmyzsh",
                "prs": [("14006", "fix(git): force C locale"), ("14021", "fix(pipenv): keep activation"), ("14027", "fix(aws): asr error")],
                "desc": "命令行狂魔的必修课 · 12 万+ 项目依赖",
            },
            {
                "repo": "tldr-pages/tldr", "stars": "64k", "url": "https://github.com/tldr-pages/tldr",
                "prs": [("23780", "doctl CLI 手册页")],
                "desc": "社区驱动命令手册 · 跨平台 CLI 帮助",
            },
            {
                "repo": "collective/icalendar", "stars": "1.2k", "url": "https://github.com/collective/icalendar",
                "prs": [("1731", "docs: public exports"), ("1750", "deprecate single_string_parameter"), ("1751", "TYPE_CHECKING imports")],
                "desc": "Python iCalendar 标准库生态",
            },
            {
                "repo": "nix-community/NUR", "stars": "2k", "url": "https://github.com/nix-community/NUR",
                "prs": [("1220", "treat SSL errors as transient")],
                "desc": "Nix 用户仓库 · 社区分发中枢",
            },
        ],
        "others": "此外还合入 [EnderBridge](https://github.com/Hydrooxzgen/EnderBridge)（110★）、[claude-tool-agent](https://github.com/jaychouchannel/claude-tool-agent)（Agent 编排 ×3）等项目的 PR。",
        "more": "另有 **pydantic / galaxy / LibreChat / PDFMathTranslate / getmoto / zsh-completions / LibrePhotos / freeCodeCamp / awesome-mcp-servers** 等 20+ 项目在评或已提。",
        "per_account": [
            ("GitHub · Morningstar202604", "https://github.com/Morningstar202604", "**12 PRs merged**"),
            ("GitHub · X33834", "https://github.com/X33834", "**4 PRs merged**（Nailong-Studio/website ×4）+ 评审中：airflow #73099 · MonkeyCode #1298 · simona #1–6"),
            ("GitCode · badhope", "https://gitcode.com/badhope", "16 个开源项目镜像（移动端 IDE / AI 助手 / 学习终端）"),
            ("Gitee · badhope", "https://gitee.com/badhope", "项目镜像 + 小程序作品集"),
        ],
    },
    "en": {
        "intro": "Merged into some of the most starred open source projects — **16 PRs merged across two GitHub accounts**, including **ohmyzsh (189k★)** and **tldr-pages (64k★)**.",
        "cards_title": "⭐ High-impact merges",
        "review_title": "🚧 Under review",
        "cards": [
            {
                "repo": "ohmyzsh/ohmyzsh", "stars": "189k", "url": "https://github.com/ohmyzsh/ohmyzsh",
                "prs": [("14006", "fix(git): force C locale"), ("14021", "fix(pipenv): keep activation"), ("14027", "fix(aws): asr error")],
                "desc": "The essential zsh framework · 100k+ dependent projects",
            },
            {
                "repo": "tldr-pages/tldr", "stars": "64k", "url": "https://github.com/tldr-pages/tldr",
                "prs": [("23780", "doctl CLI pages")],
                "desc": "Community-curated command cheatsheets",
            },
            {
                "repo": "collective/icalendar", "stars": "1.2k", "url": "https://github.com/collective/icalendar",
                "prs": [("1731", "docs: public exports"), ("1750", "deprecate single_string_parameter"), ("1751", "TYPE_CHECKING imports")],
                "desc": "Python iCalendar ecosystem",
            },
            {
                "repo": "nix-community/NUR", "stars": "2k", "url": "https://github.com/nix-community/NUR",
                "prs": [("1220", "treat SSL errors as transient")],
                "desc": "Nix user repository hub",
            },
        ],
        "others": "Also merged into [EnderBridge](https://github.com/Hydrooxzgen/EnderBridge) (110★) and [claude-tool-agent](https://github.com/jaychouchannel/claude-tool-agent) (agent orchestration ×3).",
        "more": "20+ more PRs open/submitted across **pydantic / galaxy / LibreChat / PDFMathTranslate / getmoto / zsh-completions / LibrePhotos / freeCodeCamp / awesome-mcp-servers**.",
        "per_account": [
            ("GitHub · Morningstar202604", "https://github.com/Morningstar202604", "**12 PRs merged**"),
            ("GitHub · X33834", "https://github.com/X33834", "**4 PRs merged** (Nailong-Studio/website ×4) + reviewing: airflow #73099 · MonkeyCode #1298 · simona #1–6"),
            ("GitCode · badhope", "https://gitcode.com/badhope", "16 open source projects mirrored (mobile IDE / AI assistant / learning terminal)"),
            ("Gitee · badhope", "https://gitee.com/badhope", "Project mirror + mini-program portfolio"),
        ],
    },
    "ja": {
        "intro": "スター数の多いオープンソースへのコード提供 — **2つのGitHubアカウントで合計16 PR マージ済み**、中でも **ohmyzsh（189k★）**・**tldr-pages（64k★）** は有名プロジェクトです。",
        "cards_title": "⭐ ハイインパクト・マージ済み",
        "review_title": "🚧 レビュー中",
        "cards": [
            {
                "repo": "ohmyzsh/ohmyzsh", "stars": "189k", "url": "https://github.com/ohmyzsh/ohmyzsh",
                "prs": [("14006", "fix(git): force C locale"), ("14021", "fix(pipenv): keep activation"), ("14027", "fix(aws): asr error")],
                "desc": "zsh フレームワークの定番",
            },
            {
                "repo": "tldr-pages/tldr", "stars": "64k", "url": "https://github.com/tldr-pages/tldr",
                "prs": [("23780", "doctl CLI pages")],
                "desc": "コミュニティのコマンドチートシート",
            },
            {
                "repo": "collective/icalendar", "stars": "1.2k", "url": "https://github.com/collective/icalendar",
                "prs": [("1731", "docs: public exports"), ("1750", "deprecate single_string_parameter"), ("1751", "TYPE_CHECKING imports")],
                "desc": "Python iCalendar エコシステム",
            },
            {
                "repo": "nix-community/NUR", "stars": "2k", "url": "https://github.com/nix-community/NUR",
                "prs": [("1220", "treat SSL errors as transient")],
                "desc": "Nix ユーザーリポジトリ",
            },
        ],
        "others": "ほかにも [EnderBridge](https://github.com/Hydrooxzgen/EnderBridge)（110★）や [claude-tool-agent](https://github.com/jaychouchannel/claude-tool-agent)（エージェント連携 ×3）にも合流。",
        "more": "pydantic / galaxy / LibreChat / PDFMathTranslate / getmoto / zsh-completions など 20+ プロジェクトでレビュー中・提出済み。",
        "per_account": [
            ("GitHub · Morningstar202604", "https://github.com/Morningstar202604", "**12 PR merged**"),
            ("GitHub · X33834", "https://github.com/X33834", "**4 PR merged**（Nailong-Studio/website ×4）+ レビュー中：airflow #73099 · MonkeyCode #1298 · simona #1–6"),
            ("GitCode · badhope", "https://gitcode.com/badhope", "16のオープンソースをミラー公開"),
            ("Gitee · badhope", "https://gitee.com/badhope", "プロジェクトミラー＋ミニアプリ"),
        ],
    },
}

TOTAL_REPOS = 16  # GitCode 现有 16 个
TOTAL_STARS = 12  # 四平台按项目取最大后合计（bot4cj6 + awesome-skillkit3 + mobilecode1 + scholarhub1 + 网安智能体1）
TOTAL_MERGED = 16

def build_stats(lang):
    if lang == "zh":
        return f"- ⭐ **{TOTAL_STARS}** stars（四平台取最大）&nbsp;·&nbsp; 👥 **13** followers &nbsp;·&nbsp; 📦 **{TOTAL_REPOS}+ 项目**（以 GitCode 为准）"
    if lang == "en":
        return f"- ⭐ **{TOTAL_STARS}** stars (max across 4 platforms) &nbsp;·&nbsp; 👥 **13** followers &nbsp;·&nbsp; 📦 **{TOTAL_REPOS}+ repos** (GitCode-based)"
    return f"- ⭐ **{TOTAL_STARS}** stars（4プラットフォーム最大値）&nbsp;·&nbsp; 👥 **13** followers &nbsp;·&nbsp; 📦 **{TOTAL_REPOS}+ リポジトリ**（GitCode 基準）"

def build_projects(lang):
    cat_map = {
        "zh": {"硬件 · 机器人": "硬件 · 机器人", "移动端 · Kotlin": "移动端 · Kotlin", "移动端 · 离线": "移动端 · 离线", "AI 工具链": "AI 工具链", "SaaS": "SaaS", "量化 · 金融": "量化 · 金融", "多智能体": "多智能体", "教育": "教育", "支付": "支付"},
        "en": {"硬件 · 机器人": "Hardware · Robotics", "移动端 · Kotlin": "Mobile · Kotlin", "移动端 · 离线": "Mobile · Offline", "AI 工具链": "AI toolchain", "SaaS": "SaaS", "量化 · 金融": "Quant · FinTech", "多智能体": "Multi-agent", "教育": "Education", "支付": "Payments"},
        "ja": {"硬件 · 机器人": "ハードウェア · ロボット", "移动端 · Kotlin": "モバイル · Kotlin", "移动端 · 离线": "モバイル · オフライン", "AI 工具链": "AI ツール", "SaaS": "SaaS", "量化 · 金融": "Quant · 金融", "多智能体": "マルチエージェント", "教育": "教育", "支付": "決済"},
    }
    lines = []
    for name, desc, stars, cat in GC_PROJECTS:
        url = f"https://gitcode.com/badhope/{name}"
        cat_l = cat_map.get(lang, cat_map["zh"]).get(cat, cat)
        lines.append(f"- **[{name}]({url})** · {stars}★ · {desc} · `{cat_l}`")
    return "\n".join(lines)

def build_contrib(lang):
    c = CONTRIB[lang]
    # 卡片表格（借鉴原模板风格）：每行 2 卡片
    cards = []
    for i in range(0, len(c["cards"]), 2):
        row = "  <tr>"
        for card in c["cards"][i:i+2]:
            pr_links = " · ".join(
                f'<a href="{card["url"]}/pull/{num}">#{num}</a>'
                for num, _ in card["prs"]
            )
            pr_descs = " · ".join(desc for _, desc in card["prs"])
            row += (
                f'<td align="center" width="280"><sub><b><a href="{card["url"]}">{card["repo"]}</a></b> '
                f'⭐{card["stars"]}</sub><br/>{pr_links}<br/><sub>{pr_descs}</sub><br/><sub>{card["desc"]}</sub></td>'
            )
        row += "</tr>"
        cards.append(row)
    card_rows = "\n".join(cards)
    link_word = {"zh": "链接", "en": "link", "ja": "リンク"}[lang]
    per = "\n".join(
        f"- **{name}** — [{link_word}]({url}) · {desc}"
        for name, url, desc in c["per_account"]
    )
    if lang == "zh":
        return (
            f"{c['intro']}\n\n"
            f"### {c['cards_title']}\n\n"
            f'<table align="center">\n{card_rows}\n</table>\n\n'
            f"{c['others']}\n\n"
            f"### {c['review_title']}\n\n"
            f"{c['more']}\n\n"
            f"### 📌 四平台贡献一览\n\n{per}\n"
        )
    elif lang == "en":
        return (
            f"{c['intro']}\n\n"
            f"### {c['cards_title']}\n\n"
            f'<table align="center">\n{card_rows}\n</table>\n\n'
            f"{c['others']}\n\n"
            f"### {c['review_title']}\n\n"
            f"{c['more']}\n\n"
            f"### 📌 Contributions across four platforms\n\n{per}\n"
        )
    else:
        return (
            f"{c['intro']}\n\n"
            f"### {c['cards_title']}\n\n"
            f'<table align="center">\n{card_rows}\n</table>\n\n'
            f"{c['others']}\n\n"
            f"### {c['review_title']}\n\n"
            f"{c['more']}\n\n"
            f"### 📌 4プラットフォームの貢献一覧\n\n{per}\n"
        )

def footprint(lang, active_key):
    act = {"gh_morningstar": ("GitHub", "Morningstar202604"), "gh338": ("GitHub", "X33834"),
           "gitcode": ("GitCode", "badhope"), "gitee": ("Gitee", "badhope")}[active_key]
    accounts = [
        ("GitHub", "X33834", "https://github.com/X33834",
         "开源贡献 · 上游 PR", "Upstream OSS contributions", "OSS へのコントリビューション"),
        ("GitHub", "Morningstar202604", "https://github.com/Morningstar202604",
         "作品集 · 奶龙系列 / 工具集", "Portfolio · Nailong / Tooling", "ポートフォリオ · Nailong / ツール群"),
        ("GitCode", "badhope", "https://gitcode.com/badhope",
         "移动端开发 · 离线工具", "Mobile dev · Offline tools", "モバイル開発 · オフラインツール"),
        ("Gitee", "badhope", "https://gitee.com/badhope",
         "作品镜像 · 小程序", "Mirror · Mini-programs", "ミラー · ミニアプリ"),
    ]
    rows = []
    for site, account, url, z, e, j in accounts:
        cur = " ◆" if (site, account) == act else ""
        fnote = {"zh": z, "en": e, "ja": j}[lang]
        rows.append(f"| **{site}** | [{account}]({url}) | {fnote}{cur} |")
    if lang == "zh":
        head = "### 🌐 四平台镜像 &nbsp;`一页 · 四地 · 互为镜像`\n\n> 同一份主页在四个平台互为镜像同步——GitHub 双账号 + GitCode + Gitee，贡献与作品跨平台聚合展示。\n\n| 平台 | 账号 | 定位 |\n|------|------|------|\n"
    elif lang == "en":
        head = "### 🌐 Four-Platform Mirror &nbsp;`one page · four places`\n\n> The same profile is mirrored & synced across four platforms — two GitHub accounts + GitCode + Gitee; contributions & works aggregated.\n\n| Platform | Account | Focus |\n|------|------|------|\n"
    else:
        head = "### 🌐 4プラットフォームミラー &nbsp;`1ページ·4つの場所`\n\n> 同じプロフィールを4つのプラットフォームでミラー同期 — GitHub 2アカウント + GitCode + Gitee。\n\n| プラットフォーム | アカウント | 内容 |\n|------|------|------|\n"
    return head + "\n".join(rows) + "\n"

def replace_block(text, start_marker, end_marker, new_content, keep_boundary=True):
    pat = re.compile(rf"({re.escape(start_marker)}).*?({re.escape(end_marker)})", re.S)
    if keep_boundary:
        return pat.sub(lambda m: m.group(1) + "\n" + new_content.strip() + "\n" + m.group(2), text)
    return pat.sub(new_content, text, count=1)

def build(lang, active_key, base_text):
    # 1) 四平台镜像注入到统计前
    froot = footprint(lang, active_key)
    stats_marker = {"zh": "<!-- STATS:START -->", "en": "<!-- STATS:START -->", "ja": "<!-- STATS:START -->"}[lang]
    if "四平台镜像" in base_text or "Four-Platform" in base_text or "4プラットフォーム" in base_text:
        # 已有镜像区块（从249cb56继承来的注入版？base 是249cb56 无）——本函数基于249cb56，无需处理
        pass
    # 注入到 "## 统计"/"## Stats"/"## 統計" 之前
    stats_title = {"zh": "## 统计", "en": "## Stats", "ja": "## 統計"}[lang]
    new_stats = froot + "\n" + stats_title
    text = base_text.replace(stats_title, new_stats, 1)
    # 2) 重写 STATS 内容
    text = replace_block(text, "<!-- STATS:START -->", "<!-- STATS:END -->", build_stats(lang))
    # 3) 重写 PROJECTS（以 GitCode 为主）
    proj_start = "<!-- PROJECTS:START -->"
    proj_end = "<!-- PROJECTS:END -->"
    text = replace_block(text, proj_start, proj_end, build_projects(lang))
    # 4) 重写开源贡献（四平台）
    contrib_title = {"zh": "## 开源贡献", "en": "## Open Source Contributions", "ja": "## オープンソースへの貢献"}[lang]
    blog_title = {"zh": "## 博客", "en": "## Blog", "ja": "## ブログ"}[lang]
    cpat = re.compile(rf"({re.escape(contrib_title)}).*?(?={re.escape(blog_title)})", re.S)
    text = cpat.sub(lambda m: contrib_title + "\n\n" + build_contrib(lang).strip() + "\n\n", text, count=1)
    # 5) 语言切换链接上方加镜像提示（在第一个空行后标题行前保留；head 区已有切换链接，补充一句）
    # 6) 在别处扩展为四平台链接（保留 CSDN/Juejin）
    text = extend_elsewhere(lang, text)
    return text

def extend_elsewhere(lang, text):
    marker = {"zh": "## 在别处", "en": "## Elsewhere", "ja": "## 他の場所"}[lang]
    note = {
        "zh": "> 同一身份 · 四个平台互为镜像同步",
        "en": "> One identity · mirrored across four platforms",
        "ja": "> 同一人物 · 4プラットフォームでミラー公開",
    }[lang]
    logo = {"GitHub": "github", "GitCode": "git", "Gitee": "gitee"}
    lines = text.split("\n")
    out = []
    i = 0
    replaced = False
    while i < len(lines):
        line = lines[i]
        if not replaced and line.strip() == marker:
            j = i + 1
            kept = []
            platform_urls = {url for _, _, url, *_ in [
                ("GitHub", "X33834", "https://github.com/X33834"),
                ("GitHub", "Morningstar202604", "https://github.com/Morningstar202604"),
                ("GitCode", "badhope", "https://gitcode.com/badhope"),
                ("Gitee", "badhope", "https://gitee.com/badhope"),
            ]}
            while j < len(lines) and "</p>" not in lines[j]:
                if "<a href=" in lines[j] and "img.shields.io" in lines[j]:
                    if not any(purl in lines[j] for purl in platform_urls):
                        kept.append(lines[j].strip())
                j += 1
            if j < len(lines):
                j += 1
            accounts = [
                ("GitHub", "X33834", "https://github.com/X33834"),
                ("GitHub", "Morningstar202604", "https://github.com/Morningstar202604"),
                ("GitCode", "badhope", "https://gitcode.com/badhope"),
                ("Gitee", "badhope", "https://gitee.com/badhope"),
            ]
            badge_lines = "\n".join(
                f'  <a href="{url}"><img src="https://img.shields.io/badge/{site}-{account}-C9A86A?style=flat&logo={logo.get(site, "github")}&logoColor=white&labelColor=0B1026" alt="{site}" /></a>'
                for site, account, url in accounts
            )
            all_badges = [badge_lines]
            if kept:
                all_badges.append("<br/>")
                all_badges.extend(kept)
            out.append(marker)
            out.append("")
            out.append(note)
            out.append("")
            out.append('<p align="center">')
            out.extend(all_badges)
            out.append("</p>")
            out.append("")
            replaced = True
            i = j
            continue
        out.append(line)
        i += 1
    if not replaced:
        print("!! else marker not found:", marker)
    return "\n".join(out)

def main():
    mapping = {
        "README.zh.md": ("zh", "templates/README.zh.md"),
        "README.md": ("en", "templates/README.en.md"),
        "README.ja.md": ("ja", "templates/README.ja.md"),
    }
    active_key = sys.argv[1] if len(sys.argv) > 1 else "gitcode"
    if active_key not in ("gh_morningstar", "gh338", "gitcode", "gitee"):
        print("usage: build.py <gh_morningstar|gh338|gitcode|gitee>")
        sys.exit(1)
    for fname, (lang, tpl) in mapping.items():
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), tpl)
        with open(base_path, encoding="utf-8") as f:
            base = f.read()
        text = build(lang, active_key, base)
        with open(f"{OUT}/{fname}", "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("built", fname, "for", active_key)

if __name__ == "__main__":
    main()