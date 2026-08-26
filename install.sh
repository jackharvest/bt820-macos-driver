#!/bin/sh
# Set up the BT820 driver on this Mac. Safe to re-run.
set -e
ROOT=$(cd "$(dirname "$0")" && pwd)

echo "==> checking libusb (pyusb needs it)"
if ! ls /opt/homebrew/lib/libusb-1.0.dylib /usr/local/lib/libusb-1.0.dylib >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install libusb
  else
    echo "libusb missing and Homebrew not found."
    echo "Install Homebrew (https://brew.sh) then: brew install libusb"
    exit 1
  fi
fi

echo "==> creating venv"
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install --quiet --upgrade pip
"$ROOT/.venv/bin/pip" install --quiet -r "$ROOT/requirements.txt"

echo "==> checking for the printer"
if "$ROOT/bin/bt820print" --status; then
  echo
  echo "Done. Print from the command line with:"
  echo "  $ROOT/bin/bt820print label.pdf"
  echo
  echo "For a queue you can Cmd+P into:"
  echo "  $ROOT/bin/bt820ctl start"
else
  echo
  echo "Driver installed, but the printer did not answer."
  echo "Plug it in / power it on, then run: $ROOT/bin/bt820print --status"
fi
