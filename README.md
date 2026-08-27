# BT820 macOS Driver

**A macOS driver for the REKDOM BT820 4×6 thermal label printer** — the same
hardware also sold as the **Rongta RP4xx** and various rebadges. Print UPS,
FedEx, USPS and Amazon return labels from your Mac.

There is no official macOS driver for this printer, and the vendor's download
site is frequently down. This is a complete replacement: print from the command
line, or add it as a normal printer and hit **⌘P**.

Works on macOS 13 and later — **including macOS 26 (Tahoe)**, where Apple
removed raw print queues and PPD printer drivers, which is why most older
workarounds for cheap thermal printers no longer function.

### Will this work with my printer?

Check the USB ID. Plug it in and run:

```sh
system_profiler SPUSBDataType | grep -A 4 -i printer
```

If you see vendor `0x0fe6` and product `0x811e`, this driver is for your
printer, whatever name is on the box. Mine reports as `BT820 Printer`.

Other Rongta RP4xx models (RP410, RP420) speak the same TSPL language and will
very likely work, possibly needing a different USB ID in `src/bt820/__init__.py`
— but I only own a BT820, so that is untested.

---

## Install

Pick whichever suits you.

### Homebrew — recommended

```sh
brew tap jackharvest/tap
brew trust jackharvest/tap
brew install jackharvest/tap/bt820
```

Works on both Apple Silicon and Intel, and there are no security warnings to
click through. Homebrew 6 requires the `brew trust` step for any third-party
tap — without it you get *"Refusing to load formula from untrusted tap."*

### Installer

