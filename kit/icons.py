# -*- coding: utf-8 -*-
"""图标资产：读取、解析、着色、内联。

热点在 `icon_svg_body`：一次全量生成会调用数百次，而源文件只有几十个。
这里用 `functools.lru_cache` 把「文件解析结果」缓存到进程级，避免重复
open/read/regex；缓存键包含 mtime/size，源文件变化会自动失效。
"""

import functools
import pathlib
import re
import shutil

import accounts as A

from .paths import ROOT

SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>")
SVG_BODY_RE = re.compile(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', re.S)


@functools.lru_cache(maxsize=256)
def _resolve(name):
    """在 data/icons 下按 si → dev 前缀找到图标文件；找不到返回 None。"""
    for prefix in A.ICON_PREFIXES:
        cand = ROOT / "data" / "icons" / ("%s-%s.svg" % (prefix, name))
        if cand.is_file():
            return str(cand)
    return None


@functools.lru_cache(maxsize=256)
def _load(key):
    """读取并解析图标：返回 (viewBox, body, has_xlink)。"""
    path, _mtime, _size = key
    text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    m = SVG_BODY_RE.search(text)
    if not m:
        return None
    viewbox, body = m.group(1), m.group(2).strip()
    return viewbox, body, "xlink:" in body


def _stat_key(path):
    st = pathlib.Path(path).stat()
    return (path, st.st_mtime_ns, st.st_size)


def icon_exists(name, prefix=None):
    """图标是否存在。prefix 指定时只查该来源（si / dev）。"""
    if prefix is None:
        return _resolve(name) is not None
    return (ROOT / "data" / "icons" / ("%s-%s.svg" % (prefix, name))).is_file()


def copy_icon_light(src, dst, color):
    """拷贝图标并确保其在深色底上可见。

    simple-icons 的 SVG 不带 fill（默认黑色），在深色 README 上不可见；
    这里给根元素补一个浅色 fill（仅当图标自身未指定）。
    """
    text = src.read_text(encoding="utf-8", errors="replace")
    m = SVG_OPEN_RE.match(text)
    if m and "fill=" not in m.group(0):
        text = text.replace(m.group(0), m.group(0)[:-1] + ' fill="%s">' % color, 1)
    dst.write_text(text, encoding="utf-8", newline="\n")


def icon_svg_body(name, size, color=None):
    """取 vendored 图标的内部图形（path/circle/...），返回可直接内联的片段。

    图标来源 devicon / simple-icons（纯几何元素，无 <style>/<class>），
    以嵌套 <svg> 承载：外层给尺寸与配色，内层保留原始 viewBox 与路径。
    color 为 None 时保留图标自身配色；否则以单色填充覆盖（外层 fill 继承）。

    个别图标（dev-go）带 xlink:href 引用，内联时须补命名空间声明，
    否则整份 SVG 会因 unbound prefix 解析失败。
    """
    path = _resolve(name)
    if path is None:
        return None
    parsed = _load(_stat_key(path))
    if parsed is None:
        return None
    viewbox, body, has_xlink = parsed
    ns = ' xmlns:xlink="http://www.w3.org/1999/xlink"' if has_xlink else ""
    style = ' fill="%s"' % color if color else ""
    return ('<svg x="0" y="0" width="%s" height="%s" viewBox="%s"%s%s>%s</svg>'
            % (size, size, viewbox, ns, style, body))
