"""USB transport for the BT820.

macOS 26 (Tahoe) removed raw CUPS queues, so we bypass CUPS and write straight
to the USB printer-class bulk endpoint.
"""
import os
import sys
import time
import usb.core
import usb.util

from . import VID, PID

EP_OUT, EP_IN = 0x01, 0x81


def _find_backend():
    """Locate libusb.

    ctypes' default search misses Homebrew paths under some launch contexts,
    and finds nothing at all inside a PyInstaller bundle, so try explicit
    locations before falling back to pyusb's own lookup.
    """
    import usb.backend.libusb1

    candidates = []
    if getattr(sys, "frozen", False):                     # PyInstaller bundle
        candidates.append(os.path.join(sys._MEIPASS, "libusb-1.0.0.dylib"))
    candidates += [
        "/opt/homebrew/lib/libusb-1.0.0.dylib",           # Apple Silicon brew
        "/usr/local/lib/libusb-1.0.0.dylib",              # Intel brew
    ]
    for path in candidates:
        if os.path.exists(path):
            backend = usb.backend.libusb1.get_backend(find_library=lambda _p=path: _p)
            if backend is not None:
                return backend
    return usb.backend.libusb1.get_backend()


class BT820:
    def __init__(self, serial=None):
        self.dev = None
        self.serial = serial

    def __enter__(self):
        dev = usb.core.find(idVendor=VID, idProduct=PID, backend=_find_backend())
        if dev is None:
            raise RuntimeError(
                "BT820 not found on USB. Check the cable and that the printer is on."
            )
        if self.serial and dev.serial_number != self.serial:
            raise RuntimeError(f"BT820 {self.serial} not found (saw {dev.serial_number}).")
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
        except (NotImplementedError, usb.core.USBError):
            pass
        dev.set_configuration()
        usb.util.claim_interface(dev, 0)
        self.dev = dev
        return self

    def __exit__(self, *exc):
        if self.dev is not None:
            usb.util.release_interface(self.dev, 0)
            usb.util.dispose_resources(self.dev)
            self.dev = None
        return False

    def write(self, data, chunk=4096):
        for i in range(0, len(data), chunk):
            self.dev.write(EP_OUT, data[i:i + chunk], timeout=15000)

    def read(self, n=256, timeout=1200):
        try:
            return bytes(self.dev.read(EP_IN, n, timeout=timeout))
        except usb.core.USBError:
            return b""

    def query(self, cmd, pause=0.35):
        self.write(cmd)
        time.sleep(pause)
        return self.read()

    def status(self):
        """TSPL <ESC>!? -- 0x00 means ready."""
        raw = self.query(b"\x1b!?", pause=0.3)
        if not raw:
            return None, "no response"
        code = raw[0]
        flags = {
            0x00: "ready", 0x01: "head open", 0x02: "paper jam",
            0x03: "head open + paper jam", 0x04: "out of paper",
            0x08: "out of ribbon", 0x10: "pause", 0x20: "printing",
        }
        return code, flags.get(code, f"unknown status 0x{code:02X}")

    def info(self):
        return {
            "firmware": self.query(b"~!@\r\n").decode(errors="replace").strip(),
            "codepage": self.query(b"~!I\r\n").decode(errors="replace").strip(),
            "serial": self.dev.serial_number,
        }
