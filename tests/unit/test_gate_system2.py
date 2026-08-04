from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    legacy_passthrough_record,
)
from bakugan_ds.gates.system2 import (
    FallbackReason,
    FallbackScope,
    GateCalculationContext,
    calculate_gate_bonus,
    clamp_i16,
    clamp_u16,
    trunc_div_toward_zero,
)


def calculation_context(
    *,
    core_g: int = 190,
    attribute_id: int = 0,
    current_participant: int = 1,
    owner_participant: int = 1,
    owner_score: int = 1,
    opposing_score: int = 1,
) -> GateCalculationContext:
    return GateCalculationContext(
        compressed_core_g=core_g,
        attribute_id=attribute_id,
        current_participant=current_participant,
        owner_participant=owner_participant,
        owner_side_score=owner_score,
        opposing_side_score=opposing_score,
    )


@pytest.mark.parametrize(
    ("core_g", "attribute_id", "behind", "expected"),
    [
        (190, 0, False, 74),
        (190, 1, False, 104),
        (190, 0, True, 114),
        (190, 1, True, 144),
        (525, 0, False, 101),
        (525, 1, False, 131),
        (525, 0, True, 141),
        (525, 1, True, 171),
    ],
)
def test_juggernoid_vectors(
    core_g: int, attribute_id: int, behind: bool, expected: int
) -> None:
    context = calculation_context(
        core_g=core_g,
        attribute_id=attribute_id,
        current_participant=1,
        owner_participant=1,
        owner_score=0 if behind else 1,
        opposing_score=1,
    )
    result = calculate_gate_bonus(approved_juggernoid_record(), context)

    assert result.effective_gate_bonus == expected
    assert result.target_total_g == min(0xFFFF, core_g + expected)
    assert result.fallback_scope is FallbackScope.NONE
    assert result.fallback_reason is FallbackReason.NONE


def test_non_owner_never_receives_comeback_rider() -> None:
    result = calculate_gate_bonus(
        approved_juggernoid_record(),
        calculation_context(
            current_participant=0,
            owner_participant=1,
            owner_score=0,
            opposing_score=1,
        ),
    )

    assert result.effective_gate_bonus == 74
    assert result.trace.condition_result is False
    assert result.trace.effect_value == 0


def test_tied_owner_does_not_satisfy_owner_behind() -> None:
    result = calculate_gate_bonus(
        approved_juggernoid_record(),
        calculation_context(owner_score=1, opposing_score=1),
    )

    assert result.effective_gate_bonus == 74
    assert result.trace.condition_result is False


def test_legacy_passthrough_returns_record_fallback_without_components() -> None:
    result = calculate_gate_bonus(
        legacy_passthrough_record(1), calculation_context()
    )

    assert result.effective_gate_bonus is None
    assert result.target_total_g is None
    assert result.fallback_scope is FallbackScope.RECORD
    assert result.fallback_reason is FallbackReason.LEGACY_PASSTHROUGH
    assert result.trace.scaled_component == 0
    assert result.trace.attribute_modifier == 0
    assert result.trace.base_gate_bonus == 0


@pytest.mark.parametrize(
    ("record_change", "reason"),
    [
        ({"card_id": 20}, FallbackReason.INVALID_CARD_IDENTITY),
        ({"condition_id": 2}, FallbackReason.INVALID_ENUM),
        ({"effect_id": 2}, FallbackReason.INVALID_ENUM),
        ({"target_mode": 2}, FallbackReason.INVALID_TARGET),
        ({"timing_phase": 1}, FallbackReason.INVALID_ENUM),
        ({"activation_limit": 1}, FallbackReason.UNSUPPORTED_RECORD),
        ({"fatigue_rate": 1}, FallbackReason.UNSUPPORTED_RECORD),
        ({"drawback_id": 1}, FallbackReason.UNSUPPORTED_RECORD),
        ({"secondary_effect_id": 1}, FallbackReason.UNSUPPORTED_RECORD),
    ],
)
def test_unsupported_record_semantics_fail_before_calculation(
    record_change: dict[str, int], reason: FallbackReason
) -> None:
    record = replace(approved_juggernoid_record(), **record_change)
    result = calculate_gate_bonus(record, calculation_context())

    assert result.effective_gate_bonus is None
    assert result.target_total_g is None
    assert result.fallback_scope is FallbackScope.RECORD
    assert result.fallback_reason is reason
    assert result.trace.scaled_component == 0
    assert result.trace.base_gate_bonus == 0


