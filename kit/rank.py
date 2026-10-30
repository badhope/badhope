# -*- coding: utf-8 -*-
"""Rank 与成就系统。

两个来源合并：

1. **github-readme-stats 的百分位 Rank**（`src/calculateRank.js`）：
   用指数/对数正态 CDF 对 commits/PRs/issues/reviews/stars/followers 六项
   加权混合成 0..1 的 rank，映射到 S/A+/A/A-/B+/B/B-/C+/C 九档，
   卡片上画一个进度环。
2. **github-profile-trophy 的绝对阈值**（`src/trophy.ts`）+ **lowlighter/metrics
   的成就阈值表**（`source/plugins/achievements/list/users.mjs`）：
   每一项统计一个 SSS→C 的阈值表，算出当前档位和到下一档的进度。

本项目数据源是 `data/stats.json`（repos/stars/followers/merged）+ 
`data/works.json`（语言数、仓库年龄），没有 commits/issues/reviews 的 GraphQL
明细，因此：
- Rank 环用 repos/stars/followers/merged 四项（merged 用 merged 权重替代 reviews）；
- 成就表只用能从现有数据推导的字段（Developer/Influencer/Maintainer/Polyglot/
  Member/Contributor），其余标记 needs-token（fetcher 侧支持后再开）。
"""

import math

# ---- github-readme-stats: percentile rank ---------------------------------
# 与 src/calculateRank.js 完全同源；只调整了 medians 以匹配本数据源口径。

def _exponential_cdf(x):
    return 1 - 2 ** (-x)


def _log_normal_cdf(x):
    return x / (1 + x)


_WEIGHTS = (
    # (字段, median, weight, cdf)
    ("commits", 250, 2, _exponential_cdf),
    ("prs", 50, 3, _exponential_cdf),
    ("issues", 25, 1, _exponential_cdf),
    ("reviews", 2, 1, _exponential_cdf),
    ("stars", 50, 4, _log_normal_cdf),
    ("followers", 10, 1, _log_normal_cdf),
)
_TOTAL_WEIGHT = sum(w for _, _, w, _ in _WEIGHTS)

_THRESHOLDS = (1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100)
_LEVELS = ("S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C")


def calculate_rank(fields):
    """fields: {"commits": n, "prs": n, ...}。返回 {"level","percentile","rank"}。

    缺失的字段按 0 计（= 显著拉低 rank，与 GRS 对新账号的行为一致）。
    """
    total = 0.0
    for name, median, weight, cdf in _WEIGHTS:
        value = max(0, fields.get(name) or 0)
        total += weight * cdf(value / median)
    rank = 1 - total / _TOTAL_WEIGHT
    percentile = rank * 100
    level = _LEVELS[-1]
    for threshold, level_name in zip(_THRESHOLDS, _LEVELS):
        if percentile <= threshold:
            level = level_name
            break
    return {"level": level, "percentile": percentile, "rank": rank}


# ---- trophy / metrics 风格：绝对阈值成就表 ---------------------------------
# 来源：
#   github-profile-trophy  src/trophy_list.ts（SSS..C 八档）
#   lowlighter/metrics     source/plugins/achievements/list/users.mjs（C/B/A/S/max 五档）

RANKS = ("SECRET", "SSS", "SS", "S", "AAA", "AA", "A", "B", "C")

#: 阈值表：成就名 → (统计字段, {rank: 阈值}, 描述)。阈值沿用 trophy 原值。
TROPHY_TABLE = (
    ("stars", "Stars", {"SSS": 2000, "SS": 700, "S": 200, "AAA": 100, "AA": 50, "A": 30, "B": 10, "C": 1}),
    ("merged", "Pull Request", {"SSS": 1000, "SS": 500, "S": 200, "AAA": 100, "AA": 50, "A": 20, "B": 10, "C": 1}),
    ("repos", "Repositories", {"SSS": 50, "SS": 45, "S": 40, "AAA": 35, "AA": 30, "A": 20, "B": 10, "C": 1}),
)

#: metrics 成就（C/B/A/S/max 五档 → 显示用四档 S/A/B/C）
ACHIEVEMENT_TABLE = (
    # (成就名, 字段, (C, B, A, S), 图标名)
    ("Developer", "repos", (1, 20, 50, 100), "repos"),
    ("Influencer", "followers", (1, 200, 500, 1000), "followers"),
    ("Maintainer", "stars", (1, 1000, 5000, 10000), "stars"),
    ("Polyglot", "languages", (1, 4, 8, 16), "languages"),
    ("Member", "years", (1, 3, 5, 10), "duration"),
)

