# -*- coding: utf-8 -*-
"""扩展卡片：Gist、等距日历、编码习惯、关注者、项目看板。

所有数据来自 `data/extras.json`（可选的构建期快照），由
`scripts/refresh_extras.py` 在 GitHub token 可用时刷新。没有快照或
对应字段为空时返回 None，README 不出现空卡；渲染器永不联网。
"""

import math

from .textutil import clip_w, esc, fmt_num, text_w

PANEL = "#0E1630"
INK = "#F4F7FF"
MUTED = "#9AA8CC"
FAINT = "#5C6A94"
GOLD = "#D9B876"
TEAL = "#4FE3C1"


def _panel(width, height, title, body, alt):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
        'width="%d" height="%d" role="img" aria-label="%s">'
        '<rect x="0.75" y="0.75" width="%s" height="%s" rx="16" fill="%s" '
        'stroke="%s" stroke-opacity="0.30" stroke-width="1.5"/>'
        '<text x="26" y="38" font-family="Georgia,SimSun,serif" font-size="15" '
        'fill="%s">%s</text>%s</svg>'
        % (width, height, width, height, esc(alt), width - 1.5, height - 1.5,
           PANEL, GOLD, INK, esc(title), body)
    )


def _rows(items, x, y, step, label_key, value_key, max_w, value_suffix=""):
    parts = []
    for index, item in enumerate(items):
        top = y + index * step
        label = clip_w(str(item.get(label_key) or ""), max_w, 12.5)
        parts.append(
            '<text x="%d" y="%d" font-family="Helvetica,Arial,sans-serif" '
            'font-size="12.5" fill="%s">%s</text>'
            '<text x="974" y="%d" text-anchor="end" font-family="ui-monospace,Consolas,monospace" '
            'font-size="12" fill="%s">%s%s</text>'
            % (x, top, MUTED, esc(label), top, GOLD, esc(fmt_num(item.get(value_key))), value_suffix)
        )
    return "".join(parts)


def gist_svg(gists, lang=""):
    items = [g for g in (gists or []) if g.get("name")]
    if not items:
        return None
    height = 52 + len(items) * 30 + 18
    body = []
    for index, gist in enumerate(items):
        top = 72 + index * 30
        name = clip_w(str(gist.get("name")), 220, 12.5)
        desc = clip_w(str(gist.get("description") or ""), 340, 12)
        language = str(gist.get("language") or "")
        body.append(
            '<text x="26" y="%d" font-family="ui-monospace,Consolas,monospace" font-size="12.5" '
            'fill="%s">%s</text>'
            '<text x="270" y="%d" font-family="Helvetica,Arial,sans-serif" font-size="12" '
            'fill="%s">%s</text>'
            '<text x="974" y="%d" text-anchor="end" font-family="ui-monospace,Consolas,monospace" '
            'font-size="11.5" fill="%s">%s</text>'
            % (top, INK, esc(name), top, MUTED, esc(desc), top, FAINT, esc(language))
        )
    return _panel(1000, height, "Gists", "".join(body), "gists")


def isocalendar_svg(days, lang=""):
    rows = [d for d in (days or []) if d.get("date")]
    if not rows:
        return None
    counts = {str(d["date"]): int(d.get("count") or 0) for d in rows}
    months = sorted({d[:7] for d in counts})
    columns = max(1, len(months))
    cell, gap = 11, 3
    width = 26 + columns * (cell + gap) + 20
    height = 74 + 31 * (cell + gap) + 12
    parts = []
    for column, month in enumerate(months):
        x = 26 + column * (cell + gap)
        parts.append('<text x="%d" y="62" font-family="Helvetica,Arial,sans-serif" font-size="9" '
                     'fill="%s">%s</text>' % (x, FAINT, esc(month[5:])))
        for day in range(1, 32):
            date = "%s-%02d" % (month, day)
            if date not in counts:
                continue
            count = counts[date]
            level = 0 if count <= 0 else min(4, 1 + int(math.log2(count + 1)))
            fill = (FAINT, "#1F3B66", "#2F6DA8", TEAL, GOLD)[level]
            y = 68 + (day - 1) * (cell + gap)
            parts.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s">'
                         '<title>%s: %d</title></rect>'
                         % (x, y, cell, cell, fill, esc(date), count))
    return _panel(width, height, "Isocalendar", "".join(parts), "contribution calendar")


def habits_svg(habits, lang=""):
    if not isinstance(habits, dict):
        return None
    languages = [x for x in (habits.get("languages") or []) if x.get("name")]
    editors = [x for x in (habits.get("editors") or []) if x.get("name")]
    if not languages and not editors:
        return None
    parts = []
    y = 70
    if languages:
        parts.append('<text x="26" y="%d" font-family="Helvetica,Arial,sans-serif" font-size="11" '
                     'fill="%s">Languages</text>' % (y, FAINT))
        parts.append(_rows(languages[:6], 26, y + 22, 26, "name", "minutes", 780, " min"))
        y += 22 + min(6, len(languages)) * 26 + 10
    if editors:
        parts.append('<text x="26" y="%d" font-family="Helvetica,Arial,sans-serif" font-size="11" '
                     'fill="%s">Editors</text>' % (y, FAINT))
        parts.append(_rows(editors[:6], 26, y + 22, 26, "name", "minutes", 780, " min"))
        y += 22 + min(6, len(editors)) * 26
    return _panel(1000, y + 18, "Habits", "".join(parts), "coding habits")


def people_svg(people, lang=""):
    items = [p for p in (people or []) if p.get("login")]
    if not items:
        return None
    columns = min(10, len(items))
    rows = (len(items) + columns - 1) // columns
    body = []
    for index, person in enumerate(items):
        col = index % columns
        row = index // columns
        x = 26 + col * 96
        top = 62 + row * 86
        initials = esc(str(person["login"])[:1].upper())
        body.append(
            '<circle cx="%d" cy="%d" r="26" fill="#1F3B66"/>'
            '<text x="%d" y="%d" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" '
            'font-size="18" fill="%s">%s</text>'
            '<text x="%d" y="%d" text-anchor="middle" font-family="ui-monospace,Consolas,monospace" '
            'font-size="10" fill="%s">%s</text>'
            % (x + 26, top + 26, x + 26, top + 32, INK, initials,
               x + 26, top + 64, MUTED, esc(clip_w(str(person["login"]), 82, 10)))
        )
    return _panel(26 * 2 + columns * 96, 70 + rows * 86, "People", "".join(body), "followers")


def projects_svg(projects, lang=""):
    items = [p for p in (projects or []) if p.get("name")]
    if not items:
        return None
    height = 58 + len(items) * 42 + 18
    body = []
    for index, project in enumerate(items):
        top = 74 + index * 42
        name = clip_w(str(project["name"]), 240, 13)
        desc = clip_w(str(project.get("description") or ""), 560, 12)
        body.append(
            '<text x="26" y="%d" font-family="Georgia,SimSun,serif" font-size="13" '
            'fill="%s">%s</text>'
            '<text x="290" y="%d" font-family="Helvetica,Arial,sans-serif" font-size="12" '
            'fill="%s">%s</text>'
            % (top, INK, esc(name), top, MUTED, esc(desc))
        )
    return _panel(1000, height, "Projects", "".join(body), "projects")
