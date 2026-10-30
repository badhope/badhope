# -*- coding: utf-8 -*-
"""构建编排：账号资产/README 写出、增量清单、原地重建、并行生成。"""

import concurrent.futures
import hashlib
import json
import os
import pathlib
import shutil
import sys

import accounts as A

from . import cardset  # noqa: F401  注册内置卡片插件（hero/footer/stats/skills/works/activity/langs）
from .config import SNAKE_NAMES
from .data import _snake_available, cards_dir_for, load_stats, load_works
from .icons import copy_icon_light
from .paths import ROOT
from .plugins import filenames as card_filenames, render_all as render_cards, render_static
from .readme import render_readme
from .textutil import esc
from . import theme as theme_mod

def write_text_atomic(path, text):
    """写入文本：先写临时文件再 rename，避免进程中断留下半截 SVG/README。"""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def write_account_files(acct, key, out_dir, stats, base=None, assets_only=False):
    out = pathlib.Path(out_dir)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "icons").mkdir(parents=True, exist_ok=True)
    (assets / "cards").mkdir(parents=True, exist_ok=True)
    works_data = load_works(base)
    ctx = {"stats": stats, "discovered": works_data, "key": key, "base": base,
           "theme": theme_mod.resolve(acct)}
    wanted = card_filenames(acct, ctx) | {A.STATS_NAME[l] for l in A.LANGS}
    if acct.get("contrib_graph") and _snake_available(key, base):
        wanted |= set(SNAKE_NAMES)
    for stale in assets.glob("*.svg"):
        if stale.name not in wanted:
            stale.unlink()
    for stale in (assets / "icons").glob("*.svg"):
        stale.unlink()
    for stale in (assets / "cards").glob("*.svg"):
        stale.unlink()
    png_dir = assets / "png"
    # PNG 兜底只认 kit 源里按账号分目录的那份（assets/png/<key>/hero.png）。
    # 绝不复用部署仓库根下的 assets/png/hero.png —— 镜像仓库里那份可能属于
    # 另一个账号，会把别人的 hero 图贴到本页。
    hero_png_src = ROOT / "assets" / "png" / key / "hero.png"
    hero_png = hero_png_src.is_file()
    # 卡片先于 README：README 对 snake（GitHub 账号专属）与 badges（GitCode/Gitee
    # 专属）的引用决策直接看本次输出目录的 assets —— 引用与文件同源，跨账号
    # 渲染（verify 临时目录、dist/<key>）不再产生悬空引用，断网时也优雅降级。
    for lang in A.LANGS:
        for filename, svg in render_cards(acct, key, lang, ctx):
            (assets / filename).write_text(svg, encoding="utf-8", newline="\n")
    for filename, svg in render_static(acct, key, ctx):
        (assets / filename).write_text(svg, encoding="utf-8", newline="\n")
    if not assets_only:
        for lang in A.LANGS:
            (out / A.README_NAME[lang]).write_text(
                render_readme(acct, key, lang, stats, base=base, discovered=works_data,
                              hero_png=hero_png, assets_dir=assets),
                encoding="utf-8", newline="\n"
            )
    # hero 的 PNG 兜底（由 scripts/rasterize.py 生成；缺失时 README 只引用 SVG）
    if hero_png:
        png_dir.mkdir(parents=True, exist_ok=True)
        hero_png_dst = png_dir / "hero.png"
        if hero_png_src.resolve() != hero_png_dst.resolve():
            # 源 PNG 在 rasterize.py 里已经做过无损优化；这里只做拷贝，
            # 每次构建都重压缩会把单账号耗时从 20ms 拉到 2s+。
            shutil.copyfile(hero_png_src, hero_png_dst)
    else:
        stale_png = png_dir / "hero.png"
        if stale_png.is_file():
            stale_png.unlink()
    # README 引用的图标（平台徽标 + 写作平台），只拷贝用到的那几个
    icon_roots = [pathlib.Path(base) / "data" / "icons", ROOT / "data" / "icons"] if base else [ROOT / "data" / "icons"]
    used_icons = sorted({A.PLATFORM_ICON[p] for p in
                         {a["platform"] for a in A.ACCOUNTS.values()}})
    used_icons += [icon for _name, _url, icon in A.WRITING]
    for name in used_icons:
        for root in icon_roots:
            src = root / name
            if src.is_file():
                if name.startswith("si-"):
                    # simple-icons 默认黑色，深色底上不可见 → 补浅色填充
                    copy_icon_light(src, assets / "icons" / name, ctx["theme"].get("muted", "#9AA8CC"))
                else:
                    shutil.copyfile(src, assets / "icons" / name)
                break
    # 官方卡片种子（存在才拷贝 —— 缺失即 README 自动降级，见 load_card_seed）
    card_dir = cards_dir_for(key, base)
    if card_dir.is_dir():
        for f in sorted(card_dir.glob("*.svg")):
            shutil.copyfile(f, assets / "cards" / f.name)
    if acct.get("contrib_graph") and _snake_available(key, base):
        seed_dir = ROOT / "data" / "contrib" / key
        for src_name, dst_name in (("snake.svg", SNAKE_NAMES[0]), ("snake-dark.svg", SNAKE_NAMES[1])):
            src = seed_dir / src_name
            if src.is_file():
                shutil.copyfile(src, assets / dst_name)

