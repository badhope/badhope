# -*- coding: utf-8 -*-
"""HTTP 访问层：连接复用、重试退避、条件请求缓存、按主机限流。

设计取舍：
- **优先用 httpx**（若已安装）：HTTP/1.1 连接池、自动重试钩子、更完整的超时模型；
- **零依赖兜底**：没有 httpx 时用 `http.client` 自己维护长连接池，
  功能不减（ETag / 重试 / 限流全部由本模块实现），只是少了 HTTP/2。
- 条件请求缓存写 `.cache/http/<sha1>.json`，命中 304 直接返回上次的 body，
  每日定时任务在数据没变时几乎不消耗 API 配额。
"""

import email.utils
import hashlib
import http.client
import json
import os
import pathlib
import random
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

try:  # 可选加速：装了 httpx 就走连接池 + HTTP/2
    import httpx as _httpx
except ImportError:  # pragma: no cover - 环境相关
    _httpx = None

UA = "profile-kit/2.0 (+https://gitcode.com/badhope/badhope)"
CACHE_DIR = pathlib.Path(os.environ.get("PROFILE_KIT_HTTP_CACHE", "") or ".cache/http")
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}


class HttpError(RuntimeError):
    def __init__(self, status, url, body=""):
        super().__init__("HTTP %s for %s" % (status, url))
        self.status = status
        self.url = url
        self.body = body


class _RateLimiter:
    """按主机的最小间隔限流（令牌桶的简化版），避免把公开 API 打爆。"""

    def __init__(self, min_interval=0.0):
        self.min_interval = min_interval
        self._last = {}

    def wait(self, host):
        if self.min_interval <= 0:
            return
        last = self._last.get(host, 0.0)
        delta = time.monotonic() - last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last[host] = time.monotonic()


class HttpClient:
    """极简 HTTP 客户端：GET JSON / GET bytes，带缓存、重试与连接复用。"""

    def __init__(self, cache_dir=None, timeout=DEFAULT_TIMEOUT, max_retries=MAX_RETRIES,
                 min_interval=0.0, cache=True):
        self.cache_dir = pathlib.Path(cache_dir) if cache_dir else CACHE_DIR
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache = cache
        self.limiter = _RateLimiter(min_interval)
        self._conns = {}
        self._client = _httpx.Client(timeout=timeout, follow_redirects=True,
                                     headers={"User-Agent": UA}) if _httpx else None
        self.stats = {"requests": 0, "cache_hits": 0, "retries": 0, "errors": 0}

    # -- cache -------------------------------------------------------------
    def _cache_path(self, url):
        return self.cache_dir / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".json")

    def _cache_load(self, url):
        if not self.cache:
            return None
        try:
            return json.loads(self._cache_path(url).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _cache_store(self, url, entry):
        if not self.cache:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_path(url).write_text(
                json.dumps(entry, ensure_ascii=False), encoding="utf-8", newline="\n")
        except OSError:
            pass

    # -- transport ---------------------------------------------------------
    def _conn(self, scheme, host):
        key = (scheme, host)
        conn = self._conns.get(key)
        if conn is None:
            cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
            conn = cls(host, timeout=self.timeout)
            self._conns[key] = conn
        return conn

    def _request_httpclient(self, url, headers):
        parts = urllib.parse.urlsplit(url)
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        conn = self._conn(parts.scheme, parts.netloc)
        try:
            conn.request("GET", path, headers=headers)
            resp = conn.getresponse()
            body = resp.read()
            status = resp.status
            resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        except (http.client.HTTPException, OSError):
            # 长连接可能已被对端关闭：丢弃后重试一次新连接
            self._conns.pop((parts.scheme, parts.netloc), None)
            conn.close()
            conn = self._conn(parts.scheme, parts.netloc)
            conn.request("GET", path, headers=headers)
            resp = conn.getresponse()
            body = resp.read()
            status = resp.status
            resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        if status == 304:
            raise HttpError(304, url)
        if status >= 400:
            raise HttpError(status, url, body[:200].decode("utf-8", "replace"))
        return body, resp_headers

    def _request_httpx(self, url, headers):
        resp = self._client.get(url, headers=headers)
        if resp.status_code == 304:
            raise HttpError(304, url)
        if resp.status_code >= 400:
            raise HttpError(resp.status_code, url, resp.text[:200])
        return resp.content, {k.lower(): v for k, v in resp.headers.items()}

    def get(self, url, headers=None, cache=None):
        """GET 原始字节。返回 (body, headers)。304 命中时返回缓存体。"""
        headers = dict(headers or {})
        headers.setdefault("User-Agent", UA)
        use_cache = self.cache if cache is None else cache
        cached = self._cache_load(url) if use_cache else None
        if cached:
            if cached.get("etag"):
                headers.setdefault("If-None-Match", cached["etag"])
            if cached.get("last_modified"):
                headers.setdefault("If-Modified-Since", cached["last_modified"])

        last_err = None
        for attempt in range(self.max_retries + 1):
            self.limiter.wait(urllib.parse.urlsplit(url).netloc)
            self.stats["requests"] += 1
            try:
                if self._client is not None:
                    body, resp_headers = self._request_httpx(url, headers)
                else:
                    body, resp_headers = self._request_httpclient(url, headers)
                self._cache_store(url, {
                    "etag": resp_headers.get("etag"),
                    "last_modified": resp_headers.get("last-modified"),
                    "body": body.decode("utf-8", "replace"),
                })
                return body, resp_headers
            except HttpError as err:
                if err.status == 304 and cached:
                    self.stats["cache_hits"] += 1
                    return cached["body"].encode("utf-8"), {}
                last_err = err
                if err.status not in RETRY_STATUS or attempt >= self.max_retries:
                    raise
            except (urllib.error.URLError, OSError, socket.timeout) as err:
                last_err = err
                if attempt >= self.max_retries:
                    raise
            self.stats["retries"] += 1
            # 指数退避 + 抖动，避免多个 worker 同时重试
            time.sleep(min(8.0, (2 ** attempt) * 0.5) * (0.7 + random.random() * 0.6))
        raise last_err  # pragma: no cover

    def get_json(self, url, headers=None, cache=None, timeout=None):
        old = self.timeout
        if timeout is not None:
            self.timeout = timeout
        try:
            body, _ = self.get(url, headers=headers, cache=cache)
        finally:
            self.timeout = old
        return json.loads(body.decode("utf-8"))

    def close(self):
        if self._client is not None:
            self._client.close()
        for conn in self._conns.values():
            try:
                conn.close()
            except OSError:
                pass
        self._conns.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


_DEFAULT = None


def default_client():
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = HttpClient()
    return _DEFAULT


def http_json(url, headers=None, timeout=DEFAULT_TIMEOUT):
    """兼容旧接口：一次性 GET JSON（走默认客户端，享受缓存与重试）。"""
    client = default_client()
    old = client.timeout
    client.timeout = timeout
    try:
        return client.get_json(url, headers=headers)
    finally:
        client.timeout = old
