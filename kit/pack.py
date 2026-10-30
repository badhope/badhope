# -*- coding: utf-8 -*-
"""打包：生成可部署仓库树（README + 资产 + 脚本 + CI 配置）。"""

import json
import pathlib
import shutil
import sys

import accounts as A

from .build import write_account_files
from .data import load_stats
from .paths import ROOT

PACK_EXTRAS = ("scripts/generate.py", "scripts/refresh.py", "scripts/refresh_sections.py",
                "accounts.py", "data/stats.json", "data/writing.json", "data/works.json",
                "scripts/discover_works.py")

PACK_GITIGNORE = ".gitignore"

def _has_mirror(key):
    """该账号是否在 GitCode / Gitee 另有主页（需要镜像作业）。

    目前仅 github/badhope 在 GitCode、Gitee 均有同名主页；其余账号只在 GitHub。
    """
    acct = A.ACCOUNTS.get(key, {})
    return acct.get("platform") == "github" and acct.get("handle") == "badhope"

def pack(key, out_dir):
    acct = A.ACCOUNTS[key]
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stats_path = ROOT / "data" / "stats.json"
    stats = load_stats(stats_path)
    write_account_files(acct, key, out, stats)
    for rel in PACK_EXTRAS:
        src = ROOT / rel
        if not src.is_file():
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    # kit 包是生成器的实际实现，必须随部署仓库一起走（scripts/generate.py 只是垫片）
    if (ROOT / "kit").is_dir():
        shutil.copytree(ROOT / "kit", out / "kit",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
    if acct.get("contrib_graph"):
        seed_src = ROOT / "data" / "contrib" / key
        if seed_src.is_dir():
            dst_dir = out / "data" / "contrib" / key
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in sorted(seed_src.glob("*.svg")):
                shutil.copyfile(f, dst_dir / f.name)
    # 图标库与卡片种子随包携带（目标仓库内可 --here 重建 / 由 workflow 刷新卡片）
    icon_src = ROOT / "data" / "icons"
    if icon_src.is_dir():
        dst_icons = out / "data" / "icons"
        dst_icons.mkdir(parents=True, exist_ok=True)
        for f in sorted(icon_src.glob("*.svg")):
            shutil.copyfile(f, dst_icons / f.name)
    card_src = ROOT / "data" / "cards" / key
    if card_src.is_dir():
        dst_cards = out / "data" / "cards" / key
        dst_cards.mkdir(parents=True, exist_ok=True)
        for f in sorted(card_src.glob("*.svg")):
            shutil.copyfile(f, dst_cards / f.name)
    (out / "profile.json").write_text(
        json.dumps({"kit_version": A.KIT_VERSION, "account": key}, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    if acct["platform"] == "github":
        # 以下文件只有 kit 源仓库才有；镜像/精简 checkout 里缺失时跳过并告警，
        # 不能因为一次 pack 就整体抛 FileNotFoundError。
        optional = [
            ("workflows/refresh.yml", ".github/workflows/refresh.yml"),
            ("workflows/gitleaks.yml", ".github/workflows/gitleaks.yml"),
            (".gitleaks.toml", ".gitleaks.toml"),
            ("scripts/render_cards.mjs", "scripts/render_cards.mjs"),
            ("package.json", "package.json"),
            ("package-lock.json", "package-lock.json"),
        ]
        if _has_mirror(key):
            optional += [
                ("workflows/mirror.yml", ".github/workflows/mirror.yml"),
                ("workflows/mirror-shared.sh", "scripts/mirror-shared.sh"),
            ]
        for rel_src, rel_dst in optional:
            src = ROOT / rel_src
            if not src.is_file():
                print("warn: skip missing kit file %s" % rel_src, file=sys.stderr)
                continue
            dst = out / rel_dst
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        if (ROOT / "tests").is_dir():
            shutil.copytree(ROOT / "tests", out / "tests",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
        doc_src_dir = ROOT / "docs"
        if doc_src_dir.is_dir():
            doc_dir = out / "docs"
            doc_dir.mkdir(parents=True, exist_ok=True)
            for d in sorted(doc_src_dir.glob("*.md")):
                shutil.copyfile(d, doc_dir / d.name)
    (out / PACK_GITIGNORE).write_text(
        (ROOT / PACK_GITIGNORE).read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
    )
    return out
