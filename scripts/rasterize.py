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
import xml.etree.ElementTree as ET

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


def discover_targets(key, build_root=None):
    if key not in A.ACCOUNTS:
        return []
    assets = pathlib.Path(build_root or ROOT) / "assets"
    if not assets.is_dir():
        return []
    return sorted(path for path in assets.rglob("*.svg") if path.is_file())


def svg_dimensions(svg_path):
    root = ET.parse(svg_path).getroot()
    viewbox = root.get("viewBox", "").replace(",", " ").split()
    if len(viewbox) == 4:
        width, height = float(viewbox[2]), float(viewbox[3])
    else:
        width = float(root.get("width", "0").removesuffix("px"))
        height = float(root.get("height", "0").removesuffix("px"))
    if width <= 0 or height <= 0 or width > 8192 or height > 8192:
        raise ValueError("invalid SVG dimensions")
    return round(width), round(height)


def rasterize(browser, svg_path, png_path):
    png_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = svg_dimensions(svg_path)
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-extensions",
        "--force-device-scale-factor=%d" % SCALE,
        "--window-size=%d,%d" % (width, height),
        "--screenshot=%s" % png_path,
        svg_path.resolve().as_uri(),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not png_path.is_file() or png_path.stat().st_size == 0:
        raise RuntimeError("browser produced no PNG: %s" % (result.stderr or result.stdout))
    return png_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="rasterize profile SVGs to PNG")
    ap.add_argument("--account", help="only this account key")
    ap.add_argument("--all-cards", action="store_true",
                    help="rasterize every card SVG, not just hero")
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
        if args.all_cards:
            with tempfile.TemporaryDirectory() as tmp:
                from kit.build import write_account_files
                from kit.data import load_stats
                build_root = pathlib.Path(tmp)
                write_account_files(A.ACCOUNTS[key], key, build_root,
                                    load_stats(ROOT / "data" / "stats.json"))
                for svg_path in discover_targets(key, build_root):
                    relative = svg_path.relative_to(build_root / "assets")
                    dst = ROOT / "assets" / "png" / key / relative.with_suffix(".png")
                    rasterize(browser, svg_path, dst)
                    old, new = optimize_file(dst)
                    print("rasterized %s -> %s (%d -> %d bytes)"
                          % (key, dst.relative_to(ROOT), old, new))
            continue
        else:
            sources = []
        if not sources:
            svg = hero_svg(A.ACCOUNTS[key])
            with tempfile.TemporaryDirectory() as tmp:
                svg_path = pathlib.Path(tmp) / "hero.svg"
                svg_path.write_text(svg, encoding="utf-8", newline="\n")
                dst = ROOT / "assets" / "png" / key / "hero.png"
                rasterize(browser, svg_path, dst)
                old, new = optimize_file(dst)
            print("rasterized %s -> %s (%d -> %d bytes)" % (key, dst.relative_to(ROOT), old, new))
            continue
        for svg_path in sources:
            if not svg_path.is_file():
                continue
            dst = ROOT / "assets" / "png" / key / (svg_path.stem + ".png")
            rasterize(browser, svg_path, dst)
            old, new = optimize_file(dst)
            print("rasterized %s -> %s (%d -> %d bytes)"
                  % (key, dst.relative_to(ROOT), old, new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
