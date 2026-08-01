import os
from pathlib import Path

import pytest

from bakugan_ds.analysis.model import Component
from bakugan_ds.analysis.references import load_reference_catalog
from bakugan_ds.analysis.report import analyze_components


def required_path(name: str) -> Path:
    value = os.environ.get(name)
    if value is None:
        pytest.skip(f"set {name} to run exact static-analysis integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"{name} does not point to a file: {path}")
    return path


@pytest.mark.integration
def test_exact_arm9_and_overlay7_candidates() -> None:
    arm9 = required_path("BAKUGAN_DS_ARM9")
    overlay7 = required_path("BAKUGAN_DS_OVERLAY7")
    reference = required_path("BAKUGAN_DS_REFERENCE")
    report = analyze_components(
        (
            Component("arm9", arm9, 0x02000000, arm9.read_bytes()),
            Component("overlay_0007", overlay7, 0x02219440, overlay7.read_bytes()),
        ),
        load_reference_catalog(reference),
    )

    assert report["components"][0]["sha256"] == (
        "c4ac54ee4c8cd36bd572deb78c224c5739f6847418dc7554974a7e0ce1c4dcbf"
    )
    assert report["components"][1]["sha256"] == (
        "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"
    )
    assert len(report["keyword_strings"]) == 210
    assert len(report["numeric_matches"]) == 21
    assert [row["address"] for row in report["symbol_candidates"]] == [
        0x022665EC,
        0x02266868,
        0x02266A28,
    ]
    arm9_matches = [row for row in report["numeric_matches"] if row["component"] == "arm9"]
    assert len(arm9_matches) == 19
    arm9_cluster = next(
        row for row in report["numeric_clusters"] if row["component"] == "arm9"
    )
    assert arm9_cluster["start_address"] == 0x0205EFBA
    assert arm9_cluster["end_address"] == 0x0205F173
