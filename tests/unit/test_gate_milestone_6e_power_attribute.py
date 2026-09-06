from __future__ import annotations

from pathlib import Path

from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    load_gate_roster_authoring_document,
)
from bakugan_ds.gates.balance import analyze_gate_balance
from bakugan_ds.gates.record import GateArchetype
from bakugan_ds.gates.roster_analysis import (
    build_roster_analysis,
    validate_hard_duplicate_classes,
)
from bakugan_ds.gates.roster_metadata import (
    DesignTier,
    ReviewStatus,
    load_gate_roster_metadata,
)
from bakugan_ds.gates.system2 import FallbackReason, record_fallback_reason

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
POWER_IDS = frozenset(range(1, 16))
ATTRIBUTE_IDS = frozenset(range(40, 62))
CONVERTED_IDS = POWER_IDS | ATTRIBUTE_IDS


def test_power_and_attribute_batches_are_reviewed_and_juggernoid_is_frozen() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)
    by_id = {record.card_id: record for record in records}
    metadata_by_id = {entry.card_id: entry for entry in metadata}

    assert by_id[19] == approved_juggernoid_record()

    for card_id in POWER_IDS:
        record = by_id[card_id]
        entry = metadata_by_id[card_id]
        report = analyze_gate_balance(record)
        assert GateArchetype(record.archetype) is GateArchetype.POWER
        assert entry.archetype is GateArchetype.POWER
        assert entry.net_budget == report.budget.net_budget
        assert entry.design_tier is not DesignTier.UNASSIGNED
        assert entry.review_status in {ReviewStatus.REVIEWED, ReviewStatus.APPROVED}
        assert report.attribute.positive_count <= 2
        assert record_fallback_reason(record) is FallbackReason.NONE

    for card_id in ATTRIBUTE_IDS:
        record = by_id[card_id]
        entry = metadata_by_id[card_id]
        report = analyze_gate_balance(record)
        assert GateArchetype(record.archetype) is GateArchetype.ATTRIBUTE
        assert entry.archetype is GateArchetype.ATTRIBUTE
        assert entry.net_budget == report.budget.net_budget
        assert entry.design_tier is not DesignTier.UNASSIGNED
        assert entry.review_status in {ReviewStatus.REVIEWED, ReviewStatus.APPROVED}
        assert report.attribute.maximum >= 40
        assert report.attribute.minimum <= -20
        assert report.attribute.spread >= 60
        assert record_fallback_reason(record) is FallbackReason.NONE


def test_power_and_attribute_batches_are_distinct_bounded_and_cover_battle_types() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)
    by_id = {record.card_id: record for record in records}

    report = build_roster_analysis(records, metadata)
    validate_hard_duplicate_classes(report)

    assert report["valid_for_draft"] is True
    assert set(CONVERTED_IDS) <= set(report["live_card_ids"])
    assert report["identity_conflicts"] == []
    assert report["hard_duplicate_groups"] == []
    assert report["identical_evaluation_groups"] == []
    assert {by_id[card_id].preferred_type for card_id in POWER_IDS} == set(range(6))
    assert {by_id[card_id].preferred_type for card_id in ATTRIBUTE_IDS} == set(range(6))

    card_reports = {
        card["card_id"]: card
        for card in report["cards"]
        if isinstance(card, dict) and isinstance(card.get("card_id"), int)
    }
    assert all(card_reports[card_id]["out_of_tier"] is False for card_id in CONVERTED_IDS)