@pytest.mark.parametrize(
    ("context_change", "reason"),
    [
        ({"compressed_core_g": -1}, FallbackReason.INVALID_CORE_G),
        ({"compressed_core_g": 0x10000}, FallbackReason.INVALID_CORE_G),
        ({"attribute_id": -1}, FallbackReason.INVALID_ATTRIBUTE),
        ({"attribute_id": 6}, FallbackReason.INVALID_ATTRIBUTE),
        ({"current_participant": -1}, FallbackReason.INVALID_PARTICIPANT),
        ({"current_participant": 16}, FallbackReason.INVALID_PARTICIPANT),
        ({"owner_participant": 16}, FallbackReason.INVALID_PARTICIPANT),
        ({"owner_side_score": -1}, FallbackReason.INVALID_SCORE),
        ({"owner_side_score": 0x100}, FallbackReason.INVALID_SCORE),
        ({"opposing_side_score": 0x100}, FallbackReason.INVALID_SCORE),
    ],
)
def test_invalid_context_returns_complete_calculation_fallback(
    context_change: dict[str, int], reason: FallbackReason
) -> None:
    context = replace(calculation_context(), **context_change)
    result = calculate_gate_bonus(approved_juggernoid_record(), context)

    assert result.effective_gate_bonus is None
    assert result.target_total_g is None
    assert result.fallback_scope is FallbackScope.CALCULATION
    assert result.fallback_reason is reason
    assert result.trace.scaled_component == 0
    assert result.trace.attribute_modifier == 0
    assert result.trace.base_gate_bonus == 0
    assert result.trace.effect_value == 0


def test_fixed_point_division_rounds_toward_zero() -> None:
    assert trunc_div_toward_zero(257, 256) == 1
    assert trunc_div_toward_zero(255, 256) == 0
    assert trunc_div_toward_zero(-255, 256) == 0
    assert trunc_div_toward_zero(-257, 256) == -1


def test_fixed_point_division_rejects_nonpositive_denominator() -> None:
    with pytest.raises(Exception, match="denominator must be positive"):
        trunc_div_toward_zero(1, 0)


def test_negative_q8_8_component_uses_toward_zero_rounding() -> None:
    record = replace(
        approved_juggernoid_record(),
        flat_bonus_g=0,
        percent_q8_8=-257,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        effect_value=0,
    )
    result = calculate_gate_bonus(record, calculation_context(core_g=1))

    assert result.trace.scaled_component == -1
    assert result.effective_gate_bonus == -1
    assert result.target_total_g == 0


def test_gate_bonus_and_target_total_are_clamped() -> None:
    record = replace(
        approved_juggernoid_record(),
        flat_bonus_g=0x7FFF,
        percent_q8_8=0x7FFF,
        attribute_modifiers=(0x7F, 0, 0, 0, 0, 0),
        effect_value=0x7FFF,
    )
    result = calculate_gate_bonus(
        record,
        calculation_context(
            core_g=0xFFFF,
            owner_score=0,
            opposing_score=1,
        ),
    )

    assert result.effective_gate_bonus == 0x7FFF
    assert result.target_total_g == 0xFFFF
    assert result.trace.unclamped_gate_bonus > 0x7FFF


def test_clamp_helpers_cover_signed_and_unsigned_boundaries() -> None:
    assert clamp_i16(-0x8001) == -0x8000
    assert clamp_i16(0x8000) == 0x7FFF
    assert clamp_u16(-1) == 0
    assert clamp_u16(0x10000) == 0xFFFF


def test_trace_is_ordered_and_contains_exact_components() -> None:
    result = calculate_gate_bonus(
        approved_juggernoid_record(),
        calculation_context(
            core_g=190,
            attribute_id=1,
            owner_score=0,
            opposing_score=1,
        ),
    )

    assert result.trace.to_dict() == {
        "card_id": 19,
        "current_participant": 1,
        "owner_participant": 1,
        "compressed_core_g": 190,
        "attribute_id": 1,
        "flat_bonus_g": 60,
        "percent_q8_8": 20,
        "scaled_component": 14,
        "attribute_modifier": 30,
        "base_gate_bonus": 104,
        "owner_side_score": 0,
        "opposing_side_score": 1,
        "condition_result": True,
        "effect_value": 40,
        "unclamped_gate_bonus": 144,
        "effective_gate_bonus": 144,
        "target_total_g": 334,
        "fallback_scope": "none",
        "fallback_reason": "none",
    }


def test_confirmed_lcg_transition() -> None:
    from bakugan_ds.gates.history import advance_weighted_lcg

    next_state = advance_weighted_lcg(0x0000000012345678)
    assert next_state == (
        0x0000000012345678 * 0x5D588B656C078965 + 0x00269EC3
    ) & 0xFFFFFFFFFFFFFFFF
    assert next_state == 0xF287E3062E5AF41B


def test_confirmed_weighted_roll_uses_advanced_high_word() -> None:
    from bakugan_ds.gates.history import weighted_roll_from_state

    next_state, roll = weighted_roll_from_state(0x12345678, 200)
    assert next_state == 0xF287E3062E5AF41B
    assert roll == 189


