from __future__ import annotations

from pathlib import Path

from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    load_gate_roster_authoring_document,
)
from bakugan_ds.gates.balance import analyze_gate_balance
from bakugan_ds.gates.record import GateArchetype, GateConditionId, GateTargetMode
from bakugan_ds.gates.roster_analysis import (
    build_roster_analysis,
    validate_hard_duplicate_classes,
)
from bakugan_ds.gates.roster_metadata import ReviewStatus, load_gate_roster_metadata
from bakugan_ds.gates.system2 import (
    FallbackReason,
    FallbackScope,
    GateCalculationContext,
    calculate_gate_bonus,
    record_fallback_reason,
)

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
COMEBACK_IDS = frozenset(range(69, 82))
ALL_COMEBACK_IDS = COMEBACK_IDS | {19}


def _context(
    card_id: int,
    *,
    owner_score: int,
    opposing_score: int,
) -> GateCalculationContext:
    return GateCalculationContext(
        compressed_core_g=400,
        attribute_id=0,
        current_participant=1,
        owner_participant=1,
        owner_side_score=owner_score,
        opposing_side_score=opposing_score,
        gate_id=card_id,
        landing_result=None,
    )


def test_comeback_batch_is_reviewed_bounded_and_preserves_juggernoid() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)
    by_id = {record.card_id: record for record in records}
    metadata_by_id = {entry.card_id: entry for entry in metadata}

    assert by_id[19] == approved_juggernoid_record()
    assert {
        record.card_id
        for record in records
        if GateArchetype(record.archetype) is GateArchetype.COMEBACK
    } == ALL_COMEBACK_IDS

    conditions: set[int] = set()
    for card_id in COMEBACK_IDS:
        record = by_id[card_id]
        entry = metadata_by_id[card_id]
        report = analyze_gate_balance(record)
        conditions.add(record.condition_id)

        assert GateArchetype(record.archetype) is GateArchetype.COMEBACK
        assert entry.archetype is GateArchetype.COMEBACK
        assert entry.review_status is ReviewStatus.REVIEWED
        assert entry.net_budget == report.budget.net_budget
        assert record.condition_id in {
            GateConditionId.OWNER_BEHIND,
            GateConditionId.OWNER_SCORE_ZERO,
        }
        assert record.target_mode == GateTargetMode.GATE_OWNER
        assert record.effect_value > 0
        assert record_fallback_reason(record) is FallbackReason.NONE

    assert conditions == {
        GateConditionId.OWNER_BEHIND,
        GateConditionId.OWNER_SCORE_ZERO,
    }
    assert {by_id[card_id].preferred_type for card_id in COMEBACK_IDS} == set(range(6))


def test_comeback_rider_only_improves_the_supported_trigger_branch() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    by_id = {record.card_id: record for record in records}

    for card_id in COMEBACK_IDS:
        record = by_id[card_id]
        trigger_scores = (
            (0, 1)
            if record.condition_id == GateConditionId.OWNER_BEHIND
            else (0, 0)
        )
        triggered = calculate_gate_bonus(
            record,
            _context(
                card_id,
                owner_score=trigger_scores[0],
                opposing_score=trigger_scores[1],
            ),
        )
        neutral = calculate_gate_bonus(
            record,
            _context(card_id, owner_score=1, opposing_score=1),
        )
        leading = calculate_gate_bonus(
            record,
            _context(card_id, owner_score=2, opposing_score=1),
        )

        assert triggered.fallback_scope is FallbackScope.NONE
        assert neutral.fallback_scope is FallbackScope.NONE
        assert leading.fallback_scope is FallbackScope.NONE
        assert triggered.fallback_reason is FallbackReason.NONE
        assert triggered.trace.condition_result is True
        assert neutral.trace.condition_result is False
        assert leading.trace.condition_result is False
        assert triggered.effective_gate_bonus is not None
        assert neutral.effective_gate_bonus is not None
        assert leading.effective_gate_bonus is not None
        assert neutral.effective_gate_bonus > 0
        assert leading.effective_gate_bonus > 0
        assert triggered.effective_gate_bonus > neutral.effective_gate_bonus
        assert neutral.effective_gate_bonus == leading.effective_gate_bonus


def test_comeback_batch_is_unique_against_the_complete_live_roster() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)

    report = build_roster_analysis(records, metadata)
    validate_hard_duplicate_classes(report)

    assert report["valid_for_draft"] is True
    assert set(report["live_card_ids"]) >= ALL_COMEBACK_IDS
    assert report["hard_duplicate_groups"] == []
    assert report["identical_evaluation_groups"] == []
    assert report["identity_conflicts"] == []
    assert report["archetype_distribution"]["comeback"] == 14
