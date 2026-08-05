from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.conditions import GateConditionContext, evaluate_gate_condition
from bakugan_ds.gates.record import GateEffectId, GateRecordV1, GateTargetMode

_MIN_I32 = -(1 << 31)
_MAX_I32 = (1 << 31) - 1


@dataclass(frozen=True)
class GateEffectContext:
    current_participant: int
    owner_participant: int

    def validate(self) -> None:
        for label, value in (
            ("current participant", self.current_participant),
            ("owner participant", self.owner_participant),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise WorkspaceError(f"{label} must be an integer")
            if not 0 <= value <= 15:
                raise WorkspaceError(f"{label} must be between 0 and 15")


@dataclass(frozen=True)
class GateModifierTrace:
    condition_result: bool
    target_result: bool
    pre_effect_bonus: int
    primary_delta: int
    drawback_delta: int
    secondary_delta: int
    unclamped_result: int
    final_result: int


def _checked_i32(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    if not _MIN_I32 <= value <= _MAX_I32:
        raise WorkspaceError(f"{label} exceeds signed 32-bit range")
    return value


def clamp_i16(value: int) -> int:
    _checked_i32(value, "Gate bonus")
    return min(0x7FFF, max(-0x8000, value))


def matches_gate_target(target_mode: int, context: GateEffectContext) -> bool:
    context.validate()
    try:
        target = GateTargetMode(target_mode)
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D target mode: {target_mode}") from exc
    if target is GateTargetMode.CURRENT_COMBATANT:
        return True
    if target is GateTargetMode.GATE_OWNER:
        return context.current_participant == context.owner_participant
    if target is GateTargetMode.GATE_NON_OWNER:
        return context.current_participant != context.owner_participant
    raise AssertionError("target enum dispatch is incomplete")


def effect_delta(effect_id: int, value: int) -> int:
    _checked_i32(value, "effect value")
    try:
        effect = GateEffectId(effect_id)
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D effect ID: {effect_id}") from exc
    if effect is GateEffectId.NONE:
        return 0
    if effect is GateEffectId.ADD_SIGNED_G:
        return value
    if effect is GateEffectId.SUBTRACT_MAGNITUDE_G:
        if value == _MIN_I32:
            raise WorkspaceError("cannot take magnitude of signed 32-bit minimum")
        return -abs(value)
    raise AssertionError("effect enum dispatch is incomplete")


def apply_gate_effect(effect_id: int, value: int, gate_bonus: int) -> int:
    gate_bonus = _checked_i32(gate_bonus, "Gate bonus")
    delta = effect_delta(effect_id, value)
    return _checked_i32(gate_bonus + delta, "Gate effect result")


def dispatch_gate_modifiers(
    record: GateRecordV1,
    condition_context: GateConditionContext,
    effect_context: GateEffectContext,
    gate_bonus: int,
    *,
    allow_secondary_fixture: bool = False,
) -> GateModifierTrace:
    gate_bonus = _checked_i32(gate_bonus, "base Gate bonus")
    condition_result = evaluate_gate_condition(
        record.condition_id,
        condition_context,
        record.condition_value,
    )
    target_result = matches_gate_target(record.target_mode, effect_context)

    primary_delta = 0
    drawback_delta = 0
    secondary_delta = 0
    current = gate_bonus
    if condition_result and target_result:
        primary_delta = effect_delta(record.effect_id, record.effect_value)
        current = _checked_i32(current + primary_delta, "primary Gate effect result")
        drawback_delta = effect_delta(record.drawback_id, record.drawback_value)
        current = _checked_i32(current + drawback_delta, "Gate drawback result")

        if allow_secondary_fixture:
            secondary_condition = evaluate_gate_condition(
                record.secondary_condition_id,
                condition_context,
                record.condition_value,
            )
            if secondary_condition:
                secondary_delta = effect_delta(
                    record.secondary_effect_id,
                    record.secondary_value,
                )
                current = _checked_i32(current + secondary_delta, "secondary Gate effect result")
        elif record.secondary_effect_id or record.secondary_condition_id or record.secondary_value:
            raise WorkspaceError("Milestone 6D live records must not use secondary effects")

    return GateModifierTrace(
        condition_result=condition_result,
        target_result=target_result,
        pre_effect_bonus=gate_bonus,
        primary_delta=primary_delta,
        drawback_delta=drawback_delta,
        secondary_delta=secondary_delta,
        unclamped_result=current,
        final_result=clamp_i16(current),
    )
