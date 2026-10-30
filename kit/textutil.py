# -*- coding: utf-8 -*-
"""纯文本工具：转义、裁剪、数字格式、确定性随机、月份解析。"""

import datetime
import functools
import random
import xml.sax.saxutils as xu
import zlib

def esc(text):
    return xu.escape(str(text), {'"': "&quot;"})

def seed_of(acct):
    return zlib.crc32(acct["home_display"].encode("utf-8"))

@functools.lru_cache(maxsize=128)
def _seed_value(home_display, salt):
    """缓存 CRC 种子。注意：不能缓存 Random 实例本身——它是有状态的，
    复用会让第二次调用接着上一次的序列走，产物就不再确定。"""
    return zlib.crc32(home_display.encode("utf-8")) ^ zlib.crc32(salt.encode("utf-8"))


def rng(acct, salt=""):
    return random.Random(_seed_value(acct["home_display"], salt))

def fmt_num(v):
    try:
        return format(int(v), ",")
    except (TypeError, ValueError):
        return str(v)

@functools.lru_cache(maxsize=512)
def _char_w(char):
    return 1.0 if ord(char) > 0x2E80 else 0.6


def text_w(text, size):
    """估算文本宽度：拉丁/符号按 0.6em，CJK 按 1.0em（等宽标签用）。"""
    return sum(_char_w(ch) for ch in text) * size

def clip_w(text, max_w, size):
    """按估算像素宽度裁剪文本（CJK 1.0em / 拉丁 0.6em），超出以 … 结尾。"""
    out, used = [], 0.0
    for ch in text:
        cw = size if ord(ch) > 0x2E80 else size * 0.6
        if used + cw > max_w:
            return "".join(out).rstrip() + "…"
        out.append(ch)
        used += cw
    return "".join(out)

def clip_text(text, max_em):
    """按保守字宽（拉丁 0.55em / CJK 1.0em）裁剪文本，超出以 … 结尾。"""
    out, used = [], 0.0
    for ch in text:
        w = 1.0 if ord(ch) > 0x2E80 else 0.55
        if used + w > max_em:
            return "".join(out).rstrip() + "…"
        out.append(ch)
        used += w
    return text

def _stats_month(stats):
    """stats.json 的 as_of（YYYY-MM-DD）取月份；缺失/损坏时退回当前月。"""
    raw = str((stats or {}).get("as_of") or "")
    try:
        return int(raw[5:7])
    except (TypeError, ValueError):
        return datetime.date.today().month
