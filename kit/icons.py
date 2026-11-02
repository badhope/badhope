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


_HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
# 深色背景上的可读下限：相对亮度低于此值就把颜色提亮。
_LUMA_FLOOR = 0.42


def _luma(hex_color):
    """感知亮度（ITU-R BT.601 加权，0–1）。"""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except (ValueError, IndexError):
        return None
    return 0.299 * r + 0.587 * g + 0.114 * b


def _lighten(hex_color, target=_LUMA_FLOOR):
    """把颜色朝白色混合到目标亮度，保留色相。已是亮色则原样返回。"""
    luma = _luma(hex_color)
    if luma is None or luma >= target:
        return hex_color
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    # 解 luma' = luma + (1-luma)*t 中的混合比例 t
    t = (target - luma) / max(1e-6, 1.0 - luma)
    r, g, b = (round(c + (255 - c) * t) for c in (r, g, b))
    return "#%02X%02X%02X" % (r, g, b)


def brighten_for_dark(body, target=_LUMA_FLOOR):
    """把图标内部过暗的填充色提亮，保证深色背景上的可辨识度。

    只处理 `fill="#rrggbb"` / `stroke="#rrggbb"`，不动 none / url(#…) /
    具名颜色；同一颜色重复出现时结果一致，因此仍满足字节级可复现。
    """
    cache = {}

    def repl(match):
        prefix, color = match.group(1), match.group(2)
        if color not in cache:
            cache[color] = _lighten("#" + color, target).lstrip("#")
        return '%s="#%s"' % (prefix, cache[color])

    return re.sub(r'\b(fill|stroke)="#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})"', repl, body)


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
    if color:
        # 单色图标：外层 fill 由调用方指定，内部硬编码的深色需清掉否则不生效
        style = ' fill="%s"' % color
        body = re.sub(r'\bfill="#[0-9a-fA-F]{3,6}"', '', body)
    else:
        # 彩色图标：保留原配色，但把深到看不见的颜色提亮
        style = ""
        body = brighten_for_dark(body)
    return ('<svg x="0" y="0" width="%s" height="%s" viewBox="%s"%s%s>%s</svg>'
            % (size, size, viewbox, ns, style, body))
