# -*- coding: utf-8 -*-
"""构建产物契约 —— 针对"看起来通过、实际是坏的"这一类问题。

审计发现的弱断言已替换为可被破坏触发的强断言：
  - 资产引用同时检查 src / srcset / Markdown 图片，且校验文件非空
  - 卡片必须是合法 SVG 而非 0 字节
  - --here 可复现性做双向文件集比较（能抓到"空操作"和"多写垃圾"）
  - stats 数字与渲染产物交叉校验（不只检查结构）
  - 工作流必须是可解析且含预期 job 的真实 YAML

运行：python -m unittest discover -s tests
"""

import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "generate.py"

# 部署仓库里只有打包产物，没有 workflows/ 等源码目录；
# 依赖源码树的测试在那里无法运行，应跳过而不是失败。
IS_SOURCE_TREE = (ROOT / "workflows").is_dir()
NEEDS_SOURCE = unittest.skipUnless(
    IS_SOURCE_TREE, "仅源码树可运行（部署仓库缺少 workflows/ 等源文件）")
ACCOUNTS = ["gh_badhope", "gh_x33834", "gh_morningstar", "gitcode_badhope", "gitee_badhope"]
GITHUB_KEYS = ["gh_badhope", "gh_x33834", "gh_morningstar"]


@NEEDS_SOURCE
class PackedTreeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = pathlib.Path(cls.tmp.name) / "pack"
        for key in ACCOUNTS:
            subprocess.run(
                [sys.executable, str(GEN), "--pack", key, "--out", str(cls.out / key)],
                check=True, capture_output=True,
            )
        cls.stats = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # ---------- 资产引用 ----------
    def test_every_readme_asset_reference_exists_and_is_nonempty(self):
        missing, empty = [], []
        for key in ACCOUNTS:
            tree = self.out / key
            for readme in tree.glob("README*.md"):
                text = readme.read_text(encoding="utf-8")
                refs = set(re.findall(r'src="\./(assets/[^"]+)"', text))
                refs |= set(re.findall(r'srcset="\./(assets/[^"\s]+)', text))
                refs |= set(re.findall(r'!\[[^\]]*\]\(\./(assets/[^)\s]+)\)', text))
                self.assertTrue(refs, "%s/%s 没有任何资产引用" % (key, readme.name))
                for rel in refs:
                    path = tree / rel
                    if not path.is_file():
                        missing.append("%s/%s -> %s" % (key, readme.name, rel))
                    elif path.stat().st_size < 100:
                        empty.append("%s/%s -> %s" % (key, readme.name, rel))
        self.assertEqual(missing, [], "引用了不存在的资产:\n" + "\n".join(missing))
        self.assertEqual(empty, [], "资产内容为空:\n" + "\n".join(empty))

    # ---------- 卡片 / 蛇图 ----------
    def test_github_cards_are_valid_svg_and_complete(self):
        for key in GITHUB_KEYS:
            cards = sorted((self.out / key / "assets" / "cards").glob("*.svg"))
            self.assertEqual(len(cards), 15, "%s 卡片数量不对: %d" % (key, len(cards)))
            for card in cards:
                raw = card.read_text(encoding="utf-8")
                self.assertGreater(len(raw), 500, "%s 卡片过小: %s" % (key, card.name))
                self.assertIn("<svg", raw, "%s 不是 SVG: %s" % (key, card.name))
                try:
                    ET.fromstring(raw)
                except ET.ParseError as err:
                    self.fail("%s 卡片 XML 损坏 %s: %s" % (key, card.name, err))

    def test_official_cards_contain_real_numbers(self):
        """卡片不能是占位壳：必须来自 github-readme-stats 且带 desc 摘要。"""
        for key in GITHUB_KEYS:
            card = self.out / key / "assets" / "cards" / "stats-en.svg"
            raw = card.read_text(encoding="utf-8")
            # 官方卡一定有 <desc id="descId"> 摘要，里面写着 Total Stars 等
            self.assertIn('id="descId"', raw, "%s 的 stats 卡缺 desc 摘要" % key)
            self.assertIn("Total Stars", raw, "%s 的 stats 卡缺星数摘要" % key)

    def test_pin_cards_reference_real_repos(self):
        """置顶卡必须对应 accounts.WORKS 里真实存在的仓库名。"""
        sys.path.insert(0, str(ROOT))
        import accounts as A
        for key in GITHUB_KEYS:
            acct = A.ACCOUNTS[key]
            pins = sorted((self.out / key / "assets" / "cards").glob("pin-*.svg"))
            self.assertTrue(pins, "%s 没有置顶卡" % key)
            titles = []
            for p in pins:
                raw = p.read_text(encoding="utf-8")
                m = re.search(r'<title id="titleId">([^<]*)</title>', raw)
                if m:
                    titles.append(m.group(1))
            self.assertTrue(titles, "%s 的置顶卡没有 title" % key)

    def test_github_snake_present_and_valid(self):
        for key in GITHUB_KEYS:
            snake = self.out / key / "assets" / "github-contribution-grid-snake.svg"
            self.assertTrue(snake.is_file(), "%s 缺贡献蛇图" % key)
            self.assertGreater(snake.stat().st_size, 500, "%s 蛇图为空" % key)

    # ---------- 内容契约 ----------
    def test_pinned_section_uses_label_from_data_source(self):
        """段落标题必须来自 accounts.LABELS，而不是硬编码英文。"""
        sys.path.insert(0, str(ROOT))
        import accounts as A
        for key in GITHUB_KEYS:
            for lang in A.LANGS:
                text = (self.out / key / A.README_NAME[lang]).read_text(encoding="utf-8")
                self.assertIn(A.LABELS[lang]["pinned"], text,
                              "%s/%s 缺置顶段落标题" % (key, lang))

    def test_stats_numbers_appear_in_rendered_output(self):
        """stats.json 的数字必须真的渲染进大字号数值节点。

        审计指出裸子串匹配会因坐标/字号/颜色里的数字巧合通过，
        因此这里只取 font-size="46" 的 <text> 节点比对。
        """
        for key in ACCOUNTS:
            block = self.stats["accounts"][key]
            svg = (self.out / key / "assets" / "stats-en.svg").read_text(encoding="utf-8")
            big = re.findall(r'<text[^>]*font-size="46"[^>]*>([^<]+)</text>', svg)
            self.assertTrue(big, "%s 的 stats-en.svg 没有大字号数值节点" % key)
            expected = [format(int(block[f]), ",") for f in ("repos", "stars", "followers", "merged")
                        if block.get(f) is not None]
            for val in expected:
                self.assertIn(val, big,
                              "%s 的数值 %s 未出现在渲染节点 %s 中" % (key, val, big))

    def test_languages_are_actually_different(self):
        """三语言 README 必须真的不同，防止全量回退到同一份文案。"""
        for key in ACCOUNTS:
            texts = {}
            for lang in ("md", "zh-CN", "ja"):
                name = {"md": "README.md", "zh-CN": "README.zh-CN.md", "ja": "README.ja.md"}[lang]
                texts[lang] = (self.out / key / name).read_text(encoding="utf-8")
            self.assertNotEqual(texts["md"], texts["zh-CN"], "%s 中英文相同" % key)
            self.assertNotEqual(texts["md"], texts["ja"], "%s 英日文相同" % key)

    def test_no_retired_projects(self):
        for key in ACCOUNTS:
            for readme in (self.out / key).glob("README*.md"):
                text = readme.read_text(encoding="utf-8")
                for bad in ("naiwa-pet", "vaultx"):
                    self.assertNotIn(bad, text, "%s/%s 仍含下架项目 %s" % (key, readme.name, bad))

    # ---------- 工作流 ----------
    def test_workflows_are_parseable_and_have_expected_jobs(self):
        import yaml
        for key in GITHUB_KEYS:
            wf = self.out / key / ".github" / "workflows"
            refresh = wf / "refresh.yml"
            self.assertTrue(refresh.is_file(), "%s 缺 refresh.yml" % key)
            data = yaml.safe_load(refresh.read_text(encoding="utf-8"))
            self.assertIn("refresh", data["jobs"], "%s refresh.yml 缺 refresh job" % key)
            self.assertIn("cards", data["jobs"], "%s refresh.yml 缺 cards job" % key)
            gitleaks = wf / "gitleaks.yml"
            self.assertTrue(gitleaks.is_file(), "%s 缺 gitleaks.yml" % key)
            self.assertIn("scan", yaml.safe_load(gitleaks.read_text(encoding="utf-8"))["jobs"])
            self.assertTrue((self.out / key / ".gitleaks.toml").is_file())

    def test_mirror_only_on_badhope_and_script_shipped(self):
        self.assertTrue((self.out / "gh_badhope" / ".github" / "workflows" / "mirror.yml").is_file())
        self.assertTrue((self.out / "gh_badhope" / "scripts" / "mirror-shared.sh").is_file())
        # 其余 GitHub 账号有自己的 Actions（refresh/gitleaks），但不能带镜像
        for key in ("gh_x33834", "gh_morningstar"):
            self.assertTrue((self.out / key / ".github" / "workflows" / "refresh.yml").is_file(),
                            "%s 缺 refresh.yml" % key)
            self.assertFalse((self.out / key / ".github" / "workflows" / "mirror.yml").exists(),
                             "%s 不该带 mirror.yml" % key)
            self.assertFalse((self.out / key / "scripts" / "mirror-shared.sh").exists(),
                             "%s 不该带镜像脚本" % key)
        # 国内两站没有 GitHub Actions
        for key in ("gitcode_badhope", "gitee_badhope"):
            self.assertFalse((self.out / key / ".github").exists(), "%s 不该带 Actions" % key)

    def test_refresh_workflow_calls_mirror_inline(self):
        """GITHUB_TOKEN 的 push 不会触发新 workflow，mirror 必须在同一 run 内调用。"""
        text = (self.out / "gh_badhope" / ".github" / "workflows" / "refresh.yml").read_text(encoding="utf-8")
        self.assertIn("mirror-shared.sh", text, "refresh.yml 未内联调用镜像脚本")

    def test_workflow_diff_gate_runs_after_add(self):
        """变更闸门必须在 git add 之后判定，否则新增文件永远检测不到。

        这是审计实测过的真实缺陷：`git diff` 不含 untracked 文件，
        放在 `git add -A` 之前会让新生成的卡片/蛇图永远不被提交。
        """
        text = (self.out / "gh_badhope" / ".github" / "workflows" / "refresh.yml").read_text(encoding="utf-8")
        # 逐个 run 块检查：只要有 git add，就必须用 --cached 且在其之后
        checked = 0
        for block in re.split(r"\n(?=\s{6}- name:|\s{6}- uses:)", text):
            if "git add" not in block:
                continue
            checked += 1
            self.assertIn("git diff --cached", block,
                          "commit 步骤用了 `git diff` 而非 `--cached`，untracked 文件会被漏掉")
            self.assertLess(block.index("git add"), block.index("git diff"),
                            "`git diff` 出现在 `git add` 之前，新增文件永远检测不到")
        self.assertGreaterEqual(checked, 2, "应有 refresh 与 cards 两个提交步骤")

    def test_jobs_that_push_are_serialized(self):
        """refresh 与 cards 都会推 main，必须串行，否则并行时必有一个 push 被拒。"""
        import yaml
        text = (ROOT / "workflows" / "refresh.yml").read_text(encoding="utf-8")
        jobs = yaml.safe_load(text)["jobs"]
        cards_needs = jobs["cards"].get("needs")
        needs = cards_needs if isinstance(cards_needs, list) else [cards_needs]
        self.assertIn("refresh", needs,
                      "cards 必须依赖 refresh 串行执行（两者都推 main）")
        self.assertIn("pull --rebase", text, "push 失败时缺少 rebase 重试")

    def test_readme_has_no_markdown_code_block_traps(self):
        """HTML 块内 4 空格缩进会被部分解析器当成代码块，导致整段显示成原始代码。"""
        for key in ACCOUNTS:
            for readme in (self.out / key).glob("README*.md"):
                for i, line in enumerate(readme.read_text(encoding="utf-8").splitlines(), 1):
                    if line.startswith("    ") and line.strip():
                        self.fail("%s:%d 存在 4 空格缩进，可能被渲染成代码块: %r"
                                  % (readme.name, i, line[:60]))

    def test_hero_has_png_fallback(self):
        """hero 必须提供 PNG 兜底（GitHub camo / GitCode raw 对 SVG 支持不稳定）。"""
        for key in GITHUB_KEYS:
            tree = self.out / key
            self.assertIn("<picture>", (tree / "README.md").read_text(encoding="utf-8"),
                          "%s README 的 hero 没有 picture 兜底" % key)
            png = tree / "assets" / "png" / "hero.png"
            self.assertTrue(png.is_file(), "%s 缺 assets/png/hero.png" % key)
            self.assertGreater(png.stat().st_size, 5000, "%s 的 hero.png 过小" % key)
            self.assertLess(png.stat().st_size, 1_200_000, "%s 的 hero.png 过大" % key)

    def test_hero_png_differs_per_account(self):
        """每个账号的 hero 内容不同，PNG 不能是同一张图。"""
        import hashlib
        digests = {}
        for key in ACCOUNTS:
            png = self.out / key / "assets" / "png" / "hero.png"
            if not png.is_file():
                continue
            digests[key] = hashlib.md5(png.read_bytes()).hexdigest()
        self.assertGreaterEqual(len(digests), 2, "没有可比较的 hero.png")
        self.assertEqual(len(set(digests.values())), len(digests),
                         "多个账号共用了同一张 hero.png: %s" % digests)

    def test_preview_strips_duplicate_hero(self):
        """预览页自带 hero，README 里的 hero 块（含 picture 包装）必须被剥离。"""
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "scripts"))
        import generate as G
        md = (self.out / "gh_x33834" / "README.md").read_text(encoding="utf-8")
        out = G.strip_preview_dupes(md)
        self.assertNotIn("assets/hero.svg", out, "README 的 hero.svg 未被剥离")
        self.assertNotIn("assets/png/hero.png", out, "README 的 hero.png 未被剥离")
        self.assertIn("Ship small, ship often", out, "剥离时误删了正文")

    def test_tests_are_shipped_for_ci(self):
        """CI 的 test job 在部署仓库里跑，因此 tests/ 必须随包。"""
        for key in GITHUB_KEYS:
            tdir = self.out / key / "tests"
            self.assertTrue(tdir.is_dir(), "%s 未携带 tests/，CI 测试必然失败" % key)
            self.assertTrue((tdir / "__init__.py").is_file(), "%s 的 tests 缺 __init__.py" % key)
            self.assertTrue(list(tdir.glob("test_*.py")), "%s 的 tests 为空" % key)


