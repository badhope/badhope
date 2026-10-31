# -*- coding: utf-8 -*-
"""README 渲染：三语言模板、贡献表、写作区、在别处表格。"""

import pathlib
import re

import accounts as A

from .cards import live_badges
from .config import PLATFORM_LABEL, STAT_FIELDS, WORKS_LIMIT
from .data import _snake_available, acct_stats, load_card_seed, load_writing_items
from .paths import ROOT
from .emoji import parse_emojis
from .textutil import _stats_month, esc, fmt_num

def pr_links(repo_url, nums):
    return " · ".join("[#%s](%s/pull/%s)" % (n, repo_url, n) for n in nums)


def _has_cjk(text):
    return bool(re.search(r"[\u3400-\u9fff]", text or ""))


def _has_japanese(text):
    return bool(re.search(r"[\u3040-\u30ff]", text or ""))


def _curated_description(name, lang):
    for work_id, work in A.WORKS.items():
        if work_id.casefold() == (name or "").casefold():
            return (work.get("desc") or {}).get(lang)
    return None


def _work_label(repo, lang):
    """Return a localized label without leaking an incompatible source language."""
    name = (repo.get("name") or "").strip()
    title = (repo.get("title") or name).strip()
    desc = _curated_description(name, lang) or (repo.get("desc") or "").strip()
    if not _curated_description(name, lang):
        if lang == "ja" and desc and not _has_japanese(desc):
            desc = ""
        elif lang == "md" and desc and _has_cjk(desc):
            desc = ""
        elif lang == "zh-CN" and desc and not _has_cjk(desc):
            desc = ""
    label = title if not desc else "%s — %s" % (title, desc)
    if len(label) > 68:
        label = label[:67].rstrip() + "…"
    return label.replace("|", "\\|").replace("[", "(").replace("]", ")")


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

