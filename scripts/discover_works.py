#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从三平台真实 API 拉取仓库列表，作为「作品区」的数据源。

设计目标（解决"项目列表过期"问题）：
  - 不再硬编码项目名。每次刷新都从真实仓库读取。
  - 按 updated_at 倒序，自动选最近更新的若干个 —— 永远显示最新作品。
  - 排除本人主页仓库（badhope）、归档仓库、fork。
  - 失败时返回空列表而非抛异常，调用方保留旧数据（fail-soft）。

输出：data/works.json
  {
    "as_of": "2026-10-21",
    "accounts": {
      "gh_badhope": {"platform": "github", "handle": "badhope",
                     "repos": [{"name":..., "url":..., "stars":..., "updated":..., "desc":...}]}
    }
  }
"""

import argparse
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import accounts as A  # noqa: E402
import refresh as R   # noqa: E402

WORKS_PATH = ROOT / "data" / "works.json"

# 不参与展示的仓库：本人主页本身、纯归档/测试
EXCLUDE_NAMES = {"badhope", ".github", "profile", "test", "tmp", "scratch"}


def _repo_ident(repo, platform):
    """仓库的稳定标识：优先用 path（Gitee 的 name 可能是中文标题）。"""
    return (repo.get("path") or repo.get("name") or "").strip()


def _norm(repo, platform):
    """把三平台不同的字段归一成统一结构。

    坑位（实测）：
      - GitCode 没有 html_url，链接在 web_url；
      - Gitee 的 name 可能是中文标题（如「知客 Zhike」），仓库路径在 path；
      - Gitee 的 html_url 带 .git 后缀，展示时要剥掉。
    """
    ident = _repo_ident(repo, platform)
    title = (repo.get("human_name") or "").strip() or ident
    updated = (repo.get("updated_at") or repo.get("pushed_at") or "")[:10]
    desc = (repo.get("description") or "").strip()
    stars = repo.get("stargazers_count") or 0
    owner = ((repo.get("namespace") or {}).get("path")
             or (repo.get("owner") or {}).get("login")
             or "")
    if platform == "gitcode":
        url = repo.get("web_url") or ("https://gitcode.com/%s/%s" % (owner, ident))
    elif platform == "gitee":
        url = (repo.get("html_url") or ("https://gitee.com/%s/%s" % (owner, ident))).removesuffix(".git")
    else:
        url = repo.get("html_url") or ("https://github.com/%s/%s" % (owner, ident))
    return {"name": ident, "title": title, "url": url, "stars": stars,
            "updated": updated, "desc": desc}


def fetch_repos(platform, handle):
    """拉取某账号的全部公开仓库（已归一）。失败返回 None 以便调用方保留旧值。"""
    try:
        if platform == "github":
            token = R.resolve_token("github", handle, generic_env=("GITHUB_TOKEN", "GH_TOKEN"))
            headers = {"Authorization": "Bearer " + token} if token else {}
            repos, page = [], 1
            while True:
                batch = R.http_json(
                    "https://api.github.com/users/%s/repos?per_page=100&page=%d" % (handle, page),
                    headers,
                )
                if not isinstance(batch, list):
                    return None
                repos += batch
                if len(batch) < 100:
                    break
                page += 1
        elif platform == "gitee":
            token = R.resolve_token("gitee", handle, generic_env=("GITEE_TOKEN",))
            headers = {"Authorization": "token " + token} if token else None
            repos, page = [], 1
            while True:
                batch = R.http_json(
                    "https://gitee.com/api/v5/users/%s/repos?per_page=100&page=%d&sort=updated" % (handle, page),
                    headers,
                )
                if not isinstance(batch, list):
                    return None
                repos += batch
                if len(batch) < 100:
                    break
                page += 1
        elif platform == "gitcode":
            token = R.resolve_token("gitcode", handle, generic_env=("GITCODE_TOKEN",))
            if not token:
                return None
            headers = {"Authorization": "Bearer " + token}
            repos, page = [], 1
            while True:
                batch = R.http_json(
                    "https://api.gitcode.com/api/v5/users/%s/repos?per_page=100&page=%d" % (handle, page),
                    headers,
                )
                if not isinstance(batch, list):
                    return None
                repos += batch
                if len(batch) < 100:
                    break
                page += 1
        else:
            return None
    except R.NETWORK_ERRORS as err:
        print("  works %-16s FAIL %s" % (handle, err))
        return None

    out = []
    for r in repos:
        if r.get("fork"):
            continue
        ident = _repo_ident(r, platform)
        if not ident or ident.lower() in EXCLUDE_NAMES:
            continue
        # 排除本人主页仓库（与 handle 同名，如 X33834/X33834）
        if ident.lower() == (handle or "").lower():
            continue
        out.append(_norm(r, platform))
    # 按更新时间倒序 —— 最近有动静的排前面
    out.sort(key=lambda x: (x["updated"] or "", x["stars"]), reverse=True)
    return out


def refresh_works(limit=None):
    """刷新全部账号的作品列表。返回 True 表示有数据变化。"""
    cur = {}
    try:
        cur = json.loads(WORKS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = {}
    accounts = cur.get("accounts") or {}
    changed = False

    for key in A.ACCOUNT_ORDER:
        acct = A.ACCOUNTS[key]
        repos = fetch_repos(acct["platform"], acct["handle"])
        if repos is None:
            print("  works %-16s kept old (%d repos)" % (key, len(accounts.get(key, {}).get("repos", []))))
            continue
        if limit:
            repos = repos[:limit]
        old = (accounts.get(key) or {}).get("repos") or []
        if [r["name"] for r in old] != [r["name"] for r in repos]:
            changed = True
        accounts[key] = {
            "platform": acct["platform"],
            "handle": acct["handle"],
            "repos": repos,
        }
        print("  works %-16s %d repos (latest: %s)"
              % (key, len(repos), repos[0]["name"] if repos else "-"))

    if not changed:
        print("works: no data change — skip write")
        return False

    out = {
        "as_of": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "source": "scripts/discover_works.py",
        "accounts": accounts,
    }
    WORKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    WORKS_PATH.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print("works: written")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="discover real repos for profile works section")
    ap.add_argument("--limit", type=int, default=None, help="每账号最多保留几个")
    args = ap.parse_args(argv)
    return 0 if refresh_works(limit=args.limit) is not None else 1


if __name__ == "__main__":
    sys.exit(main())
