from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

ARTIFACT = Path("analysis/gates/landing-and-shot-context.json")
OVERLAY_BASE = 0x02219440
OVERLAY_SHA256 = "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"


def required_overlay() -> bytes:
    value = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if value is None:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run landing integration tests")
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


def parse_addresses(values: list[str]) -> tuple[int, ...]:
    return tuple(int(value, 16) for value in values)


@pytest.mark.integration
def test_exact_landing_and_shot_regions() -> None:
    overlay = required_overlay()
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    for region in payload["exact_regions"]:
        assert region["component"] == "overlay_0007"
        start = int(region["start"], 16)
        end = int(region["end"], 16)
        assert OVERLAY_BASE <= start < end <= OVERLAY_BASE + len(overlay)
        chunk = overlay[start - OVERLAY_BASE : end - OVERLAY_BASE]
        assert hashlib.sha256(chunk).hexdigest() == region["sha256"]


@pytest.mark.integration
def test_landing_direct_call_inventories() -> None:
    overlay = required_overlay()
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    inventory = payload["direct_call_inventory"]

    assert direct_bl_calls(overlay, 0x02252730) == parse_addresses(
        inventory["throw_controller_constructor_0x02252730"]
    )
    assert direct_bl_calls(overlay, 0x02259AF0) == parse_addresses(
        inventory["primary_landing_evaluator_0x02259AF0"]
    )
    assert direct_bl_calls(overlay, 0x0225A278) == parse_addresses(
        inventory["alternate_landing_evaluator_0x0225A278"]
    )
    assert direct_bl_calls(overlay, 0x02262768) == parse_addresses(
        inventory["arena_descriptor_attachment_0x02262768"]
    )


@pytest.mark.integration
def test_committed_landing_boundaries_are_inside_guarded_regions() -> None:
    required_overlay()
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    guarded = [
        (int(region["start"], 16), int(region["end"], 16))
        for region in payload["exact_regions"]
    ]
    addresses = {
        0x02252730,
        0x02255640,
        0x02255684,
        0x0225568C,
        0x02259AF0,
        0x0225A278,
        0x02260A64,
        0x02260B04,
        0x02262768,
        0x0226A988,
        0x0226B5C4,
        0x0226BDAC,
        0x0226D488,
    }

    for address in addresses:
        assert any(start <= address < end for start, end in guarded), hex(address)
