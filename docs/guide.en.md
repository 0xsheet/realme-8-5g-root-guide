# Full procedure: RMX3241 F.12 / LATAM

[العربية](guide.ar.md) · [Troubleshooting](troubleshooting.md) · [Other devices](other-devices.md)

Read the entire sequence before starting. Unlocking erased the documented phone.
Copy personal data independently before unlocking. The backup below excludes
`userdata`, `super`, and `cache`; it is not a complete factory-image recovery solution.
Modifying a preloader can prevent boot. Keep this phone's original files and stop on
failed checks rather than forcing a write.

## 0. Requirements and scope

Documented identity: RMX3241 / RE513CL1, Android 13, build RMX3241_11_F.12,
LATAM, MT6833, UFS. The original case recorded project 20796 / NV ID 10011010.
Only this exact identity is enabled for the write helpers. Unlock availability and
DA acceptance may still differ on another physical phone with similar properties.

Host tested in the original session: Ubuntu 26.04.1 x86_64, Python 3.14.4,
Platform-Tools 36.0.0, Antumbra 2.0.0, Magisk 30.7.
The new repository helpers require Python >=3.11. Their offline checks are distinct
from the original hardware test; they have not been re-flashed on another phone.

On Ubuntu 26.04, install host prerequisites yourself:

```bash
sudo apt install git usbutils python3 python3-venv python3-pip \
  libusb-1.0-0 libudev1 libfuse2t64
python3 -m venv --without-pip .venv
python3 -m pip --python .venv/bin/python3 install -r requirements.txt
.venv/bin/python3 -m rootguide fetch-tools
```

Older distributions may call the FUSE2 library `libfuse2`; use your distribution's
package names. Downloaded native binaries are Linux x86_64, not Windows/macOS.
The scripts download upstream release files and pinned Git sources, verify them,
and store them only in `local/tools/`. Read [THIRD_PARTY.md](../THIRD_PARTY.md) for
upstream licensing/download terms. If Gitee or a checksum check fails, stop; do not
replace a DA with an unverified file advertised for a vaguely similar chipset.

## 1. USB permissions and phone settings

```bash
sudo install -m 0644 drivers/70-realme-mtk.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
id -nG
```

The original user belonged to `plugdev`. If adding that membership, log out/in
afterward. Your distribution's Android udev rules may also be needed for ADB/fastboot.
This service-port rule file is not a Windows VCOM driver installer.

Enable Developer options (tap Build number 7 times), OEM unlocking and USB debugging.
Connect one phone only, unlock its screen and approve the computer's ADB fingerprint.
Use a stable data cable and a direct USB port. Observed IDs:

| Mode | USB VID:PID |
|---|---|
| Android/ADB | 22d9:2769 or 22d9:2765 |
| OPLUS Preloader / loaded DA | 22d9:0006 |
| Fastboot | 0e8d:201c |
| BROM, prepared for but never reached in this case | 0e8d:0003 |

```bash
.venv/bin/python3 -m rootguide doctor
```

Require `supported_profile: "rmx3241-f12"`. The printed serial is hashed, not raw.
With multiple ADB devices, use an explicit `--serial` for supported commands;
disconnect all other phones before any DA operation because upstream DA selection
uses service ports rather than ADB serial targeting.

## 2. Back up this phone

```bash
.venv/bin/python3 -m rootguide backup
.venv/bin/python3 -m rootguide backup --execute
```

The first invocation is a plan. The second records phone identity privately,
starts `antumbra -b libusb read-all`, then runs targeted `adb reboot edl`.
Despite that command name, the actual observed mode was MediaTek OPLUS Preloader.
Carbonara loads the accepted 2025 DA and extensions. No Qualcomm tool is involved.

Backups go to `local/session/backups/`. A manifest records sizes and SHA256.
Both GPT header and partition-array CRCs are validated. Expected partition sizes
are checked. A session that already exists is not silently overwritten. To use a
different session, pass `--session local/another-session` consistently in later commands.

