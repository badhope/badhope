#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为原模板注入「四平台镜像」区块 + 扩展「在别处」为四平台链接。

用法: python3 inject_footprint.py <gh_x33834|gh_morningstar|gitcode|gitee>
"""
import re
import sys

PLATFORM = {
    "gh_x33834": {
        "name": "GitHub", "account": "X33834", "url": "https://github.com/X33834",
        "focus_zh": "开源贡献 · 上游 PR", "focus_en": "Upstream OSS contributions", "focus_ja": "OSS へのコントリビューション",
    },
    "gh_morningstar": {
        "name": "GitHub", "account": "Morningstar202604", "url": "https://github.com/Morningstar202604",
        "focus_zh": "作品集 · 奶龙系列 / 工具集", "focus_en": "Portfolio · Nailong / Tooling", "focus_ja": "ポートフォリオ · Nailong / ツール群",
    },
    "gitcode": {
        "name": "GitCode", "account": "badhope", "url": "https://gitcode.com/badhope",
        "focus_zh": "移动端开发 · 离线工具", "focus_en": "Mobile dev · Offline tools", "focus_ja": "モバイル開発 · オフラインツール",
    },
    "gitee": {
        "name": "Gitee", "account": "badhope", "url": "https://gitee.com/badhope",
        "focus_zh": "作品镜像 · 小程序", "focus_en": "Mirror · Mini-programs", "focus_ja": "ミラー · ミニアプリ",
    },
}

ALL_ACCOUNTS = [
    ("GitHub", "X33834", "https://github.com/X33834", "开源贡献 · 上游 PR", "Upstream OSS contributions", "OSS へのコントリビューション"),
    ("GitHub", "Morningstar202604", "https://github.com/Morningstar202604", "作品集 · 奶龙系列 / 工具集", "Portfolio · Nailong / Tooling", "ポートフォリオ · Nailong / ツール群"),
    ("GitCode", "badhope", "https://gitcode.com/badhope", "移动端开发 · 离线工具", "Mobile dev · Offline tools", "モバイル開発 · オフラインツール"),
    ("Gitee", "badhope", "https://gitee.com/badhope", "作品镜像 · 小程序", "Mirror · Mini-programs", "ミラー · ミニアプリ"),
]

def footprint(lang, active_key):
    p = PLATFORM[active_key]
    rows = []
    for site, account, url, z, e, j in ALL_ACCOUNTS:
        cur = " ◆" if site == p["name"] and account == p["account"] else ""
        focus = {"zh": z, "en": e, "ja": j}[lang]
        rows.append(f"| **{site}** | [{account}]({url}) | {focus}{cur} |")
    if lang == "zh":
        head = "### 🌐 四平台镜像 &nbsp;`一页 · 四地 · 互为镜像`\n\n> 同一份主页在四个平台互为镜像同步，贡献与作品跨平台聚合展示。\n\n| 平台 | 账号 | 定位 |\n|------|------|------|\n"
    elif lang == "en":
        head = "### 🌐 Four-Platform Mirror &nbsp;`one page · four places`\n\n> The same profile is mirrored & synced across four platforms; contributions and works are aggregated here.\n\n| Platform | Account | Focus |\n|------|------|------|\n"
    else:
        head = "### 🌐 4プラットフォームミラー &nbsp;`1ページ·4つの場所`\n\n> 同じプロフィールを4つのプラットフォームでミラー同期。貢献と作品を集約表示します。\n\n| プラットフォーム | アカウント | 内容 |\n|------|------|------|\n"
    return head + "\n".join(rows) + "\n"

# 在别处 区块整体替换（原 GitHub/CSDN/Juejin 徽章 + 四平台及其他链接）
def extend_elsewhere(lang, text):
    if lang == "zh":
        marker = "## 在别处"
        note = "> 同一身份 · 四个平台互为镜像同步"
        logo = {"GitHub": "github", "GitCode": "git", "Gitee": "gitee"}
    elif lang == "en":
        marker = "## Elsewhere"
        note = "> One identity · mirrored across four platforms"
        logo = {"GitHub": "github", "GitCode": "git", "Gitee": "gitee"}
    else:
        marker = "## 他の場所"
        note = "> 同一人物 · 4プラットフォームでミラー公開"
        logo = {"GitHub": "github", "GitCode": "git", "Gitee": "gitee"}

    lines = text.split("\n")
    out = []
    i = 0
    replaced = False
    while i < len(lines):
        line = lines[i]
        if not replaced and line.strip() == marker:
            # 收集原随后的非平台徽章（如 CSDN / Juejin），平台链接由四平台重列
            j = i + 1
            kept = []
            platform_urls = {url for _, _, url, *_ in ALL_ACCOUNTS}
            while j < len(lines) and "</p>" not in lines[j]:
                if "<a href=" in lines[j] and "img.shields.io" in lines[j]:
                    # 跳过已在四平台列表中的账号徽章（避免重复）
                    if not any(purl in lines[j] for purl in platform_urls):
                        kept.append(lines[j].strip())
                j += 1
            if j < len(lines):
                j += 1  # 跳过 </p>
            badge_lines = "\n".join(
                f'  <a href="{url}"><img src="https://img.shields.io/badge/{site}-{account}-C9A86A?style=flat&logo={logo.get(site, "github")}&logoColor=white&labelColor=0B1026" alt="{site}" /></a>'
                for site, account, url, *_ in ALL_ACCOUNTS
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
    if len(sys.argv) < 2 or sys.argv[1] not in PLATFORM:
        print("usage: python3 inject_footprint.py <gh_x33834|gh_morningstar|gitcode|gitee>")
        sys.exit(1)
    key = sys.argv[1]
    files = [
        ("README.zh.md", "zh", "## 统计"),
        ("README.md", "en", "## Stats"),
        ("README.ja.md", "ja", "## 統計"),
    ]
    for fname, lang, stats_marker in files:
        with open(fname, encoding="utf-8") as f:
            text = f.read()
        assert stats_marker in text, f"stats marker missing in {fname}"
        block = footprint(lang, key)
        if block.strip() not in text:
            text = text.replace(stats_marker, block + "\n" + stats_marker)
        text = extend_elsewhere(lang, text)
        with open(fname, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("injected", fname)

if __name__ == "__main__":
    main()