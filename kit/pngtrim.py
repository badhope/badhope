# -*- coding: utf-8 -*-
"""PNG 尾部空白裁剪（纯标准库）。

为什么需要：Chromium 无头截图的尺寸由 `--window-size` 决定，而页面实际高度
事先不可知。给一个保守的大高度再裁掉尾部纯背景行，比反复试探更稳，
也不会在成品里留下大片空白。

只支持本项目截图会遇到的形态：8 位深、非隔行、RGB / RGBA。其他形态原样返回。
"""

import struct
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _chunks(data):
    pos = len(PNG_SIG)
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        yield ctype, body
        pos += 12 + length


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _unfilter(raw, width, height, channels):
    stride = width * channels
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if ftype == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                upleft = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(left, prev[i], upleft)) & 0xFF
        elif ftype != 0:
            raise ValueError("unsupported PNG filter %d" % ftype)
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def _encode(width, height, channels, pixels):
    color_type = 6 if channels == 4 else 2
    stride = width * channels
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter: none
        raw.extend(pixels[y * stride:(y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)

    def chunk(ctype, body):
        return (struct.pack(">I", len(body)) + ctype + body
                + struct.pack(">I", zlib.crc32(ctype + body) & 0xFFFFFFFF))

    return (PNG_SIG + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def trim_bottom(path, background=None, tolerance=6):
    """裁掉尾部与最后一行同色（或指定背景色）的行。返回 (原高, 新高)。"""
    data = path.read_bytes()
    if not data.startswith(PNG_SIG):
        return None
    header = None
    idat = bytearray()
    for ctype, body in _chunks(data):
        if ctype == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif ctype == b"IDAT":
            idat.extend(body)
    if header is None:
        return None
    width, height, depth, color_type, _comp, _filt, interlace = header
    if depth != 8 or interlace != 0 or color_type not in (2, 6):
        return None
    channels = 4 if color_type == 6 else 3
    try:
        pixels = _unfilter(zlib.decompress(bytes(idat)), width, height, channels)
    except (zlib.error, ValueError):
        return None

    stride = width * channels
    ref = background if background else tuple(pixels[(height - 1) * stride:
                                                     (height - 1) * stride + channels])
    if len(ref) not in (3, 4):
        return None

    def row_is_ref(y):
        base = y * stride
        for x in range(width):
            offset = base + x * channels
            for ch in range(3):
                if abs(pixels[offset + ch] - ref[ch]) > tolerance:
                    return False
        return True

    bottom = height
    while bottom > 1 and row_is_ref(bottom - 1):
        bottom -= 1
    if bottom == height:
        return (height, height)
    out = _encode(width, bottom, channels, pixels[:bottom * stride])
    path.write_bytes(out)
    return (height, bottom)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="trim trailing blank rows from a PNG")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    for name in args.paths:
        import pathlib
        result = trim_bottom(pathlib.Path(name))
        print("%s -> %s" % (name, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
