from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from bakugan_ds.gates.loader import ARM9_DECODED_SHA256


def required_arm9() -> bytes:
    value = os.environ.get("BAKUGAN_DS_ARM9_DECODED")
    if value is None:
        pytest.skip("set BAKUGAN_DS_ARM9_DECODED to run NitroFS reference tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"BAKUGAN_DS_ARM9_DECODED does not point to a file: {path}")
    return path.read_bytes()


@pytest.mark.integration
def test_reference_arm9_contains_exact_confirmed_nitrofs_functions() -> None:
    arm9 = required_arm9()
    assert hashlib.sha256(arm9).hexdigest() == ARM9_DECODED_SHA256
    base = 0x02000000
    regions = {
        (0x0200A7B4, 0x0200A7DC): (
            "131f15b7db06da746cb03744ffda8f5453b1c6c2fbdf8f0dacab41326e10421f"
        ),
        (0x0200A920, 0x0200A99C): (
            "0d82a4200a16927edd1012c75b49d5ef0f99934a7fb36f289aaa0604b144e481"
        ),
        (0x0200AA24, 0x0200AA94): (
            "611e41d8d1b768da2e873e2ec320815dbd118d51589c6363ffea380ea8858f39"
        ),
        (0x0200AADC, 0x0200AB18): (
            "586363903833fc2366f21761acac6938077ebf87d71daef90d602aa27c36d686"
        ),
        (0x0200AC30, 0x0200AC40): (
            "cf5c1821cef4a3567d28cffdf6210f5cc4b71edd52af40b9eea9794becbb6956"
        ),
        (0x0200AC40, 0x0200ACAC): (
            "99e8a8db572238f5c2aa23d35ddfe505843277a0623dedfe207c2d5872236747"
        ),
    }
    for (start, end), expected in regions.items():
        region = arm9[start - base : end - base]
        assert hashlib.sha256(region).hexdigest() == expected
