"""Command line front end: bt820print."""
import argparse
import os
import pathlib
import sys

from . import __version__, DPI
from .device import BT820
from .render import render, page_count, IMG_W
from . import tspl


CONFIG = pathlib.Path(
    os.path.expanduser("~/Library/Application Support/bt820/config"))


def load_config():
    """Read persistent defaults, so the print queue behaves like the CLI.

    Jobs arriving over the queue get no command-line flags, so anything that
    has to hold for every job -- notably continuous vs gap media -- has to
    live here.
    """
    cfg = {}
    try:
        for line in CONFIG.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    except OSError:
        pass
    return cfg


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="bt820print",
        description="Print PDFs and images on a REKDOM BT820 4x6 thermal label printer.",
        epilog="""examples:
  bt820print label.pdf              print a shipping label
  bt820print -n 3 label.png         three copies
  bt820print --preview out.png x.pdf    check the layout without using a label
  bt820print --status               is the printer connected and ready?

  bt820ctl start                    add BT820 to the macOS print dialog
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("file", nargs="?", help="PDF or image to print")
    p.add_argument("-n", "--copies", type=int, default=1)
    p.add_argument("-p", "--pages", default="all",
                   help="'all', or a 1-based page number for multi-page PDFs")
    p.add_argument("-d", "--density", type=int, default=8, choices=range(0, 16),
                   metavar="0-15", help="burn darkness (default 8)")
    p.add_argument("-s", "--speed", type=int, default=4, choices=range(2, 5),
                   metavar="2-4", help="inches/sec (default 4)")
    p.add_argument("-r", "--rotate", default="auto",
                   choices=["auto", "none", "cw", "ccw", "180"])
    p.add_argument("--direction", type=int, default=0, choices=[0, 1],
                   help="flip feed orientation if labels print upside down")
    p.add_argument("--threshold", type=int, default=128,
                   help="black/white cutoff, 0-255 (default 128)")
    p.add_argument("--dither", action="store_true",
                   help="dither instead of threshold -- for photos, not barcodes")
    p.add_argument("--bline", type=float, metavar="MM",
                   help="use black-mark sensing instead of gap sensing")
    p.add_argument("--gap", type=float, default=None, metavar="MM",
                   help="gap between die-cut labels in mm (default 2.0)")
    p.add_argument("--continuous", action="store_true",
                   help="continuous media: do not look for gaps between labels. "
                        "Use this when feeding labels one at a time, otherwise "
                        "the printer reprints on reload.")
    p.add_argument("--preview", metavar="PNG",
                   help="write the exact 1-bit bitmap here instead of printing")
    p.add_argument("--wait", type=float, default=60.0, metavar="SEC",
                   help="how long to wait for the printer to be ready, e.g. for "
                        "the next hand-fed label (default 60)")
    p.add_argument("--status", action="store_true", help="report printer status and exit")
    p.add_argument("--calibrate", action="store_true",
                   help="re-run gap sensing (feeds a few blank labels)")
    p.add_argument("--version", action="version", version=f"bt820 {__version__}")
    if not (argv or sys.argv[1:]):
        p.print_help()
        return 0
    a = p.parse_args(argv)

    # Persistent defaults, overridden by anything given explicitly.
    cfg = load_config()
    if a.gap is None:
        a.gap = 0.0 if cfg.get("media") == "continuous" else float(cfg.get("gap", 2.0))
    if a.continuous:
        a.gap = 0.0
    for key, attr, cast in (("density", "density", int), ("speed", "speed", int),
                            ("direction", "direction", int),
                            ("threshold", "threshold", int)):
        if key in cfg and p.get_default(attr) == getattr(a, attr):
            setattr(a, attr, cast(cfg[key]))

    if a.status:
        with BT820() as dev:
            code, msg = dev.status()
            info = dev.info()
            print(f"codepage : {info['codepage']}")
            print(f"serial   : {info['serial']}")
            print(f"status   : {msg}" + (f" (0x{code:02X})" if code is not None else ""))
        return 0 if code == 0 else 1

    if a.calibrate:
        with BT820() as dev:
            dev.write(tspl.calibrate(a.gap))
        print("calibration sent -- printer will feed to find the next gap")
        return 0

    if not a.file:
        p.error("give me a file to print, or use --status / --calibrate")

    pages = range(page_count(a.file)) if a.pages == "all" else [int(a.pages) - 1]

    jobs = []
    for i in pages:
        bw, h = render(a.file, page=i, rotate=a.rotate,
                       threshold=a.threshold, dither=a.dither)
        if a.preview:
            out = a.preview if len(list(pages)) == 1 else f"{a.preview[:-4]}-{i+1}.png"
            bw.save(out)
            print(f"page {i+1}: {IMG_W}x{h} dots "
                  f"({IMG_W/DPI:.2f}\" x {h/DPI:.2f}\") -> {out}")
            continue
        jobs.append(tspl.build(bw, h, density=a.density, speed=a.speed,
                               gap_mm=a.gap, bline_mm=a.bline,
                               direction=a.direction) + tspl.print_cmd(a.copies))

    if a.preview:
        return 0

    with BT820() as dev:
        # Everything except the "printing" bit means we should not start a job.
        # Wait first: the printer may still be positioning paper from the last
        # job, or waiting for the next hand-fed label.
        code, msg = dev.status()
        if code is not None and (code & ~0x20) != 0:
            hint = "feed a label" if code & 0x04 else "waiting"
            print(f"printer says: {msg} -- {hint} "
                  f"({a.wait:g}s)...", file=sys.stderr)
            code, msg = dev.wait_ready(timeout=a.wait)
        if code is not None and (code & ~0x20) != 0:
            print(f"printer not ready: {msg}", file=sys.stderr)
            if code & 0x04:
                print("Load a label and run this again.", file=sys.stderr)
            return 1
        for n, job in enumerate(jobs, 1):
            dev.write(job)
        code, msg = dev.status()
    print(f"printed {len(jobs)} label(s) x{a.copies} -- printer status: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
