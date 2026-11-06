#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh the committed stats snapshot (the only network component).

    python3 scripts/refresh_sections.py --section stats --platform github
    python3 scripts/refresh_sections.py --section stats --platform gitee
    python3 scripts/refresh_sections.py --section stats --platform gitcode

Updates data/stats.json: account totals plus per-work stars for the featured
works of each github account. Tokens are read from the environment when
present (GITHUB_TOKEN, GITEE_TOKEN); everything degrades gracefully offline.
"""

import argparse
import datetime
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

STATS_PATH = ROOT / "data" / "stats.json"

GH_ACCOUNTS = {
    "gh_badhope": "badhope",
    "gh_morningstar": "Morningstar202604",
    "gh_x33834": "X33834",
}


def fetch_json(url, token=None):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", "token %s" % token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def gh_user(login, token):
    return fetch_json("https://api.github.com/users/%s" % login, token)


def gh_repo(owner, name, token):
    return fetch_json("https://api.github.com/repos/%s/%s" % (owner, name), token)


def refresh_github(stats, token):
    as_of = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    accounts = stats.setdefault("accounts", {})
    for key, login in GH_ACCOUNTS.items():
        try:
            user = gh_user(login, token)
        except OSError as exc:
            print("skip %s (%s): %s" % (key, login, exc))
            continue
        acc = accounts.setdefault(key, {})
        acc.update({
            "repos": user.get("public_repos"),
            "stars": user.get("stars") if "stars" in user else None,
            "followers": user.get("followers"),
        })
        # per-work stars for the featured works
        works = acc.setdefault("works", {})
        for slug in build.FEATURED.get(key, []):
            try:
                repo = gh_repo(login, slug, token)
                works[slug] = {"stars": repo.get("stargazers_count"), "updated": (repo.get("pushed_at") or "")[:10]}
            except OSError as exc:
                print("skip work %s/%s: %s" % (login, slug, exc))
    stats["as_of"] = as_of
    stats["source"] = "scripts/refresh_sections.py"


def refresh_gitee(stats):
    accounts = stats.setdefault("accounts", {})
    try:
        repos = fetch_json("https://gitee.com/api/v5/users/badhope/repos?per_page=100")
        accounts["gitee_badhope"] = {
            "repos": len(repos),
            "stars": sum(r.get("stargazers_count") or 0 for r in repos),
            "followers": None,
        }
        stats["as_of"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    except OSError as exc:
        print("skip gitee: %s" % exc)


def refresh_gitcode(stats):
    accounts = stats.setdefault("accounts", {})
    try:
        repos = fetch_json("https://gitcode.com/api/v5/users/badhope/repos?per_page=100")
        accounts["gitcode_badhope"] = {
            "repos": len(repos),
            "stars": sum(r.get("stargazers_count") or 0 for r in repos),
            "followers": None,
        }
        stats["as_of"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    except OSError as exc:
        print("skip gitcode: %s" % exc)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=["stats"], required=True)
    ap.add_argument("--platform", choices=["github", "gitee", "gitcode"], required=True)
    args = ap.parse_args(argv)

    stats = json.loads(STATS_PATH.read_text(encoding="utf-8")) if STATS_PATH.exists() else {}
    if args.platform == "github":
        refresh_github(stats, os.environ.get("GITHUB_TOKEN"))
    elif args.platform == "gitee":
        refresh_gitee(stats)
    else:
        refresh_gitcode(stats)

    STATS_PATH.write_text(json.dumps(stats, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("stats refreshed (%s): as_of=%s" % (args.platform, stats.get("as_of")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
