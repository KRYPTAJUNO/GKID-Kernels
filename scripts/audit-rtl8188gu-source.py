#!/usr/bin/env python3
"""Safety and feature audit for the pinned RTL8188GU/RTL8710BU source."""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "rtl8188gu-src")
usb = (root / "os_dep/linux/usb_intf.c").read_text(errors="replace")
cfg = (root / "os_dep/linux/ioctl_cfg80211.c").read_text(errors="replace")
xmit = (root / "os_dep/linux/xmit_linux.c").read_text(errors="replace")
make = (root / "Makefile").read_text(errors="replace")
autoconf = (root / "include/autoconf.h").read_text(errors="replace")

checks = {
    "B711 USB ID present": bool(re.search(
        r"USB_DEVICE_AND_INTERFACE_INFO\s*\(\s*USB_VENDER_ID_REALTEK\s*,\s*0xB711\s*,\s*0xff\s*,\s*0xff\s*,\s*0xff",
        usb, re.I)),
    "monitor interface advertised": "NL80211_IFTYPE_MONITOR" in cfg,
    "monitor channel callback": "cfg80211_rtw_set_monitor_channel" in cfg and ".set_monitor_channel" in cfg,
    "radiotap monitor transmit path": "rtw_cfg80211_monitor_if_xmit_entry" in cfg,
    "monitor transmit dispatch": "rtw_monitor_xmit_entry" in xmit,
    "monitor mode build switch": "CONFIG_WIFI_MONITOR" in make,
    "RTL8710B firmware embedded build support": "LOAD_FW_HEADER_FROM_DRIVER" in autoconf,
}
for label, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(checks.values()):
    sys.exit(1)
