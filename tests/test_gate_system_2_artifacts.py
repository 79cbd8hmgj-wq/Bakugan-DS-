from __future__ import annotations

import csv
import json
from pathlib import Path

EVIDENCE = Path("analysis/gates/card-id-evidence.json")
SYMBOLS = Path("analysis/symbols/gate_cards.csv")
LIFECYCLE = Path("analysis/gates/activation-lifecycle.json")
LIFECYCLE_DOC = Path("docs/gate-card-runtime-lifecycle.md")
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


def test_gate_lifecycle_artifact_has_battle_path_and_evidence() -> None:
    payload = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    transitions = payload["transitions"]
    assert transitions
    assert any(item["to_state"] == "battle_started" for item in transitions)
    assert all(item["evidence"].strip() for item in transitions)
    assert all(item["owner_source"].strip() for item in transitions)
    assert all(item["card_id_source"].strip() for item in transitions)
    assert payload["ai_path"]["shared"] is True
    assert payload["reuse_supported"] is False
    assert payload["complete_runtime_capture_committed"] is False
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))

    document = LIFECYCLE_DOC.read_text(encoding="utf-8")
    assert "0x0223EA60" in document
    assert "Resolved to reset" in document
    assert "Reused" in document
