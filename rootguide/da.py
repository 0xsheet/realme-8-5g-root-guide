"""Read-only verification plus explicit shutdown on an ALREADY LOADED XFlash DA."""
import logging
import sys

from .common import profile, require, save_json, sha256
from .gpt import parse_gpt
from .session import session_path, verify_backups
from .tools import TOOLS


def connect_loaded_da():
    sys.path.insert(0, str(TOOLS / "mtkclient"))
    import usb.core
    devices = list(usb.core.find(find_all=True, idVendor=0x22d9, idProduct=0x0006))
    require(len(devices) == 1, "Exactly one OPLUS DA/Preloader interface is required")
    from mtkclient.config.mtk_config import MtkConfig
    from mtkclient.Library.mtk_class import Mtk
    from mtkclient.Library.DA.xflash.xflash_lib import DAXFlash
    config = MtkConfig(loglevel=logging.INFO, gui=None, guiprogress=None)
    config.init_hwcode(profile()["hwcode"])
    mtk = Mtk(config)
    require(mtk.port.cdc.connect(), "Cannot open already-loaded DA")
    # Deliberately NO BROM handshake: another handshake corrupts this active DA stream.
    da = DAXFlash(mtk, mtk.daloader.daconfig, logging.INFO)
    geometry = da.get_ufs_info(display=False)
    require(geometry is not None, "No UFS geometry from active DA; stop and reconnect")
    storage = mtk.daloader.daconfig.storage
    storage.flashtype, storage.ufs = "ufs", geometry
    storage.set_flash_size()
    return da


def readback(path, partition, expected, shutdown=False):
    session = session_path(path)
    manifest = verify_backups(session)
    da = connect_loaded_da()
    pgpt = session / "readback-PGPT.bin"
    require(da.readflash(addr=0, length=0x8000, filename=str(pgpt), parttype="user", display=False),
            "Cannot read fresh GPT")
    parts = parse_gpt(pgpt.read_bytes(), profile()["sector_size"], allow_mtk_recovery_quirk=True)
    require(parts == manifest["partitions"], "Device GPT changed; no reboot sent")
    if partition == "boot":
        address, length, section = parts["boot"]["address"], parts["boot"]["size"], "user"
    elif partition == "preloader":
        address, length, section = 0, profile()["preloader_size"], "boot1"
    else:
        raise ValueError("Unsupported readback partition")
    from pathlib import Path
    expected = Path(expected)
    require(expected.stat().st_size == length, "Readback image/partition size mismatch")
    output = session / (partition + "-readback.bin")
    require(da.readflash(addr=address, length=length, filename=str(output), parttype=section, display=False),
            "Incomplete readback; no reboot sent")
    output.chmod(0o600)
    require(output.stat().st_size == length and sha256(output) == sha256(expected),
            "READBACK MISMATCH; no reboot sent. Use the documented recovery procedure.")
    result = {"partition": partition, "bytes": length, "sha256": sha256(output), "matches": True}
    save_json(session / (partition + "-verification.json"), result)
    print("Readback verified:", result)
    if shutdown:
        require(da.shutdown(bootmode=1), "DA did not acknowledge shutdown")
        print("Shutdown acknowledged. The documented phone may require pressing Power for 3 seconds.")


def shutdown_da():
    da = connect_loaded_da()
    require(da.shutdown(bootmode=1), "DA did not acknowledge shutdown")
    print("Shutdown acknowledged. Power on and reconnect Android.")
