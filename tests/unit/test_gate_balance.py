from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import approved_juggernoid_record, legacy_passthrough_record
from bakugan_ds.gates.balance import (
    AttributeRelation,
    BattleWeightPressure,
    analyze_attribute_profile,
    analyze_battle_weights,
    analyze_gate_balance,
    calculate_gate_budget,
    classify_attribute_modifier,
    validate_attribute_profile,
)
from bakugan_ds.gates.record import (
    GateArchetype,
    GateConditionId,
    GateEffectId,
    GateRecordV1,
    GateTargetMode,
)


def make_record(
    *,
    card_id: int,
    archetype: GateArchetype,
    flat_bonus_g: int = 0,
    percent_q8_8: int = 0,
    attribute_modifiers: tuple[int, ...] = (0, 0, 0, 0, 0, 0),
    battle_weights: tuple[int, ...] = (30, 30, 30, 30, 30, 30),
    preferred_type: int = 0,
    condition_id: GateConditionId = GateConditionId.NONE,
    effect_id: GateEffectId = GateEffectId.NONE,
    effect_value: int = 0,
    drawback_id: GateEffectId = GateEffectId.NONE,
    drawback_value: int = 0,
    target_mode: GateTargetMode = GateTargetMode.CURRENT_COMBATANT,
) -> GateRecordV1:
    return GateRecordV1(
        card_id=card_id,
        archetype=int(archetype),
        flags=0,
        flat_bonus_g=flat_bonus_g,
        percent_q8_8=percent_q8_8,
        attribute_modifiers=attribute_modifiers,
        battle_weights=battle_weights,
        preferred_type=preferred_type,
        condition_id=int(condition_id),
        effect_id=int(effect_id),
        drawback_id=int(drawback_id),
        effect_value=effect_value,
        drawback_value=drawback_value,
        activation_limit=0,
        fatigue_rate=0,
        target_mode=int(target_mode),
        timing_phase=0,
        condition_value=0,
        secondary_effect_id=0,
        secondary_condition_id=0,
        secondary_value=0,
        reserved=0,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-100, AttributeRelation.OPPOSED),
        (-10, AttributeRelation.OPPOSED),
        (-9, AttributeRelation.NEUTRAL),
        (0, AttributeRelation.NEUTRAL),
        (9, AttributeRelation.NEUTRAL),
        (10, AttributeRelation.SECONDARY),
        (40, AttributeRelation.SECONDARY),
        (41, AttributeRelation.PRIMARY),
        (100, AttributeRelation.PRIMARY),
    ],
)
def test_attribute_tier_boundaries(value: int, expected: AttributeRelation) -> None:
    assert classify_attribute_modifier(value) is expected


@pytest.mark.parametrize("value", [-101, 101])
def test_attribute_tier_rejects_out_of_range(value: int) -> None:
    with pytest.raises(WorkspaceError, match="between -100 and 100"):
        classify_attribute_modifier(value)


def test_attribute_archetype_requires_positive_negative_and_spread() -> None:
    record = make_record(
        card_id=6,
        archetype=GateArchetype.ATTRIBUTE,
        flat_bonus_g=75,
        percent_q8_8=16,
        attribute_modifiers=(75, 40, 0, 0, -40, -20),
        battle_weights=(60, 24, 24, 24, 24, 24),
    )
    report = analyze_attribute_profile(record)
    assert report.maximum == 75
    assert report.minimum == -40
    assert report.spread == 115
    validate_attribute_profile(record)


def test_attribute_archetype_rejects_inadequate_spread() -> None:
    record = make_record(
        card_id=6,
        archetype=GateArchetype.ATTRIBUTE,
        attribute_modifiers=(40, 20, 0, 0, -10, -20),
    )
    with pytest.raises(WorkspaceError, match="spread"):
        validate_attribute_profile(record)


def test_non_attribute_archetype_rejects_three_positive_affinities() -> None:
    record = make_record(
        card_id=2,
        archetype=GateArchetype.POWER,
        flat_bonus_g=150,
        attribute_modifiers=(10, 10, 10, 0, 0, 0),
    )
    with pytest.raises(WorkspaceError, match="at most two"):
        validate_attribute_profile(record)


@pytest.mark.parametrize(
    ("weights", "pressure", "cost"),
    [
        ((30, 30, 30, 30, 30, 30), BattleWeightPressure.NEUTRAL, 0),
        ((50, 30, 30, 30, 30, 30), BattleWeightPressure.MILD, 10),
        ((60, 24, 24, 24, 24, 24), BattleWeightPressure.STRONG, 20),
        ((80, 24, 24, 24, 24, 24), BattleWeightPressure.EXTREME_BOUNDED, 30),
    ],
)
def test_weight_pressure_uses_integer_probability(
    weights: tuple[int, ...],
    pressure: BattleWeightPressure,
    cost: int,
) -> None:
    record = make_record(card_id=3, archetype=GateArchetype.SKILL, battle_weights=weights)
    report = analyze_battle_weights(record)
    assert report.pressure is pressure
    assert report.budget_cost == cost


