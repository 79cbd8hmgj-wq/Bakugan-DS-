from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.record import GateArchetype
from bakugan_ds.gates.roster_metadata import (
    DesignTier,
    GateRosterMetadataEntry,
    MappingConfidence,
    ReviewStatus,
    RosterFamily,
    load_gate_roster_metadata,
    parse_gate_roster_metadata,
    write_gate_roster_metadata,
)

METADATA = Path("config/gates/milestone-6e-roster-metadata.json")


def _entry(card_id: int = 1) -> GateRosterMetadataEntry:
    if card_id <= 39:
        family = RosterFamily.BAKUGAN_CHARACTER
    elif card_id <= 71:
        family = RosterFamily.ENVIRONMENTAL_FIELD
    else:
        family = RosterFamily.TACTICAL_CONDITIONAL
    return GateRosterMetadataEntry(
        card_id=card_id,
        name=f"Gate {card_id:03d} (provisional)",
        mapping_confidence=MappingConfidence.UNRESOLVED,
        evidence_reference=f"unresolved-card-id-{card_id:03d}",
        family=family,
        archetype=GateArchetype.LEGACY,
        design_tier=DesignTier.UNASSIGNED,
        gameplay_identity="Pending Milestone 6E design.",
        g_influence_summary="Unassigned pending Milestone 6E authoring.",
        battle_weight_summary="Unassigned pending Milestone 6E authoring.",
        rule_summary="Unassigned pending Milestone 6E authoring.",
        net_budget=None,
        differentiation_rationale="Pending authored conversion and review.",
        review_status=ReviewStatus.PROVISIONAL,
    )


def _payload(entries: list[GateRosterMetadataEntry]) -> dict[str, object]:
    return {
        "entries": [entry.to_json() for entry in entries],
        "format_version": 1,
        "profile_id": "b6re_rev0",
    }


def test_draft_metadata_covers_all_103_gate_ids_deterministically() -> None:
    entries = load_gate_roster_metadata(METADATA)

    assert len(entries) == 103
    assert [entry.card_id for entry in entries] == list(range(1, 104))
    assert len({entry.name.casefold() for entry in entries}) == 103

    by_id = {entry.card_id: entry for entry in entries}
    assert by_id[19] == GateRosterMetadataEntry(
        card_id=19,
        name="Juggernoid",
        mapping_confidence=MappingConfidence.CONFIRMED,
        evidence_reference="gate-id-019",
        family=RosterFamily.BAKUGAN_CHARACTER,
        archetype=GateArchetype.COMEBACK,
        design_tier=DesignTier.MID,
        gameplay_identity="Comeback Gate that rewards its owner for fighting from behind.",
        g_influence_summary=(
            "Hybrid flat, compressed-core percentage, Aquos, and owner-behind G bonuses."
        ),
        battle_weight_summary="Mild Scratch preference with all six battle types reachable.",
        rule_summary="Adds 40 G to the Gate owner when its side is behind.",
        net_budget=91,
        differentiation_rationale=(
            "Frozen Milestone 6D compatibility fixture and reference Comeback Gate."
        ),
        review_status=ReviewStatus.APPROVED,
    )
    assert by_id[20].name == "Robotallion"
    assert by_id[20].mapping_confidence is MappingConfidence.CONFIRMED
    assert by_id[22].name == "Serpenoid"
    assert by_id[22].mapping_confidence is MappingConfidence.CONFIRMED

    unassigned = [entry for entry in entries if entry.archetype is GateArchetype.LEGACY]
    reviewed = [entry for entry in entries if entry.review_status is ReviewStatus.REVIEWED]
    unresolved = [
        entry for entry in entries if entry.mapping_confidence is MappingConfidence.UNRESOLVED
    ]
    assert len(unassigned) == 0
    assert len(reviewed) == 102
    assert len(unresolved) == 100
    assert all(entry.design_tier is DesignTier.UNASSIGNED for entry in unassigned)
    assert all(entry.net_budget is None for entry in unassigned)
    assert all(entry.review_status is ReviewStatus.PROVISIONAL for entry in unassigned)


def test_metadata_uses_canonical_authoring_family_ranges() -> None:
    entries = load_gate_roster_metadata(METADATA)

    assert all(entry.family is RosterFamily.BAKUGAN_CHARACTER for entry in entries[:39])
    assert all(entry.family is RosterFamily.ENVIRONMENTAL_FIELD for entry in entries[39:71])
    assert all(entry.family is RosterFamily.TACTICAL_CONDITIONAL for entry in entries[71:])


def test_metadata_parser_rejects_missing_duplicate_unsorted_or_unknown_fields() -> None:
    entries = [_entry(card_id) for card_id in range(1, 104)]

    with pytest.raises(WorkspaceError, match="exactly 103"):
        parse_gate_roster_metadata(_payload(entries[:-1]))

    duplicate = [entries[0], entries[0], *entries[2:]]
    with pytest.raises(WorkspaceError, match="duplicate Gate metadata card ID"):
        parse_gate_roster_metadata(_payload(duplicate))

    unsorted = [entries[1], entries[0], *entries[2:]]
    with pytest.raises(WorkspaceError, match="canonical ID order"):
        parse_gate_roster_metadata(_payload(unsorted))

    payload = json.loads(METADATA.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    with pytest.raises(WorkspaceError, match="document fields mismatch"):
        parse_gate_roster_metadata(payload)

    payload = json.loads(METADATA.read_text(encoding="utf-8"))
    payload["entries"][0]["unexpected"] = True
    with pytest.raises(WorkspaceError, match="entry fields mismatch"):
        parse_gate_roster_metadata(payload)


def test_metadata_rejects_invalid_family_name_archetype_and_budget() -> None:
    entry = _entry()

    with pytest.raises(WorkspaceError, match="family must be environmental_field"):
        replace(_entry(40), family=RosterFamily.BAKUGAN_CHARACTER).validate()

    with pytest.raises(WorkspaceError, match="explicitly marked provisional"):
        replace(entry, name="Unknown Gate").validate()

    with pytest.raises(WorkspaceError, match="unassigned design tier"):
        replace(entry, archetype=GateArchetype.POWER).validate()

    live = replace(
        entry,
        archetype=GateArchetype.POWER,
        design_tier=DesignTier.MID,
        net_budget=100,
        review_status=ReviewStatus.REVIEWED,
    )
    live.validate()
    with pytest.raises(WorkspaceError, match="net budget must be between"):
        replace(live, net_budget=121).validate()


def test_final_validation_rejects_legacy_unapproved_or_placeholder_designs() -> None:
    entry = _entry()
    with pytest.raises(WorkspaceError, match="cannot use legacy archetype"):
        entry.validate(final=True)

    live = replace(
        entry,
        archetype=GateArchetype.POWER,
        design_tier=DesignTier.MID,
        net_budget=100,
        review_status=ReviewStatus.REVIEWED,
    )
    with pytest.raises(WorkspaceError, match="must be approved"):
        live.validate(final=True)

    approved = replace(live, review_status=ReviewStatus.APPROVED)
    with pytest.raises(WorkspaceError, match="contains placeholder text"):
        approved.validate(final=True)


def test_metadata_writer_is_deterministic(tmp_path: Path) -> None:
    entries = load_gate_roster_metadata(METADATA)
    output = tmp_path / "metadata.json"

    write_gate_roster_metadata(output, entries)
    first = output.read_bytes()
    write_gate_roster_metadata(output, entries)

    assert output.read_bytes() == first
    assert first.endswith(b"\n")
    assert load_gate_roster_metadata(output) == entries
