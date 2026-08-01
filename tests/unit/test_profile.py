import hashlib
import json
from pathlib import Path

import pytest

from bakugan_ds.errors import ProfileError, UnsupportedRomError
from bakugan_ds.profile import load_profile, read_rom_identity, sha256_file, validate_rom


def make_identity_rom(path: Path, *, size: int = 0x200) -> bytes:
    data = bytearray(size)
    data[0x00:0x0C] = b"BAKUGAN W\x00\x00\x00"
    data[0x0C:0x10] = b"B6RE"
    data[0x10:0x12] = b"52"
    data[0x1E] = 0
    path.write_bytes(data)
    return bytes(data)


def valid_profile_payload() -> dict[str, object]:
    return {
        "id": "test",
        "sha256": "0" * 64,
        "size": 512,
        "title": "BAKUGAN W",
        "game_code": "B6RE",
        "maker_code": "52",
        "revision": 0,
        "expected": {
            "arm9_offset": 16384,
            "arm9_ram_address": 33554432,
            "arm9_size": 448192,
            "arm7_offset": 887296,
            "arm7_ram_address": 37224448,
            "arm7_size": 160048,
            "fnt_offset": 1047552,
            "fnt_size": 212348,
            "fat_offset": 1260032,
            "fat_size": 88040,
            "nitrofs_file_count": 11005,
            "directory_count": 95,
            "arm9_overlay_offset": 464896,
            "arm9_overlay_size": 288,
            "arm7_overlay_offset": 0,
            "arm7_overlay_size": 0,
            "arm9_overlay_count": 9,
            "arm7_overlay_count": 0,
        },
    }


def test_load_profile_reads_exact_values(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(valid_profile_payload()), encoding="utf-8")

    profile = load_profile(profile_path)

    assert profile.id == "test"
    assert profile.game_code == "B6RE"
    assert profile.expected.nitrofs_file_count == 11005
    assert profile.expected.arm9_overlay_offset == 0x71800


def test_load_profile_rejects_bad_sha_length(tmp_path: Path) -> None:
    profile_path = tmp_path / "bad.json"
    payload = valid_profile_payload()
    payload["sha256"] = "abc"
    profile_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ProfileError, match="sha256"):
        load_profile(profile_path)


def test_read_rom_identity_reads_header_fields_and_hash(tmp_path: Path) -> None:
    rom_path = tmp_path / "test.nds"
    data = make_identity_rom(rom_path)

    identity = read_rom_identity(rom_path)

    assert identity.title == "BAKUGAN W"
    assert identity.game_code == "B6RE"
    assert identity.maker_code == "52"
    assert identity.revision == 0
    assert identity.size == len(data)
    assert identity.sha256 == hashlib.sha256(data).hexdigest()


def test_validate_rom_rejects_hash_mismatch(tmp_path: Path) -> None:
    rom_path = tmp_path / "test.nds"
    make_identity_rom(rom_path)
    profile = load_profile(Path("config/b6re_rev0.json"))

    with pytest.raises(UnsupportedRomError, match="size"):
        validate_rom(rom_path, profile)


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"Bakugan" * 1000)

    assert sha256_file(path, chunk_size=17) == hashlib.sha256(path.read_bytes()).hexdigest()
