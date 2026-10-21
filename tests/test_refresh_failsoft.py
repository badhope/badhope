# -*- coding: utf-8 -*-
"""refresh.py 的失败契约：网络失败必须保留旧值，空结果必须清零。

审计指出原测试只覆盖了成功的 mock 路径，fail-soft 这条唯一的安全保证完全没测。
"""

import pathlib
import sys
import unittest
import urllib.error
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import refresh as R  # noqa: E402


def repo(name, stars, fork=False):
    return {"name": name, "stargazers_count": stars, "fork": fork}


class FailSoftTest(unittest.TestCase):
    """网络异常时旧值必须原样保留。"""

    def setUp(self):
        p = mock.patch.object(R, "gh_headers", lambda h: {})
        p.start()
        self.addCleanup(p.stop)

    def failing(self, url, headers=None, timeout=30):
        raise urllib.error.URLError("network down")

    def test_github_keeps_all_old_values_on_failure(self):
        old = {"repos": 5, "stars": 7, "followers": 3, "merged": 2}
        block = dict(old)
        with mock.patch.object(R, "http_json", self.failing):
            R.refresh_github("someone", block)
        self.assertEqual(block, old, "网络失败后必须原样保留旧值")

    def test_gitee_keeps_old_values_on_failure(self):
        old = {"repos": 5, "stars": 7, "followers": 3}
        block = dict(old)
        with mock.patch.object(R, "resolve_token", lambda *a, **k: None), \
             mock.patch.object(R, "http_json", self.failing):
            R.refresh_gitee("someone", block)
        self.assertEqual(block, old)

    def test_gitcode_keeps_old_values_on_failure(self):
        old = {"repos": 5, "stars": 7, "followers": 3}
        block = dict(old)
        with mock.patch.object(R, "resolve_token", lambda *a, **k: "t"), \
             mock.patch.object(R, "http_json", self.failing):
            R.refresh_gitcode("someone", block)
        self.assertEqual(block, old)

    def test_gitcode_without_token_keeps_old_values(self):
        old = {"repos": 5, "stars": 7}
        block = dict(old)
        with mock.patch.object(R, "resolve_token", lambda *a, **k: None):
            R.refresh_gitcode("someone", block)
        self.assertEqual(block, old)


class EmptyResultTest(unittest.TestCase):
    """仓库被清空时，stars 必须真的降到 0，而不是保留旧值（审计发现的缺陷）。"""

    def setUp(self):
        p = mock.patch.object(R, "gh_headers", lambda h: {})
        p.start()
        self.addCleanup(p.stop)

    def test_empty_repo_list_zeroes_stars(self):
        def fake(url, headers=None, timeout=30):
            if "/repos?" in url:
                return []
            if "/users/" in url:
                return {"public_repos": 0, "followers": 0}
            return {"total_count": 0}

        block = {"repos": 9, "stars": 123, "followers": 4, "merged": 3}
        with mock.patch.object(R, "http_json", fake):
            R.refresh_github("someone", block)
        self.assertEqual(block["stars"], 0, "仓库清空后星数必须归零")


class PayloadShapeTest(unittest.TestCase):
    """API 返回非预期结构时不能静默当作成功。"""

    def setUp(self):
        p = mock.patch.object(R, "gh_headers", lambda h: {})
        p.start()
        self.addCleanup(p.stop)

    def test_non_list_payload_keeps_old_values(self):
        def fake(url, headers=None, timeout=30):
            if "/repos?" in url:
                return {"message": "rate limited"}
            return {"public_repos": 1, "followers": 1}

        block = {"repos": 9, "stars": 123}
        with mock.patch.object(R, "http_json", fake):
            R.refresh_github("someone", block)
        self.assertEqual(block["stars"], 123, "非法 payload 不应覆盖旧值")


class AuthHeaderTest(unittest.TestCase):
    """鉴权头必须真的带上（审计指出原测试把它 mock 掉了）。"""

    def test_github_headers_carry_token(self):
        import os
        with mock.patch.dict(os.environ, {"GH_BADHOPE_TOKEN": "tok-abc"}, clear=True), \
             mock.patch.object(R, "SECRETS_FILE", pathlib.Path("Z:/nope.json")):
            headers = R.gh_headers("badhope")
        self.assertEqual(headers.get("Authorization"), "Bearer tok-abc")

    def test_gitcode_request_uses_bearer_token(self):
        captured = {}

        def fake(url, headers=None, timeout=30):
            captured.update(headers or {})
            if "/repos?" in url:
                return []
            return {"followers": 1}

        with mock.patch.object(R, "resolve_token", lambda *a, **k: "gc-token"), \
             mock.patch.object(R, "http_json", fake):
            R.refresh_gitcode("someone", {})
        self.assertEqual(captured.get("Authorization"), "Bearer gc-token")


