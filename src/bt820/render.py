"""Turn PDFs and images into 1-bit bitmaps sized for 4x6 media at 203 dpi."""
from PIL import Image

from . import DPI, MEDIA_W, MEDIA_H

# TSPL's BITMAP verb takes width in whole BYTES, and 812 is not divisible by 8.
# Rounding up to 816 dots risks overrunning the print head, so round down.
IMG_BYTES = MEDIA_W // 8          # 101
IMG_W = IMG_BYTES * 8             # 808 dots == 3.98"

ROTATIONS = {
    "none": None,
    "cw":   Image.ROTATE_270,
    "ccw":  Image.ROTATE_90,
    "180":  Image.ROTATE_180,
}


def _sniff(path):
    with open(path, "rb") as fh:
        return fh.read(8)


def load(path, page=0):
    """Return a grayscale PIL image, rasterizing PDFs at 2x target density."""
    head = _sniff(path)
    if head[:7] == b"UNIRAST":
        # Apple Raster, i.e. what iOS sends over AirPrint. Already rasterised
        # at the size and resolution we advertise, so no rescaling is needed
        # beyond the usual fit.
        from . import urf
        with open(path, "rb") as fh:
            return urf.decode(fh.read(), page)
    if head[:5] == b"%PDF-":
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(path)
        # Render at 2x so the downsample to 203 dpi has detail to average.
        bmp = doc[page].render(scale=2 * DPI / 72)
        return bmp.to_pil().convert("L")
    return Image.open(path).convert("L")


def page_count(path):
    head = _sniff(path)
    if head[:7] == b"UNIRAST":
        from . import urf
        with open(path, "rb") as fh:
            return urf.page_count(fh.read(12))
    if head[:5] != b"%PDF-":
        return 1
    import pypdfium2 as pdfium
    return len(pdfium.PdfDocument(path))


def render(path, page=0, rotate="auto", threshold=128, dither=False):
    """Return (1-bit image, height in dots) ready for TSPL BITMAP."""
    im = load(path, page)

    if rotate == "auto":
        # Carrier labels (UPS, FedEx) ship as 6x4 landscape; turn them upright.
        op = Image.ROTATE_270 if im.width > im.height else None
    else:
        op = ROTATIONS[rotate]
    if op is not None:
        im = im.transpose(op)

    # Contain within the printable area, preserving aspect ratio.
    scale = min(IMG_W / im.width, MEDIA_H / im.height)
    size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
    im = im.resize(size, Image.LANCZOS)

    if dither:
        bw = im.convert("1")                                   # photos
    else:
        bw = im.point(lambda p: 0 if p < threshold else 255, "1")   # barcodes/text

    # Pad to a whole number of bytes per row so TSPL's row stride matches.
    if bw.width != IMG_W:
        canvas = Image.new("1", (IMG_W, bw.height), 1)         # 1 == white
        canvas.paste(bw, ((IMG_W - bw.width) // 2, 0))
        bw = canvas
    return bw, bw.height
