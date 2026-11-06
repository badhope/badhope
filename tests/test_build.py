"""Offline tests for the profile page generator."""

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build  # noqa: E402
from scripts.generate import build_out  # noqa: E402


class DeterminismTest(unittest.TestCase):
    def test_two_builds_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            outputs_a = build_out(a)
            outputs_b = build_out(b)
            self.assertEqual(outputs_a, outputs_b)
            for name in outputs_a:
                self.assertEqual(
                    (pathlib.Path(a) / name).read_bytes(),
                    (pathlib.Path(b) / name).read_bytes(),
                    name,
                )


class AssetRefsTest(unittest.TestCase):
    def test_every_referenced_asset_exists(self):
        for name in ("README.md", "README.zh-CN.md", "README.ja.md"):
            path = ROOT / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for token in text.replace('"', " ").replace(")", " ").split():
                if token.startswith("assets/") and token.endswith(".svg"):
                    self.assertTrue((ROOT / token).exists(), token)


class IsolationTest(unittest.TestCase):
    MARKS = {
        "gh_badhope": ("gitcode.com/badhope", "gitee.com/badhope"),
        "gh_morningstar": ("gitcode.com/badhope", "gitee.com/badhope"),
        "gh_x33834": ("gitcode.com/badhope", "gitee.com/badhope"),
        "gitcode_badhope": ("gitee.com/badhope",),
        "gitee_badhope": ("gitcode.com/badhope",),
    }

    def test_no_cross_platform_leakage(self):
        account = build.current_account()
        for foreign in self.MARKS[account]:
            for name in ("README.md", "README.zh-CN.md", "README.ja.md"):
                path = ROOT / name
                if not path.exists():
                    continue
                self.assertNotIn(foreign, path.read_text(encoding="utf-8"))


class DataTest(unittest.TestCase):
    def test_featured_works_exist_in_catalogue(self):
        for account, slugs in build.FEATURED.items():
            for slug in slugs:
                self.assertIn(slug, build.WORKS, "%s -> %s" % (account, slug))
                self.assertTrue(build.WORKS[slug]["line"]["zh-CN"].strip())

    def test_profile_account_is_known(self):
        self.assertIn(build.current_account(), build.COPY)

    def test_stats_snapshot_valid(self):
        account = build.current_account()
        stats = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
        self.assertIn("accounts", stats)
        self.assertIn(account, stats["accounts"])
        works = stats["accounts"][account].get("works", {})
        for slug in build.FEATURED[account]:
            self.assertIn(slug, works)


if __name__ == "__main__":
    unittest.main()
