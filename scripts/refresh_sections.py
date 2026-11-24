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
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

STATS_PATH = ROOT / "data" / "stats.json"
CALENDAR_PATH = ROOT / "data" / "calendar.json"
REPOS_PATH = ROOT / "data" / "repos.json"
CONTRIBUTIONS_PATH = ROOT / "data" / "contributions.json"

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
    """Recompute every GitHub metric that feeds the Numbers card.

    prs = all pull requests authored in the trailing year (GraphQL);
    upstream_merged = merged PRs in other people's repos (Search). The stale
    account entry is replaced wholesale so old fields never linger.
    """
    as_of = today_utc()
    since = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    accounts = stats.setdefault("accounts", {})
    for key, login in GH_ACCOUNTS.items():
        try:
            user = gh_user(login, token)
            owned = gh_owned_repos(login, token)
            data = graphql(
                "https://api.github.com/graphql", token,
                "query($login:String!){ user(login:$login){ contributionsCollection {"
                " totalPullRequestContributions totalCommitContributions } } }",
                {"login": login},
            )
            coll = (data.get("user") or {}).get("contributionsCollection") or {}
            query = "author:%s type:pr is:merged -user:%s created:>=%s" % (login, login, since)
            search = fetch_json_retry(
                "https://api.github.com/search/issues?per_page=1&q="
                + urllib.parse.quote(query, safe=""),
                token,
            )
        except OSError as exc:
            print("skip %s (%s): %s" % (key, login, exc))
            continue
        accounts[key] = {
            "repos": len(owned),
            "followers": user.get("followers"),
            "prs": coll.get("totalPullRequestContributions"),
            "commits": coll.get("totalCommitContributions"),
            "upstream_merged": search.get("total_count"),
            "as_of": as_of,
        }
        print("stats refreshed (%s/%s): prs=%s upstream_merged=%s" % (
            key, login, accounts[key]["prs"], accounts[key]["upstream_merged"]))
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


# ---------------------------------------------------------------------------
# Repo catalog (data/repos.json) — popular cards + language breakdown
# ---------------------------------------------------------------------------


def normalize_repo(entry, name_key="name"):
    description = (entry.get("description") or "").strip()
    return {
        "name": entry.get(name_key) or entry.get("path") or "",
        "description": re.sub(r"\s+", " ", description),
        "language": entry.get("language") or None,
        "stars": int(entry.get("stargazers_count") or 0),
    }


def refresh_github_repos(repos_data, token):
    as_of = today_utc()
    accounts = repos_data.setdefault("accounts", {})
    for key, login in GH_ACCOUNTS.items():
        try:
            owned = gh_owned_repos(login, token)
        except OSError as exc:
            print("skip %s (%s): %s" % (key, login, exc))
            continue
        entries = sorted(
            (normalize_repo(repo) for repo in owned),
            key=lambda r: (-r["stars"], r["name"]),
        )
        accounts[key] = {"source": "github-api", "repos": entries}
        print("repos refreshed (%s/%s): %d" % (key, login, len(entries)))
    repos_data["as_of"] = as_of


# ---------------------------------------------------------------------------
# Upstream pull requests (data/contributions.json pull_requests)
# ---------------------------------------------------------------------------

PULLS_LIMIT = {"github": 6, "mirror": 3}  # mirrors show the same person, shorter list


def normalize_pull(search_item, pull):
    """Merge a Search-API hit with its pulls-API detail into snapshot shape."""
    repo = (search_item.get("repository_url") or "").rsplit("/", 2)
    full_name = "%s/%s" % (repo[-2], repo[-1]) if len(repo) >= 2 else search_item.get("repository_url", "")
    if pull.get("head") and (pull["head"].get("repo") or {}).get("full_name"):
        full_name = pull["head"]["repo"]["full_name"]
    if pull.get("base") and (pull["base"].get("repo") or {}).get("full_name"):
        full_name = pull["base"]["repo"]["full_name"]
    state = pull.get("state") or search_item.get("state") or "closed"
    if pull.get("merged_at") or (search_item.get("pull_request") or {}).get("merged_at"):
        status = "merged"
    elif state == "open":
        status = "open"
    else:
        status = "closed"
    opened = (pull.get("created_at") or search_item.get("created_at") or "")[:10]
    comments = int(search_item.get("comments") or 0) + int(pull.get("review_comments") or 0)
    return {
        "repo": full_name,
        "number": pull.get("number", search_item.get("number")),
        "title": pull.get("title") or search_item.get("title") or "",
        "status": status,
        "opened": opened,
        "merged_at": (pull.get("merged_at") or "")[:10] or None,
        "additions": int(pull.get("additions") or 0),
        "deletions": int(pull.get("deletions") or 0),
        "files": int(pull.get("changed_files") or 0),
        "comments": comments,
    }


