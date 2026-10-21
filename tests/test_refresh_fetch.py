# -*- coding: utf-8 -*-
"""refresh.py 抓取口径与分页的回归测试（用假 HTTP，不发真实请求）。

运行：python -m unittest discover -s tests
"""

import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import refresh as R  # noqa: E402


def repo(name, stars, fork=False):
    return {"name": name, "stargazers_count": stars, "fork": fork}


class GitHubStarsTest(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(R, "gh_headers", lambda h: {})
        p.start()
        self.addCleanup(p.stop)
        p2 = mock.patch.object(R, "SECRETS_FILE", pathlib.Path("Z:/nope.json"))
        p2.start()
        self.addCleanup(p2.stop)

    def test_fork_stars_are_excluded(self):
        def fake(url, headers=None, timeout=30):
            if "/users/someone/repos" in url:
                return [repo("own-a", 10), repo("forked", 999, fork=True), repo("own-b", 5)]
            if "/users/someone" in url:
                return {"public_repos": 3, "followers": 1}
            return {"total_count": 0}

        with mock.patch.object(R, "http_json", fake):
            block = {}
            R.refresh_github("someone", block)
        self.assertEqual(block["stars"], 15)
        self.assertEqual(block["repos"], 3)

    def test_repo_pagination_accumulates_all_pages(self):
        pages = {1: [repo("r%d" % i, 1) for i in range(100)],
                 2: [repo("s%d" % i, 1) for i in range(3)]}

        def fake(url, headers=None, timeout=30):
            if "/repos?" in url:
                page = int(url.rsplit("page=", 1)[-1])
                return pages.get(page, [])
            return {"total_count": 0}

        with mock.patch.object(R, "http_json", fake):
            block = {}
            R.refresh_github("someone", block)
        self.assertEqual(block["stars"], 103)


class GitCodePaginationTest(unittest.TestCase):
    def test_gitcode_walks_all_pages(self):
        pages = {1: [repo("a%d" % i, 1) for i in range(100)],
                 2: [repo("b%d" % i, 2) for i in range(7)]}

        def fake(url, headers=None, timeout=30):
            if "/repos?" in url:
                page = int(url.rsplit("page=", 1)[-1])
                return pages.get(page, [])
            return []

        with mock.patch.object(R, "resolve_token", lambda *a, **k: "fake-token"), \
             mock.patch.object(R, "http_json", fake):
            block = {}
            R.refresh_gitcode("someone", block)
        self.assertEqual(block["repos"], 107)
        self.assertEqual(block["stars"], 100 * 1 + 7 * 2)


if __name__ == "__main__":
    unittest.main()
