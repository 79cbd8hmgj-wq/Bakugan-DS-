from __future__ import annotations

from pathlib import Path

from bakugan_ds.gates.authoring import load_gate_roster_authoring_document
from bakugan_ds.gates.balance import BattleWeightPressure, analyze_gate_balance
from bakugan_ds.gates.record import (
    GateArchetype,
    GateConditionId,
    GateEffectId,
    GateTargetMode,
)
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
RISK_IDS = frozenset(range(82, 96))
CHAOS_IDS = frozenset(range(96, 104))


def _trigger_context(
    record_card_id: int,
    condition_id: int,
    target_mode: int,
) -> GateCalculationContext:
    owner_score = 1
    opposing_score = 1
    landing_result: int | None = None
    if condition_id == GateConditionId.OWNER_BEHIND:
        owner_score, opposing_score = 0, 1
    elif condition_id == GateConditionId.OWNER_AHEAD:
        owner_score, opposing_score = 2, 1
    elif condition_id == GateConditionId.OWNER_SCORE_ZERO:
        owner_score, opposing_score = 0, 1
    elif condition_id == GateConditionId.OWNER_AT_MATCH_POINT:
        owner_score, opposing_score = 2, 1
    elif condition_id == GateConditionId.OPPONENT_AT_MATCH_POINT:
        owner_score, opposing_score = 1, 2
    elif condition_id == GateConditionId.LANDING_GATE_CARD_WON:
        landing_result = 1

    current_participant = 1
    if target_mode == GateTargetMode.GATE_NON_OWNER:
        current_participant = 0
    return GateCalculationContext(
        compressed_core_g=400,
        attribute_id=0,
        current_participant=current_participant,
        owner_participant=1,
        owner_side_score=owner_score,
        opposing_side_score=opposing_score,
        gate_id=record_card_id,
        landing_result=landing_result,
    )


def test_risk_and_chaos_batches_are_reviewed_with_real_drawbacks() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)
    by_id = {record.card_id: record for record in records}
    metadata_by_id = {entry.card_id: entry for entry in metadata}

    assert all(record.archetype != GateArchetype.LEGACY for record in records)

    for card_id in RISK_IDS:
        record = by_id[card_id]
        entry = metadata_by_id[card_id]
        report = analyze_gate_balance(record)
        assert GateArchetype(record.archetype) is GateArchetype.RISK
        assert entry.archetype is GateArchetype.RISK
        assert entry.review_status is ReviewStatus.REVIEWED
        assert entry.net_budget == report.budget.net_budget
        assert report.budget.gross_budget >= 110
        assert report.budget.drawback_credit > 0
        assert record.drawback_id == GateEffectId.SUBTRACT_MAGNITUDE_G
        assert record.drawback_value >= 25
        assert record.effect_id == GateEffectId.ADD_SIGNED_G
        assert record.effect_value > 0
        assert record_fallback_reason(record) is FallbackReason.NONE

    for card_id in CHAOS_IDS:
        record = by_id[card_id]
        entry = metadata_by_id[card_id]
        report = analyze_gate_balance(record)
        assert GateArchetype(record.archetype) is GateArchetype.CHAOS
        assert entry.archetype is GateArchetype.CHAOS
        assert entry.review_status is ReviewStatus.REVIEWED
        assert entry.net_budget == report.budget.net_budget
        assert report.budget.drawback_credit > 0
        assert report.battle_weights.pressure in {
            BattleWeightPressure.STRONG,
            BattleWeightPressure.EXTREME_BOUNDED,
        }
        assert record.drawback_id == GateEffectId.SUBTRACT_MAGNITUDE_G
        assert record.drawback_value >= 25
        assert record.effect_id == GateEffectId.ADD_SIGNED_G
        assert record.effect_value > 0
        assert record_fallback_reason(record) is FallbackReason.NONE

    assert {by_id[card_id].preferred_type for card_id in RISK_IDS} == set(range(6))
    assert {by_id[card_id].preferred_type for card_id in CHAOS_IDS} == set(range(6))


def test_every_risk_and_chaos_trigger_applies_both_upside_and_drawback() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    by_id = {record.card_id: record for record in records}

    for card_id in RISK_IDS | CHAOS_IDS:
        record = by_id[card_id]
        result = calculate_gate_bonus(
            record,
            _trigger_context(card_id, record.condition_id, record.target_mode),
        )
        modifiers = result.trace.modifier_trace

        assert result.fallback_scope is FallbackScope.NONE
        assert result.fallback_reason is FallbackReason.NONE
        assert modifiers is not None
        assert modifiers.condition_result is True
        assert modifiers.target_result is True
        assert modifiers.primary_delta > 0
        assert modifiers.drawback_delta < 0
        assert abs(modifiers.drawback_delta) >= 25


def test_complete_roster_is_unique_and_inside_distribution_bands() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)

    report = build_roster_analysis(records, metadata)
    validate_hard_duplicate_classes(report)

    assert report["valid_for_draft"] is True
    assert report["live_card_ids"] == list(range(1, 104))
    assert report["legacy_passthrough_count"] == 0
    assert report["legacy_duplicate_groups"] == []
    assert report["hard_duplicate_groups"] == []
    assert report["identical_evaluation_groups"] == []
    assert report["identity_conflicts"] == []
    assert report["archetype_distribution"] == {
        "attribute": 22,
        "chaos": 8,
        "comeback": 14,
        "control": 15,
        "power": 15,
        "risk": 14,
        "skill": 15,
    }
    assert report["archetype_distribution_warnings"] == []
