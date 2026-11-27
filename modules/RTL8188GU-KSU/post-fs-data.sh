#!/system/bin/sh
MODDIR=${0%/*}
LOG_TAG="rtl8188gu"

log_msg() {
    echo "$LOG_TAG: $1" > /dev/kmsg 2>/dev/null
}

# Use the device's already-present cfg80211. Never bundle, load, unload,
# or replace cfg80211/mac80211 or any existing Wi-Fi driver.
if [ ! -d /sys/module/cfg80211 ]; then
    log_msg "cfg80211 is not present; skipping RTL8188GU load"
    exit 0
fi

if grep -q '^8188gu ' /proc/modules 2>/dev/null; then
    log_msg "8188gu already loaded; leaving it untouched"
    exit 0
fi

if [ ! -s "$MODDIR/lkm/8188gu.ko" ]; then
    log_msg "8188gu.ko is missing; nothing loaded"
    exit 0
fi

if ksud insmod "$MODDIR/lkm/8188gu.ko" 2>/dev/null; then
    log_msg "8188gu module loaded; waiting for USB ID 0bda:b711"
else
    log_msg "FAILED to load 8188gu. Check dmesg, vermagic, symbol versions, dependencies and module-signature policy"
fi
