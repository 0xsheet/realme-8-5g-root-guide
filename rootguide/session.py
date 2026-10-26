from pathlib import Path
import os
import subprocess
import time

from .common import LOCAL, Refusal, load_json, private_dir, profile, require, save_json, sha256
from .device import Device, compatible, same_device
from .gpt import parse_gpt
from .tools import da_path, executable


def session_path(path):
    target = Path(path).resolve()
    require(target.is_relative_to(LOCAL.resolve()), "Sessions must stay under ignored local/")
    return target


def antumbra(device, session, arguments, timeout=600):
    import usb.core
    service_ids = {(0x22d9, 0x0006), (0x0e8d, 0x0003), (0x0e8d, 0x2000), (0x0e8d, 0x201c)}
    require(not any((d.idVendor, d.idProduct) in service_ids for d in usb.core.find(find_all=True)),
            "Another MTK service/fastboot port exists before reboot. Disconnect all other phones.")
    log = session / (arguments[0] + ".log")
    with log.open("w") as stream:
        os.chmod(log, 0o600)
        process = subprocess.Popen([executable("antumbra"), "-b", "libusb", *map(str, arguments),
                                    "--da", str(da_path())], stdout=stream, stderr=subprocess.STDOUT)
        try:
            time.sleep(1)
            require(process.poll() is None, f"Antumbra exited before reboot; inspect {log}")
            device.call("reboot", "edl", timeout=15)
            require(process.wait(timeout=timeout) == 0, f"Antumbra failed; inspect {log}")
        except BaseException:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            raise
    return log.read_text(errors="replace")


def create_manifest(folder):
    folder = Path(folder)
    required = profile()["required_backups"]
    for name in required:
        require((folder / (name + ".bin")).is_file(), f"Required backup missing: {name}")
    require((folder / "boot.bin").stat().st_size == profile()["boot_size"], "Wrong boot backup size")
    for name in ("preloader", "preloader_backup"):
        require((folder / (name + ".bin")).stat().st_size == profile()["preloader_size"],
                "Wrong preloader backup size")
    parts = parse_gpt((folder / "PGPT.bin").read_bytes(), profile()["sector_size"],
                      allow_mtk_recovery_quirk=True)
    require(parts["boot"]["size"] == profile()["boot_size"], "Unexpected GPT boot geometry")
    records = []
    for path in sorted(folder.glob("*.bin")):
        require(path.stat().st_size > 0, f"Empty backup: {path.name}")
        if path.stem in parts:
            require(path.stat().st_size == parts[path.stem]["size"], f"Truncated backup: {path.name}")
        path.chmod(0o600)
        records.append({"partition": path.stem, "file": path.name,
                        "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {"profile": "rmx3241-f12", "excluded": profile()["excluded_backups"],
            "partitions": parts, "files": records}


def verify_backups(session):
    manifest = load_json(session / "backups/manifest.json")
    names = {record["partition"] for record in manifest["files"]}
    require(set(profile()["required_backups"]).issubset(names), "Incomplete backup manifest")
    for item in manifest["files"]:
        path = (session / "backups" / item["file"]).resolve()
        require(path.parent == (session / "backups").resolve(), "Unsafe backup manifest path")
        require(path.is_file() and path.stat().st_size == item["bytes"] and sha256(path) == item["sha256"],
                f"Backup changed or incomplete: {item['file']}")
    parsed = parse_gpt((session / "backups/PGPT.bin").read_bytes(), profile()["sector_size"],
                       allow_mtk_recovery_quirk=True)
    require(parsed == manifest["partitions"], "Backup GPT differs from saved geometry")
    return manifest


def backup(path, serial=None, execute=False):
    session = session_path(path)
    device = Device(serial)
    identity = device.inspect()
    compatible(identity)
    if not execute:
        print("PLAN: reboot this supported phone to Preloader and read all except userdata,super,cache")
        print("Destination:", session)
        print("No device state changed. Add --execute to perform the backup.")
        return
    require(not session.exists(), "Session already exists; choose a new path to protect original backups")
    private_dir(session)
    private_dir(session / "backups")
    save_json(session / "identity.json", identity)
    log = antumbra(device, session, ["read-all", session / "backups", "--skip", "userdata,super,cache"])
    require("All partitions read successfully" in log, "Missing successful backup acknowledgment")
    manifest = create_manifest(session / "backups")
    save_json(session / "backups/manifest.json", manifest)
    print(f"Verified {len(manifest['files'])} backup files. Personal data and super are excluded.")
    print("DA remains loaded. Run shutdown-da, then power on and reconnect Android.")


def bind_current(session, serial=None, unlocked=False):
    device = Device(serial)
    identity = device.inspect()
    compatible(identity, unlocked=unlocked)
    same_device(load_json(session / "identity.json"), identity)
    verify_backups(session)
    return device
