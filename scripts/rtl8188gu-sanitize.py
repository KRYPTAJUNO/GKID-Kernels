#!/usr/bin/env python3
"""Restrict rtl8xxxu derivative to USB ID 0bda:b711 only."""
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
s = p.read_text()
pat = re.compile(r"(static const struct usb_device_id dev_table\[\] = \{).*?(\n\};)", re.S)
m = pat.search(s)
if not m: raise SystemExit("USB table not found; refusing to modify")
replacement = r"""\1
/* RTL8710BU aka RTL8188GU: target-only binding */
{ USB_DEVICE_AND_INTERFACE_INFO(USB_VENDOR_ID_REALTEK, 0xb711, 0xff, 0xff, 0xff),
  .driver_info = (unsigned long)&rtl8710bu_fops },
{ }
\2"""
out = pat.sub(lambda x: replacement.replace("\\1", x.group(1)).replace("\\2", x.group(2)), s, count=1)
table = pat.search(out).group(0)
ids = re.findall(r"USB_DEVICE_AND_INTERFACE_INFO\(([^,]+),\s*([^,]+)", table)
if len(ids) != 1 or ids[0][0] != "USB_VENDOR_ID_REALTEK" or ids[0][1].strip().lower() != "0xb711":
    raise SystemExit(f"Target-only validation failed: {ids}")
p.write_text(out)
print("USB table sanitized and verified: only 0bda:b711")