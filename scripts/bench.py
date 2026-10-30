#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""性能基准：量化本次重构带来的实际收益（可重复、无第三方依赖）。

用法：
  python scripts/bench.py            # 默认 5 轮
  python scripts/bench.py --rounds 10

输出四组数字：
1. 全量生成耗时（串行 vs 线程池）
2. 增量构建：输入未变化时 `--here --skip-if-unchanged` 的耗时与写盘量
3. SVG 产物体积（各卡片字节数）
4. 可选依赖状态（httpx / markdown-it-py / jsonschema / Pillow）
"""

import argparse
import pathlib
import statistics
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import accounts as A  # noqa: E402
from kit.build import generate_accounts, here, write_account_files  # noqa: E402
from kit.data import load_stats  # noqa: E402


def timeit(fn, rounds):
    samples = []
    for _ in range(rounds):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return min(samples), statistics.median(samples)


def bench_generation(rounds):
    stats = load_stats(ROOT / "data" / "stats.json")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        serial = timeit(lambda: generate_accounts(list(A.ACCOUNT_ORDER), root / "s", stats, jobs=1), rounds)
        parallel = timeit(lambda: generate_accounts(list(A.ACCOUNT_ORDER), root / "p", stats, jobs=5), rounds)
    return serial, parallel


def bench_single_account(rounds):
    stats = load_stats(ROOT / "data" / "stats.json")
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "one"
        write_account_files(A.ACCOUNTS["gitcode_badhope"], "gitcode_badhope", out, stats)
        return timeit(lambda: write_account_files(
            A.ACCOUNTS["gitcode_badhope"], "gitcode_badhope", out, stats), rounds)


def bench_incremental(rounds):
    """首次全量 vs 之后输入未变化时的短路耗时。"""
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "repo"
        work.mkdir()
        for rel in ("accounts.py", "profile.json", "data/stats.json", "data/works.json",
                    "data/writing.json"):
            src, dst = ROOT / rel, work / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        import shutil
        shutil.copytree(ROOT / "data" / "icons", work / "data" / "icons", dirs_exist_ok=True)
        shutil.copytree(ROOT / "assets" / "png" / "gitcode_badhope",
                        work / "assets" / "png" / "gitcode_badhope", dirs_exist_ok=True)
        first = timeit(lambda: here(work), 1)
        # 第二次起输入未变化：应直接短路，不重写任何文件
        again = timeit(lambda: here(work, skip_if_unchanged=True), rounds)
        files = sum(1 for p in work.rglob("*") if p.is_file())
    return first, again, files


def bench_assets():
    rows = []
    for name in ("hero.svg", "stats-en.svg", "skills-md.svg", "works-md.svg",
                 "activity-md.svg", "langs-md.svg", "footer.svg"):
        path = ROOT / "assets" / name
        if path.is_file():
            rows.append((name, path.stat().st_size))
    png = ROOT / "assets" / "png" / "gitcode_badhope" / "hero.png"
    if png.is_file():
        rows.append(("png/hero.png", png.stat().st_size))
    return rows


def bench_optional():
    import importlib.util
    status = {}
    for mod in ("httpx", "markdown_it", "jsonschema", "PIL"):
        status[mod] = importlib.util.find_spec(mod) is not None
    return status


def main(argv=None):
    ap = argparse.ArgumentParser(description="profile kit benchmark")
    ap.add_argument("--rounds", type=int, default=5)
    args = ap.parse_args(argv)

    print("== versions ==")
    print("python", sys.version.split()[0])
    for mod, ok in bench_optional().items():
        print("  %-12s %s" % (mod, "installed" if ok else "not installed (fallback path)"))

    (s_min, s_med), (p_min, p_med) = bench_generation(args.rounds)
    print("\n== generate all accounts (5 accounts) ==")
    print("  serial   min %.3fs  median %.3fs" % (s_min, s_med))
    print("  parallel min %.3fs  median %.3fs  speedup %.2fx"
          % (p_min, p_med, s_med / p_med if p_med else 0))

    one_min, one_med = bench_single_account(args.rounds)
    print("\n== single account (gitcode_badhope) ==")
    print("  min %.3fs  median %.3fs" % (one_min, one_med))

    (f_min, _), (a_min, a_med), files = bench_incremental(args.rounds)
    print("\n== incremental build ==")
    print("  first full build      %.3fs" % f_min)
    print("  unchanged short-circuit min %.4fs  median %.4fs  (%d files scanned)"
          % (a_min, a_med, files))
    if f_min:
        print("  skip speedup %.0fx" % (f_min / a_med if a_med else 0))

    print("\n== asset sizes ==")
    total = 0
    for name, size in bench_assets():
        total += size
        print("  %-18s %7.1f KB" % (name, size / 1024.0))
    print("  %-18s %7.1f KB" % ("TOTAL", total / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
