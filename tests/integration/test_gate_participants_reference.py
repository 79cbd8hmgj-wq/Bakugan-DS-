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
        pytest.skip(f"set {name} to run Gate participant integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"{name} does not point to a file: {path}")
    return path


def digest_region(data: bytes, base: int, start: int, end: int) -> str:
    assert base <= start < end <= base + len(data)
    return hashlib.sha256(data[start - base : end - base]).hexdigest()


@pytest.mark.integration
def test_exact_human_ai_and_result_targeting_regions() -> None:
    arm9 = required_path("BAKUGAN_DS_RUNTIME_ARM9").read_bytes()
    overlay7 = required_path("BAKUGAN_DS_OVERLAY7").read_bytes()

    assert hashlib.sha256(arm9).hexdigest() == (
        "7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e"
    )
    assert hashlib.sha256(overlay7).hexdigest() == (
        "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"
    )

    assert digest_region(arm9, ARM9_BASE, 0x0202F134, 0x0202F17C) == (
        "ee69568e4b002492e56a928a0d555d5f8e1fdd3e18cfd9686922e469efd78f07"
    )
    expected_overlay_regions = {
        (0x02230F58, 0x02231020): (
            "67af925fb10a4a4b9547d58b3670822a131475e420308d6213a45a7c441efcb9"
        ),
        (0x0223E238, 0x0223E340): (
            "37899124ba7100bb8bd0a2ba05aa31817d2a314e0709ee2cffe6cf806f8cda74"
        ),
        (0x02241A64, 0x02241A78): (
            "8e07a67a5a7ec93cd2da0d3268bdff3262890d29145dc479ff6e400733f5f8d5"
        ),
        (0x02242094, 0x022420C0): (
            "4a43aa1075b6c2af40b5c690905fbd20b077d8b287e5eb3e80fdde787d7d6c8e"
        ),
        (0x02244440, 0x022447C0): (
            "8dbc3c0727ab824736bc041f86297fa15cdfb8efe88e25b25736cf8d64f5a75a"
        ),
        (0x02269734, 0x02269838): (
            "1204717e82a81de6da25158104d566f92df13ce85243055bbf433a6d42fef8a9"
        ),
        (0x0226B4AC, 0x0226B4D8): (
            "1462485f96c1a4c73d58aef0bf5bfce5f3cdb2539a2acbb16b9bcc2065c19a34"
        ),
        (0x0226E430, 0x0226E478): (
            "429fd1f6cb43dc95e636805217948866488465c35bb8111de5549e55ac62226f"
        ),
    }
    for (start, end), expected in expected_overlay_regions.items():
        assert digest_region(overlay7, OVERLAY7_BASE, start, end) == expected
