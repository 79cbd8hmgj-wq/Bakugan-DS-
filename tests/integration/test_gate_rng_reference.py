from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

ARM9_BASE = 0x02000000
OVERLAY7_BASE = 0x02219440


def required_path(name: str) -> Path:
    value = os.environ.get(name)
    if value is None:
        pytest.skip(f"set {name} to run Gate RNG integration tests")
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
def test_exact_weighted_rng_and_selector_precedence_regions() -> None:
    arm9 = required_path("BAKUGAN_DS_RUNTIME_ARM9").read_bytes()
    overlay7 = required_path("BAKUGAN_DS_OVERLAY7").read_bytes()

    assert hashlib.sha256(arm9).hexdigest() == (
        "7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e"
    )
    assert hashlib.sha256(overlay7).hexdigest() == (
        "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"
    )

    arm9_regions = {
        (0x02021A30, 0x02021AF8): (
            "44562a42147ade041be4cc565a65e8cff38a6b21b6f9cb60001a6ea370a9a009"
        ),
        (0x020219DC, 0x02021A30): (
            "f2594a13d55f98488687ee8501422c0a4c5a7cd085abe424b867c22672f6ffb1"
        ),
    }
    overlay_regions = {
        (0x022306B8, 0x02230720): (
            "ddd80b4d62d62c7c59b5eb8d8d40ec7ac9c76059866a5b57889de285d9a9421e"
        ),
        (0x022433AC, 0x022433C8): (
            "a2ca7b7b527814153df7c077fe02fa3b0617a7c51c808def3c3c6fccc5247e3c"
        ),
        (0x0223E338, 0x0223E358): (
            "b1fb46f46149a2cca760289f5d8cdb1d653010736dc2d861ee56e5ab68cfd56e"
        ),
        (0x022417A8, 0x02241840): (
            "cb0e50a7e140fd1a7804cdbf40a49a46f8bb690b56a082561fd836f4f892e83f"
        ),
        (0x0224183C, 0x0224193C): (
            "beb63fdf101a88f72f60e91ffe9f3e39cfbe4e99c4eaefdde690a84149ca7a51"
        ),
    }
    for (start, end), expected in arm9_regions.items():
        assert digest_region(arm9, ARM9_BASE, start, end) == expected
    for (start, end), expected in overlay_regions.items():
        assert digest_region(overlay7, OVERLAY7_BASE, start, end) == expected

    assert direct_bl_calls(overlay7, OVERLAY7_BASE, 0x02021A30) == (
        0x022306D4,
    )


def test_future_history_cache_geometry_is_nonoverlapping() -> None:
    cache_start = 0x02293C20
    activation_start = cache_start + 0x2C
    activation_end = cache_start + 0x38
    history_start = cache_start + 0x38
    history_end = cache_start + 0x3C
    reserved_end = cache_start + 0x40

    assert activation_start < activation_end
    assert activation_end == history_start
    assert history_end <= reserved_end
    assert reserved_end == 0x02293C60