MANIFEST_NAME = ".build-manifest.json"


def manifest_path(out_dir):
    return pathlib.Path(out_dir) / MANIFEST_NAME


def input_digest(cwd=None, out_dir=None):
    """输入指纹：accounts.py + data/*.json + profile.json。

    与产物无关，因此可以判断「这次构建是否可能产生不同结果」。
    """
    cwd = pathlib.Path(cwd) if cwd else ROOT
    h = hashlib.sha256()
    for rel in ("accounts.py", "profile.json", "data/stats.json", "data/works.json",
                "data/writing.json"):
        path = cwd / rel
        if path.is_file():
            h.update(rel.encode("utf-8"))
            h.update(path.read_bytes())
    return h.hexdigest()


def current_manifest(out_dir):
    try:
        return json.loads(manifest_path(out_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_manifest(out_dir):
    data = {
        "version": 1,
        "input_digest": input_digest(out_dir),
        "outputs": _output_digest(out_dir),
    }
    write_text_atomic(manifest_path(out_dir), json.dumps(data, indent=2, sort_keys=True) + "\n")
    return data


def _output_digest(out_dir):
    out = pathlib.Path(out_dir)
    h = hashlib.sha256()
    files = sorted(str(p.relative_to(out)).replace(os.sep, "/")
                   for p in out.rglob("*")
                   if p.is_file() and p.name != MANIFEST_NAME)
    for name in files:
        h.update(name.encode("utf-8"))
        h.update((out / name).read_bytes())
    return h.hexdigest()


def here(cwd, assets_only=False, skip_if_unchanged=False):
    cwd = pathlib.Path(cwd)
    prof = json.loads((cwd / "profile.json").read_text(encoding="utf-8"))
    key = prof["account"]
    stats = load_stats(cwd / "data" / "stats.json")
    if skip_if_unchanged:
        before = current_manifest(cwd) or {}
        if before.get("input_digest") == input_digest(cwd):
            return key + " (unchanged)"
    write_account_files(A.ACCOUNTS[key], key, cwd, stats, base=cwd, assets_only=assets_only)
    write_manifest(cwd)
    return key


def generate_to(out_dir, key, stats):
    write_account_files(A.ACCOUNTS[key], key, out_dir, stats)


def _generate_one(args):
    out_dir, key, stats = args
    write_account_files(A.ACCOUNTS[key], key, out_dir, stats)
    return key


def generate_accounts(keys, out_dir, stats, jobs=None):
    """并发生成多个账号。

    SVG 渲染是纯 CPU 计算，多账号彼此独立；用进程池把 5 个账号摊到多个核上。
    单账号时直接串行，避免进程池固定开销。
    """
    out_dir = pathlib.Path(out_dir)
    keys = list(keys)
    if jobs is None:
        jobs = min(len(keys), os.cpu_count() or 1)
    if jobs <= 1 or len(keys) <= 1:
        for key in keys:
            write_account_files(A.ACCOUNTS[key], key, out_dir / key, stats)
        return len(keys)
    # 线程而非进程：瓶颈是文件 I/O 与字符串拼接，线程池没有解释器启动成本
    # （Windows 上进程池光启动就要 ~0.2s，比整个构建还慢）。
    tasks = [(out_dir / key, key, stats) for key in keys]
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(_generate_one, tasks))
    return len(keys)
