#!/usr/bin/env python3
"""Shared plumbing for the profile automation scripts (single source of truth)."""

import json
import os
import re
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
README_FILES = ("README.md", "README.zh.md", "README.ja.md")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def http(
    url,
    method="GET",
    payload=None,
    headers=None,
    timeout=30,
    retries=1,
    allow_404=False,
):
    """HTTP helper returning decoded text. Retries transient failures;
    returns None on 404 when allow_404 is set."""
    body = json.dumps(payload).encode() if payload is not None else None
    hdrs = {"User-Agent": UA, **(headers or {})}
    if body is not None:
        hdrs.setdefault("Content-Type", "application/json")
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as err:
            if err.code == 404 and allow_404:
                return None
            last = err
        except Exception as err:  # noqa: BLE001 - network noise is retried below
            last = err
        if attempt + 1 < retries:
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{method} {url} failed after {retries} tries: {last}")


def http_json(url, **kwargs):
    return json.loads(http(url, **kwargs))


def github_api(path, token, **kwargs):
    """Authenticated call against api.github.com."""
    return http_json(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        **kwargs,
    )


def update_all_readmes(blocks):
    """Rewrite <!-- NAME:START -->…<!-- NAME:END --> regions in every README.
    Returns the list of files that changed."""
    touched = []
    for name in README_FILES:
        path = os.path.join(ROOT, name)
        with open(path, encoding="utf-8") as fh:
            original = fh.read()
        text = original
        for kind, content in blocks.items():
            text = re.sub(
                rf"(<!-- {kind}:START -->).*?(<!-- {kind}:END -->)",
                lambda m, c=content: f"{m.group(1)}\n{c}\n{m.group(2)}",
                text,
                flags=re.S,
            )
        if text != original:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            touched.append(name)
    print("updated:", ", ".join(touched) if touched else "nothing (already current)")
    return touched
