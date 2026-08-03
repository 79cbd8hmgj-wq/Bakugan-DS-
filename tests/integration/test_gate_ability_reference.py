from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

ARTIFACT = Path("analysis/gates/ability-card-state.json")
OVERLAY_BASE = 0x02219440
OVERLAY_SHA256 = "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"


def required_overlay() -> bytes:
    value = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if value is None:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run Gate Ability integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"BAKUGAN_DS_OVERLAY7 does not point to a file: {path}")
    overlay = path.read_bytes()
    assert hashlib.sha256(overlay).hexdigest() == OVERLAY_SHA256
    return overlay


def direct_bl_calls(data: bytes, target: int) -> tuple[int, ...]:
    calls: list[int] = []
    for offset in range(0, len(data) - 3, 4):
        word = int.from_bytes(data[offset : offset + 4], "little")
        if word & 0x0F000000 != 0x0B000000:
            continue
        displacement = (word & 0x00FFFFFF) << 2
        if displacement & 0x02000000:
            displacement -= 0x04000000
        address = OVERLAY_BASE + offset
        destination = (address + 8 + displacement) & 0xFFFFFFFF
        if destination == target:
            calls.append(address)
    return tuple(calls)


@pytest.mark.integration
def test_exact_ability_state_and_timing_regions() -> None:
    overlay = required_overlay()
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    for region in payload["exact_regions"]:
        assert region["component"] == "overlay_0007"
        start = int(region["start"])
        end = int(region["end"])
        assert OVERLAY_BASE <= start < end <= OVERLAY_BASE + len(overlay)
        chunk = overlay[start - OVERLAY_BASE : end - OVERLAY_BASE]
        assert hashlib.sha256(chunk).hexdigest() == region["sha256"]


@pytest.mark.integration
def test_ability_direct_call_inventories() -> None:
    overlay = required_overlay()
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert direct_bl_calls(overlay, 0x0226A448) == tuple(
        payload["direct_calls"]["ability_state_setter"]
    )
    assert direct_bl_calls(overlay, 0x0226A700) == tuple(
        payload["direct_calls"]["ability_slot_selector"]
    )
