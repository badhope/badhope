#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 accounts.py 里的 hero SVG 栅格化为 PNG（README 的 <picture> 兜底）。

用法：
  python scripts/rasterize.py                 # 为全部账号生成 assets/png/<key>/hero.png
  python scripts/rasterize.py --account gitcode_badhope
  python scripts/rasterize.py --check         # 只检查浏览器是否可用

实现：调用本机已有的 Chromium 系浏览器（Edge / Chrome / Chromium）无头截图，
纯 stdlib、不引入 npm / Python 依赖。找不到浏览器时以退出码 3 结束，
调用方可据此跳过 PNG 兜底（README 会自动只引用 SVG）。
"""

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import accounts as A  # noqa: E402
from kit.cards import hero_svg  # noqa: E402
from kit.pngopt import optimize_file  # noqa: E402

VIEW_W, VIEW_H = 1200, 430
SCALE = 2

CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "msedge",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)


def find_browser():
    for cand in CANDIDATES:
        if pathlib.Path(cand).is_file():
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return None


def rasterize(browser, svg_path, png_path):
    png_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-extensions",
        "--force-device-scale-factor=%d" % SCALE,
        "--window-size=%d,%d" % (VIEW_W, VIEW_H),
        "--screenshot=%s" % png_path,
        svg_path.resolve().as_uri(),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not png_path.is_file() or png_path.stat().st_size == 0:
        raise RuntimeError("browser produced no PNG: %s" % (result.stderr or result.stdout))
    return png_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="rasterize hero SVG to PNG")
    ap.add_argument("--account", help="only this account key")
    ap.add_argument("--check", action="store_true", help="only check browser availability")
    args = ap.parse_args(argv)

    browser = find_browser()
    if not browser:
        print("warn: no Chromium-family browser found; skip PNG fallback", file=sys.stderr)
        return 3
    if args.check:
        print("browser: %s" % browser)
        return 0

    keys = [args.account] if args.account else list(A.ACCOUNT_ORDER)
    for key in keys:
        if key not in A.ACCOUNTS:
            print("unknown account: %s" % key, file=sys.stderr)
            return 2
        svg = hero_svg(A.ACCOUNTS[key])
        with tempfile.TemporaryDirectory() as tmp:
            svg_path = pathlib.Path(tmp) / "hero.svg"
            svg_path.write_text(svg, encoding="utf-8", newline="\n")
            dst = ROOT / "assets" / "png" / key / "hero.png"
            rasterize(browser, svg_path, dst)
            old, new = optimize_file(dst)
        print("rasterized %s -> %s (%d -> %d bytes)" % (key, dst.relative_to(ROOT), old, new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
