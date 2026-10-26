from pathlib import Path
import platform
import shutil
import struct
import urllib.request
import zipfile

from .common import ROOT, LOCAL, Refusal, load_json, private_dir, require, run, sha256

TOOLS = LOCAL / "tools"


def checked(path, digest):
    require(Path(path).is_file(), f"Missing tool: {path}. Run fetch-tools.")
    require(sha256(path) == digest, f"SHA256 mismatch: {path}; refusing to use it.")
    return Path(path)


def safe_extract(archive, target):
    target = Path(target).resolve()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            dest = (target / member.filename).resolve()
            require(dest.is_relative_to(target), "ZIP path traversal rejected")
            require(not ((member.external_attr >> 16) & 0o170000) == 0o120000,
                    "ZIP symlink rejected")
        source.extractall(target)


def fetch_tools():
    require(platform.system() == "Linux" and platform.machine().lower() in ("x86_64", "amd64"),
            "Pinned binaries are for Linux x86_64 only")
    private_dir(TOOLS)
    lock = load_json(ROOT / "assets.lock.json")
    for item in lock["files"]:
        destination = TOOLS / item["path"]
        if not destination.exists():
            temporary = destination.with_suffix(destination.suffix + ".download")
            try:
                print("Downloading", item["name"], flush=True)
                with urllib.request.urlopen(item["url"], timeout=90) as source, temporary.open("wb") as output:
                    shutil.copyfileobj(source, output)
                checked(temporary, item["sha256"])
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        checked(destination, item["sha256"])
        if item.get("executable"):
            destination.chmod(0o755)
        if item.get("extract"):
            safe_extract(destination, TOOLS)
            for name in ("adb", "fastboot"):
                (TOOLS / "platform-tools" / name).chmod(0o755)
    for item in lock["repositories"]:
        dest = TOOLS / item["name"]
        if not dest.exists():
            run(["git", "init", dest])
            run(["git", "-C", dest, "remote", "add", "origin", item["url"]])
            run(["git", "-C", dest, "fetch", "--depth=1", "origin", item["commit"]], timeout=240)
            run(["git", "-C", dest, "checkout", "--detach", "FETCH_HEAD"], timeout=60)
        require(run(["git", "-C", dest, "rev-parse", "HEAD"]).stdout.strip() == item["commit"],
                f"Wrong source revision: {dest}")
        require(not run(["git", "-C", dest, "status", "--porcelain", "--untracked-files=no"]).stdout.strip(),
                f"Modified source tree: {dest}")
    for item in lock["da_stages"]:
        checked(TOOLS / "geek-mtk" / item["path"], item["sha256"])
    wrap_da()
    print("Pinned tools verified. No phone command was executed.")


def wrap_da():
    lock = load_json(ROOT / "assets.lock.json")
    for item in lock["da_stages"]:
        checked(TOOLS / "geek-mtk" / item["path"], item["sha256"])
    reference = (TOOLS / "mtkclient/mtkclient/Loader/MTK_DA_V5.bin").read_bytes()
    count = struct.unpack_from("<I", reference, 0x68)[0]
    record = None
    for i in range(count):
        offset = 0x6C + i * 0xDC
        if struct.unpack_from("<H", reference, offset + 2)[0] == 0x6833:
            record = bytearray(reference[offset:offset + 0xDC])
            break
    require(record is not None, "MT6833 reference record missing")
    pos, length, address, start, signature = struct.unpack_from("<5I", record, 20)
    info = reference[pos:pos + length]
    stage1, stage2 = [(TOOLS / "geek-mtk" / x["path"]).read_bytes() for x in lock["da_stages"]]
    output = bytearray(reference[:0x68]) + struct.pack("<I", 1)
    output += b"\0" * (0x200 - len(output))
    info_pos = len(output)
    output += info
    output += b"\0" * (-len(output) % 16)
    p1 = len(output)
    output += stage1
    output += b"\0" * (-len(output) % 16)
    p2 = len(output)
    output += stage2
    struct.pack_into("<5I", record, 20, info_pos, len(info), address, start, signature)
    struct.pack_into("<5I", record, 40, p1, len(stage1), 0x200000, len(stage1) - 0x100, 0x100)
    struct.pack_into("<5I", record, 60, p2, len(stage2), 0x40000000, len(stage2) - 0x100, 0x100)
    output[0x6C:0x6C + 0xDC] = record
    dest = TOOLS / "geek-oplus-mt6833-2025.bin"
    dest.write_bytes(output)
    checked(dest, lock["da_container_sha256"])
    return dest


def executable(name):
    if name in ("adb", "fastboot"):
        candidate = TOOLS / "platform-tools" / name
        if candidate.exists():
            archive = load_json(ROOT / "assets.lock.json")["files"][2]
            checked(TOOLS / archive["path"], archive["sha256"])
            with zipfile.ZipFile(TOOLS / archive["path"]) as source:
                import hashlib
                digest = hashlib.sha256(source.read("platform-tools/" + name)).hexdigest()
            return str(checked(candidate, digest))
        result = shutil.which(name)
        require(result, f"{name} missing; install Platform-Tools or run fetch-tools")
        return result
    item = next(x for x in load_json(ROOT / "assets.lock.json")["files"] if x["name"] == name)
    return str(checked(TOOLS / item["path"], item["sha256"]))


def da_path():
    lock = load_json(ROOT / "assets.lock.json")
    return checked(TOOLS / "geek-oplus-mt6833-2025.bin", lock["da_container_sha256"])
