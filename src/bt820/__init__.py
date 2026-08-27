"""Userspace driver for the REKDOM BT820 4x6 thermal label printer.

The BT820 is a rebadged Rongta RP4xx. Its Windows driver ships an XPD file
containing the literal string "TSPL", and BT820Render.dll emits TSPL verbs
(SIZE/GAP/DIRECTION/DENSITY/SPEED/BITMAP/PRINT), so the printer speaks TSC's
label language over a bog-standard USB printer-class interface.
"""
__version__ = "1.1.1"

VID, PID = 0x0FE6, 0x811E
DPI = 203
MEDIA_W_IN, MEDIA_H_IN = 4.0, 6.0
MEDIA_W = int(MEDIA_W_IN * DPI)   # 812 dots
MEDIA_H = int(MEDIA_H_IN * DPI)   # 1218 dots
