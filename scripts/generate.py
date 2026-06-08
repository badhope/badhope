#!/usr/bin/env python3
"""
Generate / refresh the auto-updating parts of the GitHub profile READMEs.

Sections that are AUTO-REFRESHED (daily by GitHub Actions):
  - Repository constellation (sorted by stars)
  - CSDN latest dispatches
  - Daily reflection (one quote per day)

The script reads README.md / README.zh-CN.md as templates and rewrites the
content delimited by <!-- AUTO:SECTION_NAME:START --> ... <!-- AUTO:SECTION_NAME:END -->
markers. Everything outside the markers is preserved verbatim.

Stdlib-only on purpose — no pip dependency required in the runner.
"""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

ROOT          = Path(__file__).resolve().parent.parent
README_EN     = ROOT / "README.md"
README_ZH     = ROOT / "README.zh-CN.md"
GITHUB_API    = "https://api.github.com"
CSDN_RSS_TPL  = "https://blog.csdn.net/{user}/rss/list"
QUOTE_APIS    = [
    # (url, kind) — kind is "quotable" or "zenquotes"
    ("https://api.quotable.io/random", "quotable"),
    ("https://zenquotes.io/api/random", "zenquotes"),
]
UA            = "badhope-profile-bot/1.0 (+https://github.com/badhope)"

GH_USER       = os.environ.get("GH_USER", "badhope")
CSDN_USER     = os.environ.get("CSDN_USER", "weixin_56622231")
QUOTE_API     = os.environ.get("QUOTE_API", QUOTE_APIS[0][0])

FETCH_TIMEOUT = 15  # seconds

# Repositories to always exclude (e.g. the profile README repo itself).
EXCLUDED_REPOS: set[str] = set()

# ──────────────────────────────────────────────────────────────────────────────
# Tiny HTTP helper
# ──────────────────────────────────────────────────────────────────────────────

