from __future__ import annotations

import hashlib
import json
import os
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "patches/core-g-compression-400.json"
DOC_PATH = ROOT / "docs/core-g-compression.md"
RUNTIME_PATH = ROOT / "analysis/runtime-observations/core_g_compression_400.json"
OVERLAY_BASE = 0x02219440
OVERLAY_SIZE = 467360
OVERLAY_SHA256 = "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"

EXPECTED_REGIONS = {
    "preload-core-compression-constant": {
        "offset": 0x23C18,
        "runtime": 0x0223D058,
        "expected": "0c70a0e3",
        "replacement": "c870a0e3",
    },
    "compress-both-core-g-inputs": {
        "offset": 0x23CB0,
        "runtime": 0x0223D0F0,
        "expected": (
            "b420d1e1b610d1e1011082e0bc10c6e1b410d0e1b600d0e1000081e0"
            "b002c6e1bc00d6e1b001c6e1b002d6e10ab0a0e30b70a0e1b402c6e1"
            "b241c6e1b642c6e1b641c6e1ba42c6e1"
        ),
        "replacement": (
            "b420d1e1b610d1e1190e52e3a2208780011082e0bc10c6e1b011c6e1"
            "b410d0e1b600d0e1190e51e3a1108780000081e0b002c6e1b402c6e1"
            "b241c6e1b642c6e1b641c6e1ba42c6e1"
        ),
    },
    "restore-gate-scale-constant": {
        "offset": 0x23D78,
        "runtime": 0x0223D1B8,
        "expected": "0b80a0e1",
        "replacement": "0a80a0e3",
    },
}

REPLACEMENT_WORDS = [
    0xE1D120B4,
    0xE1D110B6,
    0xE3520E19,
    0x808720A2,
    0xE0821001,
    0xE1C610BC,
    0xE1C611B0,
    0xE1D010B4,
    0xE1D000B6,
    0xE3510E19,
    0x808710A1,
    0xE0810000,
    0xE1C602B0,
    0xE1C602B4,
    0xE1C641B2,
    0xE1C642B6,
    0xE1C641B6,
    0xE1C642BA,
]


def compressed_core_g(value: int) -> int:
    if not 0 <= value <= 0xFFFF:
        raise ValueError("core G must fit unsigned 16-bit storage")
    return value if value <= 400 else 200 + (value >> 1)


def load_patch_document() -> dict[str, object]:
    return json.loads(PATCH_PATH.read_text(encoding="utf-8"))


def patch_entries() -> dict[str, dict[str, object]]:
    payload = load_patch_document()
    return {entry["id"]: entry for entry in payload["patches"]}


def test_patch_document_targets_exact_profile_and_three_regions() -> None:
    payload = load_patch_document()
    assert payload["format_version"] == 1
    assert payload["profile_id"] == "b6re_rev0"
    assert len(payload["patches"]) == 3

    entries = patch_entries()
    assert list(entries) == list(EXPECTED_REGIONS)
    for patch_id, expected in EXPECTED_REGIONS.items():
        entry = entries[patch_id]
        assert entry["type"] == "binary_replace"
        assert entry["target"] == "overlay:7"
        assert entry["offset"] == expected["offset"]
        assert OVERLAY_BASE + entry["offset"] == expected["runtime"]
        assert entry["expected"] == expected["expected"]
        assert entry["replacement"] == expected["replacement"]
        assert len(bytes.fromhex(entry["expected"])) == len(
            bytes.fromhex(entry["replacement"])
        )


