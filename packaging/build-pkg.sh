#!/bin/sh
# Build a double-clickable installer for the BT820 driver.
#
# Produces build/BT820-<version>.pkg containing a self-contained binary
# (Python + libusb + pdfium all bundled by PyInstaller), so the target Mac
# needs neither Homebrew nor Python.
#
# The result is UNSIGNED -- there is no Developer ID on this machine. Users
# will need to right-click > Open, or approve it in System Settings > Privacy
# & Security. Notarizing requires the $99/yr Apple Developer Program.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/src/bt820/__init__.py")
ID=com.jackharvest.bt820
PREFIX=/usr/local/lib/bt820
BUILD="$ROOT/build"
PAYLOAD="$BUILD/payload"
SCRIPTS="$BUILD/scripts"

echo "==> building frozen binary (v$VERSION)"
[ -x "$ROOT/.venv/bin/pyinstaller" ] || "$ROOT/.venv/bin/pip" install -q pyinstaller
LIBUSB=$(ls /opt/homebrew/lib/libusb-1.0.0.dylib /usr/local/lib/libusb-1.0.0.dylib 2>/dev/null | head -1)
[ -n "$LIBUSB" ] || { echo "libusb not found -- brew install libusb"; exit 1; }
"$ROOT/.venv/bin/pyinstaller" --noconfirm --clean --onefile \
  --name bt820print --paths "$ROOT/src" \
  --add-binary "$LIBUSB:." \
  --hidden-import usb.backend.libusb1 --collect-all pypdfium2 \
  --distpath "$BUILD/dist" --workpath "$BUILD/work" --specpath "$BUILD" \
  "$ROOT/src/bt820_main.py" >/dev/null

echo "==> staging payload"
rm -rf "$PAYLOAD" "$SCRIPTS"
mkdir -p "$PAYLOAD$PREFIX" "$PAYLOAD/usr/local/bin" "$SCRIPTS"
cp "$BUILD/dist/bt820print"    "$PAYLOAD$PREFIX/"
cp "$ROOT/bin/bt820ctl"        "$PAYLOAD$PREFIX/"
cp "$ROOT/bin/bt820-ippfilter" "$PAYLOAD$PREFIX/"
cp "$ROOT/share/bt820.conf"    "$PAYLOAD$PREFIX/"
chmod +x "$PAYLOAD$PREFIX"/bt820print "$PAYLOAD$PREFIX"/bt820ctl "$PAYLOAD$PREFIX"/bt820-ippfilter
ln -sf "$PREFIX/bt820print" "$PAYLOAD/usr/local/bin/bt820print"
ln -sf "$PREFIX/bt820ctl"   "$PAYLOAD/usr/local/bin/bt820ctl"

cat > "$PAYLOAD$PREFIX/uninstall.sh" <<'UNINSTALL'
#!/bin/sh
# Remove the copy of the BT820 driver installed by the .pkg.
set -e
# bt820ctl keeps shared state (queue, LaunchAgent, settings) intact if another
# install is present, so this is safe to run alongside a Homebrew install.
/usr/local/lib/bt820/bt820ctl uninstall || true
echo "Removing program files (needs admin)..."
sudo rm -rf /usr/local/lib/bt820 /usr/local/bin/bt820print /usr/local/bin/bt820ctl
sudo pkgutil --forget com.jackharvest.bt820 2>/dev/null || true
if [ -x /opt/homebrew/bin/bt820ctl ]; then
  echo
  echo "The Homebrew install is still here. Restart its queue with:"
  echo "  /opt/homebrew/bin/bt820ctl start"
else
  echo "Done. Nothing of the BT820 driver remains."
fi
UNINSTALL
chmod +x "$PAYLOAD$PREFIX/uninstall.sh"

echo "==> writing postinstall"
cat > "$SCRIPTS/postinstall" <<'POST'
#!/bin/sh
# Start the queue for the user who is actually logged in (we run as root).
CONSOLE_USER=$(stat -f%Su /dev/console)
[ -n "$CONSOLE_USER" ] && [ "$CONSOLE_USER" != "root" ] || exit 0
CONSOLE_UID=$(id -u "$CONSOLE_USER")
launchctl asuser "$CONSOLE_UID" sudo -u "$CONSOLE_USER" \
  /usr/local/lib/bt820/bt820ctl start >/dev/null 2>&1 || true
exit 0
POST
chmod +x "$SCRIPTS/postinstall"

echo "==> installer resources"
RES="$BUILD/resources"
rm -rf "$RES"; mkdir -p "$RES"
cat > "$RES/conclusion.html" <<'HTML'
<html><body style="font:13px -apple-system,sans-serif;margin:16px;line-height:1.5">
<h2 style="margin:0 0 10px">BT820 is installed</h2>
<p><b>Print a label</b><br>
<code>bt820print label.pdf</code></p>
<p><b>Add it to Printers &amp; Scanners and the Print dialog</b><br>
<code>bt820ctl start</code></p>
<p><b>Feeding labels one at a time?</b> Run this once, or every label prints twice:<br>
<code>bt820ctl media continuous</code></p>
<hr style="border:none;border-top:1px solid #ccc;margin:14px 0">
<p><b>To print from an iPhone or iPad</b><br>
This needs a newer CUPS than macOS ships. macOS bundles a 2020 version that
cannot accept jobs from iOS, so AirPrint will not work until you install one:</p>
<p><code>brew install cups &amp;&amp; bt820ctl start</code></p>
<p>Check status any time with <code>bt820ctl airprint</code>.
Printing from this Mac works either way.</p>
<p style="color:#666">Docs: https://github.com/jackharvest/bt820-macos-driver</p>
</body></html>
HTML

echo "==> pkgbuild"
pkgbuild --root "$PAYLOAD" --scripts "$SCRIPTS" \
  --identifier "$ID" --version "$VERSION" --install-location / \
  "$BUILD/bt820-component.pkg" >/dev/null

cat > "$BUILD/distribution.xml" <<DIST
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>BT820 Label Printer Driver</title>
    <organization>com.jackharvest</organization>
    <options customize="never" require-scripts="false" hostArchitectures="arm64"/>
    <volume-check><allowed-os-versions><os-version min="13.0"/></allowed-os-versions></volume-check>
    <conclusion file="conclusion.html" mime-type="text/html"/>
    <choices-outline><line choice="default"/></choices-outline>
    <choice id="default"><pkg-ref id="$ID"/></choice>
    <pkg-ref id="$ID" version="$VERSION" onConclusion="none">bt820-component.pkg</pkg-ref>
</installer-gui-script>
DIST

productbuild --distribution "$BUILD/distribution.xml" \
  --resources "$RES" --package-path "$BUILD" "$BUILD/BT820-$VERSION.pkg" >/dev/null

rm -f "$BUILD/bt820-component.pkg"
echo
echo "Built: $BUILD/BT820-$VERSION.pkg  ($(du -h "$BUILD/BT820-$VERSION.pkg" | cut -f1))"
echo "UNSIGNED -- users must right-click > Open, or approve in System Settings."
