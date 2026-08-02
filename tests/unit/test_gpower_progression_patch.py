from __future__ import annotations

import json
import os
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "patches/gpower-progression-50.json"
DOC_PATH = ROOT / "docs/gpower-rebalance.md"
OVERLAY_LOAD_ADDRESS = 0x02219440


def _decode_data_processing(word: int) -> dict[str, int]:
    return {
        "condition": (word >> 28) & 0xF,
        "opcode": (word >> 21) & 0xF,
        "rn": (word >> 16) & 0xF,
        "rd": (word >> 12) & 0xF,
        "shift_imm": (word >> 7) & 0x1F,
        "shift_type": (word >> 5) & 0x3,
        "rm": word & 0xF,
    }


def _load_patch_document() -> dict[str, object]:
    return json.loads(PATCH_PATH.read_text(encoding="utf-8"))


def test_patch_targets_both_confirmed_progression_add_instructions() -> None:
    payload = _load_patch_document()
    assert payload["format_version"] == 1
    assert payload["profile_id"] == "b6re_rev0"

    patches = payload["patches"]
    assert len(patches) == 2
    by_id = {item["id"]: item for item in patches}
    assert set(by_id) == {
        "halve-player-one-progression",
        "halve-player-two-progression",
    }

    expected = {
        "halve-player-one-progression": (0x0223D0F8, 0x23CB8, "011082e0", "a11082e0"),
        "halve-player-two-progression": (0x0223D108, 0x23CC8, "000081e0", "a00081e0"),
    }
    for patch_id, (runtime_address, component_offset, original, replacement) in expected.items():
        patch = by_id[patch_id]
        assert patch["type"] == "binary_replace"
        assert patch["target"] == "overlay:7"
        assert patch["offset"] == component_offset
        assert OVERLAY_LOAD_ADDRESS + patch["offset"] == runtime_address
        assert patch["expected"] == original
        assert patch["replacement"] == replacement


def test_replacements_are_arm_add_with_lsr_one() -> None:
    payload = _load_patch_document()
    for patch in payload["patches"]:
        original = struct.unpack("<I", bytes.fromhex(patch["expected"]))[0]
        replacement = struct.unpack("<I", bytes.fromhex(patch["replacement"]))[0]
        old_fields = _decode_data_processing(original)
        new_fields = _decode_data_processing(replacement)

        assert new_fields["condition"] == 0xE
        assert new_fields["opcode"] == 0x4
        assert new_fields["rn"] == old_fields["rn"]
        assert new_fields["rd"] == old_fields["rd"]
        assert new_fields["rm"] == old_fields["rm"]
        assert old_fields["shift_imm"] == 0
        assert new_fields["shift_imm"] == 1
        assert new_fields["shift_type"] == 1


def test_patch_halves_only_the_progression_component() -> None:
    def original(base: int, progression: int) -> int:
        return base + progression

    def patched(base: int, progression: int) -> int:
        return base + (progression >> 1)

    assert patched(190, 0) == original(190, 0) == 190
    assert original(190, 250) == 440
    assert patched(190, 250) == 315
    assert original(650, 250) == 900
    assert patched(650, 250) == 775
    assert patched(300, 151) == 375


def test_patch_matches_exact_overlay_when_available() -> None:
    raw_path = os.environ.get("BAKUGAN_OVERLAY7_PATH")
    if raw_path is None:
        return
    overlay = Path(raw_path).read_bytes()
    payload = _load_patch_document()
    for patch in payload["patches"]:
        offset = patch["offset"]
        expected = bytes.fromhex(patch["expected"])
        assert overlay[offset : offset + len(expected)] == expected


def test_document_states_scope_commands_and_remaining_limitations() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for required in (
        "base_G + (progression_G >> 1)",
        "0x0223D0F8",
        "0x0223D108",
        "bakugan-ds patch",
        "bakugan-ds rebuild",
        "Gate Card bonuses are unchanged",
        "form-base and evolution gaps are unchanged",
        "50%",
    ):
        assert required in text
