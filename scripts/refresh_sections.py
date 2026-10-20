#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分区刷新编排器 —— profile-kit 的网络组件之一（与 refresh.py 互补）。

设计目标（对应"每个部分动态变化、按内容刷新、不要太频繁、不超余额"）：
  - 每个 section 独立刷新、独立容错：某一块（如 gitcode 限流）失败不影响其他块，
    旧值保留（fail-soft），绝不整体崩溃、绝不清空已有数据。
  - 变更才写盘：刷新后先与磁盘上的旧值比对，没变化就跳过写文件，
    配合 CI 的 `git diff` 判断，可做到"无变化不提交"——省配额、省 Actions 额度。
  - 可被 CI 按需调用：
        python scripts/refresh_sections.py --section stats
        python scripts/refresh_sections.py --section writing
        python scripts/refresh_sections.py            # 全部
    （语言卡 / 贡献图由 workflow 里的 render_cards.mjs / snk 步骤负责，本脚本只管数据。）

复用 refresh.py 的抓取函数（唯一权威数据源），不在本文件重复实现网络逻辑。
"""

import argparse
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import accounts as A  # noqa: E402
import refresh as R   # noqa: E402

STATS_PATH = ROOT / "data" / "stats.json"
WRITING_PATH = ROOT / "data" / "writing.json"


def _load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def refresh_stats():
    """刷新全部账号的统计数字（repos/stars/followers/merged），逐账号容错。"""
    cur = _load_json(STATS_PATH, {"accounts": {}})
    accounts = cur.setdefault("accounts", {})
    changed_any = False
    for key in A.ACCOUNT_ORDER:
        block = accounts.setdefault(key, {})
        acct = A.ACCOUNTS[key]
        plat, handle = acct["platform"], acct["handle"]
        try:
            if plat == "github":
                R.refresh_github(handle, block)
            elif plat == "gitee":
                R.refresh_gitee(handle, block)
            elif plat == "gitcode":
                R.refresh_gitcode(handle, block)
            print("  stats %-16s ok" % key)
        except Exception as err:  # 单账号失败保留旧值
            print("  stats %-16s FAIL %s (kept old)" % (key, err))
    new = {
        "as_of": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "source": "scripts/refresh_sections.py",
        "accounts": accounts,
    }
    # 变更检测：序列化一致则不写盘（配合 CI 的 git diff 实现"无变化不提交"）
    text = json.dumps(new, indent=2, ensure_ascii=False) + "\n"
    old = STATS_PATH.read_text(encoding="utf-8") if STATS_PATH.exists() else ""
    if old == text:
        print("stats: unchanged — skip write")
        return False
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(text, encoding="utf-8", newline="\n")
    print("stats: written")
    return True


def refresh_writing():
    """刷新文章列表（CSDN RSS + 人工维护），失败保留旧内容。"""
    before = WRITING_PATH.read_bytes() if WRITING_PATH.exists() else b""
    try:
        R.fetch_writing()
        print("writing: ok")
    except Exception as err:
        print("writing: FAIL %s (kept old)" % err)
        return False
    after = WRITING_PATH.read_bytes() if WRITING_PATH.exists() else b""
    if before == after:
        print("writing: unchanged — skip")
        return False
    print("writing: updated")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="sectioned profile refresh (fail-soft, change-aware)")
    ap.add_argument("--section", choices=["stats", "writing", "all"], default="all",
                    help="which section to refresh (default: all)")
    args = ap.parse_args(argv)

    results = []
    if args.section in ("stats", "all"):
        results.append(("stats", refresh_stats()))
    if args.section in ("writing", "all"):
        results.append(("writing", refresh_writing()))

    print("\nrefresh summary:")
    for name, changed in results:
        print("  %-8s %s" % (name, "CHANGED" if changed else "no change"))
    print("(langs cards / contribution graph are refreshed by render_cards.mjs / snk in CI)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
