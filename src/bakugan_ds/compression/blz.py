from __future__ import annotations

from dataclasses import dataclass
import struct

from bakugan_ds.errors import RomFormatError
from bakugan_ds.util import Buffer


@dataclass(frozen=True)
class BlzFooter:
    compressed_length: int
    header_length: int
    added_length: int


def parse_blz_footer(data: Buffer) -> BlzFooter:
    if len(data) < 8:
        raise RomFormatError("BLZ footer is truncated")
    compressed_and_header, added_length = struct.unpack_from("<II", data, len(data) - 8)
    header_length = compressed_and_header >> 24
    compressed_length = compressed_and_header & 0x00FFFFFF
    if header_length < 8:
        raise RomFormatError(f"BLZ header length must be at least 8, got {header_length}")
    if header_length > len(data):
        raise RomFormatError(
            f"BLZ header length {header_length} exceeds payload size {len(data)}"
        )
    if compressed_length < header_length:
        raise RomFormatError(
            f"BLZ compressed length {compressed_length} is smaller than header {header_length}"
        )
    if compressed_length > len(data):
        raise RomFormatError(
            f"BLZ compressed length {compressed_length} exceeds payload size {len(data)}"
        )
    padding = memoryview(data)[len(data) - header_length : len(data) - 8]
    if any(byte != 0xFF for byte in padding):
        raise RomFormatError("BLZ header padding is not entirely 0xFF")
    return BlzFooter(
        compressed_length=compressed_length,
        header_length=header_length,
        added_length=added_length,
    )


def is_blz(data: Buffer) -> bool:
    try:
        footer = parse_blz_footer(data)
    except RomFormatError:
        return False
    return footer.added_length > 0


def decompress_blz(data: Buffer) -> bytes:
    footer = parse_blz_footer(data)
    if footer.added_length == 0:
        raise RomFormatError("BLZ added length is zero; payload is not compressed")

    source = memoryview(data)
    passthrough_length = len(source) - footer.compressed_length
    compressed_end = len(source) - footer.header_length
    compressed = source[passthrough_length:compressed_end]
    decoded_length = len(source) + footer.added_length - passthrough_length
    decoded = bytearray(decoded_length)

    read_count = 0
    written = 0
    flags = 0
    mask = 0

    while written < decoded_length:
        if mask == 0:
            if read_count >= len(compressed):
                raise RomFormatError("BLZ flags byte is missing")
            flags = int(compressed[len(compressed) - 1 - read_count])
            read_count += 1
            mask = 0x80

        if flags & mask:
            if read_count + 2 > len(compressed):
                raise RomFormatError("BLZ reference token is truncated")
            first = int(compressed[len(compressed) - 1 - read_count])
            read_count += 1
            second = int(compressed[len(compressed) - 1 - read_count])
            read_count += 1
            length = (first >> 4) + 3
            displacement = (((first & 0x0F) << 8) | second) + 3
            if displacement > written:
                raise RomFormatError(
                    f"BLZ displacement {displacement} exceeds decoded suffix size {written}"
                )
            source_index = written - displacement
            for _ in range(length):
                if written >= decoded_length:
                    break
                decoded[len(decoded) - 1 - written] = decoded[len(decoded) - 1 - source_index]
                written += 1
                source_index += 1
        else:
            if read_count >= len(compressed):
                raise RomFormatError("BLZ literal byte is missing")
            decoded[len(decoded) - 1 - written] = compressed[len(compressed) - 1 - read_count]
            read_count += 1
            written += 1

        mask >>= 1

    return bytes(source[:passthrough_length]) + bytes(decoded)
