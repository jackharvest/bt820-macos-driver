# BT820 — a userspace driver for the REKDOM BT820 4×6 thermal label printer

Works on macOS 26 (Tahoe), where Apple removed both raw CUPS queues and
printer drivers/PPDs. No kexts, no system files, no `sudo`.

## What this thing actually is

The BT820 is a **rebadged Rongta RP4xx**, and it speaks **TSPL** (TSC's label
language). That wasn't in any documentation — it came out of the bundled
Windows driver:

| Evidence | Where |
|---|---|
| Literal string `TSPL` | `BT820dpi.XPD`, offset `0x48` |
| `SIZE` / `GAP` / `DIRECTION` / `DENSITY` / `SPEED` / `BITMAP` / `PRINT 1,1` | format strings in `BT820Render.dll` |
| `0xCB 0xCB` = **203 × 203 dpi** | `BT820dpi.XPD`, offset `0x8C` |
| Rongta origin | `RongtaUSBMon.dll`, `RP4xxDriverInstall.exe` in `SETUP64/` |

USB is a plain printer-class interface — **`0x0FE6:0x811E`**, bulk OUT `0x01`,
bulk IN `0x81` — so we skip CUPS's device layer and write TSPL to the endpoint.

## Install

```sh
./install.sh
```

Needs Homebrew (for `libusb`) and Python 3. Creates `.venv/` in this folder and
touches nothing else. Safe to re-run.

## Print from the command line

```sh
bin/bt820print label.pdf            # PDF or PNG/JPEG/GIF; auto-fits 4x6
bin/bt820print --status             # firmware, codepage, paper/head state
bin/bt820print --preview out.png x.pdf   # render without printing
```

Useful flags: `-n` copies · `-d 0-15` darkness · `-s 2-4` speed ·
`-r cw|ccw|180|none` rotation · `--dither` for photos · `-p N` page.

## Print from any app (Cmd+P)

```sh
bin/bt820ctl start
```

This runs `ippeveprinter` as a LaunchAgent — a local IPP Everywhere printer —
and registers a CUPS queue named **BT820** pointing at it. It survives reboots.
Then just Cmd+P and pick **BT820**, or `lp -d BT820 label.pdf`.

```sh
bin/bt820ctl status      # queue state + live printer status
bin/bt820ctl log 40      # recent jobs
bin/bt820ctl stop        # stop it; will not come back at login
bin/bt820ctl uninstall   # remove LaunchAgent, spool dir, and the CUPS queue
```

To test the queue without wasting labels: `touch .dryrun` — jobs render to
`.dryrun-preview.png` instead of printing. `rm .dryrun` to resume.

## Gotchas worth knowing

**Label prints upside down** — `--direction 1`, or edit `DIRECTION` in
`src/bt820/tspl.py`.

**Printer feeds blank labels hunting for a gap** — your stock is black-mark, not
die-cut. Use `--bline 3` (mark height in mm). Or re-run sensing with
`bin/bt820print --calibrate`.

**Barcodes scan poorly** — don't use `--dither` on barcodes; it destroys bar
edges. Nudge `--threshold` (lower = more ink) or raise `-d` darkness instead.

**Print is 3.98" wide, not 4.00"** — deliberate. TSPL's `BITMAP` takes width in
whole *bytes*, and 812 dots isn't divisible by 8. Rounding up to 816 risks
overrunning the head, so we round down to 808. The 0.02" comes off the margin.

**Queue wedges after a rejected job** — `bin/bt820ctl stop && bin/bt820ctl start`.

### Two constraints that shaped the design

- `ippeveprinter` **rejects `-f`, `-M`, and `-m` when `-a` is given.** Formats
  and make/model therefore live in `share/bt820.conf`.
- Using `-a` **replaces** ippeveprinter's built-in attribute set, which hardcodes
  US Letter. The full 4×6 media collections must be spelled out in that conf or
  macOS lays every job out at Letter size and the label prints tiny in a corner.
- Do **not** add `document-format-default`/`-supported` twice — ippeveprinter
  emits its own, and duplicates make the printer fail IPP validation.

## Layout

```
bin/bt820print       CLI
bin/bt820ctl         queue lifecycle (start/stop/status/log/uninstall)
bin/bt820-ippfilter  invoked by ippeveprinter once per job
src/bt820/device.py  USB transport + TSPL status queries
src/bt820/render.py  PDF/image -> 1-bit bitmap at 203 dpi
src/bt820/tspl.py    TSPL job construction
share/bt820.conf     IPP attributes (4x6 media, formats, make/model)
```

## License

MIT
