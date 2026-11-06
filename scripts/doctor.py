#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Environment and data sanity check (no network)."""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REQUIRED_FILES = [
    "build.py",
    "profile.json",
    "data/stats.json",
    "scripts/generate.py",
    "scripts/verify.py",
    "Makefile",
    "CHANGELOG.md",
]


def main():
    problems = []

    if sys.version_info < (3, 9):
        problems.append("python >= 3.9 required, found %s" % sys.version.split()[0])

    for name in REQUIRED_FILES:
        if not (ROOT / name).exists():
            problems.append("missing file: %s" % name)

    profile = {}
    try:
        profile = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    except ValueError as exc:
        problems.append("profile.json is not valid JSON: %s" % exc)
    account = profile.get("account", "")
    if account and account not in build_copy_accounts():
        problems.append("profile.json points at unknown account: %s" % account)

    stats_path = ROOT / "data" / "stats.json"
    try:
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        if "accounts" not in stats:
            problems.append("data/stats.json has no accounts section")
    except ValueError as exc:
        problems.append("data/stats.json is not valid JSON: %s" % exc)

    if problems:
        for p in problems:
            print("doctor: %s" % p)
        return 1
    print("doctor: ok (account=%s, %d required files present)" % (account, len(REQUIRED_FILES)))
    return 0


def build_copy_accounts():
    import build

    return sorted(build.COPY)


if __name__ == "__main__":
    sys.exit(main())
