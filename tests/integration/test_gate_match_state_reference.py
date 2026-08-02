from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

OVERLAY7_BASE = 0x02219440


def required_path(name: str) -> Path:
    value = os.environ.get(name)
    if value is None:
        pytest.skip(f"set {name} to run Gate match-state integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"{name} does not point to a file: {path}")
    return path


def digest_region(data: bytes, start: int, end: int) -> str:
    assert OVERLAY7_BASE <= start < end <= OVERLAY7_BASE + len(data)
    return hashlib.sha256(
        data[start - OVERLAY7_BASE : end - OVERLAY7_BASE]
    ).hexdigest()


@pytest.mark.integration
def test_exact_match_score_capture_threshold_and_lifecycle_regions() -> None:
    overlay7 = required_path("BAKUGAN_DS_OVERLAY7").read_bytes()

    assert hashlib.sha256(overlay7).hexdigest() == (
        "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"
    )
    expected_regions = {
        (0x022423F0, 0x02242498): (
            "15e3428b8e7a68ef6c45dfbf4a4dfddd1ce28d865f861f6f59cf1928aaaf9200"
        ),
        (0x02262D38, 0x02262D78): (
            "71fdc699705f2f4ddaf66cb1add26b82e020e54eee2ca2f0f9a8906d20be1f6b"
        ),
        (0x02263150, 0x022631B8): (
            "a2944e3e3fdab1afc64676a2bee8089c10146253a704c04168d65aa19a087096"
        ),
        (0x022696B4, 0x02269724): (
            "f89817e97e58b10ec17bb677405f80c3997cf3f2e210991e946d7d28da44143a"
        ),
        (0x02269C28, 0x02269C58): (
            "af0a2582a1df6449ade79f53e56601a13f820960981599ef6c2504259ea288d9"
        ),
        (0x02269C5C, 0x02269C94): (
            "55cf368cdd94faaac1593e966b940a1694f0fdb840c42f25846e4f5e092847cf"
        ),
    }
    for (start, end), expected in expected_regions.items():
        assert digest_region(overlay7, start, end) == expected
