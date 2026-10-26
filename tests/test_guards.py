from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

from rootguide.common import Refusal, profile, sha256
from rootguide.device import compatible, same_device
from rootguide.gpt import parse_gpt
from rootguide.patch import preloader_preserved
from rootguide.tools import checked, safe_extract


def identity():
    props = dict(profile()["identity"])
    props.update({"sys.boot_completed": "1", "ro.boot.flash.locked": "0",
                  "ro.boot.vbmeta.device_state": "unlocked"})
    return {"serial_sha256": "synthetic-device-binding", "properties": props}


def gpt(overlap=False):
    data = bytearray(32768)
    sector = 4096
    entry_start = 8192
    entries = bytearray(128 * 128)
    for n, (name, first, last) in enumerate([
        ("boot", 16, 8207), ("seccfg", 20 if overlap else 10000, 2048 + (20 if overlap else 10000) - 1)
    ]):
        off = n * 128
        entries[off] = 1
        struct.pack_into("<QQ", entries, off + 32, first, last)
        encoded = name.encode("utf-16-le")
        entries[off + 56:off + 56 + len(encoded)] = encoded
    data[entry_start:entry_start + len(entries)] = entries
    header = bytearray(92)
    header[:8] = b"EFI PART"
    struct.pack_into("<III", header, 8, 0x10000, 92, 0)
    struct.pack_into("<QQQQ", header, 24, 1, 1000000, 8, 999999)
    struct.pack_into("<QIII", header, 72, 2, 128, 128, zlib.crc32(entries))
    struct.pack_into("<I", header, 16, zlib.crc32(header))
    data[sector:sector + len(header)] = header
    return data


def preloaders():
    original = bytearray(4194304)
    original[:10] = b"COMBO_BOOT"
    original[0x1000:0x1800] = bytes(range(256)) * 8
    modified = bytearray(original)
    modified[0x2000:] = original[0x1000:-0x1000]
    modified[0x1000:0x1000 + 13] = b"AND_ROMINFO_v"
    modified[0x104C] = 0
    return original, modified


class IdentityGuards(unittest.TestCase):
    def test_doctor_returns_nonzero_for_unsupported_phone(self):
        from rootguide.cli import main
        data = identity()
        data["properties"]["ro.product.model"] = "OTHER"
        with patch("rootguide.device.Device") as device, redirect_stdout(io.StringIO()):
            device.return_value.inspect.return_value = data
            self.assertEqual(main(["doctor"]), 2)

    def test_exact_supported_identity(self):
        compatible(identity(), unlocked=True)

    def test_every_identity_field_is_enforced(self):
        for key in profile()["identity"]:
            with self.subTest(key=key):
                data = identity()
                data["properties"][key] = "a different phone or build"
                with self.assertRaises(Refusal):
                    compatible(data)

    def test_locked_bootloader_refused(self):
        for key, value in [("ro.boot.flash.locked", "1"), ("ro.boot.vbmeta.device_state", "locked")]:
            data = identity()
            data["properties"][key] = value
            with self.assertRaises(Refusal):
                compatible(data, unlocked=True)

    def test_incomplete_boot_refused(self):
        data = identity()
        data["properties"]["sys.boot_completed"] = ""
        with self.assertRaises(Refusal):
            compatible(data)

    def test_other_serial_and_firmware_refused(self):
        for field in ("serial", "firmware"):
            old, new = identity(), identity()
            if field == "serial":
                new["serial_sha256"] = "other-device-binding"
            else:
                new["properties"]["ro.build.display.id"] = "other-build"
            with self.assertRaises(Refusal):
                same_device(old, new)


class GPTGuards(unittest.TestCase):
    def test_known_mtk_recovery_quirk_requires_explicit_opt_in(self):
        data = gpt()
        # Move the synthetic boot beyond recovery and add the exact observed recovery entry.
        struct.pack_into("<QQ", data, 8192 + 32, 40000, 48191)
        struct.pack_into("<QQ", data, 8192 + 128 + 32, 50000, 52047)
        offset = 8192 + 256
        data[offset] = 1
        struct.pack_into("<QQ", data, offset + 32, 8, 32775)
        name = "recovery".encode("utf-16-le")
        data[offset + 56:offset + 56 + len(name)] = name
        struct.pack_into("<Q", data, 4096 + 40, 34)
        struct.pack_into("<I", data, 4096 + 88, zlib.crc32(data[8192:8192 + 16384]))
        struct.pack_into("<I", data, 4096 + 16, 0)
        struct.pack_into("<I", data, 4096 + 16, zlib.crc32(data[4096:4096 + 92]))
        with self.assertRaises(Refusal):
            parse_gpt(data)
        self.assertEqual(parse_gpt(data, allow_mtk_recovery_quirk=True)["recovery"]["address"], 32768)

    def test_addresses_are_derived(self):
        parts = parse_gpt(gpt())
        self.assertEqual(parts["boot"], {"address": 16 * 4096, "size": 33554432})

    def test_corrupt_header_and_array_rejected(self):
        for offset in (4096 + 40, 8192 + 56):
            data = gpt()
            data[offset] ^= 1
            with self.assertRaises(Refusal):
                parse_gpt(data)

    def test_truncated_and_wrong_signature_rejected(self):
        for data in (gpt()[:12000], bytes(32768)):
            with self.assertRaises(Refusal):
                parse_gpt(data)

    def test_valid_crc_but_overlap_rejected(self):
        with self.assertRaises(Refusal):
            parse_gpt(gpt(overlap=True))


