#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release metadata gate: profile.json kit_version must match CHANGELOG."""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def latest_changelog_version():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
    return m.group(1) if m else None


def main():
    profile = (ROOT / "profile.json").read_text(encoding="utf-8")
    m = re.search(r'"kit_version":\s*"([^"]+)"', profile)
    kit_version = m.group(1) if m else None
    changelog = latest_changelog_version()

    if not kit_version or not changelog:
        print("release: FAIL (kit_version=%r changelog=%r)" % (kit_version, changelog))
        return 1
    if kit_version != changelog:
        print("release: FAIL profile.json kit_version %s != CHANGELOG %s" % (kit_version, changelog))
        return 1
    print("release: ok (v%s)" % kit_version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