Download the **`.pkg`** from
[Releases](https://github.com/jackharvest/bt820-macos-driver/releases) and double-click it.
Nothing else needs to be installed first.

Two things to know:

- Because it was downloaded, macOS quarantines it, and it isn't signed with a
  paid Apple developer certificate — so you'll likely see *"cannot be opened
  because it is from an unidentified developer."* **Right-click the .pkg →
  Open → Open**, or approve it in System Settings → Privacy & Security.
  (A `.pkg` you built yourself is never quarantined and opens straight away.)
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
| `--wait 120` | how long to wait for the printer to be ready (default 60s) |
| `--continuous` | don't look for gaps between labels — see below |

### Feeding labels by hand

If you feed labels one at a time rather than using a roll, **tell it once**:

```sh
bt820ctl media continuous
```

Without this the printer prints **two copies of everything**. In gap mode it
finishes a label by hunting for the next gap; with nothing behind the label it
runs the paper out, decides the job never finished, and reprints the moment you
reload. Continuous media never hunts, so the job completes. Switch back with
`bt820ctl media gap` for rolls and fanfold stacks.

The setting lives in `~/Library/Application Support/bt820/config` and applies to
⌘P jobs too, which is the point — those arrive with no command-line flags.

Either way, the printer reports "out of paper" between hand-fed labels.
`bt820print` waits for the next one instead of failing, and says so:

```
printer says: out of paper -- feed a label (60s)...
```

Feed one and the job prints itself. Use `--wait` to change how long it holds on
for.

---

## Print from any app (⌘P)

```sh
bt820ctl start
```

That's it. **BT820 Label Printer** appears in System Settings → Printers &
Scanners and in every app's ⌘P dialog, and it comes back after a reboot.

```sh
bt820ctl status         # is it running? is the printer ready?
bt820ctl airprint       # can iPhones print to it, and if not, what's missing
bt820ctl log            # what happened to my last job
bt820ctl dryrun on      # test without wasting labels
bt820ctl stop           # turn it off
bt820ctl uninstall      # remove it completely
```

`dryrun on` makes jobs render to a PNG in
`~/Library/Application Support/bt820/` instead of printing — handy for checking
layout before committing a label to it.

---

## Print from an iPhone or iPad (AirPrint)

```sh
bt820ctl start
```

The printer appears in the iOS share sheet under **Print** as *BT820 Label
Printer*, on the same Wi-Fi network. Nothing to install on the phone.

This does **not** go through macOS's "Share this printer" toggle — on macOS 26
that never advertises the `URF=` capability iOS requires, so the printer stays
invisible no matter what you tick. Instead the driver's own IPP printer
registers the `_universal` Bonjour subtype that iOS actually browses.

**Requires a newer CUPS than macOS ships.** macOS bundles `ippeveprinter` from
CUPS 2.3.4 (2020), which rejects the body iOS sends with `Create-Job`
(*"Unexpected document data following request"*), leaving the phone retrying
forever. Homebrew's CUPS 2.4.x fixes it, and the Homebrew formula pulls it in:

```sh
brew install cups
```

The queue prefers that binary automatically and falls back to the system one,
so printing from the Mac works either way — only iOS needs the newer server.
If you installed from the `.pkg`, install Homebrew CUPS separately for
AirPrint. You don't have to remember that: the installer's final screen says
so, `bt820ctl airprint` reports it, and until it's sorted the printer's
**Location** in Printers & Scanners reads *"USB - for AirPrint: brew install
cups"* instead of *"USB - AirPrint ready"*.

Jobs arrive as PDF. `src/bt820/urf.py` also decodes Apple Raster
(`image/urf`) for clients that send it.

Your Mac must be awake and `bt820ctl start` must have run.

---

## Troubleshooting

**Every label prints twice.**
You're feeding labels one at a time on gap media. Run
`bt820ctl media continuous` — see "Feeding labels by hand" above. This is the
printer's paper-out recovery, not a duplicated job: the driver sends exactly one
`BITMAP` and one `PRINT` per label.

**The iPhone doesn't list the printer.**
Check the Mac is awake and on the same Wi-Fi, then confirm it is being
advertised:

```sh
dns-sd -B _ipp._tcp,_universal local
```

*BT820 Label Printer* should be listed. If not, run `bt820ctl start`. Note that
System Settings' "Share this printer" is **not** the mechanism here and won't
help.

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

**It says "printer not ready: out of paper".**
Exactly what it sounds like — load a label. `bt820print` waits up to 60 seconds
(`--wait`) for one first, and only then gives up, rather than dropping the job
into a void.

**Nothing prints and `--status` says it can't find the printer.**
Check the USB cable and that the printer is powered on. If you installed from
source or Homebrew, make sure `libusb` is present (`brew install libusb`).

**The printer doesn't appear in Printers & Scanners.**
Run `bt820ctl start` again — it detects a queue left in the old "raw" form and
rebuilds it as a driverless one. See the note below on why raw queues are
invisible.

**The queue vanished after uninstalling one of two installs.**
The queue, LaunchAgent and settings are shared between the Homebrew and `.pkg`
installs. Uninstalling either tears the queue down; the remaining one brings it
back with `bt820ctl start`. Your media setting is preserved.

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

This firmware's TSPL vocabulary is narrow. The vendor driver only ever emits
`SET CUTTER`, `SET PARTIAL_CUTTER`, `SET PEEL`, `SET TEAR`, `SHIFT` and `FEED`
— there is no `SET REPRINT`, so you cannot turn off paper-out reprinting that
way; it is silently ignored. Continuous media is the lever that works.


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
gone. A bare `lpadmin -v ipp://...` with no `-m` does create a working queue —
but a **raw** one, which prints fine from `lp` yet is **hidden from Printers &
Scanners**, so it never feels like a real printer.

The way out is Apple's own `/System/Library/Printers/Libraries/ipp2ppd`, which
turns a live IPP printer's attributes into a PPD. Feeding that to
`lpadmin -P` produces a proper driverless queue —
`printer-make-and-model` becomes `REKDOM BT820-AirPrint` instead of
`Local Raw Printer` — and macOS displays it like any other printer.

For that to work the printer must advertise `urf-supported`, which becomes the
`URF=` key in its Bonjour TXT record. Without it macOS does not consider the
printer driverless at all.

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
packaging/gen-formula.py v1.0.2   # refresh PyPI checksums
```

Tag and push, then fill in the formula's `sha256` (it can only be computed once
GitHub is serving the tag tarball):

```sh
curl -sL https://github.com/jackharvest/bt820-macos-driver/archive/refs/tags/v1.0.2.tar.gz | shasum -a 256
```

The formula lives in `jackharvest/homebrew-tap` as `Formula/bt820.rb`.

## License

MIT — see [LICENSE](LICENSE).

Not affiliated with REKDOM, Rongta, or TSC. Built by reverse-engineering a
printer I own.