@pytest.mark.parametrize(
    ("weights", "match"),
    [
        ((0, 30, 30, 30, 30, 30), "between 10 and 80"),
        ((9, 30, 30, 30, 30, 30), "between 10 and 80"),
        ((81, 30, 30, 30, 30, 30), "between 10 and 80"),
        ((10, 10, 10, 10, 10, 10), "total"),
        ((80, 80, 80, 80, 80, 80), "total"),
        ((80, 19, 19, 19, 19, 19), "40 percent"),
        ((50, 10, 20, 20, 20, 20), "4:1"),
    ],
)
def test_weight_validation_rejects_unbounded_vectors(
    weights: tuple[int, ...],
    match: str,
) -> None:
    record = make_record(card_id=3, archetype=GateArchetype.SKILL, battle_weights=weights)
    with pytest.raises(WorkspaceError, match=match):
        analyze_battle_weights(record)


def test_weight_validation_requires_preferred_maximum() -> None:
    record = make_record(
        card_id=3,
        archetype=GateArchetype.SKILL,
        battle_weights=(60, 24, 24, 24, 24, 24),
        preferred_type=1,
    )
    with pytest.raises(WorkspaceError, match="maximum-weight"):
        analyze_battle_weights(record)


def test_legacy_passthrough_has_zero_balance() -> None:
    report = analyze_gate_balance(legacy_passthrough_record(8))
    assert report.budget.net_budget == 0
    assert report.battle_weights.total == 0


def test_juggernoid_budget_is_91() -> None:
    report = analyze_gate_balance(approved_juggernoid_record())
    assert report.budget.flat_cost == 45
    assert report.budget.percentage_cost == 10
    assert report.budget.attribute_cost == 12
    assert report.budget.effect_cost == 14
    assert report.budget.battle_weight_cost == 10
    assert report.budget.net_budget == 91


def valid_archetype_records() -> tuple[GateRecordV1, ...]:
    return (
        approved_juggernoid_record(),
        make_record(card_id=2, archetype=GateArchetype.POWER, flat_bonus_g=150),
        make_record(
            card_id=3,
            archetype=GateArchetype.SKILL,
            flat_bonus_g=100,
            percent_q8_8=16,
            attribute_modifiers=(25, 0, 0, 0, 0, 0),
            battle_weights=(60, 24, 24, 24, 24, 24),
        ),
        make_record(
            card_id=4,
            archetype=GateArchetype.CONTROL,
            flat_bonus_g=150,
            target_mode=GateTargetMode.GATE_OWNER,
        ),
        make_record(
            card_id=5,
            archetype=GateArchetype.RISK,
            flat_bonus_g=175,
            percent_q8_8=16,
            drawback_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
            drawback_value=100,
        ),
        make_record(
            card_id=6,
            archetype=GateArchetype.ATTRIBUTE,
            flat_bonus_g=75,
            percent_q8_8=16,
            attribute_modifiers=(75, 40, 0, 0, -40, -20),
            battle_weights=(60, 24, 24, 24, 24, 24),
        ),
        make_record(
            card_id=7,
            archetype=GateArchetype.CHAOS,
            flat_bonus_g=150,
            battle_weights=(60, 24, 24, 24, 24, 24),
            drawback_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
            drawback_value=100,
        ),
    )


@pytest.mark.parametrize("record", valid_archetype_records())
def test_each_archetype_has_a_valid_framework_fixture(record: GateRecordV1) -> None:
    report = analyze_gate_balance(record)
    assert report.archetype is GateArchetype(record.archetype)
    assert report.budget.net_budget >= 85


def test_power_rejects_low_direct_g_share() -> None:
    record = make_record(
        card_id=2,
        archetype=GateArchetype.POWER,
        flat_bonus_g=100,
        effect_id=GateEffectId.ADD_SIGNED_G,
        effect_value=75,
    )
    with pytest.raises(WorkspaceError):
        analyze_gate_balance(record)


def test_skill_requires_strong_weights() -> None:
    record = replace(valid_archetype_records()[2], battle_weights=(50, 30, 30, 30, 30, 30))
    with pytest.raises(WorkspaceError, match="strong"):
        analyze_gate_balance(record)


def test_risk_requires_explicit_drawback() -> None:
    record = replace(valid_archetype_records()[4], drawback_id=0, drawback_value=0)
    with pytest.raises(WorkspaceError, match="drawback"):
        analyze_gate_balance(record)


def test_chaos_requires_explicit_drawback() -> None:
    record = replace(valid_archetype_records()[6], drawback_id=0, drawback_value=0)
    with pytest.raises(WorkspaceError, match="drawback"):
        analyze_gate_balance(record)


def test_budget_calculation_rejects_unsupported_effect_id() -> None:
    record = replace(approved_juggernoid_record(), effect_id=99)
    with pytest.raises(WorkspaceError, match="effect ID"):
        calculate_gate_budget(record)
