# Troubleshooting and recovery boundaries

## USB error -71 / no device

This is a USB enumeration problem before the flashing application can speak to the
phone. Try another direct port and known data cable. Check `lsusb`, `lsusb -t`, and
your kernel log. Do not interpret a black screen alone as a permanently damaged device.
Do not unplug or force-restart while a write is demonstrably in progress.

## Recovery is not BROM

Volume-key combinations entered Recovery in this case. `22d9:0006` was OPLUS
Preloader; BROM `0e8d:0003` was not reached. Entering Download from Recovery could
return to Android. The successful route used `adb reboot edl` from authorized Android
to reach Preloader, then the accepted DA with Carbonara.

## DA errors

- `0x7024 DAA_SIG_VERIFY_FAILED`: the tested DA was rejected. Do not assume another
  file with the same chipset name is signed for this device.
- `0xc0070004 DA hash mismatch`: observed after accepted DA1 in stock mode. The
  documented Penumbra Carbonara route successfully loaded patched DA2/extensions.
- `CRYPTO_INIT_FAIL 0x1000`: observed in a failed BROM attempt; did not prove unlock.
- TUI failed in the recorded environment; CLI `-b libusb` worked.

## Loaded DA cannot accept a fresh handshake

After an Antumbra CLI command finishes, DA may remain in memory. Do not run normal
MTKClient initialization against that same active stream. `shutdown-da` and `readback`
connect directly without a BROM handshake. After shutdown, Power for 3 seconds may
be needed. Use an explicit power-cycle/reconnection before starting another DA session.

## Fastboot response is shifted, empty or contradictory

In the case, an interrupted host command left a reply queued. A later command
initially consumed the old result. Stop command sequences. With **no upload, write,
unlock confirmation or wipe in progress**, reconnect the cable and establish a clean
command/response exchange. Require consistent product/unlocked/secure results, then
check Android properties after normal boot. Do not issue a flash while the protocol
state is unclear. This repository does not automatically drain USB endpoints or
abort device-side operations, because context matters.

## Fastboot upload stalls at Sending

The original attempt stalled before Writing. Its host process was stopped, the
phone was rebooted, and the working DA path was used. Do not claim a completed
flash merely because the host began sending. Never interrupt a confirmed storage
write on the assumption that it is the same failure.

## Magisk installed but su says Permission denied

Finish **Requires additional setup**, allow reboot, and grant the Shell request in
Magisk's Superuser page for an explicit `su -c id` test. The first case request was
denied before the Shell grant. Installed APK alone does not establish root.

## Bootloop, failed readback or changed GPT

Stop automated steps. Keep the failure logs and original backups private. Do not
blindly flash vbmeta, erase metadata, overwrite the secondary preloader or relock.
If a stable DA connection still exists, compare the affected partition with this
phone's own original before deciding on recovery. A qualified recovery operation
can use Antumbra `write-flash boot YOUR_OWN_ORIGINAL_BOOT`, or the primary preloader
original for a known preloader failure, followed by full readback verification.
The exact connection/state/layout must first be re-established; this is not an
automatic recovery script or a guarantee. A selected-partition backup cannot
restore omitted super/userdata or recover already-erased personal files.

If the idle phone cannot leave a black screen or idle fastboot, the original owner
recovered with USB disconnected and Power + Volume Up held about 30 seconds, then
normal Power. That observation is model-specific and must not interrupt a write.

## Download or SHA256 check fails

Keep the pinned version. Check the upstream project and network availability.
Do not disable checksum validation or substitute a random DA/APK. If upstream
content legitimately changes, investigate it and update the lock file in a reviewed
change with the source and compatibility evidence.
