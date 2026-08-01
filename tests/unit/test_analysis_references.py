import csv
import json
from pathlib import Path

import pytest

from bakugan_ds.analysis.references import import_reference_catalog, load_reference_catalog


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def test_import_reference_catalog_cleans_cells(tmp_path: Path) -> None:
    bakugan = tmp_path / "bakugan.csv"
    gate = tmp_path / "gate.csv"
    ability = tmp_path / "ability.csv"
    output = tmp_path / "reference.json"
    write_csv(
        bakugan,
        [
            [
                "Bakugan",
                "Attributes",
                "Min/Max G-\nPower",
                "Speed",
                "Defense",
                "Control",
                "Steering",
                "Magnet",
            ],
            ["Serpenoid", "All", "190 / 440", "2", "1", "1", "1", "1"],
        ],
    )
    write_csv(
        gate,
        [
            [
                "Name",
                "Type",
                "Battle\nType",
                "Pyrus",
                "Aquos",
                "Subterra",
                "Haos",
                "Darkus",
                "Ventus",
                "Effect",
            ],
            [
                "Serpenoid",
                "Gold",
                "Scratch\nBattle",
                "180",
                "60",
                "90",
                "140",
                "130",
                "50",
                "bonus\ntwice",
            ],
        ],
    )
    write_csv(
        ability,
        [["Name", "Type", "Effect"], ["Twin Swap", "Red", "Swap\nG-Power"]],
    )

    catalog = import_reference_catalog(
        bakugan_csv=bakugan,
        gate_csv=gate,
        ability_csv=ability,
        output=output,
    )

    assert catalog["bakugan"][0]["min_g"] == 190
    assert catalog["gate_cards"][0]["battle_type"] == "Scratch Battle"
    assert catalog["gate_cards"][0]["bonuses"] == [180, 60, 90, 140, 130, 50]
    assert catalog["ability_cards"][0]["effect"] == "Swap G-Power"
    assert load_reference_catalog(output) == json.loads(output.read_text())


def test_load_reference_rejects_missing_lists(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"gate_cards": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="bakugan"):
        load_reference_catalog(path)
