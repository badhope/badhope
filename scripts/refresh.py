#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""刷新 data/stats.json 与 data/writing.json —— kit 里唯一联网的组件（生成器从不联网）。

用法：
  python scripts/refresh.py                # 刷新五个账号的统计数字
  python scripts/refresh.py --check-links  # 在线校验 accounts.py 里的全部链接

数据源均为公开 API；失败一律保留旧值（绝不删除已有数据）：
- GitHub : api.github.com          —— 可选 GITHUB_TOKEN / GH_TOKEN / GH_<账号>_TOKEN 提高额度
- Gitee  : gitee.com/api/v5        —— 公开接口（有 token 时用 Authorization: token 头提额）
- GitCode: api.gitcode.com         —— 需 token，缺省时跳过

凭据来源优先级：账号专属环境变量（含凭据库记录的变量名）→ 本机凭据库
`~/.zcode/secrets/accounts.json`（可用 PROFILE_KIT_SECRETS 指定路径）→ 通用环境变量。
本库不存在时静默降级，CI 上照常可用。token 只在内存中传递、不进 URL。
"""

import argparse
import datetime
import email.utils
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import accounts as A  # noqa: E402

UA = "profile-kit-refresh/1.0"
STATS_PATH = ROOT / "data" / "stats.json"
STAT_FIELDS = ("repos", "stars", "followers", "merged")

# 网络/解析失败的收窄捕获集合（refresh 对每个数据源失败软处理，绝不整体崩溃）
NETWORK_ERRORS = (urllib.error.URLError, OSError, ValueError, ET.ParseError)

WRITING_PATH = ROOT / "data" / "writing.json"
CSDN_RSS = "https://blog.csdn.net/weixin_56622231/rss/list"

# 账号专属环境变量的平台前缀：GH_<HANDLE>_TOKEN / GITEE_<HANDLE>_TOKEN / GITCODE_<HANDLE>_TOKEN
PLATFORM_ENV_PREFIX = {"github": "GH", "gitee": "GITEE", "gitcode": "GITCODE"}


def http_json(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def warn(msg):
    print("warn: %s" % msg)
    return None


SECRETS_FILE = pathlib.Path(
    os.environ.get("PROFILE_KIT_SECRETS", "").strip()
    or (pathlib.Path.home() / ".zcode" / "secrets" / "accounts.json")
)


def _load_store():
    """本机凭据库（可选）。读不到/解析失败时返回空 dict —— 刷新照常降级运行。"""
    try:
        return json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def resolve_token(platform, handle, generic_env=()):
    """凭据解析顺序：账号专属环境变量（含库中记录的变量名）→ 本机凭据库 → 通用环境变量。

    账号专属变量按平台加前缀（GH_/GITEE_/GITCODE_），因为 badhope 在三个平台同名，
    共用 GH_<HANDLE>_TOKEN 会让 Gitee/GitCode 抢到 GitHub 的令牌。
    token 只在内存中传递；不要在日志/异常消息里拼接含 token 的 URL。
    """
    store = _load_store()
    account = (((store.get("platforms") or {}).get(platform) or {}).get("accounts") or {}).get(handle) or {}
    names = []
    if account.get("env"):
        names.append(account["env"])
    names.append("%s_%s_TOKEN" % (PLATFORM_ENV_PREFIX.get(platform, platform.upper()), handle.upper()))
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    stored = (account.get("token") or "").strip()
    if stored:
        return stored
    for name in generic_env:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def gh_headers(handle):
    token = resolve_token("github", handle, generic_env=("GITHUB_TOKEN", "GH_TOKEN"))
    return {"Authorization": "Bearer " + token} if token else {}


def refresh_github(handle, block):
    try:
        user = http_json("https://api.github.com/users/%s" % handle, gh_headers(handle))
        block["repos"] = user.get("public_repos", block.get("repos"))
        block["followers"] = user.get("followers", block.get("followers"))
        print("github %s: repos=%s followers=%s" % (handle, block.get("repos"), block.get("followers")))
    except NETWORK_ERRORS as err:
        warn("github profile %s unavailable (%s); keeping old values" % (handle, err))
    stars = 0
    got = False
    try:
        page = 1
        while True:
            repos = http_json(
                "https://api.github.com/users/%s/repos?per_page=100&page=%d" % (handle, page),
                gh_headers(handle),
            )
            if not isinstance(repos, list):
                raise ValueError("unexpected repos payload: %r" % (type(repos),))
            # 空列表说明"确实没有仓库"——必须视为成功并清零，否则删除仓库后星数永远不降
            got = True
            for repo in repos:
                # 与 GitHub 个人页口径一致：fork 的 star 不计入本人获星
                if repo.get("fork"):
                    continue
                stars += repo.get("stargazers_count", 0)
            if len(repos) < 100:
                break
            page += 1
        if got:
            block["stars"] = stars
            print("github %s: total stars=%d" % (handle, stars))
    except NETWORK_ERRORS as err:
        warn("github repos %s unavailable (%s); keeping old stars" % (handle, err))
    try:
        found = http_json(
            "https://api.github.com/search/issues"
            "?q=author:%s+type:pr+is:merged+-user:%s&per_page=1" % (handle, handle),
            gh_headers(handle),
        )
        block["merged"] = found.get("total_count", block.get("merged"))
        print("github %s: upstream merged PRs=%s" % (handle, block.get("merged")))
    except NETWORK_ERRORS as err:
        warn("github search %s unavailable (%s); keeping old merged count" % (handle, err))


def refresh_gitee(owner, block):
    token = resolve_token("gitee", owner, generic_env=("GITEE_TOKEN",))
    headers = {"Authorization": "token " + token} if token else None
    try:
        repos = []
        page = 1
        while True:
            batch = http_json(
                "https://gitee.com/api/v5/users/%s/repos?per_page=100&page=%d" % (owner, page),
                headers,
            )
            if not isinstance(batch, list):
                raise ValueError("unexpected repos payload")
            repos += batch
            if len(batch) < 100:
                break
            page += 1
        block["repos"] = len(repos)
        block["stars"] = sum(r.get("stargazers_count", 0) for r in repos)
        print("gitee %s: repos=%s stars=%s" % (owner, block["repos"], block["stars"]))
    except NETWORK_ERRORS as err:
        warn("gitee %s unavailable (%s); keeping old values" % (owner, err))
        return
    try:
        user = http_json("https://gitee.com/api/v5/users/%s" % owner, headers)
        if isinstance(user, dict) and user.get("followers") is not None:
            block["followers"] = user["followers"]
            print("gitee %s: followers=%s" % (owner, block["followers"]))
    except NETWORK_ERRORS as err:
        warn("gitee profile %s unavailable (%s); keeping old followers" % (owner, err))


def refresh_gitcode(owner, block):
    token = resolve_token("gitcode", owner, generic_env=("GITCODE_TOKEN",))
    if not token:
        warn("no gitcode credential (env or local secrets store); gitcode numbers not refreshed")
        return
    headers = {"Authorization": "Bearer " + token}
    try:
        repos = []
        page = 1
        while True:
            batch = http_json(
                "https://api.gitcode.com/api/v5/users/%s/repos?per_page=100&page=%d" % (owner, page),
                headers,
            )
            if not isinstance(batch, list):
                raise ValueError("unexpected repos payload")
            repos += batch
            if len(batch) < 100:
                break
            page += 1
        block["repos"] = len(repos)
        block["stars"] = sum(r.get("stargazers_count", 0) for r in repos)
        print("gitcode %s: repos=%s stars=%s" % (owner, block["repos"], block["stars"]))
    except NETWORK_ERRORS as err:
        warn("gitcode %s unavailable (%s); keeping old values" % (owner, err))
        return
    try:
        user = http_json("https://api.gitcode.com/api/v5/users/%s" % owner, headers)
        if isinstance(user, dict) and user.get("followers") is not None:
            block["followers"] = user["followers"]
            print("gitcode %s: followers=%s" % (owner, block["followers"]))
    except NETWORK_ERRORS as err:
        warn("gitcode profile %s unavailable (%s); keeping old followers" % (owner, err))


def _fmt_pubdate(raw):
    try:
        return email.utils.parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def merge_writing(rss_items, curated_items, old_items=()):
    """合并三类写作条目 → 归一列表（R13）。

    优先级：curated（人工维护）> rss（本次抓取）> old（上次结果）。
    同一 URL 只保留首次出现的版本；按日期倒序（无日期排最后，稳定）。
    RSS 失败时 curated 与 old 都不丢——fail-closed。
    """
    merged, seen = [], set()
    for it in list(curated_items) + list(rss_items) + list(old_items):
        url = (it.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        merged.append(dict(it))
    merged.sort(key=lambda it: it.get("date") or "", reverse=True)
    return merged


def fetch_writing():
    """抓 CSDN RSS 最新文章，与人工维护的 CURATED_POSTS 合并 → data/writing.json。

    失败保留旧内容；文件总会写出（R13）。
    """
    items = []
    try:
        req = urllib.request.Request(CSDN_RSS, headers={"User-Agent": UA})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
        for it in root.findall(".//item")[:6]:
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            if title and link:
                items.append({
                    "title": title,
                    "url": link,
                    "date": _fmt_pubdate((it.findtext("pubDate") or "").strip()),
                })
        print("writing: fetched %d items (CSDN RSS)" % len(items))
    except NETWORK_ERRORS as err:
        warn("writing feed unavailable (%s); keeping old items" % err)
    old_items = []
    try:
        old_items = json.loads(WRITING_PATH.read_text(encoding="utf-8")).get("items") or []
    except (OSError, ValueError, AttributeError):
        pass
    merged = merge_writing(items, A.CURATED_POSTS, old_items)
    out = {
        "fetched": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "source": "CSDN RSS + curated",
        "items": merged,
    }
    print("writing: %d items total (curated %d + rss %d)" % (
        len(merged), len(A.CURATED_POSTS), len(items)))
    WRITING_PATH.parent.mkdir(parents=True, exist_ok=True)
    WRITING_PATH.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def collect_urls():
    urls = set()
    for acct in A.ACCOUNTS.values():
        urls.add(acct["home"])
    for work in A.WORKS.values():
        for value in work["links"].values():
            if isinstance(value, str):
                urls.add(value)
            else:
                urls.update(value)
    for block in A.CONTRIB["own"].values():
        for repo, url, nums, note in block["merged"] + block["review"]:
            urls.add(url)
    for handle, url in A.GITHUB_ACCOUNTS_FOR_SHARED:
        urls.add(url)
    for label, url, icon in A.WRITING:
        urls.add(url)
    for post in A.CURATED_POSTS:
        urls.add(post["url"])
    return sorted(urls)


def check_links():
    bad = []
    for url in collect_urls():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                status = resp.status
        except urllib.error.HTTPError as err:
            status = err.code
        except NETWORK_ERRORS as err:
            status = str(err)
        state = "ok" if status == 200 else "CHECK"
        if status != 200:
            bad.append((url, status))
        print("[%s] %s -> %s" % (state, url, status))
    if bad:
        print("\n%d link(s) need attention:" % len(bad))
        for url, status in bad:
            print("  - %s -> %s" % (url, status))
        return 1
    print("\nall links reachable.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="refresh profile-kit stats")
    parser.add_argument("--check-links", action="store_true", help="verify every link in accounts.py online")
    args = parser.parse_args(argv)

    if args.check_links:
        return check_links()

    current = {}
    if STATS_PATH.is_file():
        try:
            current = json.loads(STATS_PATH.read_text(encoding="utf-8"))
        except ValueError:
            current = {}
    accounts = current.get("accounts") or {}
    for key in A.ACCOUNT_ORDER:
        block = accounts.setdefault(key, {})
        acct = A.ACCOUNTS[key]
        if acct["platform"] == "github":
            refresh_github(acct["handle"], block)
        elif acct["platform"] == "gitee":
            refresh_gitee(acct["handle"], block)
        elif acct["platform"] == "gitcode":
            refresh_gitcode(acct["handle"], block)
    fetch_writing()
    stats = {
        "as_of": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "source": "scripts/refresh.py",
        "accounts": accounts,
    }
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print("stats written: %s" % STATS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
