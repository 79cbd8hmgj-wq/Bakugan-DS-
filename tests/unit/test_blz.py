import struct

import pytest

from bakugan_ds.compression.blz import decompress_blz, is_blz, parse_blz_footer
from bakugan_ds.errors import RomFormatError


def make_footer(compressed_length: int, header_length: int, added_length: int) -> bytes:
    return struct.pack("<II", compressed_length | (header_length << 24), added_length)


def test_blz_parses_verified_overlay_7_footer() -> None:
    data = b"x" * (255740 - 11) + b"\xFF" * 3 + bytes.fromhex("fc e6 03 0b a4 3a 03 00")
    footer = parse_blz_footer(data)

    assert footer.compressed_length == 255740
    assert footer.header_length == 11
    assert footer.added_length == 211620


def test_blz_decodes_backwards_reference_stream() -> None:
    compressed = bytes.fromhex("00 f0 41 42 43 10") + make_footer(14, 8, 7)
    assert decompress_blz(compressed) == b"ABC" * 7


def test_blz_preserves_uncompressed_prefix() -> None:
    compressed_tail = bytes.fromhex("00 f0 41 42 43 10") + make_footer(14, 8, 7)
    compressed = b"PRE" + compressed_tail
    assert decompress_blz(compressed) == b"PRE" + b"ABC" * 7


def test_blz_detection_accepts_valid_stream() -> None:
    compressed = bytes.fromhex("00 f0 41 42 43 10") + make_footer(14, 8, 7)
    assert is_blz(compressed) is True
    assert is_blz(b"not compressed") is False


def test_blz_rejects_short_header_length() -> None:
    data = b"x" * 8 + make_footer(8, 7, 1)
    with pytest.raises(RomFormatError, match="header length"):
        parse_blz_footer(data)


def test_blz_rejects_compressed_length_larger_than_payload() -> None:
    data = b"x" * 8 + make_footer(100, 8, 1)
    with pytest.raises(RomFormatError, match="compressed length"):
        parse_blz_footer(data)


def test_blz_rejects_non_ff_padding() -> None:
    data = b"payload" + b"\x00" + make_footer(16, 9, 1)
    with pytest.raises(RomFormatError, match="padding"):
        parse_blz_footer(data)


def test_blz_rejects_missing_flags() -> None:
    data = make_footer(8, 8, 1)
    with pytest.raises(RomFormatError, match="flags"):
        decompress_blz(data)


def test_blz_rejects_truncated_reference() -> None:
    data = b"\x80" + make_footer(9, 8, 10)
    with pytest.raises(RomFormatError, match="reference"):
        decompress_blz(data)


def test_blz_rejects_invalid_displacement() -> None:
    # Read backwards: literal A, then an 18-byte reference with minimum disp 3.
    data = bytes.fromhex("00 f0 41 40") + make_footer(12, 8, 7)
    with pytest.raises(RomFormatError, match="displacement"):
        decompress_blz(data)
