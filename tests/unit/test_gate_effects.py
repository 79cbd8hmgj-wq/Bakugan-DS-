from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import approved_juggernoid_record
from bakugan_ds.gates.conditions import GateConditionContext
from bakugan_ds.gates.effects import (
    GateEffectContext,
    apply_gate_effect,
    dispatch_gate_modifiers,
    effect_delta,
    matches_gate_target,
)
from bakugan_ds.gates.record import (
    GateConditionId,
    GateEffectId,
    GateTargetMode,
)


@pytest.mark.parametrize(
    ("target", "current", "owner", "expected"),
    [
        (GateTargetMode.CURRENT_COMBATANT, 0, 1, True),
        (GateTargetMode.GATE_OWNER, 1, 1, True),
        (GateTargetMode.GATE_OWNER, 0, 1, False),
        (GateTargetMode.GATE_NON_OWNER, 0, 1, True),
        (GateTargetMode.GATE_NON_OWNER, 1, 1, False),
    ],
)
def test_target_truth_table(
    target: GateTargetMode,
    current: int,
    owner: int,
    expected: bool,
) -> None:
    assert matches_gate_target(target, GateEffectContext(current, owner)) is expected


@pytest.mark.parametrize(
    ("effect", "value", "expected_delta"),
    [
        (GateEffectId.NONE, 40, 0),
        (GateEffectId.ADD_SIGNED_G, 40, 40),
        (GateEffectId.ADD_SIGNED_G, -40, -40),
        (GateEffectId.SUBTRACT_MAGNITUDE_G, 40, -40),
        (GateEffectId.SUBTRACT_MAGNITUDE_G, -40, -40),
    ],
)
def test_effect_delta_is_signed_and_deterministic(
    effect: GateEffectId,
    value: int,
    expected_delta: int,
) -> None:
    assert effect_delta(effect, value) == expected_delta
    assert apply_gate_effect(effect, value, 100) == 100 + expected_delta


def test_dispatch_applies_primary_then_drawback() -> None:
    record = replace(
        approved_juggernoid_record(),
        drawback_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
        drawback_value=25,
    )
    trace = dispatch_gate_modifiers(
        record,
        GateConditionContext(owner_side_score=0, opposing_side_score=1),
        GateEffectContext(current_participant=1, owner_participant=1),
        100,
    )
    assert trace.primary_delta == 40
    assert trace.drawback_delta == -25
    assert trace.unclamped_result == 115
    assert trace.final_result == 115


def test_false_condition_is_not_a_fallback_or_partial_effect() -> None:
    trace = dispatch_gate_modifiers(
        approved_juggernoid_record(),
        GateConditionContext(owner_side_score=1, opposing_side_score=1),
        GateEffectContext(current_participant=1, owner_participant=1),
        100,
    )
    assert trace.condition_result is False
    assert trace.target_result is True
    assert trace.primary_delta == 0
    assert trace.drawback_delta == 0
    assert trace.final_result == 100


def test_nonmatching_target_prevents_reward_and_drawback() -> None:
    record = replace(
        approved_juggernoid_record(),
        condition_id=GateConditionId.NONE,
        target_mode=GateTargetMode.GATE_OWNER,
        drawback_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
        drawback_value=25,
    )
    trace = dispatch_gate_modifiers(
        record,
        GateConditionContext(owner_side_score=0, opposing_side_score=1),
        GateEffectContext(current_participant=0, owner_participant=1),
        100,
    )
    assert trace.condition_result is True
    assert trace.target_result is False
    assert trace.primary_delta == 0
    assert trace.drawback_delta == 0
    assert trace.final_result == 100


def test_dispatch_clamps_final_gate_bonus_to_signed_16() -> None:
    record = replace(
        approved_juggernoid_record(),
        condition_id=GateConditionId.NONE,
        target_mode=GateTargetMode.CURRENT_COMBATANT,
        effect_value=0x7FFF,
    )
    trace = dispatch_gate_modifiers(
        record,
        GateConditionContext(owner_side_score=0, opposing_side_score=0),
        GateEffectContext(current_participant=0, owner_participant=1),
        0x7FFF,
    )
    assert trace.unclamped_result == 0xFFFE
    assert trace.final_result == 0x7FFF


def test_secondary_fields_are_rejected_for_live_dispatch() -> None:
    record = replace(
        approved_juggernoid_record(),
        secondary_effect_id=GateEffectId.ADD_SIGNED_G,
        secondary_condition_id=GateConditionId.NONE,
        secondary_value=10,
    )
    with pytest.raises(WorkspaceError, match="secondary"):
        dispatch_gate_modifiers(
            record,
            GateConditionContext(owner_side_score=0, opposing_side_score=1),
            GateEffectContext(current_participant=1, owner_participant=1),
            100,
        )


def test_unknown_target_and_effect_fail_closed() -> None:
    with pytest.raises(WorkspaceError, match="target mode"):
        matches_gate_target(99, GateEffectContext(0, 1))
    with pytest.raises(WorkspaceError, match="effect ID"):
        apply_gate_effect(99, 1, 100)
