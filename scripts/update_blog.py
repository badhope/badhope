#!/usr/bin/env python3
"""Aggregate latest posts from CSDN / Juejin into profile READMEs."""

import datetime
import html
import os
import re

import common

CSDN_USER = "weixin_56622231"
JUEJIN_USER_ID = "2350111542479753"
MAX_ITEMS = 6


def fetch_csdn():
    page = common.http(
        f"https://blog.csdn.net/{CSDN_USER}/article/list/1",
        headers={
            "Referer": "https://blog.csdn.net/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    out = []
    for chunk in page.split('<div class="article-item-box')[1:]:
        m_url = re.search(
            rf'href="(https://blog\.csdn\.net/{CSDN_USER}/article/details/\d+)"', chunk
        )
        m_a = re.search(r"<a[^>]*>(.*?)</a>", chunk, flags=re.S)
        if not (m_url and m_a):
            continue
        title = re.sub(r"<span[^>]*>.*?</span>", "", m_a.group(1), flags=re.S)
        title = html.unescape(re.sub(r"\s+", " ", title)).strip()
        m_date = re.search(r'<span class="date">(\d{4}-\d{2}-\d{2})', chunk)
        out.append((title, m_url.group(1), m_date.group(1) if m_date else "", "CSDN"))
    return out


def fetch_juejin():
    payload = common.http_json(
        "https://api.juejin.cn/content_api/v1/article/query_list",
        method="POST",
        payload={"user_id": JUEJIN_USER_ID, "sort_type": 2, "cursor": "0"},
    )
    tz = datetime.timezone(datetime.timedelta(hours=8))
    out = []
    for item in payload.get("data") or []:
        info = item.get("article_info") or {}
        if not info.get("title") or not info.get("article_id"):
            continue
        date = datetime.datetime.fromtimestamp(int(info["ctime"]), tz).strftime(
            "%Y-%m-%d"
        )
        out.append(
            (
                html.unescape(info["title"]).strip(),
                f"https://juejin.cn/post/{info['article_id']}",
                date,
                "掘金",
            )
        )
    return out


SOURCES = ("CSDN", fetch_csdn), ("juejin", fetch_juejin)


def main():
    articles = []
    for name, fn in SOURCES:
        try:
            items = fn()
            print(f"{name}: {len(items)} posts")
            articles.extend(items)
        except Exception as err:  # noqa: BLE001 - one source failing must not kill all
            print(f"warn: {name} unavailable ({err}); skipped")

    if not articles:
        print("no articles fetched at all, keeping existing block")
        return

    articles.sort(key=lambda a: a[2], reverse=True)
    blog_block = "\n".join(
        f"- [{t}]({u}) · `{d}` · {src}" for t, u, d, src in articles[:MAX_ITEMS]
    )
    common.update_all_readmes({"BLOG": blog_block})


if __name__ == "__main__":
    main()
