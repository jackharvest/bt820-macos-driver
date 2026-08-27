"""Decoder for Apple Raster (URF / UNIRAST, image/urf).

This is what iOS sends over AirPrint. There is no public Apple specification;
the layout below follows the long-standing reverse-engineering work in
AlanQuatermain/unirast and mbevand/urf2image.

Layout:
    file    b"UNIRAST\\0"  then uint32 BE page count
    page    32-byte header (below), then encoded lines
    line    1 byte repeat count (value + 1 lines share this data), then
            PackBits-style packets until `width` pixels have been produced:
                code == -128  fill the rest of the line with 0xFF (white)
                code >=    0  repeat the next pixel (code + 1) times
                code <     0  copy (-code + 1) literal pixels
"""
import struct

MAGIC = b"UNIRAST\0"
PAGE_HEADER = struct.Struct(">4B7I")   # bpp, colorspace, duplex, quality + 7 BE uint32
WHITE = 0xFF


class UrfError(ValueError):
    pass


def is_urf(data):
    return data[:7] == MAGIC[:7]


def page_count(data):
    if not is_urf(data):
        raise UrfError("not a URF file")
    return struct.unpack(">I", data[8:12])[0]


def _decode_line(data, off, width, ps):
    """Decode one raster line; return (line bytes, new offset)."""
    line = bytearray()
    pixels = 0
    while pixels < width:
        if off >= len(data):
            raise UrfError("truncated line data")
        code = data[off] - 256 if data[off] > 127 else data[off]
        off += 1
        if code == -128:                       # rest of the line is blank
            line += bytes([WHITE]) * (width - pixels) * ps
            pixels = width
        elif code >= 0:                        # repeat one pixel
            n = min(code + 1, width - pixels)
            line += data[off:off + ps] * n
            off += ps
            pixels += n
        else:                                  # literal run
            n = min(-code + 1, width - pixels)
            line += data[off:off + n * ps]
            off += n * ps
            pixels += n
    return bytes(line), off


def decode(data, page=0):
    """Decode one page of a URF stream into a PIL image."""
    from PIL import Image

    if not is_urf(data):
        raise UrfError("not a URF file")
    total = page_count(data)
    if page >= total:
        raise UrfError(f"page {page + 1} of {total} requested")

    off = 12
    for index in range(total):
        bpp, colorspace, _duplex, _quality, _u0, _u1, width, height, dpi, _u2, _u3 = \
            PAGE_HEADER.unpack_from(data, off)
        off += PAGE_HEADER.size
        if bpp % 8:
            raise UrfError(f"unsupported bit depth {bpp}")
        ps = bpp // 8
        mode = {1: "L", 3: "RGB", 4: "CMYK"}.get(ps)
        if mode is None:
            raise UrfError(f"unsupported pixel size {ps} bytes")

        rows = bytearray()
        produced = 0
        while produced < height:
            if off >= len(data):
                raise UrfError("truncated page data")
            repeat = data[off] + 1
            off += 1
            line, off = _decode_line(data, off, width, ps)
            repeat = min(repeat, height - produced)
            rows += line * repeat
            produced += repeat

        if index == page:
            img = Image.frombytes(mode, (width, height), bytes(rows))
            img.info["dpi"] = (dpi, dpi)
            return img.convert("L")
    raise UrfError("page not found")
