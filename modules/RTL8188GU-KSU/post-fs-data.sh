#!/system/bin/sh
MODDIR=${0%/*}
LOG_TAG="rtl8188gu"

log_msg() {
    echo "$LOG_TAG: $1" > /dev/kmsg 2>/dev/null
}

# Never unload or replace cfg80211/mac80211 or any existing Wi-Fi driver.
if ! grep -q '^cfg80211 ' /proc/modules 2>/dev/null; then
    if [ -f "$MODDIR/lkm/cfg80211.ko" ]; then
        if ksud insmod "$MODDIR/lkm/cfg80211.ko" 2>/dev/null; then
            log_msg "loaded matching cfg80211 dependency"
        else
            log_msg "could not load cfg80211 dependency; RTL8188GU load skipped"
            exit 0
        fi
    else
        log_msg "cfg80211 is not loaded and no fallback module is packaged"
        exit 0
    fi
fi

if grep -q '^8188gu ' /proc/modules 2>/dev/null; then
    log_msg "8188gu already loaded; leaving it untouched"
    exit 0
fi

if ksud insmod "$MODDIR/lkm/8188gu.ko" 2>/dev/null; then
    log_msg "8188gu module loaded; waiting for USB ID 0bda:b711"
else
    log_msg "FAILED to load 8188gu. Check dmesg, vermagic, symbol versions and module-signature policy"
fi
