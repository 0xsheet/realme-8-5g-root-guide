from pathlib import Path
import shutil
import zipfile

from .common import ROOT, load_json, private_dir, profile, require, run, save_json, sha256
from .session import bind_current, session_path, verify_backups
from .tools import TOOLS, checked


def preloader_preserved(original, patched):
    config = profile()
    size = config["preloader_size"]
    offset, shift = config["preloader_code_offset"], config["preloader_patch_shift"]
    require(len(original) == len(patched) == size, "Preloader size changed")
    require(original[:10] == b"COMBO_BOOT", "Only this documented UFS COMBO_BOOT layout is supported")
    require(original[-shift:] == bytes(shift), "No verified free tail for preloader relocation")
    require(original[offset:-shift] == patched[offset + shift:], "Original signed preloader payload changed")
    require(patched.startswith(b"AND_ROMINFO_v", offset) and patched[offset + 0x4C] == 0,
            "Expected relocated ROMINFO/unlocked fastboot flag missing")
    require(original != patched, "Preloader was not patched")


def patch_preloader(path):
    session = session_path(path)
    verify_backups(session)
    original = session / "backups/preloader.bin"
    source = TOOLS / "oppo-fastboot/path_preloader.py"
    lock = load_json(ROOT / "assets.lock.json")
    revision = next(x["commit"] for x in lock["repositories"] if x["name"] == "oppo-fastboot")
    require(run(["git", "-C", source.parent, "rev-parse", "HEAD"]).stdout.strip() == revision,
            "Preloader patcher revision changed")
    require(not run(["git", "-C", source.parent, "status", "--porcelain", "--untracked-files=no"]).stdout.strip(),
            "Preloader patcher source modified")
    run(["python3", source, original, "preloader-patched.bin"], timeout=30, input="\n", cwd=session)
    generated = session / "preloader_path/preloader-patched.bin"
    preloader_preserved(original.read_bytes(), generated.read_bytes())
    private_dir(session / "images")
    target = session / "images/preloader-patched.bin"
    shutil.copy2(generated, target)
    target.chmod(0o600)
    print("Verified signed-payload preservation:", sha256(target))


def patch_boot(path, serial=None, execute=False):
    session = session_path(path)
    device = bind_current(session, serial)
    lock = load_json(ROOT / "assets.lock.json")
    asset = next(x for x in lock["files"] if x["name"] == "Magisk-v30.7.apk")
    apk = checked(TOOLS / asset["path"], asset["sha256"])
    if not execute:
        print("PLAN: install official Magisk APK and patch this session's stock boot ON THE SAME PHONE.")
        print("Add --execute; no partitions are flashed by patch-boot.")
        return
    target = private_dir(session / "patch-tools")
    with zipfile.ZipFile(apk) as source:
        for name in ("boot_patch.sh", "util_functions.sh", "stub.apk"):
            (target / name).write_bytes(source.read("assets/" + name))
        for name in ("busybox", "magisk", "magiskboot", "magiskinit", "magiskpolicy", "init-ld"):
            (target / name).write_bytes(source.read("lib/arm64-v8a/lib" + name + ".so"))
    remote = "/data/local/tmp/rmx3241-root-guide"
    driver = f'''#!/system/bin/sh
cd {remote} || exit 1
export BOOTMODE=true KEEPVERITY=true KEEPFORCEENCRYPT=true PATCHVBMETAFLAG=false
export RECOVERYMODE=false LEGACYSAR=false
. ./util_functions.sh
TMPDIR="$PWD/tmp"
mkdir -p "$TMPDIR"
api_level_arch_detect
export SOURCEDMODE=true
. ./boot_patch.sh "$PWD/boot.img"
test -s new-boot.img
'''
    (target / "patch_stock.sh").write_text(driver)
    device.call("install", "-r", str(apk), timeout=90)
    device.call("shell", "mkdir", "-p", remote)
    device.call("push", str(target) + "/.", remote + "/", timeout=60)
    device.call("push", str(session / "backups/boot.bin"), remote + "/boot.img", timeout=60)
    device.call("shell", f"cd {remote} && chmod 755 busybox magisk magiskboot magiskinit magiskpolicy init-ld && sh ./patch_stock.sh", timeout=120)
    private_dir(session / "images")
    image = session / "images/boot-patched.img"
    device.call("pull", remote + "/new-boot.img", str(image), timeout=60)
    image.chmod(0o600)
    require(image.stat().st_size == profile()["boot_size"], "Patched boot has wrong size")
    require(image.read_bytes()[:8] == b"ANDROID!", "Patched file is not an Android boot image")
    require(sha256(image) != sha256(session / "backups/boot.bin"), "Boot did not change")
    save_json(session / "images/boot-patch.json", {"stock_sha256": sha256(session / "backups/boot.bin"),
              "patched_sha256": sha256(image), "apk_sha256": asset["sha256"], "patched_on_same_device": True})
    print("Patched boot prepared on the same phone; no partition flashed:", sha256(image))
