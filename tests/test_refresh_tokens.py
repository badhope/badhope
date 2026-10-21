# -*- coding: utf-8 -*-
"""凭据解析回归测试：CI 里同一 handle 在三个平台不能抢同一个环境变量。

运行：python -m unittest discover -s tests
"""

import os
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import refresh as R  # noqa: E402


class ResolveTokenTest(unittest.TestCase):
    def setUp(self):
        self.no_store = pathlib.Path("Z:/definitely-not-here/accounts.json")
        patcher = mock.patch.object(R, "SECRETS_FILE", self.no_store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def resolve(self, platform, handle, generic_env=(), env=None):
        with mock.patch.dict(os.environ, env or {}, clear=True):
            return R.resolve_token(platform, handle, generic_env=generic_env)

    def test_gitee_reads_generic_env(self):
        token = self.resolve("gitee", "badhope", generic_env=("GITEE_TOKEN",),
                             env={"GITEE_TOKEN": "gitee-abc", "GH_BADHOPE_TOKEN": "github-abc"})
        self.assertEqual(token, "gitee-abc")

    def test_gitcode_reads_generic_env(self):
        token = self.resolve("gitcode", "badhope", generic_env=("GITCODE_TOKEN",),
                             env={"GITCODE_TOKEN": "gitcode-abc", "GH_BADHOPE_TOKEN": "github-abc"})
        self.assertEqual(token, "gitcode-abc")

    def test_platform_specific_handle_env(self):
        token = self.resolve("gitee", "badhope",
                             env={"GITEE_BADHOPE_TOKEN": "gitee-handle"})
        self.assertEqual(token, "gitee-handle")

    def test_github_handle_env_still_wins(self):
        token = self.resolve("github", "badhope",
                             env={"GH_BADHOPE_TOKEN": "github-handle", "GITHUB_TOKEN": "generic"})
        self.assertEqual(token, "github-handle")

    def test_github_does_not_borrow_gitee_token(self):
        token = self.resolve("gitee", "badhope", generic_env=("GITEE_TOKEN",),
                             env={"GITHUB_TOKEN": "github-generic"})
        self.assertIsNone(token)

    def test_missing_everything_returns_none(self):
        self.assertIsNone(self.resolve("gitcode", "badhope", generic_env=("GITCODE_TOKEN",)))


if __name__ == "__main__":
    unittest.main()
