# BT820 Label Printer for macOS

Print 4×6 shipping labels on the **REKDOM BT820** from a Mac.

macOS has no driver for this printer, and the vendor's download site is
frequently down. This is a complete replacement — print from the command line,
or add it as a normal printer and just hit **⌘P**.

Works on macOS 13 and later, including macOS 26 (Tahoe), where Apple removed the
older printer-driver mechanisms that tools like this used to rely on.

---

## Install

Pick whichever suits you.

### Homebrew — recommended

```sh
brew install jackharvest/tap/bt820
```

Works on both Apple Silicon and Intel, and there are no security warnings to
click through.

### Installer

Download **`BT820-1.0.0.pkg`** from
[Releases](https://github.com/jackharvest/bt820/releases) and double-click it.
Nothing else needs to be installed first.

Two things to know:

- macOS will say the app "cannot be opened because it is from an unidentified
  developer." That's expected — this installer isn't signed with a paid Apple
  developer certificate. **Right-click the .pkg → Open → Open**, or go to
  System Settings → Privacy & Security and click **Open Anyway**.
- It's **Apple Silicon only** (M1 and later). On an Intel Mac, use Homebrew.

### From source

```sh
git clone https://github.com/jackharvest/bt820.git
cd bt820 && ./install.sh
```

Needs Homebrew and Python 3. Everything lands in `.venv/` inside the folder.

---

## Print a label

```sh
bt820print label.pdf
```

PDFs, PNGs, JPEGs and GIFs all work. Carrier labels (UPS, FedEx, USPS) usually
arrive as a 6×4 landscape file — those are rotated upright and scaled to fit
automatically, so most of the time there's nothing to configure.

Check the printer is talking to you:

```sh
bt820print --status
```

See what a label will look like *before* using one:

```sh
bt820print --preview check.png label.pdf
```

### Options you might actually want

| | |
|---|---|
| `-n 3` | print 3 copies |
| `-d 12` | darker (0–15, default 8) |
| `-s 2` | slower, which prints cleaner (2–4) |
| `-r 180` | rotate: `cw`, `ccw`, `180`, `none` |
| `-p 2` | print page 2 of a multi-page PDF |
| `--dither` | for photos — see the warning under Troubleshooting |

---

## Print from any app (⌘P)

```sh
bt820ctl start
```

That's it. **BT820** now shows up in the normal macOS print dialog from any
app, and it comes back automatically after a reboot.

```sh
bt820ctl status         # is it running? is the printer ready?
bt820ctl log            # what happened to my last job
bt820ctl dryrun on      # test without wasting labels
bt820ctl stop           # turn it off
bt820ctl uninstall      # remove it completely
```

`dryrun on` makes jobs render to a PNG in
`~/Library/Application Support/bt820/` instead of printing — handy for checking
layout before committing a label to it.

---

## Troubleshooting

**The label prints upside down.**
Add `--direction 1`.

**The printer spits out blank labels and keeps going.**
It can't find the gaps between labels. If your labels have a black mark on the
back instead of a die-cut gap, use `--bline 3` (the mark height in mm).
Otherwise re-run the sensor calibration:

```sh
bt820print --calibrate
```

**Barcodes won't scan.**
Don't use `--dither` on anything with a barcode — it breaks up the bars. Try a
darker print (`-d 12`) or a slower one (`-s 2`) instead. `--threshold` also
helps: lower puts down more ink.

**Nothing prints and `--status` says it can't find the printer.**
Check the USB cable and that the printer is powered on. If you installed from
source or Homebrew, make sure `libusb` is present (`brew install libusb`).

**The ⌘P queue stopped working.**

```sh
bt820ctl stop && bt820ctl start
```

**The print is very slightly narrower than the label.**
That's deliberate — 3.98" instead of 4.00". See "Why 3.98 inches" below.

---

## How it works

The BT820 is a **rebadged Rongta RP4xx** and speaks **TSPL**, TSC's label
language. That isn't documented anywhere — it came out of picking apart the
bundled Windows driver:

| Evidence | Where |
|---|---|
| Literal string `TSPL` | `BT820dpi.XPD`, offset `0x48` |
| `SIZE` / `GAP` / `DIRECTION` / `DENSITY` / `SPEED` / `BITMAP` / `PRINT 1,1` | format strings in `BT820Render.dll` |
| `0xCB 0xCB` = **203 × 203 dpi** | `BT820dpi.XPD`, offset `0x8C` |
| Rongta origin | `RongtaUSBMon.dll`, `RP4xxDriverInstall.exe` |

Over USB it's an ordinary printer-class device — **`0x0FE6:0x811E`**, bulk OUT
`0x01`, bulk IN `0x81`. So this writes TSPL straight to that endpoint rather
than going through a driver.

The ⌘P queue is a local **IPP Everywhere** printer (`ippeveprinter`) running as
a LaunchAgent, with a CUPS queue pointed at it. macOS still supports driverless
IPP printers, so this works without any of the driver machinery Apple removed.

Nothing here needs `sudo`, installs a kext, or touches a system file. Everything
lives in your home folder (or `/usr/local` if you used the installer), and
`bt820ctl uninstall` removes all of it.

### Why 3.98 inches

TSPL's `BITMAP` command takes its width in whole **bytes**, and a 4" label at
203 dpi is 812 dots — not divisible by 8. Rounding up to 816 risks driving the
print head past its edge, so it rounds down to 808. The missing 0.02" comes out
of the margin, not the label content.

### Notes for anyone building on this

Three things cost real time to work out, all in `share/bt820.conf`:

- `ippeveprinter` **rejects `-f`, `-M` and `-m` when `-a` is given** — it just
  prints its usage text with no explanation. Formats and make/model have to go
  in the attributes file instead.
- Using `-a` **replaces** ippeveprinter's built-in attributes, which hardcode US
  Letter. The 4×6 media collections must be spelled out in full or macOS lays
  every job out at Letter size and the label prints tiny in one corner.
- Don't declare `document-format-default`/`-supported` there — ippeveprinter
  emits its own, and the duplicates make the printer fail IPP validation.

And on macOS 26 specifically: `lpadmin -m raw` and `-m everywhere` are both
gone. A bare `lpadmin -v ipp://...` with **no** `-m` is the only form that still
creates a working queue.

---

## Project layout

```
bin/bt820print            CLI
bin/bt820ctl              queue lifecycle
bin/bt820-ippfilter       invoked by ippeveprinter once per job
src/bt820/device.py       USB transport + TSPL status queries
src/bt820/render.py       PDF/image -> 1-bit bitmap at 203 dpi
src/bt820/tspl.py         TSPL job construction
share/bt820.conf          IPP attributes (4x6 media, formats, make/model)
packaging/build-pkg.sh    build the .pkg installer
packaging/gen-formula.py  regenerate the Homebrew formula from PyPI
```

The scripts run from either layout — this repo, or a flat install like
`/usr/local/lib/bt820` — by probing for `../share/bt820.conf`.

## Releasing

```sh
packaging/build-pkg.sh            # -> build/BT820-<version>.pkg
packaging/gen-formula.py v1.0.0   # refresh PyPI checksums
```

Tag and push, then fill in the formula's `sha256` (it can only be computed once
GitHub is serving the tag tarball):

```sh
curl -sL https://github.com/jackharvest/bt820/archive/refs/tags/v1.0.0.tar.gz | shasum -a 256
```

The formula lives in `jackharvest/homebrew-tap` as `Formula/bt820.rb`.

## License

MIT — see [LICENSE](LICENSE).

Not affiliated with REKDOM, Rongta, or TSC. Built by reverse-engineering a
printer I own.
