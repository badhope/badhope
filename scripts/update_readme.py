#!/usr/bin/env python3
"""Live-refresh STATS / PROJECTS blocks with real cross-platform data.

The profile READMEs are curated cross-platform content (scripts/build_profile.py).
This script refreshes the *numbers* in those blocks every run:

- STATS: repo count (max of four platforms), total stars (max across platforms
  per project, then summed), followers (max GitHub).
- PROJECTS: for each curated repo, display the highest star count across
  GitHub (X33834 / Morningstar202604) + GitCode + Gitee.

Data sources need no API key on GitHub/Gitee; GitCode reads GITCODE_TOKEN from
the environment when present and skips GitCode otherwise (keeps existing numbers).

The BLOG block is handled by update_blog.py; this script never touches it.
"""

import json
import os
import re

import common

README_FILES = ("README.md", "README.zh.md", "README.ja.md")

GC_OWNER = "badhope"
GH_ACCOUNTS = ("X33834", "Morningstar202604")
GITEE_OWNER = "badhope"

# Curated project list (name, tag used for language display); descriptions
# and tags live in build_profile.py, here we only refresh star counts.
CURATED_PROJECTS = [
    "mobilecode",
    "dev-terminal",
    "awesome-skillkit",
    "scholarhub",
    "FinHub",
    "VerdictAI",
    "mashang-python",
    "KeBaiPay",
    "bot4cj",
]


def _gh_headers():
    token = os.environ.get("GH_TOKEN", "").strip() or os.environ.get(
        "GITHUB_TOKEN", ""
    ).strip()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def gh_repos(account):
    """Fetch repo star map from GitHub (public, no token needed)."""
    stars = {}
    page = 1
    while True:
        data = common.http_json(
            f"https://api.github.com/users/{account}/repos?per_page=100&page={page}",
            headers=_gh_headers(),
        )
        if not data:
            break
        for repo in data:
            stars[repo["name"]] = repo["stargazers_count"]
        if len(data) < 100:
            break
        page += 1
    return stars


def gitee_repos():
    """Fetch repo star map from Gitee (public)."""
    stars = {}
    try:
        data = common.http_json(
            f"https://gitee.com/api/v5/users/{GITEE_OWNER}/repos?per_page=100"
        )
        for repo in data:
            stars[repo["name"]] = repo.get("stargazers_count", 0)
    except Exception as err:  # noqa: BLE001
        print(f"warn: gitee unavailable ({err}); skipped")
    return stars


def gitcode_repos():
    """Fetch repo star map from GitCode (needs GITCODE_TOKEN, else None)."""
    token = os.environ.get("GITCODE_TOKEN", "").strip()
    if not token:
        print("note: GITCODE_TOKEN not set; GitCode stars not refreshed")
        return None
    stars = {}
    try:
        data = common.http_json(
            f"https://api.gitcode.com/api/v5/users/{GC_OWNER}/repos?page=1&per_page=100",
            headers={"private-token": token},
        )
        for repo in data:
            stars[repo["name"]] = repo.get("stargazers_count", 0)
    except Exception as err:  # noqa: BLE001
        print(f"warn: gitcode unavailable ({err}); skipped")
    return stars


def build_stats(stars_by_repo, followers, repo_count):
    """Refresh the STATS block numbers across all four README languages."""
    total_stars = sum(stars_by_repo.values())
    blocks = {
        "en": f"- ⭐ **{total_stars}** stars (max across 4 platforms) &nbsp;·&nbsp; 👥 **{followers}** followers &nbsp;·&nbsp; 📦 **{repo_count}+ repos** (GitCode-based)",
        "zh": f"- ⭐ **{total_stars}** stars（四平台取最大）&nbsp;·&nbsp; 👥 **{followers}** followers &nbsp;·&nbsp; 📦 **{repo_count}+ 项目**（以 GitCode 为准）",
        "ja": f"- ⭐ **{total_stars}** stars（4プラットフォーム最大値）&nbsp;·&nbsp; 👥 **{followers}** followers &nbsp;·&nbsp; 📦 **{repo_count}+ リポジトリ**（GitCode 基準）",
    }
    return blocks


def replace_star(m, nn):
    return m.group(0)[: m.group(0).rfind("· ")] + "· " + str(nn) + "★"


def refresh_project_stars(text, stars_by_repo):
    """Replace star counts in PROJECTS lines for curated repos."""
    for name in CURATED_PROJECTS:
        n = stars_by_repo.get(name)
        if n is None:
            continue
        # matches: **[name](url)** · 0★ · desc · `tag`
        text = re.sub(
            rf"\*\*\[{re.escape(name)}\]\([^)]*\)\*\* · \d+★",
            lambda m, nn=n: replace_star(m, nn),
            text,
        )
    return text


def update_block(text, kind, content):
    """Replace a <!-- KIND:START -->…<!-- KIND:END --> region."""
    return re.sub(
        rf"(<!-- {kind}:START -->).*?(<!-- {kind}:END -->)",
        lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}",
        text,
        flags=re.S,
    )


# Known stars (verified 2026-09-18); acts as a floor when a platform is
# temporarily unreachable so the aggregate never dips below real-world counts.
KNOWN_FALLBACK = {
    "bot4cj": 6,
    "awesome-skillkit": 3,
    "mobilecode": 1,
    "scholarhub": 1,
    "网安智能体": 1,
}


def main():
    # 1) Collect star maps from every reachable platform.
    maps = []
    for account in GH_ACCOUNTS:
        try:
            maps.append(gh_repos(account))
            print(f"github {account}: ok")
        except Exception as err:  # noqa: BLE001
            print(f"warn: github {account} unavailable ({err})")
    try:
        maps.append(gitee_repos())
    except Exception as err:  # noqa: BLE001
        print(f"warn: gitee unavailable ({err})")
    gc = gitcode_repos()
    if gc:
        maps.append(gc)

    if not maps:
        print("no platform data at all, keeping existing blocks")
        return

    # 2) Aggregate: per project, take the max star count seen anywhere.
    #    Known curated stars act as a floor so transient API gaps never
    #    erase a project's verified count.
    stars_by_repo = {k: v for k, v in KNOWN_FALLBACK.items()}
    for m in maps:
        for name, n in m.items():
            stars_by_repo[name] = max(stars_by_repo.get(name, 0), n)

    # 3) Followers: max across GitHub accounts (public).
    followers = 0
    for account in GH_ACCOUNTS:
        try:
            user = common.http_json(
                f"https://api.github.com/users/{account}",
                headers=_gh_headers(),
            )
            followers = max(followers, user.get("followers", 0))
        except Exception:  # noqa: BLE001
            pass

    # 4) Repo count: GitCode when available (it is the primary mirror), else the
    #    largest count seen on any platform.
    repo_count = len(gc) if gc else max(len(m) for m in maps)

    stats_blocks = build_stats(stars_by_repo, followers, repo_count)
    for name in README_FILES:
        lang = {"README.md": "en", "README.zh.md": "zh", "README.ja.md": "ja"}[name]
        path = os.path.join(common.ROOT, name)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        text = update_block(text, "STATS", stats_blocks[lang])
        text = refresh_project_stars(text, stars_by_repo)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print("STATS refreshed (repo count, stars, followers) across 4 platforms")


if __name__ == "__main__":
    main()