# -*- coding: utf-8 -*-
"""进程级常量：统计字段、平台标签、卡片命名。"""

STAT_FIELDS = ("repos", "stars", "followers", "merged")
# 「精选作品」只展示最近更新的若干个仓库；全量列表在「全部公开仓库」链接里
WORKS_LIMIT = 6
PLATFORM_LABEL = {"github": "GitHub", "gitcode": "GitCode", "gitee": "Gitee"}

SNAKE_NAMES = ("github-contribution-grid-snake.svg", "github-contribution-grid-snake-dark.svg")
CARD_NAMES = {
    "stats": "cards/stats-%s.svg",
    "langs": "cards/langs-%s.svg",
    "pin": "cards/pin-%s.svg",
}
