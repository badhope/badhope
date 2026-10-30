#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主页面 kit 生成器（兼容入口）。

实现已迁到 `kit/` 包：textutil → icons → cards → readme → build → pack/preview → cli。
本文件只保留旧的命令行参数与函数级 API（`generate.hero_svg` 等），
既有部署脚本、CI 与镜像作业无需修改。

新代码请直接使用：

    python -m kit all --out dist
    python -m kit here --assets-only
    python -m kit preview
    python -m kit pack gitcode_badhope
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import accounts as A  # noqa: E402
from kit.build import generate_accounts, generate_to, here, write_account_files  # noqa: E402
from kit.cards import (activity_svg, dipper, footer_svg, hero_svg,  # noqa: E402,F401
                       live_badges, skills_svg, starfield, stats_svg, works_svg)
from kit.config import (CARD_NAMES, PLATFORM_LABEL, SNAKE_NAMES,  # noqa: E402,F401
                        STAT_FIELDS, WORKS_LIMIT)
from kit.data import (acct_stats, cards_dir_for, load_card_seed,  # noqa: E402,F401
                      load_stats, load_works, load_writing_items,
                      _snake_available)
from kit.icons import copy_icon_light, icon_svg_body  # noqa: E402,F401
from kit.pack import PACK_EXTRAS, PACK_GITIGNORE, _has_mirror, pack  # noqa: E402,F401
from kit.paths import ROOT as KIT_ROOT  # noqa: E402,F401
from kit.preview import (LOCALIZE_BADGES, PREVIEW_FALLBACK, PREVIEW_TPL,  # noqa: E402,F401
                         _preview_panel, build_preview, md_line_html,
                         md_to_html, repl_static, strip_preview_dupes)
from kit.readme import pr_links, render_contrib, render_readme  # noqa: E402,F401
from kit.textutil import (_stats_month, clip_text, clip_w, esc,  # noqa: E402,F401
                          fmt_num, rng, seed_of, text_w)


def main(argv=None):
    parser = argparse.ArgumentParser(description="主页面 kit generator")
    parser.add_argument("--all", action="store_true", help="generate all accounts")
    parser.add_argument("--account", metavar="KEY", help="generate one account")
    parser.add_argument("--pack", metavar="KEY", help="write a deployable repo tree")
    parser.add_argument("--here", action="store_true", help="regenerate in current dir (needs profile.json)")
    parser.add_argument("--assets-only", action="store_true",
                        help="with --here: rebuild assets only, keep README untouched")
    parser.add_argument("--preview", action="store_true", help="build dist/ + preview/index.html")
    parser.add_argument("--out", metavar="DIR", help="output directory")
    parser.add_argument("--jobs", type=int, default=0, help="parallel workers (0 = auto)")
    parser.add_argument("--skip-if-unchanged", action="store_true",
                        help="with --here: skip writing when inputs are unchanged")
    args = parser.parse_args(argv)

    try:
        if args.pack:
            if args.pack not in A.ACCOUNTS:
                print("unknown account: %s (available: %s)"
                      % (args.pack, ", ".join(A.ACCOUNT_ORDER)), file=sys.stderr)
                return 1
            out = args.out or (ROOT / "pack" / args.pack)
            path = pack(args.pack, out)
            print("packed %s -> %s" % (args.pack, path))
            return 0
        if args.here:
            key = here(pathlib.Path.cwd(), assets_only=args.assets_only,
                       skip_if_unchanged=args.skip_if_unchanged)
            print("regenerated in place: %s" % key)
            return 0
        if args.preview:
            index = build_preview(args.out or (ROOT / "preview"))
            print("preview -> %s" % index)
            return 0
        keys = list(A.ACCOUNT_ORDER)
        if args.account:
            if args.account not in A.ACCOUNTS:
                print("unknown account: %s (available: %s)"
                      % (args.account, ", ".join(keys)), file=sys.stderr)
                return 1
            keys = [args.account]
        elif not args.all:
            parser.print_help()
            return 1
        base = pathlib.Path(args.out) if args.out else (ROOT / "dist")
        written = generate_accounts(keys, base, load_stats(ROOT / "data" / "stats.json"),
                                    jobs=args.jobs or None)
        print("generated %d accounts -> %s" % (written, base))
        return 0
    except (OSError, KeyError, ValueError) as err:
        print("generation failed: %r" % (err,), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
