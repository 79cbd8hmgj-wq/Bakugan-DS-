from __future__ import annotations

from dataclasses import replace

from bakugan_ds.gates.authoring import legacy_passthrough_record
from bakugan_ds.gates.record import (
    GateArchetype,
    GateConditionId,
    GateEffectId,
    GateTargetMode,
    GateTimingPhase,
    parse_record,
    serialize_record,
)


def test_milestone_6d_semantic_ids_are_frozen() -> None:
    assert int(GateArchetype.LEGACY) == 0
    assert int(GateArchetype.COMEBACK) == 1
    assert int(GateArchetype.POWER) == 2
    assert int(GateArchetype.SKILL) == 3
    assert int(GateArchetype.CONTROL) == 4
    assert int(GateArchetype.RISK) == 5
    assert int(GateArchetype.ATTRIBUTE) == 6
    assert int(GateArchetype.CHAOS) == 7

    assert int(GateConditionId.NONE) == 0
    assert int(GateConditionId.OWNER_BEHIND) == 1
    assert int(GateConditionId.LANDING_GATE_CARD_WON) == 7

    assert int(GateEffectId.NONE) == 0
    assert int(GateEffectId.ADD_SIGNED_G) == 1
    assert int(GateEffectId.SUBTRACT_MAGNITUDE_G) == 2

    assert int(GateTargetMode.CURRENT_COMBATANT) == 0
    assert int(GateTargetMode.GATE_OWNER) == 1
    assert int(GateTargetMode.GATE_NON_OWNER) == 2
    assert int(GateTimingPhase.PRE_GATE_CALCULATION) == 0


def test_signed_effect_values_round_trip_through_record_bytes() -> None:
    record = replace(
        legacy_passthrough_record(7),
        effect_value=-40,
        drawback_value=-25,
        secondary_value=-10,
    )
    decoded = parse_record(serialize_record(record))
    assert decoded.effect_value == -40
    assert decoded.drawback_value == -25
    assert decoded.secondary_value == -10
