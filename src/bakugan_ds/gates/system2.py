from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.record import GateRecordV1

_MAX_PARTICIPANT_INDEX = 15
CORE_G_COMPRESSION_THRESHOLD = 400
CORE_G_COMPRESSION_BASE = 200
Q8_8_DENOMINATOR = 256


class System2Archetype(IntEnum):
    LEGACY_PASSTHROUGH = 0
    COMEBACK = 1


class System2Condition(IntEnum):
    NONE = 0
    OWNER_BEHIND = 1


class System2Effect(IntEnum):
    NONE = 0
    ADD_GATE_BONUS_G = 1


class System2Target(IntEnum):
    CURRENT_COMBATANT = 0
    GATE_OWNER_COMBATANT = 1


class System2Timing(IntEnum):
    PRE_GATE = 0


class FallbackScope(StrEnum):
    NONE = "none"
    RECORD = "record"
    CALCULATION = "calculation"
    BATTLE_TYPE = "battle_type"


class FallbackReason(StrEnum):
    NONE = "none"
    LEGACY_PASSTHROUGH = "legacy_passthrough"
    INVALID_CARD_IDENTITY = "invalid_card_identity"
    INVALID_ENUM = "invalid_enum"
    INVALID_TARGET = "invalid_target"
    UNSUPPORTED_RECORD = "unsupported_record"
    INVALID_CORE_G = "invalid_core_g"
    INVALID_ATTRIBUTE = "invalid_attribute"
    INVALID_PARTICIPANT = "invalid_participant"
    INVALID_SCORE = "invalid_score"
    GATE_ID_MISMATCH = "gate_id_mismatch"
    INVALID_WEIGHT_VECTOR = "invalid_weight_vector"
    INVALID_BATTLE_TYPE = "invalid_battle_type"
    INVALID_RNG_STATE = "invalid_rng_state"


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def compress_core_g_for_gate(value: int) -> int:
    if not _is_int(value) or not 0 <= value <= 0xFFFF:
        raise WorkspaceError("core G must fit unsigned 16-bit storage")
    if value <= CORE_G_COMPRESSION_THRESHOLD:
        return value
    return CORE_G_COMPRESSION_BASE + (value >> 1)


