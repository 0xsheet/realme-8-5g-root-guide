import struct
import zlib

from .common import require


def parse_gpt(data, sector_size=4096, allow_mtk_recovery_quirk=False):
    """Validate both GPT CRCs and return byte ranges from a fresh primary GPT read."""
    require(len(data) >= sector_size + 92, "Truncated GPT")
    offset = sector_size
    require(data[offset:offset + 8] == b"EFI PART", "GPT signature not found")
    size, expected_crc = struct.unpack_from("<II", data, offset + 12)
    require(92 <= size <= sector_size and offset + size <= len(data), "Invalid GPT header size")
    header = bytearray(data[offset:offset + size])
    struct.pack_into("<I", header, 16, 0)
    require(zlib.crc32(header) & 0xFFFFFFFF == expected_crc, "GPT header CRC mismatch")
    current_lba = struct.unpack_from("<Q", data, offset + 24)[0]
    require(current_lba == 1, "Not a primary GPT")
    first_usable, last_usable = struct.unpack_from("<QQ", data, offset + 40)
    table_lba, count, entry_size, table_crc = struct.unpack_from("<QIII", data, offset + 72)
    require(0 < count <= 4096 and 128 <= entry_size <= 1024, "Invalid GPT entry geometry")
    start, length = table_lba * sector_size, count * entry_size
    require(start >= sector_size * 2 and start + length <= len(data), "Truncated GPT entry array")
    entries = data[start:start + length]
    require(zlib.crc32(entries) & 0xFFFFFFFF == table_crc, "GPT partition array CRC mismatch")
    parts = {}
    for n in range(count):
        entry = entries[n * entry_size:(n + 1) * entry_size]
        if entry[:16] == b"\0" * 16:
            continue
        first, last = struct.unpack_from("<QQ", entry, 32)
        name = entry[56:128].decode("utf-16-le").split("\0", 1)[0]
        require(name and name not in parts, "Empty or duplicated GPT partition name")
        # The verified RMX3241 GPT advertises FirstUsableLBA=34 but places its
        # recovery at 8..32775 on 4096-byte sectors. Accept only this exact,
        # explicitly opted-in vendor quirk, beyond the validated entry array.
        quirk = (allow_mtk_recovery_quirk and sector_size == 4096 and first_usable == 34
                 and name == "recovery" and first == 8 and last == 32775)
        require(first <= last <= last_usable and (first >= first_usable or quirk),
                "Partition lies outside usable GPT space")
        require(first * sector_size >= start + length, "Partition overlaps primary GPT metadata")
        parts[name] = {"address": first * sector_size, "size": (last - first + 1) * sector_size}
    require("boot" in parts and "seccfg" in parts, "Expected partitions missing")
    ranges = sorted((p["address"], p["address"] + p["size"]) for p in parts.values())
    require(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])), "Overlapping GPT partitions")
    return parts
