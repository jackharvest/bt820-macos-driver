"""TSPL job construction.

Verb set and defaults mirror what the stock Windows BT820Render.dll emits.
"""
from . import MEDIA_W_IN, MEDIA_H_IN, MEDIA_H
from .render import IMG_BYTES


def build(bw, height, density=8, speed=4, gap_mm=2.0, bline_mm=None, direction=0):
    """Wrap a 1-bit image in a complete TSPL print job.

    PIL's "1" mode packs pixels MSB-first with 0 == black, which is already
    exactly TSPL's BITMAP convention -- no inversion needed.
    """
    if bline_mm is not None:
        media = f"BLINE {bline_mm:.1f} mm,0 mm\r\n".encode()
    else:
        media = f"GAP {gap_mm:.1f} mm,0 mm\r\n".encode()

    y = max(0, (MEDIA_H - height) // 2)
    job = (
        f"SIZE {MEDIA_W_IN * 25.4:.1f} mm,{MEDIA_H_IN * 25.4:.1f} mm\r\n".encode()
        + media
        + f"DIRECTION {direction}\r\n".encode()
        + b"REFERENCE 0,0\r\n"
        + b"OFFSET 0 mm\r\n"
        + b"SET TEAR ON\r\n"
        + b"SET CUTTER OFF\r\n"
        + b"SET PEEL OFF\r\n"
        + f"DENSITY {density}\r\n".encode()
        + f"SPEED {speed}\r\n".encode()
        + b"CLS\r\n"
        + f"BITMAP 0,{y},{IMG_BYTES},{height},0,".encode()
        + bw.tobytes()
        + b"\r\n"
    )
    return job


def print_cmd(copies=1):
    return f"PRINT {copies},1\r\n".encode()


def calibrate(gap_mm=2.0):
    """Re-run gap sensing. Feeds a few blank labels."""
    return (
        f"SIZE {MEDIA_W_IN * 25.4:.1f} mm,{MEDIA_H_IN * 25.4:.1f} mm\r\n".encode()
        + f"GAP {gap_mm:.1f} mm,0 mm\r\n".encode()
        + b"SET TEAR ON\r\nAUTODETECT\r\n"
    )
