#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh the committed stats and contribution snapshots (the only network components).

    python3 scripts/refresh_sections.py --section stats --platform github
    python3 scripts/refresh_sections.py --section stats --platform gitee
    python3 scripts/refresh_sections.py --section stats --platform gitcode
    python3 scripts/refresh_sections.py --section calendar --platform github
    python3 scripts/refresh_sections.py --section calendar --platform gitee
    python3 scripts/refresh_sections.py --section calendar --platform gitcode

Updates data/stats.json (account totals) and data/calendar.json (contribution
days per account). Tokens are read from the environment when present
(GITHUB_TOKEN, GITEE_TOKEN, GITCODE_TOKEN); everything degrades gracefully
offline — a failed calendar fetch keeps the previously accumulated days.
"""

import argparse
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

STATS_PATH = ROOT / "data" / "stats.json"
CALENDAR_PATH = ROOT / "data" / "calendar.json"

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


# ---------------------------------------------------------------------------
# Contribution calendar (data/calendar.json)
# ---------------------------------------------------------------------------

TRAIL_DAYS = 371  # keep ~53 weeks of accumulated event days

GH_CALENDAR_QUERY = (
    "query($login:String!){ user(login:$login){ contributionsCollection {"
    " contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }"
    " totalCommitContributions totalIssueContributions totalPullRequestContributions"
    " totalPullRequestReviewContributions } } }"
)


def today_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def graphql(url, token, query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "token %s" % token,
        }, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("errors"):
        raise OSError("graphql: %s" % payload["errors"][0].get("message", "unknown"))
    return payload.get("data") or {}


def refresh_github_calendar(cal, token):
    """Exact daily contributions for every GitHub account via GraphQL."""
    as_of = today_utc()
    accounts = cal.setdefault("accounts", {})
    for key, login in GH_ACCOUNTS.items():
        try:
            data = graphql(
                "https://api.github.com/graphql", token,
                GH_CALENDAR_QUERY, {"login": login},
            )
            coll = (data.get("user") or {}).get("contributionsCollection") or {}
            weeks = ((coll.get("contributionCalendar") or {}).get("weeks")) or []
        except OSError as exc:
            print("skip %s (%s): %s" % (key, login, exc))
            continue
        days = {}
        for week in weeks:
            for day in week.get("contributionDays") or []:
                days[day["date"]] = int(day.get("contributionCount") or 0)
        accounts[key] = {
            "source": "github-graphql",
            "fetched_at": as_of,
            "days": days,
            "totals": {
                "contributions": (coll.get("contributionCalendar") or {}).get("totalContributions"),
                "commits": coll.get("totalCommitContributions"),
                "issues": coll.get("totalIssueContributions"),
                "pull_requests": coll.get("totalPullRequestContributions"),
                "reviews": coll.get("totalPullRequestReviewContributions"),
            },
        }
        print("calendar refreshed (%s/%s): %d days" % (key, login, len(days)))
    cal["as_of"] = as_of


def prune_days(days):
    """Keep only the trailing TRAIL_DAYS window."""
    if len(days) <= TRAIL_DAYS:
        return days
    cutoff = (datetime.date.today() - datetime.timedelta(days=TRAIL_DAYS)).isoformat()
    return {d: n for d, n in days.items() if d >= cutoff}


def merge_events(cal, key, per_date, source):
    """Fold a best-effort events snapshot into the accumulated day map."""
    acc = cal.setdefault("accounts", {}).setdefault(key, {})
    days = acc.setdefault("days", {})
    for date, count in per_date.items():
        days[date] = max(days.get(date, 0), int(count))
    acc["days"] = prune_days(days)
    acc["source"] = source
    acc["fetched_at"] = today_utc()
    kept = acc["days"]
    acc["totals"] = {
        "events": sum(kept.values()),
        "active_days": sum(1 for n in kept.values() if n),
    }
    print("calendar refreshed (%s): %d dates, %d events" % (key, len(kept), acc["totals"]["events"]))


def fetch_json_retry(url, token=None, token_param=None, attempts=3):
    for attempt in range(attempts):
        try:
            return fetch_json(url, token, token_param)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 403) and attempt < attempts - 1:
                time.sleep(6 * (attempt + 1))
                continue
            raise
        except OSError:
            if attempt < attempts - 1:
                time.sleep(3)
                continue
            raise
    raise OSError("unreachable")


def refresh_gitcode_calendar(cal, token):
    """GitCode exposes only a recent events feed; fold it in, never replace."""
    url = "https://api.gitcode.com/api/v5/users/badhope/events?per_page=100&page=1"
    if token:
        sep = "&" if "?" in url else "?"
        url = "%s%saccess_token=%s" % (url, sep, urllib.parse.quote(token, safe=""))
    payload = fetch_json_retry(url)
    per_date = {}
    for date, batch in (payload.get("events") or {}).items():
        if isinstance(batch, list):
            per_date[date] = max(len(batch), per_date.get(date, 0))
    if not per_date:
        raise OSError("gitcode events: empty payload")
    merge_events(cal, "gitcode_badhope", per_date, "gitcode-events")
    cal["as_of"] = today_utc()


def refresh_gitee_calendar(cal, token):
    """Gitee events feed is rate-limited; retry gently and keep old days on failure."""
    url = "https://gitee.com/api/v5/users/badhope/events?per_page=100&page=1"
    if token:
        sep = "&" if "?" in url else "?"
        url = "%s%saccess_token=%s" % (url, sep, urllib.parse.quote(token, safe=""))
    batch = fetch_json_retry(url)
    if not isinstance(batch, list):
        raise OSError("gitee events: unexpected payload")
    per_date = {}
    for event in batch:
        date = (event.get("created_at") or "")[:10]
        if date:
            per_date[date] = per_date.get(date, 0) + 1
    if not per_date:
        raise OSError("gitee events: empty payload")
    merge_events(cal, "gitee_badhope", per_date, "gitee-events")
    cal["as_of"] = today_utc()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=["stats", "calendar"], required=True)
    ap.add_argument("--platform", choices=["github", "gitee", "gitcode"], required=True)
    args = ap.parse_args(argv)

    if args.section == "stats":
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

    cal = json.loads(CALENDAR_PATH.read_text(encoding="utf-8")) if CALENDAR_PATH.exists() else {}
    try:
        if args.platform == "github":
            refresh_github_calendar(cal, os.environ.get("GITHUB_TOKEN"))
        elif args.platform == "gitee":
            refresh_gitee_calendar(cal, os.environ.get("GITEE_TOKEN"))
        else:
            refresh_gitcode_calendar(cal, os.environ.get("GITCODE_TOKEN"))
    except OSError as exc:
        # Keep the accumulated snapshot; a failed fetch must never wipe history.
        print("calendar fetch failed (%s), keeping previous data: %s" % (args.platform, exc))
        return 0
    CALENDAR_PATH.write_text(json.dumps(cal, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("calendar written (%s): as_of=%s" % (args.platform, cal.get("as_of")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