if __name__ == "__main__":
    unittest.main()


class GiteeSuccessPathTest(unittest.TestCase):
    """审计指出 Gitee 成功路径完全无覆盖（鉴权头改错会让线上 401）。"""

    def test_gitee_paginates_and_sums(self):
        pages = {1: [repo("a%d" % i, 1) for i in range(100)],
                 2: [repo("b%d" % i, 2) for i in range(5)]}
        seen_headers = {}

        def fake(url, headers=None, timeout=30):
            seen_headers.update(headers or {})
            if "/repos?" in url:
                page = int(url.rsplit("page=", 1)[-1])
                return pages.get(page, [])
            return {"followers": 7}

        with mock.patch.object(R, "resolve_token", lambda *a, **k: "gt"), \
             mock.patch.object(R, "http_json", fake):
            block = {}
            R.refresh_gitee("someone", block)
        self.assertEqual(block["repos"], 105, "两页必须累加")
        self.assertEqual(block["stars"], 100 * 1 + 5 * 2)
        self.assertEqual(block["followers"], 7, "gitee followers 必须写入")
        self.assertEqual(seen_headers.get("Authorization"), "token gt",
                         "Gitee 必须用 'token xxx' 而非 Bearer")

    def test_gitee_profile_failure_keeps_repos(self):
        def fake(url, headers=None, timeout=30):
            if "/repos?" in url:
                return [repo("a", 3)]
            raise urllib.error.URLError("profile down")

        block = {"followers": 99}
        with mock.patch.object(R, "resolve_token", lambda *a, **k: "gt"), \
             mock.patch.object(R, "http_json", fake):
            R.refresh_gitee("someone", block)
        self.assertEqual(block["repos"], 1)
        self.assertEqual(block["followers"], 99, "资料页失败不能清掉 followers")


class GithubFullFieldsTest(unittest.TestCase):
    """followers / merged 的成功路径必须被断言（审计指出只测了 stars/repos）。"""

    def setUp(self):
        p = mock.patch.object(R, "gh_headers", lambda h: {})
        p.start()
        self.addCleanup(p.stop)

    def test_followers_and_merged_are_written(self):
        def fake(url, headers=None, timeout=30):
            if "/search/issues" in url:
                return {"total_count": 4}
            if "/repos?" in url:
                return [repo("a", 2), repo("b", 3)]
            return {"public_repos": 2, "followers": 11}

        block = {}
        with mock.patch.object(R, "http_json", fake):
            R.refresh_github("someone", block)
        self.assertEqual(block["followers"], 11)
        self.assertEqual(block["merged"], 4)
        self.assertEqual(block["repos"], 2)
        self.assertEqual(block["stars"], 5)


class NoOpImplementationGuardTest(unittest.TestCase):
    """审计发现：把 refresh_* 改成空实现，fail-soft 用例仍通过（自证）。

    这里额外断言"确实发起过请求"，空实现会被抓住。
    """

    def test_gitee_actually_attempts_fetch(self):
        calls = []

        def fake(url, headers=None, timeout=30):
            calls.append(url)
            return [] if "/repos?" in url else {"followers": 0}

        with mock.patch.object(R, "resolve_token", lambda *a, **k: "gt"), \
             mock.patch.object(R, "http_json", fake):
            R.refresh_gitee("someone", {})
        self.assertTrue(calls, "refresh_gitee 必须真的发起请求")

    def test_gitcode_actually_attempts_fetch(self):
        calls = []

        def fake(url, headers=None, timeout=30):
            calls.append(url)
            return [] if "/repos?" in url else {"followers": 0}

        with mock.patch.object(R, "resolve_token", lambda *a, **k: "t"), \
             mock.patch.object(R, "http_json", fake):
            R.refresh_gitcode("someone", {})
        self.assertTrue(calls, "refresh_gitcode 必须真的发起请求")

    def test_github_actually_attempts_fetch(self):
        calls = []

        def fake(url, headers=None, timeout=30):
            calls.append(url)
            if "/search/issues" in url:
                return {"total_count": 0}
            if "/repos?" in url:
                return []
            return {"public_repos": 0, "followers": 0}

        with mock.patch.object(R, "gh_headers", lambda h: {}), \
             mock.patch.object(R, "http_json", fake):
            R.refresh_github("someone", {})
        self.assertTrue(calls, "refresh_github 必须真的发起请求")
