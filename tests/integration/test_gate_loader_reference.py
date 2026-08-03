from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from bakugan_ds.compression.lz10 import decompress_lz10
from bakugan_ds.gates.loader import (
    REFERENCE_RAW_SHA256,
    CacheLayout,
    append_validated_trailer,
    build_expanded_overlay,
    validate_overlay_expansion,
)
from bakugan_ds.gates.record import GateRecordV1, build_trailer


def required_path(name: str) -> Path:
    value = os.environ.get(name)
    if value is None:
        pytest.skip(f"set {name} to run Gate loader reference tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"{name} does not point to a file: {path}")
    return path


def empty_record(card_id: int) -> GateRecordV1:
    return GateRecordV1(
        card_id=card_id,
        archetype=0,
        flags=0,
        flat_bonus_g=0,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        battle_weights=(0, 0, 0, 0, 0, 0),
        preferred_type=255,
        condition_id=0,
        effect_id=0,
        drawback_id=0,
        effect_value=0,
        drawback_value=0,
        activation_limit=0,
        fatigue_rate=0,
        target_mode=0,
        timing_phase=0,
        condition_value=0,
        secondary_effect_id=0,
        secondary_condition_id=0,
        secondary_value=0,
        reserved=0,
    )


def fat_payload(rom: bytes, file_id: int) -> bytes:
    fat_offset = int.from_bytes(rom[0x48:0x4C], "little")
    fat_size = int.from_bytes(rom[0x4C:0x50], "little")
    entry_offset = fat_offset + file_id * 8
    if entry_offset + 8 > fat_offset + fat_size:
        pytest.fail(f"file ID {file_id} is outside the FAT")
    start = int.from_bytes(rom[entry_offset : entry_offset + 4], "little")
    end = int.from_bytes(rom[entry_offset + 4 : entry_offset + 8], "little")
    return rom[start:end]


@pytest.mark.integration
def test_reference_carrier_accepts_valid_trailer_without_changing_lz10_output() -> None:
    rom = required_path("BAKUGAN_DS_ROM").read_bytes()
    raw = fat_payload(rom, 2762)
    assert len(raw) == 2840
    assert hashlib.sha256(raw).hexdigest() == REFERENCE_RAW_SHA256

    trailer = build_trailer(
        tuple(empty_record(card_id) for card_id in range(1, 104))
    )
    combined = append_validated_trailer(raw, trailer)
    assert decompress_lz10(combined) == decompress_lz10(raw)
    assert combined[: len(raw)] == raw


@pytest.mark.integration
def test_reference_overlay_expansion_preserves_payload_and_old_bss_addresses() -> None:
    overlay = required_path("BAKUGAN_DS_OVERLAY7").read_bytes()
    module = b"\0" * 0x8000
    expanded = build_expanded_overlay(overlay, module)
    validate_overlay_expansion(overlay, expanded, CacheLayout())
    assert expanded[:0x721A0] == overlay
    assert expanded[0x721A0:0x727E0] == b"\0" * 0x640
    assert len(expanded) == 0x7A7E0