class FileGuards(unittest.TestCase):
    def test_preserved_payload_accepted(self):
        preloader_preserved(*preloaders())

    def test_signed_payload_change_rejected(self):
        old, new = preloaders()
        new[0x2400] ^= 1
        with self.assertRaises(Refusal):
            preloader_preserved(old, new)

    def test_missing_rominfo_or_wrong_flag_rejected(self):
        for offset in (0x1000, 0x104C):
            old, new = preloaders()
            new[offset] ^= 1
            with self.assertRaises(Refusal):
                preloader_preserved(old, new)

    def test_occupied_tail_rejected(self):
        old, new = preloaders()
        old[-1] = 1
        with self.assertRaises(Refusal):
            preloader_preserved(old, new)

    def test_checksum_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tool"
            path.write_bytes(b"untrusted replacement")
            with self.assertRaises(Refusal):
                checked(path, "0" * 64)

    def test_zip_traversal_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../escape", b"bad")
            with self.assertRaises(Refusal):
                safe_extract(archive, Path(folder) / "out")
            with zipfile.ZipFile(archive, "w") as z:
                item = zipfile.ZipInfo("link")
                item.external_attr = 0o120777 << 16
                z.writestr(item, "/etc/passwd")
            with self.assertRaises(Refusal):
                safe_extract(archive, Path(folder) / "out")


class FlashBoundaryGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.session = self.base / "session"
        (self.session / "backups").mkdir(parents=True)
        (self.session / "images").mkdir()
        old, new = preloaders()
        (self.session / "backups/preloader.bin").write_bytes(old)
        self.image = self.session / "images/preloader.bin"
        self.image.write_bytes(new)
        (self.session / "identity.json").write_text(json.dumps(identity()))
        self.tool = self.base / "verified-test-tool"
        self.tool.write_bytes(b"a synthetic binary")
        for target, value in [("rootguide.session.LOCAL", self.base),
                              ("rootguide.flash.verify_backups", {}),
                              ("rootguide.flash.da_path", self.tool),
                              ("rootguide.flash.executable", str(self.tool))]:
            if target.endswith("LOCAL"):
                context = patch(target, value)
            else:
                context = patch(target, return_value=value)
            context.start()
            self.addCleanup(context.stop)
        from rootguide.flash import make_plan
        with redirect_stdout(io.StringIO()):
            make_plan(self.session, "preloader", self.image)

    def test_default_does_not_contact_or_flash_phone(self):
        from rootguide.flash import flash
        with patch("rootguide.flash.bind_current") as bind, patch("rootguide.flash.antumbra") as write:
            with redirect_stdout(io.StringIO()):
                flash(self.session, "preloader")
            bind.assert_not_called()
            write.assert_not_called()

    def test_execution_without_confirmation_refused(self):
        from rootguide.flash import flash
        with patch("rootguide.flash.bind_current") as bind:
            with self.assertRaises(Refusal):
                flash(self.session, "preloader", execute=True)
            bind.assert_not_called()

    def test_changed_image_refused_before_phone_access(self):
        from rootguide.flash import flash
        data = bytearray(self.image.read_bytes())
        # Change the non-payload header; structural checks alone still pass.
        data[0x200] ^= 1
        self.image.write_bytes(data)
        with patch("rootguide.flash.bind_current") as bind:
            with self.assertRaises(Refusal):
                flash(self.session, "preloader", execute=True, confirm="RMX3241")
            bind.assert_not_called()

    def test_changed_tool_refused_before_phone_access(self):
        from rootguide.flash import flash
        self.tool.write_bytes(b"changed tool")
        with patch("rootguide.flash.bind_current") as bind:
            with self.assertRaises(Refusal):
                flash(self.session, "preloader", execute=True, confirm="RMX3241")
            bind.assert_not_called()


if __name__ == "__main__":
    unittest.main()
