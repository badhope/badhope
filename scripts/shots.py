#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用无头浏览器给预览页与各账号 README 截图，供人工核对视觉。

用法：
  python scripts/shots.py                  # 截 preview/index.html 与每个账号的 README
  python scripts/shots.py --account gitcode_badhope
  python scripts/shots.py --check          # 只检查浏览器是否可用

实现与 rasterize.py 同源：调用本机已装的 Chromium 系浏览器，
纯 stdlib、不引 npm / Python 依赖。找不到浏览器时退出码 3。
"""

import argparse
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import accounts as A  # noqa: E402

CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)

VIEWPORT = (1280, 900)


def find_browser():
    for path in CANDIDATES:
        if pathlib.Path(path).is_file():
            return path
    for name in ("msedge", "chrome", "chromium", "google-chrome"):
        found = _which(name)
        if found:
            return found
    return None


def _which(name):
    import shutil
    return shutil.which(name)


def shoot(browser, url, out_png, width, height=None):
    """截图。height 为 None 时先探测页面真实高度，避免底部大片空白。"""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    if height is None:
        height = _page_height(browser, url, width)
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--user-data-dir=%s" % profile,
            "--window-size=%d,%d" % (width, height),
            "--screenshot=%s" % out_png,
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if out_png.is_file():
        from kit.pngtrim import trim_bottom
        trimmed = trim_bottom(out_png)
        if trimmed and trimmed[0] != trimmed[1]:
            print("  trimmed %d -> %d px" % trimmed)
    return out_png.is_file(), (result.stderr or "")[-400:]


def _page_height(browser, url, width, cap=20000):
    """用 --dump-dom 量一次内容高度；失败时给一个保守的默认值。"""
    with tempfile.TemporaryDirectory() as profile:
        cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
               "--no-first-run", "--no-default-browser-check",
               "--user-data-dir=%s" % profile, "--window-size=%d,900" % width,
               "--virtual-time-budget=3000", "--dump-dom", url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return 3000
    # 没有 JS 执行环境可读 scrollHeight，用元素数量的粗估兜底
    dom = result.stdout or ""
    est = 900 + dom.count("<img") * 120 + dom.count("<tr>") * 44 + dom.count("<h2>") * 90
    return max(900, min(cap, est))


def main(argv=None):
    parser = argparse.ArgumentParser(description="screenshot preview and per-account READMEs")
    parser.add_argument("--account", action="append", default=None,
                        help="只截这些账号（可重复）")
    parser.add_argument("--check", action="store_true", help="只检查浏览器是否可用")
    parser.add_argument("--out", default=str(ROOT / "shots"), help="输出目录")
    parser.add_argument("--width", type=int, default=VIEWPORT[0])
    parser.add_argument("--height", type=int, default=None,
                        help="固定高度；默认自动量测页面高度，避免底部留白")
    args = parser.parse_args(argv)

    browser = find_browser()
    if not browser:
        print("no Chromium-family browser found; install Edge/Chrome or skip screenshots",
              file=sys.stderr)
        return 3
    print("browser: %s" % browser)
    if args.check:
        return 0

    out_root = pathlib.Path(args.out)
    keys = args.account or list(A.ACCOUNT_ORDER)
    failed = []

    preview = ROOT / "preview" / "index.html"
    if preview.is_file():
        ok, err = shoot(browser, preview.resolve().as_uri(), out_root / "preview.png",
                        args.width, args.height)
        print("%-18s %s" % ("preview", "ok" if ok else "FAIL"))
        if not ok:
            failed.append(("preview", err))

    for key in keys:
        readme = ROOT / "dist" / key / "README.md"
        if not readme.is_file():
            print("%-18s skipped (run 'make preview' first)" % key)
            continue
        html = _render_standalone(key, readme)
        target = out_root / ("%s.png" % key)
        ok, err = shoot(browser, html.resolve().as_uri(), target, args.width, args.height)
        print("%-18s %s" % (key, "ok" if ok else "FAIL"))
        if not ok:
            failed.append((key, err))

    if failed:
        for name, err in failed:
            print("\n%s stderr tail:\n%s" % (name, err))
        return 1
    return 0


def _render_standalone(key, readme_path):
    """把 dist/<key>/README.md 渲染成可直接打开的 HTML（资产用绝对 file:// 路径）。"""
    from kit.mdrender import render as render_markdown
    from kit.preview import PREVIEW_TPL  # noqa: F401 —— 保持与预览页同一套排版来源

    text = readme_path.read_text(encoding="utf-8")
    body, _engine = render_markdown(text)
    assets = (readme_path.parent / "assets").resolve().as_uri()
    body = body.replace('src="./assets/', 'src="%s/' % assets)
    html = ("<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\">"
            "<title>" + key + "</title><style>body{margin:0;background:#04060E;color:#F4F7FF;"
            "font:16px/1.65 Helvetica,Arial,sans-serif;padding:40px;max-width:1100px;"
            "margin:0 auto}img{max-width:100%}a{color:#F2DC9E}"
            "table{border-collapse:collapse}th,td{padding:6px 12px;"
            "border:1px solid rgba(217,184,118,.2)}</style></head><body>" + body + "</body></html>")
    target = ROOT / "dist" / key / "_standalone.html"
    target.write_text(html, encoding="utf-8", newline="\n")
    return target


if __name__ == "__main__":
    sys.exit(main())
