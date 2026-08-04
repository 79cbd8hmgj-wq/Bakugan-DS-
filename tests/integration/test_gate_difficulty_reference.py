from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

ARTIFACT = Path("analysis/gates/difficulty-context.json")
OVERLAY_BASE = 0x02219440
OVERLAY_SHA256 = {
    "overlay_0001": "65c807a92bce03d6e6d7d053c8c8c6c933d27de02089a39deca231f207cd139a",
    "overlay_0007": "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1",
}
OVERLAY_ENV = {
    "overlay_0001": "BAKUGAN_DS_OVERLAY1",
    "overlay_0007": "BAKUGAN_DS_OVERLAY7",
}


def required_overlay(component: str) -> bytes:
    environment = OVERLAY_ENV[component]
    value = os.environ.get(environment)
    if value is None:
        pytest.skip(f"set {environment} to run Gate difficulty integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"{environment} does not point to a file: {path}")
    overlay = path.read_bytes()
    assert hashlib.sha256(overlay).hexdigest() == OVERLAY_SHA256[component]
    return overlay


def word_at(data: bytes, runtime_address: int) -> int:
    offset = runtime_address - OVERLAY_BASE
    return int.from_bytes(data[offset : offset + 4], "little")


@pytest.mark.integration
def test_exact_difficulty_regions_match_decoded_overlays() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    overlays = {
        component: required_overlay(component)
        for component in OVERLAY_SHA256
    }

    for region in payload["exact_regions"]:
        component = region["component"]
        overlay = overlays[component]
        start = int(region["start"], 16)
        end = int(region["end"], 16)
        component_offset = int(region["component_offset"], 16)
        assert component_offset == start - OVERLAY_BASE
        assert OVERLAY_BASE <= start < end <= OVERLAY_BASE + len(overlay)
        chunk = overlay[start - OVERLAY_BASE : end - OVERLAY_BASE]
        assert hashlib.sha256(chunk).hexdigest() == region["sha256"]


@pytest.mark.integration
def test_overlay1_decodes_and_stores_selected_difficulty() -> None:
    overlay = required_overlay("overlay_0001")

    assert word_at(overlay, 0x02221E08) == 0xE5D0300E  # ldrb r3,[r0,#0x0E]
    assert word_at(overlay, 0x02221E10) == 0xE1A02C83  # lsl r2,r3,#25
    assert word_at(overlay, 0x02221E18) == 0xE1A02F22  # lsr r2,r2,#30
    assert word_at(overlay, 0x02221E1C) == 0xE5C5225C  # strb r2,[r5,#0x25C]
    assert word_at(overlay, 0x02221E8C) == 0xE5D5225C  # ldrb r2,[r5,#0x25C]
    assert word_at(overlay, 0x02221E94) == 0xE5C12096  # strb r2,[r1,#0x96]
    assert word_at(overlay, 0x02221F0C) == 0x020D433C


@pytest.mark.integration
def test_overlay7_reads_direct_setting_and_stores_derived_tuple() -> None:
    overlay = required_overlay("overlay_0007")

    assert word_at(overlay, 0x0223265C) == 0xE59F4248  # shared config literal
    assert word_at(overlay, 0x02232664) == 0xE5D45096  # ldrb r5,[r4,#0x96]
    assert word_at(overlay, 0x02232670) == 0xE3550000  # cmp r5,#0
    assert word_at(overlay, 0x02232674) == 0x13550001  # cmpne r5,#1
    assert word_at(overlay, 0x0223267C) == 0x13550002  # cmpne r5,#2
    assert word_at(overlay, 0x02232808) == 0xE1C010B0  # strh first
    assert word_at(overlay, 0x02232810) == 0xE1C010B2  # strh second
    assert word_at(overlay, 0x02232818) == 0xE1C010B4  # strh third
    assert word_at(overlay, 0x022328AC) == 0x020D433C


@pytest.mark.integration
def test_runtime_controls_use_same_direct_consumer_and_different_output() -> None:
    required_overlay("overlay_0007")
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    controls = payload["runtime_controls"]

    assert [control["difficulty_after_read"] for control in controls] == [0, 1]
    assert {control["difficulty_read_pc"] for control in controls} == {
        "0x02232664"
    }
    assert {control["output_store_boundary"] for control in controls} == {
        "0x0223281C"
    }
    assert controls[0]["ai_output_first_three_halfwords"][:2] == (
        controls[1]["ai_output_first_three_halfwords"][:2]
    )
    assert controls[0]["ai_output_first_three_halfwords"][2] != (
        controls[1]["ai_output_first_three_halfwords"][2]
    )
