from __future__ import annotations

import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.roster_identity import (
    GateRosterIdentityEntry,
    load_gate_roster_identity_map,
    parse_gate_roster_identity_map,
    write_gate_roster_identity_map,
)
from bakugan_ds.gates.roster_metadata import (
    MappingConfidence,
    load_gate_roster_metadata,
)

IDENTITY_MAP = Path("analysis/gates/milestone-6e-id-name-map.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
CARD_ID_EVIDENCE = Path("analysis/gates/card-id-evidence.json")


def test_identity_map_covers_all_103_ids_without_guide_order_inference() -> None:
    identity_map = load_gate_roster_identity_map(IDENTITY_MAP)

    assert identity_map.complete_name_table_committed is False
    assert identity_map.guide_order_used_for_ids is False
    assert identity_map.source_evidence == "analysis/gates/card-id-evidence.json"
    assert [entry.card_id for entry in identity_map.entries] == list(range(1, 104))
    assert len({entry.name.casefold() for entry in identity_map.entries}) == 103

    confirmed = [
        entry
        for entry in identity_map.entries
        if entry.mapping_confidence is MappingConfidence.CONFIRMED
    ]
    unresolved = [
        entry
        for entry in identity_map.entries
        if entry.mapping_confidence is MappingConfidence.UNRESOLVED
    ]
    assert confirmed == [
        GateRosterIdentityEntry(
            card_id=19,
            name="Juggernoid",
            mapping_confidence=MappingConfidence.CONFIRMED,
            evidence_reference="gate-id-019",
        ),
        GateRosterIdentityEntry(
            card_id=20,
            name="Robotallion",
            mapping_confidence=MappingConfidence.CONFIRMED,
            evidence_reference="gate-id-020",
        ),
        GateRosterIdentityEntry(
            card_id=22,
            name="Serpenoid",
            mapping_confidence=MappingConfidence.CONFIRMED,
            evidence_reference="gate-id-022",
        ),
    ]
    assert len(unresolved) == 100
    assert all("provisional" in entry.name.casefold() for entry in unresolved)


def test_identity_map_matches_metadata_and_confirmed_repository_evidence() -> None:
    identity_map = load_gate_roster_identity_map(IDENTITY_MAP)
    metadata = load_gate_roster_metadata(METADATA)
    evidence = json.loads(CARD_ID_EVIDENCE.read_text(encoding="utf-8"))

    assert [
        (
            entry.card_id,
            entry.name,
            entry.mapping_confidence,
            entry.evidence_reference,
        )
        for entry in identity_map.entries
    ] == [
        (
            entry.card_id,
            entry.name,
            entry.mapping_confidence,
            entry.evidence_reference,
        )
        for entry in metadata
    ]
    confirmed_entries = [
        entry.to_json()
        for entry in identity_map.entries
        if entry.mapping_confidence is MappingConfidence.CONFIRMED
    ]
    assert confirmed_entries == [
        {
            "card_id": item["card_id"],
            "evidence_reference": item["evidence_id"],
            "mapping_confidence": item["confidence"],
            "name": item["label"],
        }
        for item in evidence["mappings"]
    ]


def test_identity_map_parser_rejects_inference_duplicate_ids_and_unmarked_unknowns() -> None:
    payload = json.loads(IDENTITY_MAP.read_text(encoding="utf-8"))

    payload["guide_order_used_for_ids"] = True
    with pytest.raises(WorkspaceError, match="guide order"):
        parse_gate_roster_identity_map(payload)

    payload = json.loads(IDENTITY_MAP.read_text(encoding="utf-8"))
    payload["entries"][1]["card_id"] = 1
    with pytest.raises(WorkspaceError, match="duplicate Gate identity card ID"):
        parse_gate_roster_identity_map(payload)

    payload = json.loads(IDENTITY_MAP.read_text(encoding="utf-8"))
    payload["entries"][0]["name"] = "Unknown Gate"
    with pytest.raises(WorkspaceError, match="explicitly marked provisional"):
        parse_gate_roster_identity_map(payload)


def test_identity_map_writer_is_deterministic(tmp_path: Path) -> None:
    identity_map = load_gate_roster_identity_map(IDENTITY_MAP)
    output = tmp_path / "identity-map.json"

    write_gate_roster_identity_map(output, identity_map)
    first = output.read_bytes()
    write_gate_roster_identity_map(output, identity_map)

    assert output.read_bytes() == first
    assert first.endswith(b"\n")
    assert load_gate_roster_identity_map(output) == identity_map