#: metrics 的 rank 配色（primary/secondary）
ACHIEVEMENT_COLORS = {
    "S": ("#EB355E", "#731237"),
    "A": ("#B59151", "#FFD576"),
    "B": ("#7D6CFF", "#B2A8FF"),
    "C": ("#2088FF", "#79B8FF"),
    "$": ("#FF48BD", "#FF92D8"),
    "X": ("#7A7A7A", "#B0B0B0"),
}


def rank_of(value, thresholds):
    """thresholds: {"SSS": n, ...}，返回 (rank_name, progress 0..1)。

    与 trophy 的 setRank 语义一致：按 RANKS 顺序找第一个 value >= 阈值的档；
    progress = (value - 本档阈值) / (下一档阈值 - 本档阈值)。
    """
    ordered = [r for r in RANKS if r in thresholds]
    hit, progress = None, 0.0
    for i, r in enumerate(ordered):
        if value >= thresholds[r]:
            hit = r
            if i > 0:
                prev = thresholds[ordered[i - 1]]
                progress = (value - thresholds[r]) / (prev - thresholds[r] or 1)
            else:
                progress = 1.0
            break
    if hit is None:
        lowest = ordered[-1] if ordered else "C"
        lowest_value = thresholds.get(lowest, 1)
        progress = value / lowest_value if lowest_value else 0.0
        return "C", min(progress, 1.0)
    return hit, min(progress, 1.0)


def achievements(stats, languages=None, years=None):
    """从现有数据推导成就列表。

    stats: data/stats.json 里本账号的 block；languages: 语言数；years: 账号年龄。
    返回 [{"name","value","rank","progress","display"}]。
    """
    fields = dict(stats or {})
    if languages is not None:
        fields["languages"] = languages
    if years is not None:
        fields["years"] = years
    out = []
    for name, field, thresholds, _icon in ACHIEVEMENT_TABLE:
        value = fields.get(field)
        if value is None:
            continue
        value = max(0, value)
        # metrics 的 C/B/A/S 四档阈值映射到 (C, B, A, SSS) —— SSS 当作满档
        trophy_thresholds = {"SSS": thresholds[3], "A": thresholds[2], "B": thresholds[1], "C": thresholds[0]}
        rank, progress = rank_of(value, trophy_thresholds)
        display_rank = "S" if rank in ("SSS", "S") else rank
        out.append({
            "name": name,
            "field": field,
            "value": value,
            "rank": display_rank,
            "progress": progress,
        })
    return out


def trophies(stats):
    """trophy 风格：返回 [(name, value, rank, progress)]，阈值表原样移植。"""
    out = []
    for field, title, thresholds in TROPHY_TABLE:
        value = (stats or {}).get(field)
        if value is None:
            continue
        rank, progress = rank_of(max(0, value), thresholds)
        out.append({"name": title, "field": field, "value": value, "rank": rank, "progress": progress})
    return out


def derive_profile(stats_block, repos=None):
    """统一的数据推导入口：stats block + 仓库列表 → (languages, rank, years)。

    cardset（stats 卡）与 achievements（成就卡）共用，消除两处相同的
    「语言数去重 + rank 字段拼装」逻辑。
    repos: [{"language": "..."}, ...]（works.json 的 repos 列表）。
    """
    languages = None
    if repos:
        seen = set()
        for repo in repos:
            language = (repo.get("language") or "").strip()
            if language:
                seen.add(language)
        if seen:
            languages = len(seen)
    block = stats_block or {}
    rank = calculate_rank({
        "stars": block.get("stars") or 0,
        "followers": block.get("followers") or 0,
        "repos": block.get("repos") or 0,
        "languages": languages or 0,
        # commits/prs/issues/reviews 无数据源，按 0 计（显式声明而非误用）
        "commits": 0, "prs": 0, "issues": 0, "reviews": 0,
    })
    return {"languages": languages, "rank": rank}


def fmt_compact(value):
    """GRS kFormatter：>=1000 显示 x.xk。"""
    if value is None:
        return "—"
    if value < 1000:
        return str(value)
    return ("%.1f" % (value / 1000)).rstrip("0").rstrip(".") + "k"
