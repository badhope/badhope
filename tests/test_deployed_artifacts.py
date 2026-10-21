# -*- coding: utf-8 -*-
"""部署仓库的产物契约 —— 可在已发布的仓库里直接运行。

与 test_pack_contract.py 的区别：这里**不重新打包**，
只校验仓库里现有的文件是否自洽。因此它既能在源码树跑，也能在 CI 的部署仓库跑。

运行：python -m unittest discover -s tests
"""

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# 源码树根目录的 README 是套件说明，不是某个账号的渲染产物；
# 本文件的断言只对"部署仓库"（=打好的包）成立。
# 唯一的可靠判据：源码树有 workflows/ 与 scripts/brand.py，部署仓库没有。
# （根 README / profile.json 都会被 --here 覆盖，不能用来区分。）
IS_DEPLOY_TREE = not (ROOT / "workflows").is_dir()
NEEDS_DEPLOY = unittest.skipUnless(
    IS_DEPLOY_TREE, "仅部署产物仓库可运行（源码树根目录没有渲染出的 README/资产）")


def _readme_langs():
    out = {}
    for name, lang in (("README.md", "md"), ("README.zh-CN.md", "zh-CN"), ("README.ja.md", "ja")):
        p = ROOT / name
        if p.is_file():
            out[lang] = p.read_text(encoding="utf-8")
    return out


@NEEDS_DEPLOY
class DeployedArtifactsTest(unittest.TestCase):
    """直接针对仓库现有产物做断言。"""

    def test_readmes_exist_and_are_substantial(self):
        readmes = _readme_langs()
        self.assertEqual(set(readmes), {"md", "zh-CN", "ja"}, "三语言 README 不齐")
        for lang, text in readmes.items():
            self.assertGreater(len(text), 2000, "%s README 过短（可能被截断）" % lang)
            self.assertIn("<img", text, "%s README 没有任何图片资产" % lang)

    def test_all_asset_references_resolve(self):
        missing = []
        for lang, text in _readme_langs().items():
            refs = set(re.findall(r'src="\./(assets/[^"]+)"', text))
            refs |= set(re.findall(r'srcset="\./(assets/[^"\s]+)', text))
            self.assertTrue(refs, "%s README 没有资产引用" % lang)
            for rel in refs:
                p = ROOT / rel
                if not p.is_file():
                    missing.append("%s -> %s" % (lang, rel))
                elif p.stat().st_size < 100:
                    missing.append("%s -> %s (空文件)" % (lang, rel))
        self.assertEqual(missing, [], "资产引用失效:\n" + "\n".join(missing))

    def test_stats_json_matches_rendered_svg(self):
        stats_path = ROOT / "data" / "stats.json"
        self.assertTrue(stats_path.is_file(), "缺 data/stats.json")
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        self.assertRegex(stats.get("as_of", ""), r"^\d{4}-\d{2}-\d{2}$")

        profile = ROOT / "profile.json"
        key = json.loads(profile.read_text(encoding="utf-8"))["account"] if profile.is_file() else None
        if not key:
            self.skipTest("无 profile.json，无法定位账号")

        block = (stats.get("accounts") or {}).get(key) or {}
        svg_path = ROOT / "assets" / "stats-en.svg"
        if not svg_path.is_file():
            self.skipTest("无 stats-en.svg")
        svg = svg_path.read_text(encoding="utf-8")
        big = re.findall(r'<text[^>]*font-size="46"[^>]*>([^<]+)</text>', svg)
        for field in ("repos", "stars", "followers", "merged"):
            val = block.get(field)
            if val is None:
                continue
            self.assertIn(format(int(val), ","), big,
                          "%s=%s 未出现在 stats-en.svg 的数值节点 %s" % (field, val, big))

    def test_svg_assets_well_formed(self):
        import xml.etree.ElementTree as ET
        bad = []
        for p in (ROOT / "assets").rglob("*.svg"):
            try:
                ET.fromstring(p.read_text(encoding="utf-8"))
            except ET.ParseError as err:
                bad.append("%s: %s" % (p.name, err))
        self.assertEqual(bad, [], "XML 损坏:\n" + "\n".join(bad))

    def test_no_retired_projects(self):
        for lang, text in _readme_langs().items():
            for bad in ("naiwa-pet", "vaultx"):
                self.assertNotIn(bad, text, "%s README 仍含下架项目 %s" % (lang, bad))

    def test_profile_json_consistency(self):
        p = ROOT / "profile.json"
        self.assertTrue(p.is_file(), "缺 profile.json（--here 依赖它）")
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("account", data, "profile.json 缺 account 字段")

    def test_shipped_refresh_has_platform_tokens(self):
        """随包的 refresh.py 必须含按平台解析凭据的实现。"""
        rp = ROOT / "scripts" / "refresh.py"
        self.assertTrue(rp.is_file(), "缺 scripts/refresh.py")
        self.assertIn("PLATFORM_ENV_PREFIX", rp.read_text(encoding="utf-8"),
                      "refresh.py 是旧版（凭据会跨平台串号）")


if __name__ == "__main__":
    unittest.main()
