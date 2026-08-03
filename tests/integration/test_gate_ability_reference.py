from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

ARTIFACT = Path("analysis/gates/ability-card-state.json")
OVERLAY_BASE = 0x02219440
OVERLAY_SHA256 = "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"


def test_exact_ability_state_and_timing_regions() -> None:
    overlay_path = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if overlay_path is None:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run Gate Ability integration tests")

    overlay = Path(overlay_path).read_bytes()
    assert hashlib.sha256(overlay).hexdigest() == OVERLAY_SHA256
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    for region in payload["exact_regions"]:
        assert region["component"] == "overlay_0007"
        start = int(region["start"])
        end = int(region["end"])
        assert start < end
        chunk = overlay[start - OVERLAY_BASE : end - OVERLAY_BASE]
        assert hashlib.sha256(chunk).hexdigest() == region["sha256"]


def test_ability_direct_calls_are_guarded_by_exact_instructions() -> None:
    overlay_path = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if overlay_path is None:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run Gate Ability integration tests")

    overlay = Path(overlay_path).read_bytes()
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    for addresses in payload["direct_calls"].values():
        for address in addresses:
            offset = int(address) - OVERLAY_BASE
            assert 0 <= offset <= len(overlay) - 4
            assert overlay[offset : offset + 4] != b"\0\0\0\0"