def refresh_pulls(contributions, token):
    """Latest upstream PRs per GitHub identity, refreshed from Search + pulls API.

    The mirror accounts re-render badhope's list (same person), truncated to
    PULLS_LIMIT["mirror"]; everything stays inside data/contributions.json and
    the manually curated projects catalog is left untouched.
    """
    since = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    accounts = contributions.setdefault("accounts", {})
    lists = {}
    for key, login in GH_ACCOUNTS.items():
        limit = PULLS_LIMIT["github"]
        try:
            query = "author:%s type:pr -user:%s created:>=%s" % (login, login, since)
            payload = fetch_json_retry(
                "https://api.github.com/search/issues?per_page=%d&page=1&sort=created&order=desc&q=%s"
                % (limit, urllib.parse.quote(query, safe="")),
                token,
            )
            items = payload.get("items") or []
            prs = []
            for item in items[:limit]:
                repo_full = (item.get("repository_url") or "").rsplit("/", 2)
                if len(repo_full) < 2:
                    continue
                owner_name = "%s/%s" % (repo_full[-2], repo_full[-1])
                number = item.get("number")
                try:
                    detail = fetch_json_retry(
                        "https://api.github.com/repos/%s/pulls/%s" % (owner_name, number), token
                    )
                except OSError as exc:
                    print("pull detail skip %s/%s#%s: %s" % (key, owner_name, number, exc))
                    detail = {}
                prs.append(normalize_pull(item, detail))
                time.sleep(0.4)
        except OSError as exc:
            print("skip pulls %s (%s): %s" % (key, login, exc))
            continue
        prs.sort(key=lambda p: p.get("opened", ""), reverse=True)
        lists[key] = prs
        print("pulls refreshed (%s/%s): %d" % (key, login, len(prs)))

    if "gh_badhope" in lists:
        accounts["gh_badhope"]["pull_requests"] = lists["gh_badhope"]
        for mirror in ("gitee_badhope", "gitcode_badhope"):
            if mirror in accounts:
                accounts[mirror]["pull_requests"] = lists["gh_badhope"][: PULLS_LIMIT["mirror"]]
    for key in ("gh_morningstar", "gh_x33834"):
        if key in lists and key in accounts:
            accounts[key]["pull_requests"] = lists[key]
    if lists:
        contributions["as_of"] = today_utc()
        contributions["source"] = "GitHub Search / pulls API snapshot"


def refresh_platform_repos(repos_data, key, token, base_url, detail_url, namespace_type, label, detail=False, cross_fill_from=()):
    """Upsert per-repo entries from a Gitee/GitCode v5 list endpoint.

    `detail=True` additionally fetches each repo individually (detail_url is
    a template with {name}) because the Gitee user-repos list omits the
    language field; a failed detail call keeps the previous entry.
    `cross_fill_from` copies the language of same-named GitHub mirror repos
    (identical code, so identical language) when the platform leaves it null.
    """
    accounts = repos_data.setdefault("accounts", {})
    acc = accounts.setdefault(key, {"source": "%s-api" % label, "repos": []})
    existing = {r["name"]: r for r in acc.get("repos", []) if r.get("name")}
    try:
        listed = platform_repos(base_url, token, namespace_type)
    except OSError as exc:
        print("skip %s: %s" % (label, exc))
        raise
    for entry in listed:
        repo = normalize_repo(entry)
        if repo["name"]:
            existing[repo["name"]] = repo
    if detail:
        for name in sorted(existing):
            if existing[name].get("language"):
                continue
            try:
                full = fetch_json_retry(detail_url.format(name=urllib.parse.quote(name, safe="")), token_param=token)
                existing[name] = normalize_repo(full)
            except OSError as exc:
                print("detail skip %s/%s: %s" % (label, name, exc))
            time.sleep(0.6)
    if cross_fill_from:
        mirrors = {}
        for src in cross_fill_from:
            for r in accounts.get(src, {}).get("repos", []):
                if r.get("language"):
                    mirrors.setdefault(r["name"], r["language"])
        for name, repo in existing.items():
            if not repo.get("language") and name in mirrors:
                repo["language"] = mirrors[name]
    entries = sorted(existing.values(), key=lambda r: (-r["stars"], r["name"]))
    acc["repos"] = entries
    repos_data["as_of"] = today_utc()
    print("repos refreshed (%s): %d" % (key, len(entries)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=["stats", "calendar", "repos", "pulls"], required=True)
    ap.add_argument("--platform", choices=["github", "gitee", "gitcode"], required=True)
    args = ap.parse_args(argv)

    if args.section == "pulls":
        if args.platform != "github":
            ap.error("pulls is a github-only section")
        data = json.loads(CONTRIBUTIONS_PATH.read_text(encoding="utf-8")) if CONTRIBUTIONS_PATH.exists() else {"accounts": {}}
        try:
            refresh_pulls(data, os.environ.get("GITHUB_TOKEN"))
        except OSError as exc:
            print("pulls fetch failed, keeping previous data: %s" % exc)
            return 0
        CONTRIBUTIONS_PATH.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("pulls written: as_of=%s" % data.get("as_of"))
        return 0

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

    if args.section == "repos":
        data = json.loads(REPOS_PATH.read_text(encoding="utf-8")) if REPOS_PATH.exists() else {}
        try:
            if args.platform == "github":
                refresh_github_repos(data, os.environ.get("GITHUB_TOKEN"))
            elif args.platform == "gitee":
                refresh_platform_repos(
                    data, "gitee_badhope", os.environ.get("GITEE_TOKEN"),
                    "https://gitee.com/api/v5/users/badhope/repos",
                    "https://gitee.com/api/v5/repos/badhope/{name}", "personal", "gitee",
                    detail=True, cross_fill_from=("gh_badhope", "gh_morningstar", "gh_x33834"),
                )
            else:
                refresh_platform_repos(
                    data, "gitcode_badhope", os.environ.get("GITCODE_TOKEN"),
                    "https://api.gitcode.com/api/v5/users/badhope/repos",
                    "https://api.gitcode.com/api/v5/repos/badhope/{name}", "user", "gitcode",
                )
        except OSError as exc:
            print("repos fetch failed (%s), keeping previous data: %s" % (args.platform, exc))
            return 0
        REPOS_PATH.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("repos written (%s): as_of=%s" % (args.platform, data.get("as_of")))
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
