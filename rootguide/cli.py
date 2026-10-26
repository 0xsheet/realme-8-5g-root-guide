import argparse
import json
from pathlib import Path
import subprocess
import sys

from .common import LOCAL, Refusal, require


def parser():
    top = argparse.ArgumentParser(description="RMX3241 F.12 case-study tools. No automatic unlock or silent write.")
    sub = top.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch-tools", help="Download pinned tools and validate checksums; no device commands")
    sub.add_parser("wrap-da", help="Build verified 2025 DA container from already-downloaded stages")
    doctor = sub.add_parser("doctor", help="Read-only phone inspection; serial is hashed in output")
    doctor.add_argument("--serial")
    verify = sub.add_parser("verify-root", help="Run su -c id; grant Shell in Magisk if needed")
    verify.add_argument("--serial")
    for name in ("backup", "patch-boot", "patch-preloader", "verify-backups", "plan", "flash", "readback"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--session", type=Path, default=LOCAL / "session")
        if name in ("backup", "patch-boot", "flash"):
            cmd.add_argument("--serial")
            cmd.add_argument("--execute", action="store_true", help="Actually perform this stage; otherwise display plan")
        if name in ("plan", "flash", "readback"):
            cmd.add_argument("--partition", choices=("boot", "preloader"), required=True)
        if name in ("plan", "readback"):
            cmd.add_argument("--image", type=Path, required=True)
        if name == "flash":
            cmd.add_argument("--confirm", help="Must be RMX3241 when --execute is used")
        if name == "readback":
            cmd.add_argument("--shutdown", action="store_true")
    sub.add_parser("shutdown-da", help="Explicitly shut down an ALREADY LOADED DA; no BROM handshake")
    return top


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fetch-tools":
            from .tools import fetch_tools
            fetch_tools()
        elif args.command == "wrap-da":
            from .tools import wrap_da
            print(wrap_da())
        elif args.command == "doctor":
            from .device import Device, compatible
            identity = Device(args.serial).inspect()
            try:
                compatible(identity)
                identity["supported_profile"] = "rmx3241-f12"
            except Refusal as error:
                identity["supported_profile"] = None
                identity["reason"] = str(error)
            print(json.dumps(identity, indent=2, ensure_ascii=False))
            return 0 if identity["supported_profile"] else 2
        elif args.command == "backup":
            from .session import backup
            backup(args.session, args.serial, args.execute)
        elif args.command == "verify-backups":
            from .session import session_path, verify_backups
            result = verify_backups(session_path(args.session))
            print("Verified backup files:", len(result["files"]))
        elif args.command == "patch-boot":
            from .patch import patch_boot
            patch_boot(args.session, args.serial, args.execute)
        elif args.command == "patch-preloader":
            from .patch import patch_preloader
            patch_preloader(args.session)
        elif args.command == "plan":
            from .flash import make_plan
            make_plan(args.session, args.partition, args.image)
        elif args.command == "flash":
            from .flash import flash
            flash(args.session, args.partition, args.serial, args.execute, args.confirm)
        elif args.command == "readback":
            from .da import readback
            readback(args.session, args.partition, args.image, args.shutdown)
        elif args.command == "shutdown-da":
            from .da import shutdown_da
            shutdown_da()
        elif args.command == "verify-root":
            from .device import Device
            result = Device(args.serial).call("shell", "su", "-c", "id", timeout=60)
            require("uid=0(root)" in result.stdout, "Root is not verified")
            print(result.stdout.strip())
        return 0
    except (Refusal, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print("STOP:", error, file=sys.stderr)
        return 1
