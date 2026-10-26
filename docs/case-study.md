# Hardware case study, 2026-10-26

## Verified endpoint

One realme 8 5G (RMX3241 / RE513CL1), Android 13 build RMX3241_11_F.12,
LATAM / project 20796 / NV ID 10011010, MT6833, UFS.

After Magisk additional setup and its reboot:

```text
su -c id
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0

magisk -v
30.7:MAGISK:R

magisk -V
30700

sys.boot_completed=1
ro.boot.flash.locked=0
ro.boot.vbmeta.device_state=unlocked
```

The owner completed Hello Setup after authorizing the bootloader-unlock data wipe.
No device serial, IMEI, calibration dump or owner backup is published here.

## Sequence and evidence

| Stage | Observed result | Consequence |
|---|---|---|
| Deep Testing | Owner reported failure | Investigated Preloader route |
| Initial adb reboot bootloader | Returned to Android | Fastboot entry was blocked |
| Volume-key connection attempts | Recovery, not confirmed BROM | Used USB IDs instead of assumptions |
| BROM conversion attempts | 0x1d18 and CRYPTO_INIT_FAIL 0x1000 among errors | Recovered normal boot, stopped relying on BROM |
| Generic MTK_DA_V5 | DAA_SIG_VERIFY_FAILED 0x7024 | Needed an accepted DA |
| New signed 2025 DA with stock MTKClient | DA1 accepted, DA2 hash mismatch 0xc0070004 | Used Penumbra Carbonara patches |
| Antumbra 2.0.0, libusb, 2025 DA | DA2 and extensions loaded | GPT and flash access worked |
| Backup | 54 partitions; 1,358,987,264 bytes; hashes later rechecked | Originals retained privately |
| seccfg unlock experiment | Tool said success; Android stayed locked; later header state 4 | Not accepted as proof of unlock |
| Original preloader | Fastboot hard-lock flag 0x11 | Patched only primary preloader using preserved signed payload |
| Primary preloader write | 4 MiB readback exactly matched | Fastboot became reachable |
| Standard fastboot unlock | Phone confirmation; unlocked yes / secure no | Data wipe and setup completed |
| Android after unlock | locked=0, device_state=unlocked, orange | Allowed boot write |
| fastboot flash boot | Stalled at Sending before Writing | Stopped transfer; used DA route |
| DA boot flash | Full 32 MiB readback matched patched image | Normal Android boot |
| Official Magisk APK | Additional setup, automatic reboot, Installed 30.7 | Shell grant and UID 0 proof |

Intermittent USB `device descriptor error -71` required port/cable troubleshooting.
Stale fastboot replies once produced responses shifted between commands; the final
unlock result was checked after clearing that condition and independently in Android.
The original experiments used CLI `-b libusb`; the TUI did not establish a usable
connection in that environment.

## What was changed

- seccfg state, including the failed intermediate experiment and subsequent standard unlock.
- Primary preloader, to expose fastboot entry. The secondary original was left untouched.
- boot, with a same-phone Magisk patch.
- Magisk application setup and Shell superuser authorization.
- Userdata was erased during bootloader unlock with owner consent.

No vbmeta, super, recovery or custom-kernel flash was required. A region-mismatched
Android 12 C.06 rollback package was inspected remotely and **not flashed**:
IN_all / project 206FF / NV ID 00011011 differed from this LATAM phone.

## Limits of reuse

The device-specific stock/patched images and their private archive are intentionally
not included. A backup of selected partitions cannot restore photos or an omitted
super image. The earlier failed seccfg mutation was not isolated in a separate
hardware experiment; the new helpers do not pretend that this uncertainty is resolved.
Only the original sequence has hardware evidence; repository refactoring is validated
with offline checks and local-artifact verification, not another unrequested flash.

Use [the complete guide](guide.en.md), not this timeline alone, for stage ordering.