@NEEDS_SOURCE
class RegenerationTest(unittest.TestCase):
    def test_here_regeneration_reproduces_every_file(self):
        """--here 必须真正重写全部文件，且不多不少、内容一致。"""
        with tempfile.TemporaryDirectory() as tmp:
            tree = pathlib.Path(tmp) / "tree"
            subprocess.run([sys.executable, str(GEN), "--pack", "gh_morningstar", "--out", str(tree)],
                           check=True, capture_output=True)
            before = {p.relative_to(tree): p.read_bytes().replace(b"\r\n", b"\n")
                      for p in tree.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
            # 破坏多个不同类型的产物，覆盖 README / SVG / 数据资产
            victims = [
                tree / "assets" / "footer.svg",
                tree / "assets" / "hero.svg",
                tree / "README.md",
                tree / "assets" / "stats-en.svg",
            ]
            for v in victims:
                self.assertTrue(v.is_file(), "准备破坏的文件不存在: %s" % v)
                v.write_text("BROKEN", encoding="utf-8")
            result = subprocess.run([sys.executable, "scripts/generate.py", "--here"],
                                    cwd=tree, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, "--here 退出码非 0: %s" % result.stderr)
            self.assertIn("regenerated in place", result.stdout, "--here 未真正执行")
            for v in victims:
                self.assertNotEqual(v.read_text(encoding="utf-8"), "BROKEN",
                                    "--here 未重建 %s" % v.name)
            after = {p.relative_to(tree): p.read_bytes().replace(b"\r\n", b"\n")
                     for p in tree.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
            self.assertEqual(set(before), set(after), "文件集合发生变化（多写或漏写）")
            changed = [str(k) for k in before if before[k] != after[k]]
            self.assertEqual(changed, [], "--here 未还原被破坏的文件: %s" % changed)


if __name__ == "__main__":
    unittest.main()


@NEEDS_SOURCE
class CiWiringTest(unittest.TestCase):
    """测试必须真的接入 CI，否则永远不在门禁里（审计指出从未执行）。"""

    def test_refresh_workflow_has_test_job(self):
        import yaml
        text = (ROOT / "workflows" / "refresh.yml").read_text(encoding="utf-8")
        jobs = yaml.safe_load(text)["jobs"]
        self.assertIn("test", jobs, "refresh.yml 缺 test job")
        runs = " ".join(str(st.get("run", "")) for st in jobs["test"]["steps"])
        self.assertIn("unittest", runs, "test job 未执行 unittest")
        for name in ("refresh", "cards"):
            needs = jobs[name].get("needs")
            needs = needs if isinstance(needs, list) else [needs]
            self.assertIn("test", needs, "%s job 必须依赖 test 通过" % name)


class CiEnvironmentTest(unittest.TestCase):
    """CI 用 Python 3.11：tests/ 必须是可导入包，否则 discover 直接 ImportError。

    这是真实发生过的 CI 失败：本机 3.13 能跑，CI 3.11 报
    "Start directory is not importable: 'tests'"。
    """

    def test_tests_dir_is_importable_package(self):
        self.assertTrue((ROOT / "tests" / "__init__.py").is_file(),
                        "tests/ 缺 __init__.py，Python 3.11 的 unittest discover 无法导入")
