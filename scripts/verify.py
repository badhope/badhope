#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线自检：不联网、不写仓库，检查生成器与数据的内部一致性。

用法：
  python scripts/verify.py            # 全部离线检查
  python scripts/verify.py --online   # 额外校验 accounts.py 中的仓库链接存在

退出码：0 = 全部通过；1 = 有失败项。
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import accounts as A  # noqa: E402
import generate as G  # noqa: E402
from kit.plugins import describe as describe_plugins  # noqa: E402
from kit.schema import validate_all  # noqa: E402

ASSET_RE = re.compile(r'(?:src|srcset)="(\./[^"]+)"')


class Checker:
    def __init__(self):
        self.failures = []
        self.checked = 0

    def check(self, ok, message):
        self.checked += 1
        if not ok:
            self.failures.append(message)
        return ok

    def report(self):
        print("checked %d assertions, %d failed" % (self.checked, len(self.failures)))
        for item in self.failures:
            print("  FAIL %s" % item)
        return 0 if not self.failures else 1


def check_catalog(c):
    for key, acct in A.ACCOUNTS.items():
        for wid in acct["works"]:
            c.check(wid in A.WORKS, "%s 引用了不存在的作品 %s" % (key, wid))
        c.check(bool(acct.get("skills")), "%s 技能列表为空" % key)
        for skill in acct.get("skills", []):
            c.check(skill in A.SKILL_LABELS, "%s 技能 %s 不在 SKILL_LABELS" % (key, skill))
    for wid, work in A.WORKS.items():
        c.check(bool(work.get("links")), "作品 %s 没有任何链接" % wid)
        for lang in A.LANGS:
            c.check(bool(work["desc"].get(lang)), "作品 %s 缺 %s 描述" % (wid, lang))
            c.check(bool(work["tags"].get(lang)), "作品 %s 缺 %s 标签" % (wid, lang))
        c.check(wid in A.WORK_ICONS, "作品 %s 缺图标映射" % wid)
        icon = A.WORK_ICONS.get(wid)
        c.check(G.icon_svg_body(icon, 24) is not None, "作品 %s 的图标 %s 不可用" % (wid, icon))


def check_generated_tree(c, key, tmp_root):
    acct = A.ACCOUNTS[key]
    stats = G.load_stats(ROOT / "data" / "stats.json")
    out = tmp_root / key
    G.write_account_files(acct, key, out, stats)
    for lang in A.LANGS:
        readme = out / A.README_NAME[lang]
        c.check(readme.is_file(), "%s 缺 %s" % (key, readme.name))
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8")
        refs = set(ASSET_RE.findall(text))
        c.check(bool(refs), "%s %s 没有任何本地资产引用" % (key, readme.name))
        for ref in sorted(refs):
            c.check((out / ref[2:]).is_file(), "%s %s 引用了不存在的资产 %s" % (key, readme.name, ref))
        # fail-soft 把渲染异常降级成「card failed」错误卡；那是诊断信息，
        # 绝不能当正常产物出库。这里把它的出现变成硬门禁：任何一张错误卡
        # 都说明某张卡在当前数据/环境下真的坏了，必须修，而不是静默降级。
        for svg in sorted((out / "assets").rglob("*.svg")):
            body = svg.read_text(encoding="utf-8", errors="replace")
            c.check("card failed:" not in body,
                    "%s 产出了错误卡 %s（fail-soft 捕获到渲染异常）" % (key, svg.name))
        # README 的「在别处」表格合法列出其他账号；混账号只可能出现在生成资产里，
        # 所以这里只校验本地资产引用是否齐备（上面已做），资产内容在下面单独校验。
    hero = (out / "assets" / "hero.svg").read_text(encoding="utf-8")
    c.check(acct["home_display"] in hero, "%s hero 未写入本账号地址" % key)
    # 生成资产不得携带其他账号的主页地址（hero / 技能卡 / 统计卡）
    for asset in ("hero.svg", "skills-md.svg", "stats-en.svg", "works-md.svg"):
        path = out / "assets" / asset
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8")
        for other_key, other in A.ACCOUNTS.items():
            if other_key == key:
                continue
            c.check(other["home_display"] not in body,
                    "%s 的 %s 混入了账号 %s（%s）" % (key, asset, other_key, other["home_display"]))
    data = G.acct_stats(stats, key)
    stats_svg = (out / "assets" / A.STATS_NAME["md"]).read_text(encoding="utf-8")
    if data.get("repos") is not None:
        c.check(G.fmt_num(data["repos"]) in stats_svg, "%s 统计卡未使用 stats.json 的仓库数" % key)