def trunc_div_toward_zero(numerator: int, denominator: int) -> int:
    if not _is_int(numerator):
        raise WorkspaceError("numerator must be an integer")
    if not _is_int(denominator) or denominator <= 0:
        raise WorkspaceError("denominator must be positive")
    if numerator >= 0:
        return numerator // denominator
    return -((-numerator) // denominator)


def clamp_i16(value: int) -> int:
    if not _is_int(value):
        raise WorkspaceError("signed clamp value must be an integer")
    return min(0x7FFF, max(-0x8000, value))


def clamp_u16(value: int) -> int:
    if not _is_int(value):
        raise WorkspaceError("unsigned clamp value must be an integer")
    return min(0xFFFF, max(0, value))


@dataclass(frozen=True)
class GateCalculationContext:
    compressed_core_g: int
    attribute_id: int
    current_participant: int
    owner_participant: int
    owner_side_score: int
    opposing_side_score: int
    gate_id: int = 19

    def failure_reason(self) -> FallbackReason:
        if not _is_int(self.gate_id) or not 1 <= self.gate_id <= 103:
            return FallbackReason.INVALID_CARD_IDENTITY
        if not _is_int(self.compressed_core_g) or not 0 <= self.compressed_core_g <= 0xFFFF:
            return FallbackReason.INVALID_CORE_G
        if not _is_int(self.attribute_id) or not 0 <= self.attribute_id < 6:
            return FallbackReason.INVALID_ATTRIBUTE
        if (
            not _is_int(self.current_participant)
            or not 0 <= self.current_participant <= _MAX_PARTICIPANT_INDEX
            or not _is_int(self.owner_participant)
            or not 0 <= self.owner_participant <= _MAX_PARTICIPANT_INDEX
        ):
            return FallbackReason.INVALID_PARTICIPANT
        if (
            not _is_int(self.owner_side_score)
            or not 0 <= self.owner_side_score <= 0xFF
            or not _is_int(self.opposing_side_score)
            or not 0 <= self.opposing_side_score <= 0xFF
        ):
            return FallbackReason.INVALID_SCORE
        return FallbackReason.NONE

    def validate(self) -> None:
        reason = self.failure_reason()
        if reason is not FallbackReason.NONE:
            raise WorkspaceError(reason.value)


@dataclass(frozen=True)
class GateCalculationTrace:
    card_id: int
    current_participant: int
    owner_participant: int
    compressed_core_g: int
    attribute_id: int
    flat_bonus_g: int
    percent_q8_8: int
    scaled_component: int
    attribute_modifier: int
    base_gate_bonus: int
    owner_side_score: int
    opposing_side_score: int
    condition_result: bool
    effect_value: int
    unclamped_gate_bonus: int
    effective_gate_bonus: int
    target_total_g: int
    fallback_scope: FallbackScope
    fallback_reason: FallbackReason

    def to_dict(self) -> dict[str, object]:
        return {
            "card_id": self.card_id,
            "current_participant": self.current_participant,
            "owner_participant": self.owner_participant,
            "compressed_core_g": self.compressed_core_g,
            "attribute_id": self.attribute_id,
            "flat_bonus_g": self.flat_bonus_g,
            "percent_q8_8": self.percent_q8_8,
            "scaled_component": self.scaled_component,
            "attribute_modifier": self.attribute_modifier,
            "base_gate_bonus": self.base_gate_bonus,
            "owner_side_score": self.owner_side_score,
            "opposing_side_score": self.opposing_side_score,
            "condition_result": self.condition_result,
            "effect_value": self.effect_value,
            "unclamped_gate_bonus": self.unclamped_gate_bonus,
            "effective_gate_bonus": self.effective_gate_bonus,
            "target_total_g": self.target_total_g,
            "fallback_scope": self.fallback_scope.value,
            "fallback_reason": self.fallback_reason.value,
        }


@dataclass(frozen=True)
class GateCalculationResult:
    effective_gate_bonus: int | None
    target_total_g: int | None
    fallback_scope: FallbackScope
    fallback_reason: FallbackReason
    trace: GateCalculationTrace


def _safe_int(value: object) -> int:
    return value if _is_int(value) else 0


def _fallback_trace(
    record: GateRecordV1,
    context: GateCalculationContext,
    scope: FallbackScope,
    reason: FallbackReason,
) -> GateCalculationTrace:
    return GateCalculationTrace(
        card_id=_safe_int(record.card_id),
        current_participant=_safe_int(context.current_participant),
        owner_participant=_safe_int(context.owner_participant),
        compressed_core_g=_safe_int(context.compressed_core_g),
        attribute_id=_safe_int(context.attribute_id),
        flat_bonus_g=0,
        percent_q8_8=0,
        scaled_component=0,
        attribute_modifier=0,
        base_gate_bonus=0,
        owner_side_score=_safe_int(context.owner_side_score),
        opposing_side_score=_safe_int(context.opposing_side_score),
        condition_result=False,
        effect_value=0,
        unclamped_gate_bonus=0,
        effective_gate_bonus=0,
        target_total_g=0,
        fallback_scope=scope,
        fallback_reason=reason,
    )


def _fallback(
    record: GateRecordV1,
    context: GateCalculationContext,
    scope: FallbackScope,
    reason: FallbackReason,
) -> GateCalculationResult:
    return GateCalculationResult(
        effective_gate_bonus=None,
        target_total_g=None,
        fallback_scope=scope,
        fallback_reason=reason,
        trace=_fallback_trace(record, context, scope, reason),
    )


def record_fallback_reason(record: GateRecordV1) -> FallbackReason:
    try:
        record.validate()
    except WorkspaceError:
        return FallbackReason.UNSUPPORTED_RECORD

    if record.archetype == System2Archetype.LEGACY_PASSTHROUGH:
        return FallbackReason.LEGACY_PASSTHROUGH
    if record.archetype != System2Archetype.COMEBACK:
        return FallbackReason.INVALID_ENUM
    if record.card_id != 19:
        return FallbackReason.INVALID_CARD_IDENTITY
    if record.target_mode != System2Target.GATE_OWNER_COMBATANT:
        return FallbackReason.INVALID_TARGET
    if (
        record.condition_id != System2Condition.OWNER_BEHIND
        or record.effect_id != System2Effect.ADD_GATE_BONUS_G
        or record.timing_phase != System2Timing.PRE_GATE
    ):
        return FallbackReason.INVALID_ENUM
    if any(
        (
            record.drawback_id,
            record.drawback_value,
            record.activation_limit,
            record.fatigue_rate,
            record.condition_value,
            record.secondary_effect_id,
            record.secondary_condition_id,
            record.secondary_value,
        )
    ):
        return FallbackReason.UNSUPPORTED_RECORD
    return FallbackReason.NONE


def calculate_gate_bonus(
    record: GateRecordV1,
    context: GateCalculationContext,
) -> GateCalculationResult:
    record_reason = record_fallback_reason(record)
    if record_reason is not FallbackReason.NONE:
        return _fallback(record, context, FallbackScope.RECORD, record_reason)

    context_reason = context.failure_reason()
    if context_reason is not FallbackReason.NONE:
        return _fallback(
            record,
            context,
            FallbackScope.CALCULATION,
            context_reason,
        )
    if context.gate_id != record.card_id:
        return _fallback(
            record,
            context,
            FallbackScope.CALCULATION,
            FallbackReason.GATE_ID_MISMATCH,
        )

    scaled_component = trunc_div_toward_zero(
        context.compressed_core_g * record.percent_q8_8,
        Q8_8_DENOMINATOR,
    )
    attribute_modifier = record.attribute_modifiers[context.attribute_id]
    base_gate_bonus = record.flat_bonus_g + scaled_component + attribute_modifier
    condition_result = (
        context.current_participant == context.owner_participant
        and context.owner_side_score < context.opposing_side_score
    )
    applied_effect = record.effect_value if condition_result else 0
    unclamped_gate_bonus = base_gate_bonus + applied_effect
    effective_gate_bonus = clamp_i16(unclamped_gate_bonus)
    target_total_g = clamp_u16(context.compressed_core_g + effective_gate_bonus)
    trace = GateCalculationTrace(
        card_id=record.card_id,
        current_participant=context.current_participant,
        owner_participant=context.owner_participant,
        compressed_core_g=context.compressed_core_g,
        attribute_id=context.attribute_id,
        flat_bonus_g=record.flat_bonus_g,
        percent_q8_8=record.percent_q8_8,
        scaled_component=scaled_component,
        attribute_modifier=attribute_modifier,
        base_gate_bonus=base_gate_bonus,
        owner_side_score=context.owner_side_score,
        opposing_side_score=context.opposing_side_score,
        condition_result=condition_result,
        effect_value=applied_effect,
        unclamped_gate_bonus=unclamped_gate_bonus,
        effective_gate_bonus=effective_gate_bonus,
        target_total_g=target_total_g,
        fallback_scope=FallbackScope.NONE,
        fallback_reason=FallbackReason.NONE,
    )
    return GateCalculationResult(
        effective_gate_bonus=effective_gate_bonus,
        target_total_g=target_total_g,
        fallback_scope=FallbackScope.NONE,
        fallback_reason=FallbackReason.NONE,
        trace=trace,
    )