def test_replacement_block_decodes_to_approved_arm_words() -> None:
    replacement = bytes.fromhex(
        EXPECTED_REGIONS["compress-both-core-g-inputs"]["replacement"]
    )
    assert len(replacement) == 72
    assert list(struct.unpack("<18I", replacement)) == REPLACEMENT_WORDS

    assert struct.unpack("<I", bytes.fromhex("c870a0e3"))[0] == 0xE3A070C8
    assert struct.unpack("<I", bytes.fromhex("0a80a0e3"))[0] == 0xE3A0800A

    first_cmp, first_addhi = REPLACEMENT_WORDS[2:4]
    second_cmp, second_addhi = REPLACEMENT_WORDS[9:11]
    assert first_cmp == 0xE3520E19
    assert second_cmp == 0xE3510E19
    assert (first_addhi >> 28) == 0x8
    assert (second_addhi >> 28) == 0x8
    assert first_addhi == 0x808720A2
    assert second_addhi == 0x808710A1

    assert REPLACEMENT_WORDS[4] == 0xE0821001
    assert REPLACEMENT_WORDS[11] == 0xE0810000
    assert REPLACEMENT_WORDS[14:] == [
        0xE1C641B2,
        0xE1C642B6,
        0xE1C641B6,
        0xE1C642BA,
    ]


def test_approved_curve_vectors_and_later_contributions() -> None:
    expected = {
        0: 0,
        190: 190,
        399: 399,
        400: 400,
        401: 400,
        410: 405,
        440: 420,
        500: 450,
        650: 525,
        670: 535,
        900: 650,
        990: 695,
    }
    assert {value: compressed_core_g(value) for value in expected} == expected
    assert compressed_core_g(190) + 30 + 100 == 320
    assert compressed_core_g(650) + 30 + 100 == 655
    with pytest.raises(ValueError):
        compressed_core_g(-1)
    with pytest.raises(ValueError):
        compressed_core_g(0x10000)


def test_declared_ranges_do_not_overlap() -> None:
    ranges = []
    for item in EXPECTED_REGIONS.values():
        start = item["offset"]
        end = start + len(bytes.fromhex(item["expected"]))
        ranges.append((start, end))
    ranges.sort()
    assert all(left[1] <= right[0] for left, right in zip(ranges, ranges[1:]))


def test_optional_exact_overlay_guards() -> None:
    value = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if not value:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to validate the exact decoded overlay")
    overlay = Path(value).read_bytes()
    assert len(overlay) == OVERLAY_SIZE
    assert hashlib.sha256(overlay).hexdigest() == OVERLAY_SHA256
    for item in EXPECTED_REGIONS.values():
        expected = bytes.fromhex(item["expected"])
        offset = item["offset"]
        assert overlay[offset : offset + len(expected)] == expected


def test_document_states_scope_commands_and_runtime_gate() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for required in (
        "core G-Power at or below 400",
        "0x0223D058",
        "0x0223D0F0",
        "0x0223D1B8",
        "both combatants",
        "mutable G modifier",
        "field G-Power pickups",
        "Gate Card and attribute bonuses",
        "persistent roster",
        "no code cave",
        "bakugan-ds patch",
        "bakugan-ds rebuild",
        "Verification evidence",
    ):
        assert required in text


def test_runtime_observation_records_controlled_cpu_and_clean_battle_entry() -> None:
    payload = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
    assert payload["profile_id"] == "b6re_rev0"
    assert payload["patch"]["threshold_g"] == 400
    assert payload["patch"]["high_curve"] == "200 + floor(core_g / 2)"

    cases = {item["case"]: item for item in payload["controlled_arm9_execution"]}
    low = cases["low_unchanged"]
    assert low["inputs"] == {
        "opponent": {"core_g": 230, "mutable_modifier_g": 0},
        "player": {"core_g": 190, "mutable_modifier_g": 0},
    }
    assert low["outputs"] == {
        "opponent_base_snapshot_g": 230,
        "player_base_snapshot_g": 190,
    }

    high = cases["high_and_modifier_symmetry"]
    assert high["outputs"] == {
        "opponent_base_snapshot_g": 555,
        "player_base_snapshot_g": 525,
    }

    gate_cases = {item["case"]: item for item in payload["controlled_gate_execution"]}
    assert gate_cases["high_player_gate"]["equation"] == "525 + 100 = 625"
    assert gate_cases["high_modifier_gate"]["equation"] == "555 + 100 = 655"

    smoke = payload["clean_game_smoke"]
    assert smoke["reached_first_battle"] is True
    assert smoke["serpenoid_selection_g"] == 190
    assert smoke["full_battle_completion_claimed"] is False