def http_get(url: str, *, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, application/rss+xml, text/xml, */*",
        **(headers or {}),
    })
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        return r.read()

def http_get_json(url: str, *, headers: dict | None = None):
    return json.loads(http_get(url, headers=headers))

# ──────────────────────────────────────────────────────────────────────────────
# GitHub: repos + user meta
# ──────────────────────────────────────────────────────────────────────────────

def fetch_all_repos(user: str) -> list[dict]:
    """Paginated fetch of all public, non-fork, non-archived repos."""
    repos: list[dict] = []
    page = 1
    while True:
        url = f"{GITHUB_API}/users/{user}/repos?per_page=100&page={page}&type=owner&sort=updated"
        try:
            chunk = http_get_json(url, headers={"Accept": "application/vnd.github+json"})
        except urllib.error.HTTPError as e:
            print(f"[github] HTTP {e.code} on page {page}: {e.reason}", file=sys.stderr)
            break
        if not chunk:
            break
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
        if page > 8:    # safety cap = 800 repos
            break
    # also exclude the profile repo (username == repo name)
    EXCLUDED_REPOS.add(GH_USER)
    return [
        r for r in repos
        if not r.get("fork") and not r.get("archived")
        and r.get("name") not in EXCLUDED_REPOS
    ]


def language_emoji(lang: str | None) -> str:
    L = (lang or "").lower()
    return {
        "python": "🐍", "typescript": "🟦", "javascript": "🟨", "rust": "🦀",
        "go": "🐹", "java": "☕", "c++": "➕", "c": "🔷", "ruby": "💎",
        "swift": "🦅", "kotlin": "🟪", "vue": "🟩", "shell": "🐚", "tex": "📜",
    }.get(L, "✦")


# ──────────────────────────────────────────────────────────────────────────────
# CSDN: latest articles
# ──────────────────────────────────────────────────────────────────────────────

def fetch_csdn_latest(user: str, limit: int = 5) -> list[dict]:
    """Return list of {title, link, pubDate}."""
    url = CSDN_RSS_TPL.format(user=user)
    try:
        raw = http_get(url)
    except Exception as e:
        print(f"[csdn] failed: {e}", file=sys.stderr)
        return []

    # strip default namespace to keep xpath simple
    text = raw.decode("utf-8", errors="replace").replace('xmlns="http://www.w3.org/2005/Atom"', "")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        print(f"[csdn] parse error: {e}", file=sys.stderr)
        return []

    items: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link")  or "").strip()
        pub   = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "pubDate": pub})
        if len(items) >= limit:
            break
    return items


# ──────────────────────────────────────────────────────────────────────────────
# Daily quote
# ──────────────────────────────────────────────────────────────────────────────

def fetch_quote() -> dict:
    """Return {text, author}."""
    for api in [QUOTE_API] + [u for u, _ in QUOTE_APIS if u != QUOTE_API]:
        try:
            raw = http_get(api).decode("utf-8", errors="replace")
            data = json.loads(raw)
            if api.endswith("quotable.io/random"):
                return {
                    "text":   data.get("content", "").strip(),
                    "author": (data.get("author") or "").strip(),
                }
            if api.endswith("zenquotes.io/api/random"):
                if isinstance(data, list) and data:
                    return {"text": data[0].get("q", "").strip(),
                            "author": (data[0].get("a") or "").strip()}
        except Exception as e:
            print(f"[quote] {api} failed: {e}", file=sys.stderr)
    return {"text": "The only way to do great work is to love what you do.",
            "author": "Steve Jobs"}


# ──────────────────────────────────────────────────────────────────────────────
# Render blocks
# ──────────────────────────────────────────────────────────────────────────────

def render_repos(repos: list[dict], lang: str = "en") -> str:
    """Markdown block of all public repos, sorted by stars desc."""
    if not repos:
        return "_No data yet — the next refresh will populate this._"

    lines: list[str] = []
    for r in sorted(repos, key=lambda x: (-(x.get("stargazers_count") or 0),
                                          x.get("name", "").lower())):
        name   = r.get("name", "")
        desc   = (r.get("description") or "").strip().replace("\n", " ")
        url    = r.get("html_url", "#")
        stars  = r.get("stargazers_count", 0) or 0
        forks  = r.get("forks_count", 0) or 0
        lang_  = r.get("language") or "—"
        emoji  = language_emoji(lang_)
        topics = r.get("topics") or []
        topic_str = "  ".join(f"`{t}`" for t in topics[:4])

        if lang == "zh":
            meta = f"{emoji} **{lang_}** · ⭐ {stars} · ⑂ {forks}"
        else:
            meta = f"{emoji} **{lang_}** · ⭐ {stars} · ⑂ {forks}"

        lines.append(f"### [{name}]({url})  {meta}")
        if desc:
            lines.append(desc)
        if topic_str:
            lines.append(topic_str)
        lines.append("")
    return "\n".join(lines).rstrip()


def render_featured(repos: list[dict], n: int = 6, lang: str = "en") -> str:
    """Compact list of top N repos by stars — each entry is a big h3 with a styled sub-line."""
    if not repos:
        return "_No data yet._"
    top = sorted(repos, key=lambda x: (-(x.get("stargazers_count") or 0),
                                       x.get("name", "").lower()))[:n]
    lines: list[str] = []
    for r in top:
        name  = r.get("name", "")
        url   = r.get("html_url", "#")
        desc  = (r.get("description") or "").strip().replace("\n", " ")
        stars = r.get("stargazers_count", 0) or 0
        lang_ = r.get("language") or "—"
        emoji = language_emoji(lang_)
        if not desc:
            desc = "—"
        desc = _truncate(desc, 110)
        lines.append(
            f'<h3 style="font-size:21px;font-weight:700;letter-spacing:0.3px;margin:18px 0 6px">'
            f'<a href="{url}" style="color:#c4b5fd;text-decoration:none">{name}</a> '
            f'<span style="font-size:15px;font-weight:500;color:#fbbf24;letter-spacing:0.4px">⭐ {stars}</span> '
            f'<span style="font-size:14px;font-weight:500;color:#a5b4fc">{emoji} {lang_}</span>'
            f'</h3>\n'
            f'<p style="font-size:15px;line-height:1.65;color:#d1d5ff;margin:0 0 8px;max-width:820px">{desc}</p>'
        )
    return "\n\n".join(lines)


# ── Card styling tokens (kept inline because GitHub sanitises <style>) ──────
_CARD_BG     = "background:linear-gradient(135deg,rgba(167,139,250,0.10) 0%,rgba(30,27,75,0.40) 60%,rgba(49,46,129,0.20) 100%);"
_CARD_BORDER = "border:1px solid rgba(167,139,250,0.30);"
_CARD_RADIUS = "border-radius:10px;"
_CARD_PAD    = "padding:16px 18px;"
_CARD_SHADOW = "box-shadow:0 1px 0 rgba(167,139,250,0.05) inset,0 0 24px rgba(30,27,75,0.25);"


def _truncate(text: str, max_len: int) -> str:
    """Truncate at a word boundary that doesn't leave a broken word.

    Specifically: never end with a partial hyphenated word like "single-"
    that looks like an LLM edit. We try to chop the partial word too.
    """
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    sp  = cut.rfind(" ")
    if sp <= max_len // 2:
        return cut.rstrip() + "…"
    result = cut[:sp]
    # If the result has a trailing partial word ending in "-" (e.g. "single-"),
    # chop that word off too.
    while True:
        sp = result.rfind(" ")
        if sp <= 0:
            break
        # the last "word" is result[sp+1:]
        if result[sp+1:].endswith(("-", "–", "—")):
            result = result[:sp]
            continue
        # Also: if the second-to-last word ends with "-" and the last is
        # a connective like "and/or/to", the partial word is dangling.
        prev_sp = result.rfind(" ", 0, sp)
        if prev_sp >= 0 and result[prev_sp+1:sp].endswith(("-", "–", "—")):
            if result[sp+1:].lower() in ("and", "or", "to", "of", "in", "a", "an", "the"):
                result = result[:prev_sp]
                continue
        break
    return result.rstrip(" -–—·•") + "…"


def _card(r: dict) -> str:
    """One repo rendered as a styled 'card' cell for a 3-column table."""
    name   = r.get("name", "")
    url    = r.get("html_url", "#")
    desc   = (r.get("description") or "").strip().replace("\n", " ").replace("|", "\\|")
    stars  = r.get("stargazers_count", 0) or 0
    forks  = r.get("forks_count", 0) or 0
    lang_  = r.get("language") or "—"
    emoji  = language_emoji(lang_)
    topics = r.get("topics") or []

    if not desc:
        desc = "<i style='opacity:0.5'>no description</i>"
    desc = _truncate(desc, 95)

    topic_html = ""
    if topics:
        pills = " ".join(
            f"<span style='font-size:12px;color:#a5b4fc;background:rgba(49,46,129,0.55);"
            f"padding:2px 8px;border-radius:10px;margin-right:4px'>{t}</span>"
            for t in topics[:3]
        )
        topic_html = f"<div style='margin-top:10px;line-height:1.8'>{pills}</div>"

    style = f"{_CARD_BG}{_CARD_BORDER}{_CARD_RADIUS}{_CARD_PAD}{_CARD_SHADOW}"
    return (
        f'<td valign="top" width="33.3%" style="padding:6px">'
        f'<div style="{style}height:200px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">'
        f'<a href="{url}" style="color:#c4b5fd;font-weight:600;font-size:16px;'
        f'text-decoration:none;letter-spacing:0.2px">{name}</a>'
        f'<span style="color:#fbbf24;font-size:14px;white-space:nowrap">⭐ {stars}</span>'
        f'</div>'
        f'<div style="margin-top:5px;font-size:13px;color:#a5b4fc;letter-spacing:0.4px">'
        f'{emoji} {lang_}  ·  ⑂ {forks}</div>'
        f'<div style="margin-top:10px;font-size:14px;color:#d1d5ff;line-height:1.55">'
        f'{desc}</div>'
        f'{topic_html}'
        f'</div>'
        f'</td>'
    )


def render_repos_grid(repos: list[dict], limit: int = 9) -> str:
    """Top N repos rendered as a 3-column card grid (HTML table)."""
    if not repos:
        return "<i>No data yet — the next refresh will populate this.</i>"
    top = sorted(repos, key=lambda x: (-(x.get("stargazers_count") or 0),
                                       x.get("name", "").lower()))[:limit]
    # pad to multiple of 3 for clean rows
    while len(top) % 3:
        top.append(None)
    rows: list[str] = []
    for i in range(0, len(top), 3):
        cells = []
        for r in top[i:i + 3]:
            cells.append(_card(r) if r else '<td width="33.3%" style="padding:6px"></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        'style="border-collapse:separate;border-spacing:0;margin:8px 0 16px">'
        + "".join(rows) +
        "</table>"
    )


def render_repos_longtail(repos: list[dict], skip: int = 9) -> str:
    """Compact pill cloud for repos beyond the grid (flex-wrap so it reflows)."""
    if not repos:
        return ""
    tail = sorted(repos, key=lambda x: (-(x.get("stargazers_count") or 0),
                                         x.get("name", "").lower()))[skip:]
    if not tail:
        return ""
    pills: list[str] = []
    for r in tail:
        name  = r.get("name", "")
        url   = r.get("html_url", "#")
        stars = r.get("stargazers_count", 0) or 0
        lang_ = r.get("language") or "—"
        emoji = language_emoji(lang_)
        pills.append(
            f'<a href="{url}" style="color:#c4b5fd;text-decoration:none;'
            f'background:rgba(49,46,129,0.30);border:1px solid rgba(167,139,250,0.18);'
            f'padding:4px 11px;border-radius:12px;font-size:13px;'
            f'display:inline-block;margin:3px 5px 3px 0;letter-spacing:0;line-height:1.6">'
            f'{name}&nbsp;<span style="color:#fbbf24">⭐ {stars}</span>'
            f'<span style="color:#818cf8;margin-left:5px;font-size:12px">· {emoji} {lang_}</span>'
            f'</a>'
        )
    inner = "".join(pills)
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:0;line-height:2;'
        'margin:4px 0">' + inner + '</div>'
    )


def render_lang_bars(repos: list[dict]) -> str:
    """Horizontal bar chart of language share, sorted descending."""
    if not repos:
        return ""
    counts: dict[str, int] = {}
    for r in repos:
        lg = r.get("language")
        if lg:
            counts[lg] = counts.get(lg, 0) + 1
    if not counts:
        return ""
    total = sum(counts.values())
    rows  = sorted(counts.items(), key=lambda x: -x[1])
    max_w = 22  # bar width in cells
    out: list[str] = ['<div style="font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:14px;line-height:1.85">']
    for name, n in rows:
        bar_len = max(1, round(n / rows[0][1] * max_w))
        bar  = "█" * bar_len
        pct  = round(n / total * 100)
        emoji = language_emoji(name)
        out.append(
            f'<div style="display:flex;align-items:center;gap:12px;margin:3px 0">'
            f'<span style="display:inline-block;width:120px;color:#a5b4fc">{emoji} {name}</span>'
            f'<span style="color:#c4b5fd;letter-spacing:-1px">{bar}</span>'
            f'<span style="color:#a5b4fc;font-size:13px">{n} · {pct}%</span>'
            f'</div>'
        )
    out.append("</div>")
    return "\n".join(out)


def render_topic_cloud(repos: list[dict], top: int = 30) -> str:
    """Topic pill cloud — frequency-weighted, deduplicated."""
    if not repos:
        return ""
    counts: dict[str, int] = {}
    for r in repos:
        for t in (r.get("topics") or []):
            counts[t] = counts.get(t, 0) + 1
    if not counts:
        return ""
    items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:top]
    pills: list[str] = []
    for tag, n in items:
        # size scales with frequency, capped
        size = 13 + min(4, n - 1)   # 13px..17px
        pills.append(
            f'<span style="display:inline-block;font-size:{size}px;'
            f'color:#c4b5fd;background:rgba(49,46,129,0.45);'
            f'padding:4px 11px;border-radius:12px;margin:4px 5px 4px 0;'
            f'border:1px solid rgba(167,139,250,0.18)">'
            f'{tag}<sub style="opacity:0.55;margin-left:4px">×{n}</sub></span>'
        )
    return '<div style="line-height:2">' + "".join(pills) + "</div>"


def render_csdn(items: list[dict], lang: str = "en") -> str:
    if not items:
        return "_No data yet — the next refresh will populate this._"
    out: list[str] = []
    for it in items:
        date = it["pubDate"]
        try:
            # RFC 822 → yyyy-mm-dd
            d = datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %z")
            date_str = d.strftime("%Y-%m-%d")
        except Exception:
            date_str = date or "—"
        title = it["title"]
        link  = it["link"]
        out.append(f"- [`{date_str}`]({link}) — {title}")
    return "\n".join(out)


def render_quote(q: dict) -> str:
    text   = q.get("text", "").strip()
    author = (q.get("author") or "Unknown").strip()
    return f"> *\"{text}\"*\n> \n> — **{author}**"


def render_summary(repos: list[dict], user_meta: dict | None) -> str:
    """A small 'as of today' stat line."""
    total = len(repos)
    stars = sum((r.get("stargazers_count") or 0) for r in repos)
    lang_count: dict[str, int] = {}
    for r in repos:
        lg = r.get("language")
        if lg:
            lang_count[lg] = lang_count.get(lg, 0) + 1
    # Only languages with >= 2 repos are worth showing as "top" —
    # showing single-repo languages as "top" looks misleading.
    significant = sorted(
        ((n, c) for n, c in lang_count.items() if c >= 2),
        key=lambda x: -x[1],
    )[:3]
    if len(significant) < len(lang_count):
        # 4+ languages total: mention there's more.
        more = len(lang_count) - len(significant)
        top_str = ", ".join(f"{n} ({c})" for n, c in significant)
        top_str += f" + {more} more" if significant else f"+ {more} more"
    else:
        top_str = ", ".join(f"{n} ({c})" for n, c in significant) or "—"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (f"_As of {today} UTC — {total} public repos · "
            f"{stars} total ⭐ · top languages: {top_str}._")


# ──────────────────────────────────────────────────────────────────────────────
# Template substitution
# ──────────────────────────────────────────────────────────────────────────────

MARKER_RE = re.compile(
    r"<!--\s*AUTO:([A-Z0-9_]+):START\s*-->\n?(.*?)<!--\s*AUTO:\1:END\s*-->",
    re.DOTALL,
)

def fill_template(text: str, blocks: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return f"<!-- AUTO:{key}:START -->\n{blocks.get(key, '').rstrip()}\n<!-- AUTO:{key}:END -->"
    return MARKER_RE.sub(repl, text)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"[run] starting at {datetime.now(timezone.utc).isoformat()}")
    repos     = fetch_all_repos(GH_USER)
    print(f"[github] fetched {len(repos)} repos for {GH_USER}")

    try:
        user_meta = http_get_json(f"{GITHUB_API}/users/{GH_USER}")
    except Exception as e:
        print(f"[github] user meta failed: {e}", file=sys.stderr)
        user_meta = None

    csdn_items = fetch_csdn_latest(CSDN_USER, limit=5)
    print(f"[csdn] fetched {len(csdn_items)} articles for {CSDN_USER}")

    quote      = fetch_quote()
    print(f"[quote] \"{quote['text'][:40]}…\" — {quote['author']}")

    summary_en = render_summary(repos, user_meta)
    summary_zh = render_summary(repos, user_meta)

    # English
    if README_EN.exists():
        en = README_EN.read_text(encoding="utf-8")
        en = fill_template(en, {
            "SUMMARY":      summary_en,
            "FEATURED":     render_featured(repos, n=6, lang="en"),
            "REPOS_GRID":   render_repos_grid(repos, limit=9),
            "REPOS_TAIL":   render_repos_longtail(repos, skip=9),
            "LANG_BARS":    render_lang_bars(repos),
            "TOPIC_CLOUD":  render_topic_cloud(repos, top=30),
            "REPOS":        render_repos(repos, lang="en"),
            "CSDN":         render_csdn(csdn_items, lang="en"),
            "QUOTE":        render_quote(quote),
            "QUOTE_AUTHOR": quote.get("author", ""),
        })
        README_EN.write_text(en, encoding="utf-8")
        print(f"[write] {README_EN.relative_to(ROOT)}")
    else:
        print(f"[skip] {README_EN} not found", file=sys.stderr)

    # Chinese
    if README_ZH.exists():
        zh = README_ZH.read_text(encoding="utf-8")
        zh = fill_template(zh, {
            "SUMMARY":      summary_zh,
            "FEATURED":     render_featured(repos, n=6, lang="zh"),
            "REPOS_GRID":   render_repos_grid(repos, limit=9),
            "REPOS_TAIL":   render_repos_longtail(repos, skip=9),
            "LANG_BARS":    render_lang_bars(repos),
            "TOPIC_CLOUD":  render_topic_cloud(repos, top=30),
            "REPOS":        render_repos(repos, lang="zh"),
            "CSDN":         render_csdn(csdn_items, lang="zh"),
            "QUOTE":        render_quote(quote),
            "QUOTE_AUTHOR": quote.get("author", ""),
        })
        README_ZH.write_text(zh, encoding="utf-8")
        print(f"[write] {README_ZH.relative_to(ROOT)}")
    else:
        print(f"[skip] {README_ZH} not found", file=sys.stderr)

    print("[run] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
