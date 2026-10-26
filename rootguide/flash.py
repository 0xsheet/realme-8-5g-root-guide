import json
from pathlib import Path

from .common import load_json, profile, require, save_json, sha256
from .da import readback
from .patch import preloader_preserved
from .session import antumbra, bind_current, session_path, verify_backups
from .tools import da_path, executable


def validate_image(session, partition, image):
    manifest = verify_backups(session)
    image = Path(image).resolve()
    require(image.is_relative_to(session), "Image must belong to this private backup session")
    require(image.is_file(), "Image missing")
    if partition == "boot":
        require(image.stat().st_size == manifest["partitions"]["boot"]["size"] == profile()["boot_size"],
                "Boot image must exactly fill the documented boot partition")
        require(image.read_bytes()[:8] == b"ANDROID!", "Invalid Android boot header")
        patch = load_json(session / "images/boot-patch.json")
        require(patch["stock_sha256"] == sha256(session / "backups/boot.bin") and
                patch["patched_sha256"] == sha256(image) and patch["patched_on_same_device"] is True,
                "Image no longer matches same-device patch provenance")
    else:
        require(partition == "preloader", "Only boot and primary preloader are supported")
        preloader_preserved((session / "backups/preloader.bin").read_bytes(), image.read_bytes())
    return image


def make_plan(path, partition, image):
    session = session_path(path)
    image = validate_image(session, partition, image)
    result = {"profile": "rmx3241-f12", "partition": partition,
              "serial_sha256": load_json(session / "identity.json")["serial_sha256"],
              "image": str(image.relative_to(session)), "bytes": image.stat().st_size,
              "image_sha256": sha256(image), "da_sha256": sha256(da_path()),
              "antumbra_sha256": sha256(executable("antumbra"))}
    plan = session / (partition + "-plan.json")
    save_json(plan, result)
    print(json.dumps(result, indent=2))
    print("Plan saved:", plan, "\nNo device command executed.")


def flash(path, partition, serial=None, execute=False, confirm=None):
    session = session_path(path)
    plan = load_json(session / (partition + "-plan.json"))
    require(plan["profile"] == "rmx3241-f12" and plan["partition"] == partition, "Wrong plan")
    require(plan["serial_sha256"] == load_json(session / "identity.json")["serial_sha256"], "Plan belongs to another phone")
    image = validate_image(session, partition, session / plan["image"])
    require(image.stat().st_size == plan["bytes"] and sha256(image) == plan["image_sha256"],
            "Image changed since plan approval")
    require(sha256(da_path()) == plan["da_sha256"] and sha256(executable("antumbra")) == plan["antumbra_sha256"],
            "Tools changed since planning")
    if not execute:
        print(json.dumps(plan, indent=2))
        print("DRY RUN. Add --execute --confirm RMX3241 to write this image.")
        return
    require(confirm == "RMX3241", "Type --confirm RMX3241 explicitly to execute this write")
    device = bind_current(session, serial, unlocked=partition == "boot")
    log = antumbra(device, session, ["write-flash", partition, image])
    acknowledgement = f"Flash write completed, 0x{image.stat().st_size:X} bytes written."
    require(acknowledgement.lower() in log.lower(), "Missing full write acknowledgment; inspect log")
    readback(session, partition, image, shutdown=True)
