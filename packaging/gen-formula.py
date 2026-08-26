#!/usr/bin/env python3
"""Regenerate the Homebrew formula with current PyPI checksums.

Usage: gen-formula.py [git-tag]   (default: v<version from __init__.py>)

Pillow and pyusb build from source (brew supplies the image libraries);
pypdfium2 ships per-arch wheels because its sdist downloads a prebuilt pdfium
at build time, which Homebrew's sandbox blocks.
"""
import json, pathlib, re, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSION = re.search(r'__version__ = "(.*)"',
                    (ROOT/"src/bt820/__init__.py").read_text()).group(1)
TAG = sys.argv[1] if len(sys.argv) > 1 else f"v{VERSION}"
PINS = {"pyusb": "1.3.1", "pillow": "11.3.0", "pypdfium2": "5.13.0"}


def pypi(pkg, ver):
    with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/{ver}/json") as r:
        return json.load(r)["urls"]


def pick(pkg, ver, *want):
    """want == ("sdist",) or a set of substrings all present in the wheel name."""
    for f in pypi(pkg, ver):
        if want == ("sdist",):
            if f["packagetype"] == "sdist":
                return f["url"], f["digests"]["sha256"]
        elif f["filename"].endswith(".whl") and all(w in f["filename"] for w in want):
            return f["url"], f["digests"]["sha256"]
    raise SystemExit(f"no {want} for {pkg} {ver}")


def res(name, url, sha, indent="  "):
    return (f'{indent}resource "{name}" do\n'
            f'{indent}  url "{url}"\n'
            f'{indent}  sha256 "{sha}"\n'
            f'{indent}end\n')


pyusb = pick("pyusb", PINS["pyusb"], "sdist")
pillow = pick("pillow", PINS["pillow"], "sdist")
arm = pick("pypdfium2", PINS["pypdfium2"], "macosx", "arm64")
x86 = pick("pypdfium2", PINS["pypdfium2"], "macosx", "x86_64")

formula = f'''class Bt820 < Formula
  include Language::Python::Virtualenv

  desc "Driver for the REKDOM BT820 4x6 thermal label printer (Rongta RP4xx, TSPL)"
  homepage "https://github.com/jackharvest/bt820"
  url "https://github.com/jackharvest/bt820/archive/refs/tags/{TAG}.tar.gz"
  sha256 "REPLACE_AFTER_TAGGING"
  license "MIT"

  depends_on "libusb"
  depends_on "python@3.13"
  # Pillow builds from source; these are its image backends.
  depends_on "freetype"
  depends_on "jpeg-turbo"
  depends_on "libtiff"
  depends_on "little-cms2"
  depends_on "openjpeg"
  depends_on "webp"

{res("pyusb", *pyusb)}
{res("pillow", *pillow)}
  # pypdfium2's sdist fetches a prebuilt pdfium during build, which the
  # Homebrew sandbox blocks -- use the per-arch wheels instead.
  on_arm do
{res("pypdfium2", *arm, indent="    ")}  end

  on_intel do
{res("pypdfium2", *x86, indent="    ")}  end

  def install
    virtualenv_install_with_resources
    # bt820ctl finds its sibling binary and ../share/bt820.conf.
    bin.install "bin/bt820ctl", "bin/bt820-ippfilter"
    share.install "share/bt820.conf"
  end

  def caveats
    <<~EOS
      Command-line printing works now:
        bt820print label.pdf

      For a queue you can Cmd+P into (a local IPP Everywhere printer plus a
      CUPS queue named BT820, started at login):
        bt820ctl start

      To remove it again:
        bt820ctl uninstall
    EOS
  end

  test do
    assert_match "bt820", shell_output("#{{bin}}/bt820print --version")
  end
end
'''
out = ROOT/"packaging/bt820.rb"
out.write_text(formula)
print(f"wrote {out} (tag {TAG})")
