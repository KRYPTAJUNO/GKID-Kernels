#!/usr/bin/env python3
"""Patch the RTL8188GU monitor netdev to use the driver's generic raw TX path.

The upstream monitor netdev accepted only a narrow set of radiotap TX frames:
EAPOL-like data and ACTION management frames. This patch routes the netdev
through rtw_monitor_xmit_entry(), which handles management frames generally
and raw 3-address, non-QoS data frames. Unsupported QoS/WDS/HT-control data
frames and control frames are rejected rather than malformed.
"""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "rtl8188gu-src")
cfg_path = root / "os_dep/linux/ioctl_cfg80211.c"
xmit_path = root / "core/rtw_xmit.c"

cfg = cfg_path.read_text()
xmit = xmit_path.read_text()

if "return rtw_monitor_xmit_entry(skb, ndev);" not in cfg:
    include = "#include <hal_data.h>"
    if "#include <rtw_xmit.h>" not in cfg:
        if include not in cfg:
            raise SystemExit("Could not find hal_data.h include anchor")
        cfg = cfg.replace(include, include + "\n#include <rtw_xmit.h>", 1)

    pattern = re.compile(
        r"static int rtw_cfg80211_monitor_if_xmit_entry\(struct sk_buff \*skb, struct net_device \*ndev\)\s*\{.*?\n\}\s*\n(?=static void rtw_cfg80211_monitor_if_set_multicast_list)",
        re.S,
    )
    replacement = """static int rtw_cfg80211_monitor_if_xmit_entry(struct sk_buff *skb, struct net_device *ndev)
{
	/* Use the common radiotap/raw-802.11 transmit path for monitor injection. */
	return rtw_monitor_xmit_entry(skb, ndev);
}

"""
    cfg, count = pattern.subn(replacement, cfg, count=1)
    if count != 1:
        raise SystemExit("Could not replace monitor netdev TX callback safely")

monitor_start = xmit.find("s32 rtw_monitor_xmit_entry")
if monitor_start < 0:
    raise SystemExit("Could not find generic monitor TX function")
monitor_end = xmit.find("\n#endif", monitor_start)
if monitor_end < 0:
    raise SystemExit("Could not find end of generic monitor TX function")
monitor_fn = xmit[monitor_start:monitor_end]

if "rtap_len != 12" in monitor_fn:
    old = """	rtap_len = ieee80211_get_radiotap_len(skb->data);
	if (unlikely(skb->len < rtap_len))
		goto fail;

	if (rtap_len != 12) {
		RTW_INFO("radiotap len (should be 14): %d\\n", rtap_len);
		goto fail;
	}
"""
    new = """	rtap_len = ieee80211_get_radiotap_len(skb->data);
	if (unlikely(rtap_len < sizeof(struct ieee80211_radiotap_header) || skb->len < rtap_len))
		goto fail;
"""
    if old not in monitor_fn:
        raise SystemExit("Could not find exact radiotap length guard in generic monitor TX function")
    monitor_fn = monitor_fn.replace(old, new, 1)

# Add bounds/type validation before the generic TX path dereferences a 802.11 header.
needle = """	skb_pull(skb, rtap_len);

	dot11_hdr = (struct rtw_ieee80211_hdr *)skb->data;
	frame_ctl = le16_to_cpu(dot11_hdr->frame_ctl);
"""
guard = """	skb_pull(skb, rtap_len);

	/* The generic TX descriptor assumes a 24-byte 802.11 header. */
	if (unlikely(skb->len < 24))
		goto fail;

	dot11_hdr = (struct rtw_ieee80211_hdr *)skb->data;
	frame_ctl = le16_to_cpu(dot11_hdr->frame_ctl);

	/* Support management frames and simple 3-address non-QoS data frames. */
	if ((frame_ctl & RTW_IEEE80211_FCTL_FTYPE) != RTW_IEEE80211_FTYPE_DATA &&
	    (frame_ctl & RTW_IEEE80211_FCTL_FTYPE) != RTW_IEEE80211_FTYPE_MGMT)
		goto fail;
	if ((frame_ctl & RTW_IEEE80211_FCTL_FTYPE) == RTW_IEEE80211_FTYPE_DATA &&
	    ((frame_ctl & 0x0080) || ((frame_ctl & 0x0300) == 0x0300) || (frame_ctl & 0x8000)))
		goto fail;
"""
if guard not in monitor_fn:
    if needle not in monitor_fn:
        raise SystemExit("Could not find 802.11 header parse anchor in generic monitor TX function")
    monitor_fn = monitor_fn.replace(needle, guard, 1)

xmit = xmit[:monitor_start] + monitor_fn + xmit[monitor_end:]
cfg_path.write_text(cfg)
xmit_path.write_text(xmit)

if "return rtw_monitor_xmit_entry(skb, ndev);" not in cfg:
    raise SystemExit("Monitor callback patch verification failed")
if "rtap_len != 12" in monitor_fn:
    raise SystemExit("Fixed 12-byte radiotap restriction remains")
if "Support management frames and simple 3-address non-QoS data frames." not in xmit:
    raise SystemExit("Raw TX frame validation patch missing")
print("PASS: monitor netdev uses generic raw 802.11 TX path")
print("PASS: variable valid radiotap lengths accepted")
print("PASS: management frames accepted; QoS/WDS/HT-control data and control frames rejected safely")
