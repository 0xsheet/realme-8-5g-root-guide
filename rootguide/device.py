from datetime import datetime, timezone
import hashlib

from .common import Refusal, require, run, profile
from .tools import executable

FIELDS = ["ro.product.model", "ro.product.device", "ro.build.display.id", "ro.build.version.release",
          "ro.build.version.security_patch", "ro.boot.flash.locked", "ro.boot.vbmeta.device_state",
          "ro.boot.verifiedbootstate", "sys.boot_completed", "ro.oplus.image.my_region.type"]


class Device:
    def __init__(self, serial=None):
        self.adb = executable("adb")
        lines = run([self.adb, "devices"]).stdout.splitlines()[1:]
        devices = [line.split() for line in lines if line.strip()]
        if serial:
            require([serial, "device"] in devices, "Selected device is missing or unauthorized")
        else:
            require(len(devices) == 1 and len(devices[0]) == 2 and devices[0][1] == "device",
                    "Exactly one authorized ADB phone is required, or pass --serial explicitly")
            serial = devices[0][0]
        self.serial = serial

    def call(self, *args, timeout=30, check=True):
        return run([self.adb, "-s", self.serial, *args], timeout=timeout, check=check)

    def inspect(self):
        props = {key: self.call("shell", "getprop", key).stdout.strip() for key in FIELDS}
        return {"captured_utc": datetime.now(timezone.utc).isoformat(),
                "serial_sha256": hashlib.sha256(self.serial.encode()).hexdigest(), "properties": props}


def compatible(identity, unlocked=False):
    current = identity["properties"]
    for key, value in profile()["identity"].items():
        require(current.get(key) == value, f"Unsupported {key}: {current.get(key)!r}; expected {value!r}")
    require(current.get("sys.boot_completed") == "1", "Android must have completed boot")
    if unlocked:
        require(current.get("ro.boot.flash.locked") == "0" and
                current.get("ro.boot.vbmeta.device_state") == "unlocked",
                "Bootloader unlock is not independently confirmed in Android")


def same_device(old, new):
    require(old["serial_sha256"] == new["serial_sha256"], "Phone differs from the backup session")
    for key in profile()["identity"]:
        require(old["properties"].get(key) == new["properties"].get(key),
                "Device or firmware changed since the backup")
