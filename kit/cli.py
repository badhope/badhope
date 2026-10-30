# -*- coding: utf-8 -*-
"""命令行入口：generate / verify / rasterize 之外的构建命令统一走这里。

    python -m kit gen [--account KEY] [--here] [--assets-only] [--out DIR]
    python -m kit preview [--out DIR]
    python -m kit pack KEY [--out DIR]
    python -m kit all [--out DIR]
"""

import argparse
import pathlib
import sys

import accounts as A

from .build import generate_accounts, here
from .data import load_stats
from .pack import pack
from .paths import ROOT
from .preview import build_preview


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kit", description="profile kit builder")
    parser.add_argument("command", nargs="?", default="gen",
                        choices=["gen", "all", "preview", "pack", "here"])
    parser.add_argument("--account", metavar="KEY", help="generate one account")
    parser.add_argument("--out", metavar="DIR", help="output directory")
    parser.add_argument("--assets-only", action="store_true",
                        help="with here: rebuild assets only, keep README untouched")
    parser.add_argument("--jobs", type=int, default=0, help="parallel workers (0 = auto)")
    parser.add_argument("--skip-if-unchanged", action="store_true",
                        help="with here: skip writing when inputs are unchanged")
    args = parser.parse_args(argv)

    try:
        if args.command == "here":
            key = here(pathlib.Path.cwd(), assets_only=args.assets_only,
                       skip_if_unchanged=args.skip_if_unchanged)
            print("regenerated in place: %s" % key)
            return 0
        if args.command == "preview":
            index = build_preview(args.out or (ROOT / "preview"))
            print("preview -> %s" % index)
            return 0
        if args.command == "pack":
            if not args.account or args.account not in A.ACCOUNTS:
                print("pack needs --account (available: %s)" % ", ".join(A.ACCOUNT_ORDER),
                      file=sys.stderr)
                return 1
            path = pack(args.account, args.out or (ROOT / "pack" / args.account))
            print("packed %s -> %s" % (args.account, path))
            return 0
        keys = list(A.ACCOUNT_ORDER)
        if args.account:
            if args.account not in A.ACCOUNTS:
                print("unknown account: %s (available: %s)"
                      % (args.account, ", ".join(keys)), file=sys.stderr)
                return 1
            keys = [args.account]
        out = pathlib.Path(args.out) if args.out else (ROOT / "dist")
        written = generate_accounts(keys, out, load_stats(ROOT / "data" / "stats.json"),
                                    jobs=args.jobs or None)
        print("generated %d accounts -> %s" % (written, out))
        return 0
    except (OSError, KeyError, ValueError) as err:
        print("generation failed: %r" % (err,), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