def check_idempotent(c, tmp_root):
    key = "gitcode_badhope"
    stats = G.load_stats(ROOT / "data" / "stats.json")
    first = tmp_root / "idem1"
    second = tmp_root / "idem2"
    G.write_account_files(A.ACCOUNTS[key], key, first, stats)
    G.write_account_files(A.ACCOUNTS[key], key, second, stats)
    for path in sorted(first.rglob("*")):
        if path.is_file():
            rel = path.relative_to(first)
            twin = second / rel
            c.check(twin.is_file() and twin.read_bytes() == path.read_bytes(),
                    "两次生成不一致：%s" % rel)


def check_plugins(c):
    """卡片插件注册表自检：每个插件必须能描述自己，且文件名唯一。"""
    specs = describe_plugins()
    c.check(len(specs) >= 5, "卡片插件数量异常：%d" % len(specs))
    names = [s["name"] for s in specs]
    c.check(len(names) == len(set(names)), "插件名重复：%s" % names)
    files = [s["filename"] for s in specs]
    c.check(len(files) == len(set(files)), "插件文件模板重复：%s" % files)
    for spec in specs:
        c.check("{lang}" in spec["filename"] or not spec["per_lang"],
                "插件 %s 是多语言但文件名缺 {lang}" % spec["name"])


def check_works_data(c):
    data = G.load_works()
    for key in A.ACCOUNT_ORDER:
        block = (data.get("accounts") or {}).get(key) or {}
        c.check(block.get("platform") == A.ACCOUNTS[key]["platform"],
                "works.json 中 %s 平台不匹配" % key)
        for repo in block.get("repos") or []:
            c.check(bool(repo.get("url")), "works.json %s 仓库缺 url" % key)
            c.check("|" not in (repo.get("title") or ""), "works.json %s 标题含竖线" % key)


def check_online(c):
    """并发校验仓库链接。

    只把 404/410 判定为失效：GitHub 未认证时限流返回 403，链接本身是好的；
    网络超时单列为告警，不算失败（CI 上再跑一次即可）。
    """
    import concurrent.futures
    import urllib.error
    import urllib.request

    def status(url):
        req = urllib.request.Request(url, headers={"User-Agent": "profile-kit-verify"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status
        except urllib.error.HTTPError as err:
            return err.code
        except OSError as err:
            return type(err).__name__

    targets = {}
    for wid, work in A.WORKS.items():
        for value in work["links"].values():
            for url in ([value] if isinstance(value, str) else value):
                targets.setdefault(url, wid)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda u: (u, status(u)), sorted(targets)))

    for url, code in results:
        if code in (404, 410):
            c.check(False, "链接失效 %s -> %s (%s)" % (targets[url], code, url))
            continue
        c.check(True, "")
        if not isinstance(code, int) or code >= 400:
            print("  warn: %s -> %s（限流/网络，不判失败）" % (url, code))


def main(argv=None):
    ap = argparse.ArgumentParser(description="profile kit offline verification")
    ap.add_argument("--online", action="store_true", help="also check repository links")
    args = ap.parse_args(argv)

    import tempfile

    c = Checker()
    schema_problems = validate_all(ROOT)
    for problem in schema_problems:
        c.check(False, "schema: %s" % problem)
    if not schema_problems:
        c.check(True, "")
    check_catalog(c)
    check_works_data(c)
    check_plugins(c)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = pathlib.Path(tmp)
        for key in A.ACCOUNT_ORDER:
            check_generated_tree(c, key, tmp_root)
        check_idempotent(c, tmp_root)
    if args.online:
        check_online(c)
    return c.report()


if __name__ == "__main__":
    sys.exit(main())
