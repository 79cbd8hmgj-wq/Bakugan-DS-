from pathlib import Path
import struct

from bakugan_ds.analysis.model import Component
from bakugan_ds.analysis.report import analyze_components


def test_report_aggregates_gp_evidence_by_function() -> None:
    base = 0x02219440
    data = bytearray(0x100)
    struct.pack_into("<I", data, 0x00, 0xE92D4010)
    data[0x80:0x8B] = b"gp_pickup2\x00"
    data[0x90:0x98] = b"gp_down\x00"
    struct.pack_into("<I", data, 0x20, base + 0x80)
    struct.pack_into("<I", data, 0x24, base + 0x90)
    component = Component("overlay_0007", Path("overlay_007.bin"), base, bytes(data))
    catalog = {
        "bakugan": [],
        "ability_cards": [],
        "gate_cards": [{"name": "Gate", "bonuses": [80, 160, 70, 100, 70, 40]}],
    }

    report = analyze_components((component,), catalog)

    assert len(report["symbol_candidates"]) == 1
    candidate = report["symbol_candidates"][0]
    assert candidate["address"] == base
    assert "gp_pickup2" in candidate["evidence"]
    assert "gp_down" in candidate["evidence"]
    assert report["components"][0]["file_name"] == "overlay_007.bin"
    assert "path" not in report["components"][0]
