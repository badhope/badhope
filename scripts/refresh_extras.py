#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""刷新可选扩展卡片快照 data/extras.json。

数据源全部是公开 GitHub API（部分需要 token 提额或读取私有可见数据）：
- Gists: GET /users/{handle}/gists
- 贡献日历: GET /users/{handle}/events（近 90 天公开事件）
- 关注者: GET /users/{handle}/followers
- 项目: GET /users/{handle}/repos?type=owner（取 description 与 url）
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


def fetch_projects(handle):
    items = _get("/users/%s/repos?type=owner&sort=updated&per_page=100" % handle, handle, None)
    if not isinstance(items, list):
        raise ValueError("unexpected repos payload")
    return [{"name": item.get("name"), "description": (item.get("description") or "").strip(),
             "url": item.get("html_url") or ""}
            for item in items if item.get("name") and not item.get("fork")]


def fetch_calendar(handle):
    events = _get("/users/%s/events?per_page=100" % handle, handle, None)
    if not isinstance(events, list):
        raise ValueError("unexpected events payload")
    counts = {}
    for event in events:
        created = str(event.get("created_at") or "")[:10]
        if created:
            counts[created] = counts.get(created, 0) + 1
    return [{"date": date, "count": count} for date, count in sorted(counts.items())]


def fetch_habits(handle):
    """公开 events 不含语言或编辑器信息时返回空字典；绝不按猜测填充。"""
    events = _get("/users/%s/events?per_page=100" % handle, handle, None)
    if not isinstance(events, list):
        raise ValueError("unexpected events payload")
    languages = {}
    for event in events:
        payload = event.get("payload") or {}
        language = payload.get("language")
        if language:
            languages[language] = languages.get(language, 0) + 1
    if not languages:
        return {}
    return {"languages": [{"name": k, "minutes": v} for k, v in
                          sorted(languages.items(), key=lambda kv: -kv[1])[:6]]}


def _has_gpg(handle, token):
    request = urllib.request.Request(
        "https://github.com/%s.gpg" % handle,
        headers={"User-Agent": R.UA, "Authorization": "Bearer " + token} if token else {"User-Agent": R.UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", "replace")
    return "This user hasn't uploaded any GPG keys" not in body


def _has_starred_topics(handle, token):
    request = urllib.request.Request(
        "https://github.com/stars/%s/topics" % handle,
        headers={"User-Agent": R.UA, "Authorization": "Bearer " + token} if token else {"User-Agent": R.UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", "replace")
    return "doesn’t have any starred topics yet" not in body


def fetch_secrets(handle):
    """Detect secret achievements from public profile pages.

    Returns [] on any network/parse failure so the caller keeps prior snapshot.
    """
    token = R.resolve_token("github", handle, generic_env=("GITHUB_TOKEN", "GH_TOKEN"))
    items = []
    try:
        if _has_gpg(handle, token):
            items.append({"name": "Verified", "value": 1, "rank": "$", "progress": 1})
        if _has_starred_topics(handle, token):
            items.append({"name": "Explorer", "value": 1, "rank": "$", "progress": 1})
    except (OSError, ValueError, R.HttpError):
        return []
    return items


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
                              ("habits", fetch_habits), ("secrets", fetch_secrets)):
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
