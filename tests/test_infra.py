# -*- coding: utf-8 -*-
"""HTTP 层与增量构建的单元测试（全部离线，用本地 HTTP 服务）。"""

import http.server
import pathlib
import sys
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from kit.net import HttpClient, HttpError  # noqa: E402


class _Handler(http.server.BaseHTTPRequestHandler):
    hits = 0
    fail_first = 0
    etag = '"v1"'

    def do_GET(self):
        type(self).hits += 1
        if self.path.startswith("/missing"):
            self.send_response(404)
            self.end_headers()
            return
        if type(self).fail_first > 0:
            type(self).fail_first -= 1
            self.send_response(503)
            self.end_headers()
            return
        if self.headers.get("If-None-Match") == type(self).etag:
            self.send_response(304)
            self.end_headers()
            return
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("ETag", type(self).etag)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class NetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        _Handler.hits = 0
        _Handler.fail_first = 0
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, **kw):
        return HttpClient(cache_dir=self.tmp.name, **kw)

    def test_get_json(self):
        with self.client() as c:
            data = c.get_json(self.base + "/x")
        self.assertEqual(data, {"ok": True})

    def test_etag_cache_avoids_rebody(self):
        with self.client() as c:
            first = c.get_json(self.base + "/etag")
            second = c.get_json(self.base + "/etag")
        self.assertEqual(first, second)
        self.assertEqual(_Handler.hits, 2)          # 第二次仍发请求（条件请求）
        self.assertEqual(c.stats["cache_hits"], 1)  # 但命中 304，不重新下载

    def test_retry_on_503(self):
        _Handler.fail_first = 2
        with self.client(max_retries=3) as c:
            data = c.get_json(self.base + "/retry")
        self.assertEqual(data, {"ok": True})
        self.assertEqual(c.stats["retries"], 2)

    def test_404_not_retried(self):
        with self.client() as c:
            with self.assertRaises(HttpError) as ctx:
                c.get(self.base + "/missing")
        self.assertEqual(ctx.exception.status, 404)


class ManifestTests(unittest.TestCase):
    def test_input_digest_changes_with_data(self):
        from kit.build import input_digest
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "accounts.py").write_text("A = 1\n", encoding="utf-8")
            first = input_digest(root)
            (root / "accounts.py").write_text("A = 2\n", encoding="utf-8")
            self.assertNotEqual(first, input_digest(root))


class PngOptTests(unittest.TestCase):
    def test_recompresses_real_png_losslessly(self):
        from kit.pngopt import optimize_file
        src = ROOT / "assets" / "png" / "gitcode_badhope" / "hero.png"
        if not src.is_file():
            self.skipTest("hero png not generated")
        with tempfile.TemporaryDirectory() as tmp:
            dst = pathlib.Path(tmp) / "h.png"
            dst.write_bytes(src.read_bytes())
            old, new = optimize_file(dst)
            self.assertEqual(dst.read_bytes()[:8], src.read_bytes()[:8])
            self.assertLessEqual(new, old)


class PluginTests(unittest.TestCase):
    def test_registry_has_all_cards(self):
        from kit.plugins import describe
        names = {s["name"] for s in describe()}
        self.assertTrue({"hero", "footer", "stats", "skills", "works", "activity", "langs"} <= names)

    def test_every_plugin_produces_svg(self):
        import accounts as A
        from kit.build import write_account_files
        from kit.data import load_stats, load_works
        stats = load_stats(ROOT / "data" / "stats.json")
        works = load_works()
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            write_account_files(A.ACCOUNTS["gitcode_badhope"], "gitcode_badhope", out, stats)
            for svg in (out / "assets").glob("*.svg"):
                text = svg.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("<svg"), str(svg))
                self.assertIn("</svg>", text)


if __name__ == "__main__":
    unittest.main()