The verified vendor GPT advertises FirstUsableLBA=34 while recovery occupies LBAs
8..32775 on 4096-byte sectors. Only this exact known quirk is explicitly allowed by
the RMX3241 workflow; both CRCs, metadata bounds and non-overlapping ranges still apply.

```bash
.venv/bin/python3 -m rootguide verify-backups
.venv/bin/python3 -m rootguide shutdown-da
```

DA remains loaded after a completed Antumbra command. The explicit shutdown helper
connects directly to it **without a new BROM handshake**. Do not run an unrelated
MTKClient handshake on this already-loaded stream. After shutdown the phone may
stay off: press Power for about 3 seconds, let Android boot, and reconnect ADB.

The original case saved 54 partitions / 1,358,987,264 bytes, including boot,
preloader, secondary preloader, recovery, seccfg and calibration partitions.
This is a case result, not an expected count for every layout. Required session
files include PGPT, boot, both preloaders and seccfg. Keep calibration dumps private.

## 3. Patch this phone's stock boot with the official APK

```bash
.venv/bin/python3 -m rootguide patch-boot
.venv/bin/python3 -m rootguide patch-boot --execute
```

The executing command installs the verified Magisk APK, extracts its ARM64 tools,
pushes this session's original boot, and runs upstream `boot_patch.sh` on the same
phone. It does not flash a partition. The output is
`local/session/images/boot-patched.img` with a same-session provenance record.

Flags reproduce the original case: `BOOTMODE=true`, `KEEPVERITY=true`,
`KEEPFORCEENCRYPT=true`, `PATCHVBMETAFLAG=false`, `RECOVERYMODE=false`,
`LEGACYSAR=false`. `cache` was selected as the pre-init storage in that case.
The input is named `boot.img`, not `stock_boot.img`, because the latter is an
internal upstream temporary filename. Boot was 32 MiB with a ramdisk.

## 4. Open fastboot access using this phone's preloader

Do not use someone else's preloader. This step changes an early boot component.

```bash
.venv/bin/python3 -m rootguide patch-preloader
.venv/bin/python3 -m rootguide plan --partition preloader \
  --image local/session/images/preloader-patched.bin
.venv/bin/python3 -m rootguide flash --partition preloader
```

The upstream patcher operates only on your saved original file. The wrapper
checks its pinned source revision, 4 MiB size, COMBO_BOOT layout, free tail,
preservation of the relocated signed payload, and the expected ROMINFO flag.
The dry-run flash prints the saved image/tool hashes. Review them first.

To deliberately write the primary preloader only:

```bash
.venv/bin/python3 -m rootguide flash --partition preloader \
  --execute --confirm RMX3241
```

The helper rechecks backup integrity, the planned image and tools, current phone
identity, and absence of another MTK service port before rebooting. It writes the
primary preloader, reads back all 4 MiB, and compares its hash. The secondary
preloader is not written. A fresh GPT is validated and compared with the backup.
Shutdown is sent only after successful verification. Power on and reconnect Android.

The original session included an earlier unsuccessful `seccfg unlock` experiment.
It did not independently unlock Android. This repository documents that experiment
but does not silently repeat it; whether that preceding mutation influenced any
later behavior has not been separately established by a fresh hardware run.

## 5. Standard bootloader unlock: explicit manual step

Before this stage, ensure your personal files are backed up and OEM unlocking is enabled.
Use the downloaded tools, with only your intended phone connected:

```bash
local/tools/platform-tools/adb reboot bootloader
local/tools/platform-tools/fastboot devices
local/tools/platform-tools/fastboot getvar product
local/tools/platform-tools/fastboot getvar unlocked
local/tools/platform-tools/fastboot flashing get_unlock_ability
```

The case first showed `unlocked: no`, `secure: yes`. Only when prepared for the
data wipe, run:

```bash
local/tools/platform-tools/fastboot flashing unlock
```

