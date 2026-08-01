from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _clean(value: str | None) -> str:
    return " ".join((value or "").replace("\n", " ").split())


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def import_reference_catalog(
    *,
    bakugan_csv: Path,
    gate_csv: Path,
    ability_csv: Path,
    output: Path,
) -> dict[str, Any]:
    bakugan: list[dict[str, Any]] = []
    for row in _read_csv(bakugan_csv):
        power_key = next((key for key in row if key and "Min/Max" in key), None)
        if power_key is None:
            raise ValueError("Bakugan CSV is missing the Min/Max G-Power column")
        minimum, maximum = (int(value.strip()) for value in row[power_key].split("/"))
        bakugan.append(
            {
                "name": _clean(row.get("Bakugan")),
                "attributes": _clean(row.get("Attributes")),
                "min_g": minimum,
                "max_g": maximum,
                "speed": int(row["Speed"]),
                "defense": int(row["Defense"]),
                "control": int(row["Control"]),
                "steering": int(row["Steering"]),
                "magnet": int(row["Magnet"]),
            }
        )

    gates: list[dict[str, Any]] = []
    for row in _read_csv(gate_csv):
        battle_key = next((key for key in row if key and "Battle" in key), None)
        if battle_key is None:
            raise ValueError("Gate CSV is missing the Battle Type column")
        gates.append(
            {
                "name": _clean(row.get("Name")),
                "type": _clean(row.get("Type")),
                "battle_type": _clean(row.get(battle_key)),
                "bonuses": [
                    int(row[key])
                    for key in ("Pyrus", "Aquos", "Subterra", "Haos", "Darkus", "Ventus")
                ],
                "effect": _clean(row.get("Effect")),
            }
        )

    abilities = [
        {
            "name": _clean(row.get("Name")),
            "type": _clean(row.get("Type")),
            "effect": _clean(row.get("Effect")),
        }
        for row in _read_csv(ability_csv)
    ]
    catalog = {"bakugan": bakugan, "gate_cards": gates, "ability_cards": abilities}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    return catalog


def load_reference_catalog(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("reference catalog must be an object")
    for key in ("bakugan", "gate_cards", "ability_cards"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"reference catalog field {key!r} must be a list")
    return payload
