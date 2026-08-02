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
        "Clean full-game smoke test",
        "returned to the surrounding park story",
    ):
        assert required in text


RUNTIME_PATH = ROOT / "analysis/runtime-observations/core_g_compression_validation.json"


def test_runtime_observation_records_controlled_and_full_game_proof() -> None:
    payload = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
    assert payload["profile_id"] == "b6re_rev0"
    assert payload["source_rom_sha256"] == (
        "7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b"
    )
    assert payload["rebuilt_rom_sha256"] == (
        "429a5830e1a996cccd26e6cb93793aa229eb6f83a5e687fd4d0604e81eebbce0"
    )
    assert payload["patch"]["threshold_g"] == 400
    assert payload["patch"]["high_curve"] == "200 + floor(core_g / 2)"
    assert [item["id"] for item in payload["patch"]["regions"]] == list(
        EXPECTED_REGIONS
    )

    assert payload["overlay"]["changed_byte_count"] == 41
    assert payload["overlay"]["decoded_size"] == OVERLAY_SIZE
    assert payload["overlay"]["bss_size"] == 1600
    build = payload["build_verification"]
    assert build["rom_size"] == 134217728
    assert build["overlay_output_encoding"] == "uncompressed-overlay"
    assert build["overlay_flags"] == 0
    assert build["overlay_compressed_size"] == 0
    assert build["unchanged_fat_payloads_verified"] == 11004
    assert build["layout_mismatches"] == 0

    cases = {item["case"]: item for item in payload["controlled_constructor_cases"]}
    low = cases["low_unchanged"]
    assert low["outputs"]["opponent"]["base_snapshot_g"] == 230
    assert low["outputs"]["player"]["base_snapshot_g"] == 190
    assert low["outputs"]["zero_initialized_gate_fields"] == [0, 0, 0, 0]

    high = cases["high_modifier_and_symmetry"]
    assert high["inputs"] == {
        "opponent": {"core_g": 650, "mutable_modifier_g": 30},
        "player": {"core_g": 650, "mutable_modifier_g": 0},
    }
    assert high["outputs"]["opponent"] == {
        "compressed_core_g": 525,
        "base_snapshot_g": 555,
        "current_snapshot_g": 555,
    }
    assert high["outputs"]["player"] == {
        "compressed_core_g": 525,
        "base_snapshot_g": 525,
        "current_snapshot_g": 525,
    }

    gate_cases = {item["case"]: item for item in payload["controlled_gate_cases"]}
    assert gate_cases["high_player_gate"]["equation"] == "525 + 100 = 625"
    assert gate_cases["high_modifier_gate"]["equation"] == "555 + 100 = 655"

    smoke = payload["clean_game_smoke"]
    assert smoke["title_screen_reached"] is True
    assert smoke["profile_created"] is True
    assert smoke["first_battle_entered"] is True
    assert smoke["serpenoid_selection_g"] == 190
    assert smoke["player_throw_completed"] is True
    assert smoke["player_bakugan_stood_on_gate"] is True
    assert smoke["gate_result"] == {
        "opponent": {
            "base_snapshot_g": 230,
            "gate_bonus_g": 180,
            "target_total_g": 410,
        },
        "player": {
            "base_snapshot_g": 190,
            "gate_bonus_g": 100,
            "target_total_g": 290,
        },
    }
    assert smoke["attribute_minigame_entered"] is True
    assert smoke["tutorial_exit_method"] == "built_in_skip_after_failed_rub_retry"
    assert smoke["tutorial_completion_dialogue_observed"] is True
    assert smoke["returned_to_surrounding_story"] is True
    assert smoke["post_exit_input_responsive"] is True
    assert smoke["overlay_failure_observed"] is False
    assert "does not claim a natural win" in smoke["scope_note"]

    hashes = payload["local_evidence_hashes"]
    assert len(hashes) == 7
    assert all(len(value) == 64 for value in hashes.values())
    assert "not committed" in payload["repository_boundary"]
