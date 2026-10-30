# -*- coding: utf-8 -*-
"""打字机动画卡（readme-typing-svg `src/templates/main.php` 的移植）。

机制：文字挂在 `<textPath>` 上，对 `<path d>` 做 SMIL `<animate>` ——
`d` 从 `m0,y h0`（空）增长到 `m0,y h<width>`（满），文字就像被逐字打出。
关键帧（单行模式，与原版逐值一致）：

    dur     = duration + pause
    keyTimes = [0, 0.8*d/(d+p), (0.8*d+p)/(d+p), 1]
    values   = [空, 满, 满, 空]          # 80% 时间打字，随后停留，再清空
    begin    = "d<上一行>.end"；第一行 "0s;d<最后一行>.end"（循环）

多行模式：每行一条固定 path，逐行淡入（lineHeight = size + 5）。
字体：等宽栈即可（GitHub/GitCode 的 SVG 沙箱不允许外链资源，原版把
Google Fonts base64 内嵌 —— 我们直接用系统等宽栈避免外链）。
"""

import xml.sax.saxutils as xu

from .emoji import parse_emojis

#: 与 readme-typing-svg `$DEFAULTS` 同源的默认值
DEFAULTS = {
    "font": "monospace",
    "color": "#36BCF7",
    "background": "#00000000",
    "size": 20,
    "width": 400,
    "height": 50,
    "center": False,
    "vcenter": False,
    "duration": 5000,
    "pause": 0,
    "repeat": True,
    "separator": ";",
}

import re as _re
_HEXPAT = _re.compile(r"[^0-9A-Fa-f]")


def _clean_color(value, default):
    """原版清洗规则：只留 hex，长度必须是 3/4/6/8，否则回退默认。"""
    cleaned = _HEXPAT.sub("", str(value))
    if len(cleaned) in (3, 4, 6, 8):
        return "#" + cleaned
    return default


def typing_svg(lines, lang="md", theme=None, options=None):
    """渲染打字机 SVG。lines 为字符串列表；theme 用于取默认配色。"""
    t = theme or {}
    opts = dict(DEFAULTS)
    if options:
        opts.update(options)
    # 默认色：主题 gold_bright 优先（消除 typing 卡与主题的配色割裂）。
    # 注意 DEFAULTS 里 color 有占位值，所以必须显式覆盖而不是 setdefault。
    if not options or "color" not in (options or {}):
        opts["color"] = t.get("gold_bright") or DEFAULTS["color"]
    color = _clean_color(opts["color"], DEFAULTS["color"])
    background = _clean_color(opts["background"], DEFAULTS["background"])
    width = max(1, int(opts["width"]))
    height = max(1, int(opts["height"]))
    size = max(1, int(opts["size"]))
    duration = max(1, int(opts["duration"]))
    pause = max(0, int(opts["pause"]))
    repeat = bool(opts["repeat"])
    center = bool(opts["center"])
    vcenter = bool(opts["vcenter"])
    # emoji 短代码 → Unicode（在 XML 转义之前做，保持与其他卡一致的文案管道）
    lines = [xu.escape(parse_emojis(str(x))) for x in lines if str(x).strip()] or ["…"]
    total = len(lines)

    text_attrs = (
        'font-family="\'{font}\', monospace"'.format(font=opts["font"]) +
        ' fill="%s" font-size="%d"' % (color, size)
    )
    if vcenter:
        text_attrs += " dominant-baseline='middle'"
    text_attrs += " x='%s' text-anchor='%s'" % (
        "50%" if center else "0%", "middle" if center else "start")

    anims, paths = [], []
    if len(lines) == 1:
        y = height / 2
        paths.append('<path id="path0" fill="none" d="m0,%s h0"/>' % y)
        last = "d%d.end" % (total - 1) if repeat else None
        begin = "0s;%s" % last if repeat else "0s"
        d_p = duration + pause
        key_times = "0;%.8f;%.8f;1" % (0.8 * duration / d_p, (0.8 * duration + pause) / d_p)
        values = "m0,%s h0;m0,%s h%d;m0,%s h%d;m0,%s h0" % (y, y, width, y, width, y)
        if not repeat:
            values = values.rsplit(";", 1)[0] + ";m0,%s h%d" % (y, width)
        anims.append(
            '<animate id="d0" attributeName="d" dur="%dms" begin="%s" '
            'keyTimes="%s" values="%s" calcMode="linear"%s repeatCount="%s"/>'
            % (d_p, begin, key_times, values,
               ' fill="freeze"' if not repeat else "", "indefinite" if repeat else "1")
        )
    else:
        line_height = size + 5
        for i, line in enumerate(lines):
            y = (i + 1) * line_height
            paths.append('<path id="path%d" fill="none" d="m0,%s h0"/>' % (i, y))
            line_duration = (duration + pause) * (i + 1)
            first = "0;%.8f" % (i / (i + 1))
            second = "%.8f;%.8f" % (i / (i + 1) + duration / line_duration, 1)
            values = "m0,%s h0;m0,%s h0;m0,%s h%d;m0,%s h%d" % (
                y, y, y, width, y, width)
            begin = "0s;d%d.end" % (total - 1) if repeat else "0s"
            anims.append(
                '<animate id="d%d" attributeName="d" dur="%dms" begin="%s" '
                'keyTimes="%s;%s" values="%s" calcMode="linear" fill="freeze" '
                'repeatCount="%s"/>'
                % (i, line_duration, begin, first, second, values,
                   "indefinite" if repeat else "1")
            )
    for i, line in enumerate(lines):
        paths.append(
            '<text %s><textPath xlink:href="#path%d">%s</textPath></text>'
            % (text_attrs, i, line)
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        'viewBox="0 0 %d %d" width="%d" height="%d" '
        'style="background-color: %s;" role="img" aria-label="%s">'
        '<style>path{stroke:none;}</style>'
        '%s%s'
        '</svg>'
        % (width, height, width, height, background,
           xu.escape(" ".join(lines), {'"': "&quot;"}),
           "".join(paths), "".join(anims))
    )
