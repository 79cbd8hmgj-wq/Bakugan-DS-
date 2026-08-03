from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

OVERLAY7_BASE = 0x02219440
ARM9_BASE = 0x02000000


def required_path(name: str) -> Path:
    value = os.environ.get(name)
    if value is None:
        pytest.skip(f"set {name} to run Gate lifecycle integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"{name} does not point to a file: {path}")
    return path


def digest_region(data: bytes, base: int, start: int, end: int) -> str:
    assert base <= start < end <= base + len(data)
    return hashlib.sha256(data[start - base : end - base]).hexdigest()


def direct_bl_calls(data: bytes, base: int, target: int) -> tuple[int, ...]:
    calls: list[int] = []
    for offset in range(0, len(data) - 3, 4):
        word = int.from_bytes(data[offset : offset + 4], "little")
        if word & 0x0F000000 != 0x0B000000:
            continue
        displacement = (word & 0x00FFFFFF) << 2
        if displacement & 0x02000000:
            displacement -= 0x04000000
        address = base + offset
        destination = (address + 8 + displacement) & 0xFFFFFFFF
        if destination == target:
            calls.append(address)
    return tuple(calls)


@pytest.mark.integration
def test_exact_gate_lifecycle_regions_and_call_inventories() -> None:
    overlay7 = required_path("BAKUGAN_DS_OVERLAY7").read_bytes()
    arm9 = required_path("BAKUGAN_DS_RUNTIME_ARM9").read_bytes()

    assert hashlib.sha256(overlay7).hexdigest() == (
        "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"
    )
    assert hashlib.sha256(arm9).hexdigest() == (
        "7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e"
    )

    arm9_regions = {
        (0x02065BF4, 0x02065C0C): (
            "6537181b7873d7486e58993e3137a0129a2a515e13795dce3b1e481d51058945"
        ),
    }
    overlay_regions = {
        (0x0223CFE8, 0x0223D3F4): (
            "be136c387ed66b4b2351c464bb49518446092e1b50013dd35137bb40b2546935"
        ),
        (0x022423F0, 0x022424DC): (
            "166b5c882d31a6d9a5c60df8a0f77ea28817d72fce9eabc16585ac6f4f780467"
        ),
        (0x0225FD5C, 0x0225FF18): (
            "490bc7e93bc1c69408b29ee55eacaf200fd9d731138de9e0e071394e314c3143"
        ),
        (0x02262638, 0x02262768): (
            "70a0d60c025b5397a2a218aca6b86819c1c105f11b675766d97436621de7a8c8"
        ),
        (0x02262768, 0x022628E0): (
            "68450c107ac3c8e0425b66dc9cc275569ff35f14305018a47774d41f3761462d"
        ),
        (0x022696B4, 0x02269BC8): (
            "ecd781540b86064b3c0f1335c991380d0eca817efead34fd606557ce43c869ab"
        ),
        (0x02269C28, 0x02269C94): (
            "d79198da01f9bd6e15be8b06dd772814f870dfac32537e982244757ff6b12555"
        ),
        (0x0226A404, 0x0226A6F8): (
            "2061d140858bf8d5b4bf057fe54b5e5eb33294bfefd89595ec7223bbda6a15d7"
        ),
    }
    for (start, end), expected in arm9_regions.items():
        assert digest_region(arm9, ARM9_BASE, start, end) == expected
    for (start, end), expected in overlay_regions.items():
        assert digest_region(overlay7, OVERLAY7_BASE, start, end) == expected

    expected_calls = {
        0x0226A404: (
            0x02262690,
            0x022626DC,
            0x02262740,
            0x02262760,
            0x02262B8C,
            0x02262B9C,
        ),
        0x0223CFE8: (0x0223E334,),
        0x02262638: (
            0x02238CA8,
            0x0224A868,
            0x0224A888,
            0x0224A904,
            0x0224A9E8,
            0x0224AA0C,
            0x02262BE4,
            0x02262C00,
            0x02262C58,
            0x02262C74,
            0x02262D24,
            0x02262DF0,
            0x02262EE0,
            0x02262FE4,
            0x02263054,
        ),
        0x022626B8: (
            0x022371A0,
            0x022424B0,
            0x02260ED0,
            0x022612AC,
            0x022613F0,
        ),
        0x02262714: (0x022656D0,),
        0x02262768: (
            0x022588A8,
            0x0225A004,
            0x0225A074,
            0x0225A600,
            0x0225A6B8,
            0x0225A774,
            0x0225A830,
            0x02262E10,
            0x02262F00,
            0x02262F24,
            0x02263074,
            0x02263098,
            0x02265DD4,
        ),
        0x02262828: (
            0x0223713C,
            0x022424C4,
            0x022424D8,
            0x02254A6C,
            0x02259058,
            0x02259E38,
            0x0225A194,
            0x02260E34,
            0x02260E60,
            0x02260F04,
            0x02260F1C,
            0x022612BC,
            0x022612CC,
            0x02261484,
            0x02261494,
            0x02265DA4,
        ),
    }
    for target, expected in expected_calls.items():
        assert direct_bl_calls(overlay7, OVERLAY7_BASE, target) == expected

    assert len(direct_bl_calls(overlay7, OVERLAY7_BASE, 0x02065BF4)) == 18
