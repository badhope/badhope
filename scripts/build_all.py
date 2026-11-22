#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render all five profiles with one generator.

    python3 scripts/build_all.py --out dist

Each account gets its own directory containing README + SVG assets, built
from the same build.py and the same contribution/project snapshot. This is
the single-source counterpart to scripts/mirror-shared.sh: the mirror pushes
the shared layer, this proves every target can be rendered before pushing.
"""

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# GitCode images live behind jsDelivr; pin them to this source commit so a
# branch cache cannot serve the previous star chart after a design change.
if not os.environ.get("PROFILE_ASSET_COMMIT"):
    try:
        os.environ["PROFILE_ASSET_COMMIT"] = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        pass

import build  # noqa: E402

ACCOUNTS = [
    "gh_badhope",
    "gh_x33834",
    "gh_morningstar",
    "gitee_badhope",
    "gitcode_badhope",
]


def render(account, out_root):
    out = pathlib.Path(out_root) / account
    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)

    profile = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    profile["account"] = account
    (out / "profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy(ROOT / "data" / "stats.json", out / "data" / "stats.json")

    old_root, old_assets = build.ROOT, build.ASSETS
    build.ROOT, build.ASSETS = out, out / "assets"
    try:
        return build.build(account)
    finally:
        build.ROOT, build.ASSETS = old_root, old_assets


def main(argv=None):
    ap = argparse.ArgumentParser(description="render every profile account")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "dist")
    args = ap.parse_args(argv)

    for account in ACCOUNTS:
        outputs = render(account, args.out)
        print("%-16s %s" % (account, ", ".join(outputs)))


if __name__ == "__main__":
    sys.exit(main())
