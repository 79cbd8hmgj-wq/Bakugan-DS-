import csv
import json
from pathlib import Path


def test_overlay_import_manifest_has_verified_layout() -> None:
    payload = json.loads(Path("analysis/imports/overlay_0007.json").read_text())
    assert payload["load_address"] == 0x02219440
    assert payload["size"] == 467360
    assert payload["executable_end"] == 0x0228B5E0
    assert payload["bss_start"] == 0x0228B5E0
    assert payload["bss_end"] == 0x0228BC20


def test_symbol_csv_has_three_unique_gp_candidates() -> None:
    with Path("analysis/symbols/overlay_0007.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert [row["address"] for row in rows] == [
        "0x022665EC",
        "0x02266868",
        "0x02266A28",
    ]
    assert all(row["confidence"] == "candidate" for row in rows)


def test_ghidra_script_records_verified_layout() -> None:
    text = Path("tools/ghidra/ApplyBakuganSymbols.py").read_text(encoding="utf-8")
    assert "OVERLAY_BASE = 0x02219440" in text
    assert "BSS_START = 0x0228B5E0" in text
    assert "BSS_SIZE = 1600" in text
