# -*- coding: utf-8 -*-
"""数据快照读取：stats / works / writing / 卡片种子 / 贡献图种子。"""

import json
import pathlib

import accounts as A

from .config import CARD_NAMES, SNAKE_NAMES
from .paths import ROOT

def load_works(base=None):
    """读取已发现的真实仓库列表（data/works.json）。缺失时返回空 dict。"""
    root = pathlib.Path(base) if base else ROOT
    try:
        return json.loads((root / "data" / "works.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

def load_stats(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"as_of": "", "accounts": {}}

def acct_stats(stats, key):
    return (stats.get("accounts") or {}).get(key) or {}

def load_card_seed(key, kind, lang, base=None):
    """官方卡片种子（data/cards/<key>/<kind>-<locale>.svg，由 scripts/render_cards.mjs 产出）。

    缺失时返回 None —— README 渲染随之降级，绝不产生裂图或外链（R7/S7.2）。
    base 允许在部署仓库内（--here）从该目录的 data/cards 读取。
    """
    name = CARD_NAMES[kind] % A.CARD_LOCALE[lang]
    roots = [ROOT] if base is None else [base, ROOT]
    for root in roots:
        p = root / "data" / "cards" / key / pathlib.Path(name).name
        if p.is_file():
            return p
    return None

def cards_dir_for(key, base):
    """卡片种子目录：优先部署仓库内的一份（--here 自包含），否则用 kit 源。"""
    if base:
        local = pathlib.Path(base) / "data" / "cards" / key
        if local.is_dir():
            return local
    return ROOT / "data" / "cards" / key

def load_writing_items():
    """读取 data/writing.json（refresh.py 维护）。缺失/损坏时返回空列表。"""
    try:
        data = json.loads((ROOT / "data" / "writing.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [it for it in (data.get("items") or []) if it.get("title") and it.get("url")]

def _snake_available(key, base=None):
    """本账号是否有贡献图种子（data/contrib/<key>/snake*.svg）。"""
    roots = [pathlib.Path(base)] if base else []
    roots.append(ROOT)
    return any((root / "data" / "contrib" / key / "snake.svg").is_file() for root in roots)