def render_readme(acct, key, lang, stats, base=None, discovered=None, hero_png=True,
                  assets_dir=None):
    labels = A.LABELS[lang]
    tagline = acct["tagline"][lang]
    lines = []
    lines.append("[English](README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md)")
    lines.append("")
    lines.append('<p align="center">')
    # hero 用 <picture> 提供 PNG 兜底：GitHub camo / GitCode raw 对 SVG 的支持不稳定，
    # PNG 是位图，各平台渲染策略一致，优先使用。
    if hero_png:
        lines.append('  <picture>')
        lines.append('  <source type="image/png" srcset="./assets/png/hero.png" />')
        lines.append('  <img src="./assets/hero.svg" alt="%s · %s" width="100%%" />'
                     % (esc(acct["handle"]), esc(acct["home_display"])))
        lines.append('  </picture>')
    else:
        # 该账号没有 PNG 兜底时只引用 SVG：<source> 指向不存在的文件会让部分
        # 渲染器显示裂图而不是回落到 <img>。
        lines.append('  <img src="./assets/hero.svg" alt="%s · %s" width="100%%" />'
                     % (esc(acct["handle"]), esc(acct["home_display"])))
    lines.append("</p>")
    lines.append("")
    # 打字机格言卡（readme-typing-svg 移植）：tagline 即格言，不重复静态文本
    lines.append('<p align="center">')
    lines.append('  <img src="./assets/typing-%s.svg" alt="%s" width="600" />'
                 % (lang, esc(tagline)))
    lines.append("</p>")
    lines.append("")
    # 用数据快照月份而不是系统当月：同样的 accounts.py + stats.json 必须生成
    # 完全一致的字节，否则每月 1 号会在没有任何数据变化时产生一个噪声提交。
    month = _stats_month(stats)
    quote = A.QUOTES[(month - 1) % len(A.QUOTES)]
    quote_text = quote.get(lang) or (quote["zh"] if lang == "zh-CN" else quote["en"])
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
    # 作品清单来自 data/works.json（每次刷新从平台 API 重新发现，按更新时间倒序）。
    # 不再用写死的 SVG 卡片：图片是死的，项目会过期。
    live_works = (((discovered or {}).get("accounts") or {}).get(key) or {}).get("repos") or []
    if live_works:
        lines.append("| %s | %s | %s |" % (
            labels["works_col_name"], labels["works_col_stars"], labels["works_col_updated"]))
        lines.append("| --- | --- | --- |")
        for repo in live_works[:WORKS_LIMIT]:
            # 外部描述按目标语言过滤，避免日文页出现整段中文/英文机翻腔；
            # 名称仍保留，确保没有本地化描述时作品不会消失。
            label = parse_emojis(_work_label(repo, lang))
            lines.append("| [%s](%s) | %s | %s |" % (
                esc(label), esc(repo.get("url") or ""),
                repo.get("stars", 0), esc(repo.get("updated") or "")))
        lines.append("")
    else:
        # 没有实时数据时退回作品 SVG（保证不空白）
        lines.append('<p align="center">')
        lines.append('  <img src="./assets/works-%s.svg" alt="%s" width="100%%" />'
                     % (lang, esc(labels["works"])))
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

    # ---- 数据面板：徽章 + stats/langs 并排 + activity ----
    lines.append("## %s" % labels["numbers"])
    lines.append("")
    # 卡片产物引用一律看本次输出的 assets 目录：snake（GitHub 专属）与 badges
    # （GitCode/Gitee 专属）是按账号生成的，全局 ROOT/assets 里可能躺着别的
    # 账号的产物，跨账号渲染时会造出悬空引用。assets_dir 由 build 层传入，
    # 指向与 README 同目录的 assets —— 引用与文件同源，永不脱钩。
    assets_root = pathlib.Path(assets_dir) if assets_dir else (pathlib.Path(base) if base else ROOT) / "assets"
    # 徽章行：GitHub 走 shields.io 实时，GitCode/Gitee 走自渲染（构建期快照）
    badge_row = live_badges(acct, lang)
    if badge_row:
        lines.append(badge_row)
        lines.append("")
    else:
        badge_path = assets_root / ("badges-%s.svg" % A.CARD_LOCALE[lang])
        if badge_path.is_file():
            lines.append('<p align="center">')
            lines.append('  <img src="./assets/badges-%s.svg" alt="%s" />'
                         % (A.CARD_LOCALE[lang], esc(labels["numbers"])))
            lines.append("</p>")
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
    # langs 卡是否真的产出：README 渲染在卡片之后，直接看本次输出目录里的
    # langs 卡文件 —— 数据里"有仓库"不等于卡片渲染成功（CI 曾因此挂空引用）。
    has_langs = (assets_root / ("langs-%s.svg" % lang)).is_file()
    # stats + langs 并排（GRS 经典双卡布局）
    lines.append('<p align="center">')
    if card_stats and card_langs:
        lines.append('  <img src="./assets/cards/stats-%s.svg" alt="GitHub stats" width="49%%" />'
                     % A.CARD_LOCALE[lang])
        lines.append('  <img src="./assets/cards/langs-%s.svg" alt="Top languages" width="49%%" />'
                     % A.CARD_LOCALE[lang])
    elif card_stats:
        lines.append('  <img src="./assets/cards/stats-%s.svg" alt="GitHub stats" width="70%%" />'
                     % A.CARD_LOCALE[lang])
    elif has_langs:
        lines.append('  <img src="./assets/%s" alt="%s" width="49%%" />' % (A.STATS_NAME[lang], esc(alt)))
        lines.append('  <img src="./assets/langs-%s.svg" alt="%s" width="49%%" />'
                     % (lang, esc(labels["langs"])))
    else:
        lines.append('  <img src="./assets/%s" alt="%s" width="80%%" />' % (A.STATS_NAME[lang], esc(alt)))
    lines.append("</p>")
    lines.append("")
    if not card_stats:
        lines.append('<p align="center">')
        lines.append('  <img src="./assets/activity-%s.svg" alt="%s" width="100%%" />' % (lang, esc(alt)))
        lines.append("</p>")
        lines.append("")

    # ---- Impact：贡献蛇 + 成就 + 开源足迹（合并为一个区块） ----
    snake_path = assets_root / ("snake-%s.svg" % lang)
    ach_path = assets_root / ("achievements-%s.svg" % A.CARD_LOCALE[lang])
    has_impact = snake_path.is_file() or ach_path.is_file()
    if has_impact:
        lines.append("## %s" % labels["achievements"])
        lines.append("")
        if snake_path.is_file():
            lines.append('<p align="center">')
            lines.append('  <img src="./assets/snake-%s.svg" alt="contribution snake" width="100%%" />' % lang)
            lines.append("</p>")
            lines.append("")
        if ach_path.is_file():
            lines.append('<p align="center">')
            lines.append('  <img src="./assets/achievements-%s.svg" alt="%s" width="90%%" />'
                         % (A.CARD_LOCALE[lang], esc(labels["achievements"])))
            lines.append("</p>")
            lines.append("")
        # 开源足迹折叠为脚注
        lines.append('<details>')
        lines.append('<summary>%s</summary>' % esc(labels["contrib"]))
        lines.append("")
        lines.append(render_contrib(acct, key, lang))
        lines.append("")
        lines.append('</details>')
        lines.append("")
    if not has_impact:
        lines.append("## %s" % labels["contrib"])
        lines.append("")
        lines.append(render_contrib(acct, key, lang))
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

    # ---- 写作（日期 | 文章 两列表） ----
    lines.append("## %s" % labels["writing"])
    lines.append("")
    writing_items = load_writing_items()
    if writing_items:
        lines.append("| %s | %s |" % (labels["date"], labels["article"]))
        lines.append("|---|---|")
        for item in writing_items[:5]:
            title = (A.WRITING_TITLE_OVERRIDES.get(item["url"], {}).get(lang)
                     or item["title"])
            lines.append("| %s | [%s](%s) |"
                         % (item.get("date") or "—", title, item["url"]))
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
