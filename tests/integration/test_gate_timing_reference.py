from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

ARTIFACT = Path("analysis/gates/effect-timing.json")
OVERLAY_BASE = 0x02219440
OVERLAY_SHA256 = "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"


def required_overlay() -> bytes:
    value = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if value is None:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run Gate timing integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"BAKUGAN_DS_OVERLAY7 does not point to a file: {path}")
    overlay = path.read_bytes()
    assert hashlib.sha256(overlay).hexdigest() == OVERLAY_SHA256
    return overlay


@pytest.mark.integration
def test_exact_timing_regions_match_decoded_overlay() -> None:
    overlay = required_overlay()
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    for region in payload["exact_regions"]:
        start = int(region["start"], 16)
        end = int(region["end"], 16)
        component_offset = int(region["component_offset"], 16)
        assert component_offset == start - OVERLAY_BASE
        assert OVERLAY_BASE <= start < end <= OVERLAY_BASE + len(overlay)
        chunk = overlay[start - OVERLAY_BASE : end - OVERLAY_BASE]
        assert hashlib.sha256(chunk).hexdigest() == region["sha256"]


@pytest.mark.integration
def test_gate_and_battle_type_boundaries_match_expected_instructions() -> None:
    overlay = required_overlay()

    def word(address: int) -> int:
        offset = address - OVERLAY_BASE
        return int.from_bytes(overlay[offset : offset + 4], "little")

    assert word(0x0223D288) == 0xE0820001
    assert word(0x0223D28C) == 0xE1C500BE
    assert word(0x0223E338) == 0xE3E01000
    assert word(0x0224183C) == 0xE5D40020
    assert word(0x0224190C) == 0xE5940048


@pytest.mark.integration
def test_ability_result_and_gate_cleanup_boundaries_match() -> None:
    overlay = required_overlay()

    def word(address: int) -> int:
        offset = address - OVERLAY_BASE
        return int.from_bytes(overlay[offset : offset + 4], "little")

    assert word(0x0221A6B4) == 0xE92D4038
    assert word(0x0221B8D0) == 0xE28DD014
    assert word(0x022423E0) == 0xE1D412D1
    assert word(0x022423F0) == 0xE3A00014
    assert word(0x022626B8) == 0xE92D4038


@pytest.mark.integration
def test_round_and_match_reset_boundaries_match() -> None:
    overlay = required_overlay()

    def word(address: int) -> int:
        offset = address - OVERLAY_BASE
        return int.from_bytes(overlay[offset : offset + 4], "little")

    assert word(0x0223D3F4) == 0xE92D4070
    assert word(0x0225FD5C) == 0xE92D4010
    assert word(0x0225FEC8) == 0xE5C41294
