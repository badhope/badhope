#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分区刷新编排器 —— profile-kit 的网络组件之一（与 refresh.py 互补）。

设计目标（对应"每个部分动态变化、按内容刷新、不要太频繁、不超余额"）：
  - 每个 section 独立刷新、独立容错：某一块失败不影响其他块，
    旧值保留（fail-soft），绝不整体崩溃、绝不清空已有数据。
  - 变更才写盘：**只看数据本身**，不看时间戳。刷新后与磁盘旧值逐字段比对，
    没变化就跳过写文件；配合 CI 的 `git diff` 可做到"无变化不提交"。
  - 可被 CI 按需调用：
        python scripts/refresh_sections.py --section stats
        python scripts/refresh_sections.py --section writing
        python scripts/refresh_sections.py            # 全部
    （语言卡 / 贡献图由 workflow 里的 render_cards.mjs / snk 步骤负责。）

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


def _strip_meta(obj, keys=("as_of", "source", "fetched")):
    """去掉时间戳类字段，只保留可比较的业务数据。"""
    return {k: v for k, v in obj.items() if k not in keys}


def _same_data(old, new):
    """业务数据是否一致（忽略 as_of / source / fetched）。"""
    return _strip_meta(old) == _strip_meta(new)


def refresh_stats():
    """刷新全部账号的统计数字（repos/stars/followers/merged），逐账号容错。

    返回 True 表示**数据**有变化并已写盘；只有时间戳变化时返回 False 且不落盘。
    """
    cur = _load_json(STATS_PATH, {"accounts": {}})
    # 深拷贝一份原始数据用于比对；不能直接引用 accounts 内部对象
    old_snapshot = json.loads(json.dumps(cur))
    accounts = cur.setdefault("accounts", {})
    failures, ok_count = [], 0
    for key in A.ACCOUNT_ORDER:
        block = accounts.setdefault(key, {})
        before = dict(block)
        acct = A.ACCOUNTS[key]
        plat, handle = acct["platform"], acct["handle"]
        try:
            if plat == "github":
                R.refresh_github(handle, block)
            elif plat == "gitee":
                R.refresh_gitee(handle, block)
            elif plat == "gitcode":
                R.refresh_gitcode(handle, block)
            else:
                print("  stats %-16s SKIP unknown platform" % key)
                continue
        except Exception as err:  # 单账号失败保留旧值
            block.clear()
            block.update(before)
            failures.append(key)
            print("  stats %-16s FAIL %s (kept old)" % (key, err))
            continue
        if block == before:
            # 数值没动，但也不能断言"抓取成功"——refresh_* 内部失败时会保留旧值。
            print("  stats %-16s unchanged (or source unavailable)" % key)
        else:
            ok_count += 1
            print("  stats %-16s UPDATED" % key)

    # 只有业务数据变了才更新 as_of 并落盘（忽略时间戳字段本身）
    if _same_data(old_snapshot, cur):
        print("stats: no data change — skip write (as_of kept at %s)" % cur.get("as_of"))
        return False

    new = {
        "as_of": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "source": "scripts/refresh_sections.py",
        "accounts": accounts,
    }
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(
        json.dumps(new, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    print("stats: written (updated %d accounts, %d failed)" % (ok_count, len(failures)))
    return True
    return False


def refresh_writing():
    """刷新文章列表（CSDN RSS + 人工维护），失败保留旧内容。"""
    before_obj = _load_json(WRITING_PATH, {"items": []})
    try:
        R.fetch_writing()
    except Exception as err:
        print("writing: FAIL %s (kept old)" % err)
        return False
    after_obj = _load_json(WRITING_PATH, {"items": []})
    if _same_data(before_obj, after_obj):
        print("writing: no data change — skip")
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