def test_explicit_battle_type_bypasses_rng_but_allows_script_override() -> None:
    from bakugan_ds.gates.selector import select_system2_battle_type

    result = select_system2_battle_type(
        approved_juggernoid_record(),
        constructor_type=2,
        scripted_override=4,
        rng_state=0x12345678,
        legacy_type=0,
    )

    assert result.final_type == 4
    assert result.next_rng_state == 0x12345678
    assert result.weighted_result is None
    assert result.fallback_scope is FallbackScope.NONE
    assert result.trace.explicit_type_argument == 2
    assert result.trace.scripted_override == 4


def test_valid_normal_fallback_advances_rng_once_and_selects_bucket() -> None:
    from bakugan_ds.gates.selector import select_system2_battle_type

    result = select_system2_battle_type(
        approved_juggernoid_record(),
        constructor_type=-1,
        scripted_override=None,
        rng_state=0x12345678,
        legacy_type=0,
    )

    assert result.next_rng_state == 0xF287E3062E5AF41B
    assert result.weighted_result == 5
    assert result.final_type == 5
    assert result.trace.weight_total == 200
    assert result.trace.weights == (50, 30, 30, 30, 30, 30)
    assert result.trace.legacy_fallback is False


def test_scripted_override_supersedes_weighted_result() -> None:
    from bakugan_ds.gates.selector import select_system2_battle_type

    result = select_system2_battle_type(
        approved_juggernoid_record(),
        constructor_type=-1,
        scripted_override=1,
        rng_state=0x12345678,
        legacy_type=0,
    )

    assert result.weighted_result == 5
    assert result.final_type == 1
    assert result.next_rng_state == 0xF287E3062E5AF41B


def test_passthrough_battle_type_uses_legacy_without_rng() -> None:
    from bakugan_ds.gates.selector import select_system2_battle_type

    result = select_system2_battle_type(
        legacy_passthrough_record(1),
        constructor_type=-1,
        scripted_override=None,
        rng_state=0x12345678,
        legacy_type=3,
    )

    assert result.final_type == 3
    assert result.next_rng_state == 0x12345678
    assert result.weighted_result is None
    assert result.fallback_scope is FallbackScope.RECORD
    assert result.fallback_reason is FallbackReason.LEGACY_PASSTHROUGH
    assert result.trace.legacy_fallback is True


def test_invalid_weight_vector_uses_phase_local_legacy_fallback() -> None:
    from bakugan_ds.gates.selector import select_system2_battle_type

    record = replace(
        approved_juggernoid_record(), battle_weights=(0, 0, 0, 0, 0, 0)
    )
    result = select_system2_battle_type(
        record,
        constructor_type=-1,
        scripted_override=None,
        rng_state=0x12345678,
        legacy_type=3,
    )

    assert result.final_type == 3
    assert result.next_rng_state == 0x12345678
    assert result.weighted_result is None
    assert result.fallback_scope is FallbackScope.BATTLE_TYPE
    assert result.fallback_reason is FallbackReason.INVALID_WEIGHT_VECTOR
    assert result.trace.legacy_fallback is True


def test_scripted_override_still_applies_after_phase_local_fallback() -> None:
    from bakugan_ds.gates.selector import select_system2_battle_type

    record = replace(
        approved_juggernoid_record(), battle_weights=(0, 0, 0, 0, 0, 0)
    )
    result = select_system2_battle_type(
        record,
        constructor_type=-1,
        scripted_override=2,
        rng_state=0x12345678,
        legacy_type=3,
    )

    assert result.final_type == 2
    assert result.next_rng_state == 0x12345678
    assert result.trace.legacy_fallback is True


def test_battle_type_trace_has_approved_fields() -> None:
    from bakugan_ds.gates.selector import select_system2_battle_type

    result = select_system2_battle_type(
        approved_juggernoid_record(),
        constructor_type=-1,
        scripted_override=1,
        rng_state=0,
        legacy_type=4,
    )

    assert result.trace.to_dict() == {
        "explicit_type_argument": -1,
        "record_valid": True,
        "weights": [50, 30, 30, 30, 30, 30],
        "weight_total": 200,
        "weighted_result": 0,
        "scripted_override": 1,
        "final_type": 1,
        "legacy_fallback": False,
        "fallback_scope": "none",
        "fallback_reason": "none",
    }


def test_gate_runtime_core_compression_matches_merged_curve() -> None:
    from bakugan_ds.gates.system2 import compress_core_g_for_gate

    assert {
        value: compress_core_g_for_gate(value)
        for value in (0, 190, 400, 401, 650, 990)
    } == {
        0: 0,
        190: 190,
        400: 400,
        401: 400,
        650: 525,
        990: 695,
    }
    with pytest.raises(WorkspaceError, match="unsigned 16-bit"):
        compress_core_g_for_gate(-1)
