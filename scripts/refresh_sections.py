#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh the committed stats snapshot (the only network component).

    python3 scripts/refresh_sections.py --section stats --platform github
    python3 scripts/refresh_sections.py --section stats --platform gitee
    python3 scripts/refresh_sections.py --section stats --platform gitcode

Updates data/stats.json: account totals only (repos, stars, followers). Tokens are read from the environment when
present (GITHUB_TOKEN, GITEE_TOKEN); everything degrades gracefully offline.
"""

import argparse
import datetime
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

STATS_PATH = ROOT / "data" / "stats.json"

GH_ACCOUNTS = {
    "gh_badhope": "badhope",
    "gh_morningstar": "Morningstar202604",
    "gh_x33834": "X33834",
}


def fetch_json(url, token=None, token_param=None):
    if token_param:
        sep = "&" if "?" in url else "?"
        url = "%s%saccess_token=%s" % (url, sep, urllib.parse.quote(token_param, safe=""))
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", "token %s" % token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def gh_user(login, token):
    return fetch_json("https://api.github.com/users/%s" % login, token)


def gh_repo(owner, name, token):
    return fetch_json("https://api.github.com/repos/%s/%s" % (owner, name), token)


def gh_owned_repos(login, token):
    """Every personal, non-fork repo owned by the account."""
    repos = []
    page = 1
    while True:
        url = "https://api.github.com/users/%s/repos?type=owner&per_page=100&page=%d" % (login, page)
        batch = fetch_json(url, token)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [
        repo for repo in repos
        if repo.get("owner", {}).get("login", "").lower() == login.lower()
        and not repo.get("fork")
    ]


def refresh_github(stats, token):
    as_of = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    accounts = stats.setdefault("accounts", {})
    for key, login in GH_ACCOUNTS.items():
        try:
            user = gh_user(login, token)
            owned = gh_owned_repos(login, token)
        except OSError as exc:
            print("skip %s (%s): %s" % (key, login, exc))
            continue
        acc = accounts.setdefault(key, {})
        acc.update({
            "repos": len(owned),
            "stars": None,
            "followers": user.get("followers"),
        })
    stats["as_of"] = as_of
    stats["source"] = "scripts/refresh_sections.py"


def platform_repos(url, token, namespace_type):
    """Paginate a Gitee/GitCode user repo endpoint and keep personal non-forks."""
    repos = []
    page = 1
    while True:
        batch = fetch_json("%s?type=owner&per_page=100&page=%d" % (url, page), token_param=token)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [
        repo for repo in repos
        if (repo.get("namespace") or {}).get("type") == namespace_type
        and not repo.get("fork")
    ]


def refresh_platform(stats, key, token, url, namespace_type, label):
    accounts = stats.setdefault("accounts", {})
    try:
        repos = platform_repos(url, token, namespace_type)
        user = fetch_json(url.replace("/repos", ""), token_param=token)
        accounts[key] = {
            "repos": len(repos),
            "stars": sum(r.get("stargazers_count") or 0 for r in repos),
            "followers": user.get("followers"),
        }
        stats["as_of"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    except OSError as exc:
        print("skip %s: %s" % (label, exc))
        raise


def refresh_gitee(stats, token):
    refresh_platform(
        stats, "gitee_badhope", token,
        "https://gitee.com/api/v5/users/badhope/repos", "personal", "gitee",
    )


def refresh_gitcode(stats, token):
    refresh_platform(
        stats, "gitcode_badhope", token,
        "https://api.gitcode.com/api/v5/users/badhope/repos", "user", "gitcode",
    )


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=["stats"], required=True)
    ap.add_argument("--platform", choices=["github", "gitee", "gitcode"], required=True)
    args = ap.parse_args(argv)

    stats = json.loads(STATS_PATH.read_text(encoding="utf-8")) if STATS_PATH.exists() else {}
    if args.platform == "github":
        refresh_github(stats, os.environ.get("GITHUB_TOKEN"))
    elif args.platform == "gitee":
        refresh_gitee(stats, os.environ.get("GITEE_TOKEN"))
    else:
        refresh_gitcode(stats, os.environ.get("GITCODE_TOKEN"))

    STATS_PATH.write_text(json.dumps(stats, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("stats refreshed (%s): as_of=%s" % (args.platform, stats.get("as_of")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
