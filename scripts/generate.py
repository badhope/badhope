#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate README + SVG assets. Thin wrapper around build.py.

    python3 scripts/generate.py --here            # build in place (CI, mirror)
    python3 scripts/generate.py --skip-if-unchanged
    python3 scripts/generate.py --out <dir>       # build into a scratch dir
"""

import argparse
import hashlib
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

FINGERPRINT_FILE = ROOT / ".build-fingerprint"


def input_fingerprint():
    """Fingerprint of every generator input (build.py, profile.json, stats)."""
    inputs = [ROOT / "build.py", ROOT / "profile.json", ROOT / "data" / "stats.json"]
    h = hashlib.sha256()
    for p in inputs:
        h.update(p.read_bytes() if p.exists() else b"missing")
    return h.hexdigest()


def build_out(target_root, account=None):
    """Build into target_root by temporarily pointing build.ROOT there.

    Generator inputs (profile.json, data/stats.json) are copied in first so
    the scratch build sees the same numbers as the committed tree.
    """
    if account is None:
        account = build.current_account()
    target_root = pathlib.Path(target_root)
    (target_root / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "profile.json", target_root / "profile.json")
    shutil.copy(ROOT / "data" / "stats.json", target_root / "data" / "stats.json")
    old_root = build.ROOT
    old_assets = build.ASSETS
    build.ROOT = target_root
    build.ASSETS = target_root / "assets"
    try:
        return build.build(account)
    finally:
        build.ROOT = old_root
        build.ASSETS = old_assets


def main(argv=None):
    ap = argparse.ArgumentParser(description="profile page generator")
    ap.add_argument("--here", action="store_true", help="build into the repository")
    ap.add_argument("--skip-if-unchanged", action="store_true",
                    help="skip when no generator input changed since last run")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="build into a scratch directory instead")
    args = ap.parse_args(argv)

    if args.out:
        outputs = build_out(args.out)
        for name in outputs:
            print("wrote %s" % (args.out / name))
        return 0

    if args.skip_if_unchanged and FINGERPRINT_FILE.exists():
        if FINGERPRINT_FILE.read_text().strip() == input_fingerprint():
            print("inputs unchanged, skipping")
            return 0

    outputs = build.build()
    FINGERPRINT_FILE.write_text(input_fingerprint())
    for name in outputs:
        print("wrote %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
