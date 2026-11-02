#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""刷新可选扩展卡片快照 data/extras.json。

数据源全部是公开 GitHub API（部分需要 token 提额或读取私有可见数据）：
- Gists: GET /users/{handle}/gists
- 贡献日历: GitHub GraphQL contributionCalendar（默认近一年）
- 关注者: GET /users/{handle}/followers
- 项目: GitHub GraphQL projectsV2（只展示公开项目）
- 编码习惯: 由贡献日历中按语言归类的事件推导；只有 API 返回 language 时才写入。

失败策略：每个 section 单独 fail-soft；失败时保留旧值，不把空数组当成功。
不会把 token 写入 URL、日志或快照。
"""

import argparse
import datetime
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import accounts as A  # noqa: E402
import refresh as R  # noqa: E402

EXTRAS_PATH = ROOT / "data" / "extras.json"


def _load():
    try:
        data = json.loads(EXTRAS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"as_of": "", "accounts": {}}
    if not isinstance(data, dict):
        return {"as_of": "", "accounts": {}}
    data.setdefault("accounts", {})
    return data


def _get(path, handle, token):
    return R.http_json("https://api.github.com" + path, R.gh_headers(handle))


def fetch_gists(handle):
    items = _get("/users/%s/gists?per_page=100" % handle, handle, None)
    if not isinstance(items, list):
        raise ValueError("unexpected gists payload")
    out = []
    for item in items[:20]:
        files = item.get("files") or {}
        first = next(iter(files.values()), {}) if isinstance(files, dict) else {}
        out.append({
            "name": first.get("filename") or item.get("id") or "gist",
            "description": (item.get("description") or "").strip(),
            "language": first.get("language") or "",
            "url": item.get("html_url") or "",
        })
    return out


def fetch_people(handle):
    items = _get("/users/%s/followers?per_page=100" % handle, handle, None)
    if not isinstance(items, list):
        raise ValueError("unexpected followers payload")
    return [{"login": item.get("login"), "avatar_url": item.get("avatar_url")}
            for item in items if item.get("login")]


def _extra_graphql(handle, query, cursor=None):
    token = R.resolve_token("github", handle, generic_env=("GITHUB_TOKEN", "GH_TOKEN"))
    if not token:
        raise ValueError("GitHub token required")
    body = json.dumps({"query": query, "variables": {"login": handle, "cursor": cursor}}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql", data=body, method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": R.UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _graphql_user(payload):
    if not isinstance(payload, dict) or payload.get("errors"):
        raise ValueError("GitHub GraphQL request failed")
    user = (payload.get("data") or {}).get("user")
    if not isinstance(user, dict):
        raise ValueError("GitHub user unavailable")
    return user


def fetch_projects(handle):
    query = """query($login: String!, $cursor: String) {
      user(login: $login) {
        projectsV2(first: 100, after: $cursor) {
          nodes { title url shortDescription public }
          pageInfo { hasNextPage endCursor }
        }
      }
    }"""
    result, cursor, seen = [], None, set()
    while True:
        user = _graphql_user(_extra_graphql(handle, query, cursor))
        connection = user.get("projectsV2") or {}
        nodes, page = connection.get("nodes"), connection.get("pageInfo")
        if not isinstance(nodes, list) or not isinstance(page, dict) or not isinstance(page.get("hasNextPage"), bool):
            raise ValueError("incomplete project response")
        for node in nodes:
            if isinstance(node, dict) and node.get("title") and node.get("url") and node.get("public") is True:
                result.append({"name": node["title"], "description": node.get("shortDescription") or "",
                               "url": node["url"]})
        if not page.get("hasNextPage"):
            return result
        cursor = page.get("endCursor")
        if not cursor or cursor in seen:
            raise ValueError("invalid project cursor")
        seen.add(cursor)


def fetch_calendar(handle):
    query = """query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar { weeks { contributionDays { date contributionCount } } }
        }
      }
    }"""
    user = _graphql_user(_extra_graphql(handle, query))
    collection = user.get("contributionsCollection") or {}
    weeks = (collection.get("contributionCalendar") or {}).get("weeks")
    if not isinstance(weeks, list):
        raise ValueError("incomplete calendar response")
    result = []
    for week in weeks:
        for day in week.get("contributionDays") or []:
            count = day.get("contributionCount")
            if not day.get("date") or not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError("invalid calendar day")
            result.append({"date": day["date"], "count": count})
    return result


def fetch_habits(handle):
    raise ValueError("GitHub events do not provide coding duration")


def _has_gpg(handle, token):
    request = urllib.request.Request(
        "https://github.com/%s.gpg" % handle,
        headers={"User-Agent": R.UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", "replace")
    if "This user hasn't uploaded any GPG keys" in body:
        return False
    if "-----BEGIN PGP PUBLIC KEY BLOCK-----" in body:
        return True
    raise ValueError("unrecognized GPG response")


def _has_starred_topics(handle, token):
    request = urllib.request.Request(
        "https://github.com/stars/%s/topics" % handle,
        headers={"User-Agent": R.UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", "replace")
    if "doesn’t have any starred topics yet" in body or "doesn't have any starred topics yet" in body:
        return False
    raise ValueError("starred topics page cannot be verified reliably")


def fetch_secrets(handle):
    """Detect secret achievements from public profile pages.

    Returns [] on any network/parse failure so the caller keeps prior snapshot.
    """
    token = R.resolve_token("github", handle, generic_env=("GITHUB_TOKEN", "GH_TOKEN"))
    items = []
    if _has_gpg(handle, token):
        items.append({"name": "Verified", "value": 1, "rank": "$", "progress": 1})
    if _has_starred_topics(handle, token):
        items.append({"name": "Explorer", "value": 1, "rank": "$", "progress": 1})
    return items


def fetch_wakatime(handle):
    """采集 WakaTime 统计并写入快照；未配置 API key 时抛错由上层保留旧值。"""
    from kit.wakatime import fetch_stats
    stats = fetch_stats()
    if not isinstance(stats, dict) or not stats.get("data"):
        raise ValueError("wakatime unavailable")
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="refresh optional GitHub extra cards")
    ap.add_argument("--platform", choices=["github"], default="github")
    args = ap.parse_args(argv)
    data = _load()
    changed = False
    for key in A.ACCOUNT_ORDER:
        acct = A.ACCOUNTS[key]
        if acct["platform"] != args.platform:
            continue
        handle = acct["handle"]
        block = dict((data["accounts"] or {}).get(key) or {})
        old = json.loads(json.dumps(block))
        for name, fetcher in (("gists", fetch_gists), ("people", fetch_people),
                              ("projects", fetch_projects), ("contribution_days", fetch_calendar),
                              ("habits", fetch_habits), ("secrets", fetch_secrets),
                              ("wakatime", fetch_wakatime)):
            try:
                block[name] = fetcher(handle)
            except R.NETWORK_ERRORS as err:
                print("  extras %-16s %-18s FAIL %s (kept old)" % (key, name, type(err).__name__))
        if block != old:
            data["accounts"][key] = block
            changed = True
    if not changed:
        print("extras: no data change — skip write")
        return 0
    data["as_of"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    data["source"] = "scripts/refresh_extras.py"
    EXTRAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXTRAS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8", newline="\n")
    print("extras: written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
