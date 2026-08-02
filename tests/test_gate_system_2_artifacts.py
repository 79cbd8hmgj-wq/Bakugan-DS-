from __future__ import annotations

import csv
import json
from pathlib import Path

EVIDENCE = Path("analysis/gates/card-id-evidence.json")
SYMBOLS = Path("analysis/symbols/gate_cards.csv")
FORBIDDEN_KEYS = {"raw_bytes", "ram_dump", "save_state", "screenshot", "complete_gate_table"}


def walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_selected_gate_identity_artifacts_preserve_copyright_boundary() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["complete_name_table_committed"] is False
    assert payload["guide_order_used_for_ids"] is False
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))

    attributes = payload["attributes"]
    assert [(item["attribute_id"], item["name"]) for item in attributes] == [
        (0, "pyrus"),
        (1, "aquos"),
        (2, "subterra"),
        (3, "haos"),
        (4, "darkus"),
        (5, "ventus"),
    ]
    assert all(item["confidence"] == "confirmed" for item in attributes)

    mappings = payload["mappings"]
    assert [(item["card_id"], item["label"]) for item in mappings] == [
        (19, "Juggernoid"),
        (20, "Robotallion"),
        (22, "Serpenoid"),
    ]
    assert len(payload["selected_rows"]) == 3


def test_gate_symbol_csv_matches_selected_mappings() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    with SYMBOLS.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [(int(row["card_id"]), row["label"]) for row in rows] == [
        (item["card_id"], item["label"]) for item in payload["mappings"]
    ]
    assert all(row["confidence"] == "confirmed" for row in rows)
