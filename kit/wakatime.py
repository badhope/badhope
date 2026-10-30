# -*- coding: utf-8 -*-
"""WakaTime 编码统计卡（可选插件，token 门槛）。

github-readme-stats 的 wakatime 卡（src/cards/wakatime.js）移植：
- 需要 WAKATIME_API_KEY（或 WAKATIME_API_URL 指向自托管 wakapi）
- 没有 token 时本插件整体跳过（不占卡片位），doctor 会标注
- 布局复用 langs 卡的进度条风格：label | bar | value
"""

import json

from .net import HttpError, default_client

SUPPORTED_RANGES = ("last_7_days", "last_30_days", "last_6_months", "last_year")
RANGE_LABELS = {
    "md": {"last_7_days": "Last 7 Days", "last_30_days": "Last 30 Days",
           "last_6_months": "Last 6 Months", "last_year": "Last Year"},
}


def _api_key():
    import os
    return (os.environ.get("WAKATIME_API_KEY") or "").strip()


def fetch_stats(api_key=None, api_domain="wakatime.com", timeout=30):
    key = api_key or _api_key()
    if not key:
        return None
    url = "https://%s/api/v1/users/current/stats/%s?is_including_today=true" % (
        api_domain.rstrip("/"), SUPPORTED_RANGES[0])
    try:
        return default_client().get_json(
            url, headers={"Authorization": "Basic " + key}, timeout=timeout)
    except (HttpError, OSError, ValueError):
        return None


def wakatime_svg(stats, lang="md", theme=None, layout="normal", langs_count=5, width=495):
    """渲染 WakaTime 卡。stats 为 API 的 data 节点。"""
    from .textutil import esc, text_w
    t = theme or {}
    if not stats:
        return None
    data = stats.get("data") or {}
    categories = data.get("categories") or []
    total_text = (categories[0].get("text") if categories else "") or ""
    languages = sorted(
        ({"name": x.get("name") or "", "text": x.get("text") or "",
          "percent": float(x.get("percent") or 0)}
         for x in data.get("languages") or []),
        key=lambda x: -x["percent"])
    languages = languages[:max(1, langs_count)]
    if not languages:
        return None
    padding = 25
    row_h = 25
    bar_x, bar_w_max = 130, width - 275
    height = 45 + (len(languages) + 1) * row_h
    label = "%s · %s" % (
        esc("WakaTime"),
        esc(RANGE_LABELS.get(lang, RANGE_LABELS["md"]).get(
            data.get("range") or SUPPORTED_RANGES[0], "")),
    )
    parts = []
    top = max(x["percent"] for x in languages) or 1
    for i, item in enumerate(languages):
        y = 55 + i * row_h
        parts.append(
            '<text x="25" y="%d" font-family="%s" font-size="14" fill="%s">%s</text>'
            % (y + 14, A.SANS, t.get("ink", "#fff"), esc(item["name"])))
        if layout == "normal":
            bar_w = bar_w_max * item["percent"] / top
            parts.append(
                '<rect x="%d" y="%d" width="%d" height="8" rx="4" fill="%s" opacity="0.2"/>'
                % (bar_x, y + 6, bar_w_max, t.get("ink", "#fff")))
            parts.append(
                '<rect x="%d" y="%d" width="%.1f" height="8" rx="4" fill="%s"/>'
                % (bar_x, y + 6, bar_w, t.get("gold", "#d9b876")))
            parts.append(
                '<text x="%d" y="%d" font-family="%s" font-size="13" fill="%s">%s</text>'
                % (bar_x + bar_w_max + 10, y + 14, A.MONO, t.get("muted", "#aaa"),
                   esc(item["text"])))
        else:
            parts.append(
                '<text x="%d" y="%d" font-family="%s" font-size="13" fill="%s">%s</text>'
                % (width - padding, y + 14, A.MONO, t.get("muted", "#aaa"),
                   esc("%s - %s" % (item["name"], item["text"]))))
    title = esc("WakaTime · %s" % total_text)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'role="img" aria-label="%s">'
        '<rect x="0.5" y="0.5" width="%d" height="%d" rx="4.5" fill="%s" '
        'stroke="%s" stroke-opacity="0.3"/>'
        '<text x="%d" y="35" font-family="%s" font-size="18" fill="%s">%s</text>'
        '%s'
        '</svg>'
        % (width, height, title, width - 1, height - 1, t.get("panel", "#0E1630"),
           t.get("deep_blue", "#24356B"), padding, A.SANS,
           t.get("gold", "#D9B876"), title, "\n".join(parts))
    )
