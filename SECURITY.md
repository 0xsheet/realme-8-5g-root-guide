# Reporting and private phone data

Report a software defect with the command name, sanitized error, host/tool versions,
and non-identifying firmware/model information. Public issues are public: never
attach IMEI/serial identifiers, credentials, raw NVRAM/NVDATA, calibration partitions,
personal files, device dumps, or the entire ignored `local/` directory.

The guards reduce common wrong-device/wrong-file mistakes; they are not an
adversarial security boundary against someone modifying local code, profiles or
session manifests. A checksum establishes byte identity, not device compatibility.

Downloaded tools run with their own upstream code and terms. Check `assets.lock.json`
and upstream notices before execution. Never add GitHub tokens to this repository.

Bootloader opening and Magisk root expand device privileges. Keep original images,
do not relock with modified boot, and reassess firmware before system updates.
No claim of complete factory recovery or security certification is made.
