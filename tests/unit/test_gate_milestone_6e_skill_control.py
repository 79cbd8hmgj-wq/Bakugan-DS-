from __future__ import annotations

from pathlib import Path

from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    legacy_passthrough_record,
    load_gate_roster_authoring_document,
)
from bakugan_ds.gates.balance import BattleWeightPressure, analyze_gate_balance
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
POWER_IDS = frozenset(range(1, 16))
ATTRIBUTE_IDS = frozenset(range(40, 62))
SKILL_IDS = frozenset({16, 17, 18, *range(20, 32)})
CONTROL_IDS = frozenset({*range(32, 40), *range(62, 69)})
LIVE_IDS = POWER_IDS | ATTRIBUTE_IDS | SKILL_IDS | CONTROL_IDS | {19}


def test_skill_and_control_batches_are_reviewed_and_use_supported_semantics() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)
    by_id = {record.card_id: record for record in records}
    metadata_by_id = {entry.card_id: entry for entry in metadata}

    assert by_id[19] == approved_juggernoid_record()
    assert {record.card_id for record in records if record.archetype != 0} == LIVE_IDS

    for card_id in SKILL_IDS:
        record = by_id[card_id]
        entry = metadata_by_id[card_id]
        report = analyze_gate_balance(record)
        assert GateArchetype(record.archetype) is GateArchetype.SKILL
        assert entry.archetype is GateArchetype.SKILL
        assert entry.review_status is ReviewStatus.REVIEWED
        assert entry.net_budget == report.budget.net_budget
        assert report.battle_weights.pressure in {
            BattleWeightPressure.STRONG,
            BattleWeightPressure.EXTREME_BOUNDED,
        }
        assert record_fallback_reason(record) is FallbackReason.NONE

    for card_id in CONTROL_IDS:
        record = by_id[card_id]
        entry = metadata_by_id[card_id]
        report = analyze_gate_balance(record)
        assert GateArchetype(record.archetype) is GateArchetype.CONTROL
        assert entry.archetype is GateArchetype.CONTROL
        assert entry.review_status is ReviewStatus.REVIEWED
        assert entry.net_budget == report.budget.net_budget
        assert (
            record.condition_id != GateConditionId.NONE
            or record.target_mode != GateTargetMode.CURRENT_COMBATANT
        )
        assert record_fallback_reason(record) is FallbackReason.NONE

    for card_id in set(range(1, 104)) - LIVE_IDS:
        assert by_id[card_id] == legacy_passthrough_record(card_id)


def test_skill_and_control_batches_have_distinct_decision_profiles() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)
    by_id = {record.card_id: record for record in records}

    report = build_roster_analysis(records, metadata)
    validate_hard_duplicate_classes(report)

    assert report["valid_for_draft"] is True
    assert report["live_card_ids"] == sorted(LIVE_IDS)
    assert report["legacy_passthrough_count"] == 35
    assert report["hard_duplicate_groups"] == []
    assert report["identical_evaluation_groups"] == []
    assert report["identity_conflicts"] == []
    assert {by_id[card_id].preferred_type for card_id in SKILL_IDS} == set(range(6))
    assert {by_id[card_id].preferred_type for card_id in CONTROL_IDS} == set(range(6))
    assert {by_id[card_id].target_mode for card_id in CONTROL_IDS} >= {
        GateTargetMode.GATE_OWNER,
        GateTargetMode.GATE_NON_OWNER,
    }
    assert GateConditionId.LANDING_GATE_CARD_WON in {
        by_id[card_id].condition_id for card_id in CONTROL_IDS
    }
    assert {
        by_id[card_id].condition_id for card_id in CONTROL_IDS
    } & {
        GateConditionId.OWNER_AHEAD,
        GateConditionId.SCORE_TIED,
        GateConditionId.OWNER_SCORE_ZERO,
        GateConditionId.OWNER_AT_MATCH_POINT,
        GateConditionId.OPPONENT_AT_MATCH_POINT,
    }


def test_landing_conditioned_control_gates_fail_back_without_landing_context() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    landing_records = [
        record
        for record in records
        if record.card_id in CONTROL_IDS
        and record.condition_id == GateConditionId.LANDING_GATE_CARD_WON
    ]
    assert landing_records

    for record in landing_records:
        result = calculate_gate_bonus(
            record,
            GateCalculationContext(
                compressed_core_g=400,
                attribute_id=0,
                current_participant=0,
                owner_participant=1,
                owner_side_score=1,
                opposing_side_score=1,
                gate_id=record.card_id,
                landing_result=None,
            ),
        )
        assert result.fallback_scope is FallbackScope.CALCULATION
        assert result.fallback_reason is FallbackReason.INVALID_LANDING
        assert result.effective_gate_bonus is None
        assert result.target_total_g is None
