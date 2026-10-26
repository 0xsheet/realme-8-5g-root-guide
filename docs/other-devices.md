# Adapting the research to another device

The read-only identification approach and evidence standards transfer; binary files,
partition addresses, DA selection and unlock mechanisms do not automatically transfer.
This repository only enables writes for the documented RMX3241 F.12 / LATAM identity.

For a different phone:

1. Identify exact model/codename, chipset, Android/build, region, storage, partition
   scheme and bootloader status. Keep the identifier output private.
2. Research the manufacturer's supported unlock method and upstream rooting guidance.
   Qualcomm, Samsung, newer MediaTek and other families may require entirely different paths.
3. Determine the correct ramdisk image (boot, init_boot, vendor_boot or recovery)
   from that device's firmware. Do not assume this case's boot target or 32 MiB size.
4. Back up this phone's own originals and personal data before destructive stages.
   Record geometry and SHA256 rather than trusting file names.
5. Establish a compatible signed DA/connection only if that route applies. A matching
   chipset label is insufficient. Do not rename this profile to bypass a refusal.
6. Prepare the image on the same phone as required by Magisk, verify actual unlock,
   write only a reviewed target, read back when available, then verify boot and UID 0.
7. Record uncertainty and failures. A new profile needs its own reviewed hardware evidence.

## Prompt for an AI assistant

```text
Read this repository as a case study, then inspect my connected Android phone.
Identify its exact model, chipset, Android build, region and bootloader state.
Research a compatible method using primary sources. Do not reuse this case's
boot/preloader/DA files, offsets or unlock method without independent validation.
Prepare required tools and private backups; record sizes and SHA256 checksums.
Proceed with inspection and preparation, and obtain my approval once before any
required user-data wipe. Explain the concrete operation before writing.
Do not equate a tool success message with actual bootloader unlock or root.
Verify normal Android boot and su -c id returning uid=0, and produce a final report.
If this device is unsupported, stop its write workflow and continue research;
do not edit the profile name just to bypass its checks.
```

## بالعربي

استفد من ترتيب التشخيص والنسخ والتحقق، لا من ملفات الجهاز الآخر أو عناوينه.
لا تغيّر اسم الموديل في profile لتجاوز الرفض. الجهاز المختلف يحتاج دراسة مستقلة
لمعالجِه وبنائه وصورة الإقلاع المناسبة وطريقة فتح القفل الخاصة به، ثم أدلة نجاح جديدة.
