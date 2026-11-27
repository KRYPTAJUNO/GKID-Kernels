#!/usr/bin/env python3
"""Restrict the external rtl8xxxu module to the target RTL8710BU USB ID only.

This is a build-tree-only transformation. It prevents this separate module from
claiming USB IDs belonging to chips already handled by the kernel's existing
Realtek drivers. The source checkout is pinned by the workflow before this runs.
"""
from pathlib import Path
import re
import sys

source_path = Path("rtl8xxxu-src/rtl8xxxu_core.c")
source = source_path.read_text()
pattern = re.compile(
    r"static const struct usb_device_id dev_table\[\] = \{.*?\n\};",
    re.DOTALL,
)
matches = list(pattern.finditer(source))
if len(matches) != 1:
    sys.exit(f"Expected exactly one dev_table, found {len(matches)}")

table = matches[0].group(0)
target = re.compile(
    r"USB_DEVICE_AND_INTERFACE_INFO\(USB_VENDOR_ID_REALTEK,\s*0xb711,"
    r".*?rtl8710bu_fops",
    re.DOTALL | re.IGNORECASE,
)
if not target.search(table):
    sys.exit("Pinned upstream table does not contain the expected RTL8710BU 0bda:b711 entry")
if table.lower().count("0xb711") != 1:
    sys.exit("Expected exactly one 0xb711 entry in the upstream USB table")

replacement = """static const struct usb_device_id dev_table[] = {
\t{USB_DEVICE_AND_INTERFACE_INFO(USB_VENDOR_ID_REALTEK, 0xb711, 0xff, 0xff, 0xff),
\t .driver_info = (unsigned long)&rtl8710bu_fops},
\t{ }
};"""

patched = source[:matches[0].start()] + replacement + source[matches[0].end():]
source_path.write_text(patched)

# Fail closed: the patched table must contain only the requested adapter ID.
new_match = pattern.search(patched)
if not new_match or new_match.group(0).lower().count("0xb711") != 1:
    sys.exit("Post-patch table validation failed")
if re.search(r"0x(?!b711)[0-9a-f]{4}", new_match.group(0), re.IGNORECASE):
    sys.exit("Unexpected USB product ID remains in the target-only table")

print("USB ID table restricted to 0bda:b711 -> rtl8710bu_fops.")