Read the phone's confirmation screen and use the indicated Volume key to approve.
Do not assume the same key on every firmware. Wait for completion. Recheck:

```bash
local/tools/platform-tools/fastboot getvar product
local/tools/platform-tools/fastboot getvar unlocked
local/tools/platform-tools/fastboot getvar secure
```

Observed successful output was `k6833v1_64_k419`, `unlocked: yes`, `secure: no`.
If replies appear shifted or contradictory, stop and read the troubleshooting guide.
Do not flash based on an ambiguous single response.

Reboot normally, allow any wipe/setup to finish, complete Hello Setup, and re-enable
USB debugging and computer authorization. In the original case a force restart
from an idle, unresponsive fastboot required disconnecting USB and holding Power +
Volume Up for about 30 seconds; this is not an instruction to interrupt a write.

```bash
.venv/bin/python3 -m rootguide doctor
```

Require Android `ro.boot.flash.locked=0`, `ro.boot.vbmeta.device_state=unlocked`,
and completed boot. The case reported `verifiedbootstate=orange`.

## 6. Write patched boot using the working DA route

```bash
.venv/bin/python3 -m rootguide plan --partition boot \
  --image local/session/images/boot-patched.img
.venv/bin/python3 -m rootguide flash --partition boot
.venv/bin/python3 -m rootguide flash --partition boot \
  --execute --confirm RMX3241
```

The executing command requires current Android proof of an unlocked bootloader,
the same phone/build as the backup, unchanged backups and patch provenance, and
unchanged tool/image hashes. It writes the full boot image by partition name.
Antumbra resolves its target partition; the readback helper independently parses
the fresh GPT and derives the boot address. There is no universal hardcoded boot
address in this helper. Any readback mismatch stops before automatic shutdown.

The original case's address was `0x47D00000`, length `0x2000000` (32 MiB).
Those are observations, not values to transfer to another device.
`fastboot flash boot` stalled at **Sending** in the original case and was stopped
before Writing; the successful flash used the DA route instead.

## 7. Magisk setup and verified root

After verified write/shutdown, press Power if necessary and allow Android to boot.
Install the APK again because bootloader unlocking may have erased the app:

```bash
local/tools/platform-tools/adb install -r local/tools/Magisk-v30.7.apk
local/tools/platform-tools/adb shell am start -n com.topjohnwu.magisk/.ui.MainActivity
```

Accept **Requires additional setup → OK** in Magisk and allow its reboot.
Once Android boots, check Installed 30.7 (30700). Grant the Shell request in Magisk
for the following explicit root test, or enable Shell in its Superuser page:

```bash
.venv/bin/python3 -m rootguide verify-root
```

Success requires output containing `uid=0(root)`, not merely an installed APK or an
unlocked bootloader. In the case the full output was:

```text
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
30.7:MAGISK:R
30700
sys.boot_completed=1
ro.boot.flash.locked=0
ro.boot.vbmeta.device_state=unlocked
```

No vbmeta/super/recovery flash, custom kernel, TWRP, Zygisk module or relock was
needed. Full application compatibility, Play Integrity, every modem feature and a
complete unroot/restore were not independently audited. Keep the original files;
do not relock with a modified boot image. Reassess firmware compatibility before OTA updates.

## References

- [Magisk installation requirements](https://topjohnwu.github.io/Magisk/install.html)
- [Magisk 30.7 release](https://github.com/topjohnwu/Magisk/releases/tag/v30.7)
- [Penumbra 2.0.0](https://github.com/shomykohai/penumbra/releases/tag/v2.0.0)
- [MTKClient](https://github.com/bkerler/mtkclient)
- [Preloader patcher](https://github.com/Shocked-Cat/oppo-mtk-fastboot-unlock)
- [GeekFlashTool DA resources](https://gitee.com/geekflashtool/package_mtk_edl)
- [Platform-Tools](https://developer.android.com/tools/releases/platform-tools)

Pinned commits and checksums, not mutable repository branches, are in `assets.lock.json`.
