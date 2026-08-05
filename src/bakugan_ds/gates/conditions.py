from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.record import GateConditionId

VICTORY_SCORE = 3


@dataclass(frozen=True)
class GateConditionContext:
    owner_side_score: int
    opposing_side_score: int
    landing_result: int | None = None

    def validate_scores(self) -> None:
        for label, value in (
            ("owner side score", self.owner_side_score),
            ("opposing side score", self.opposing_side_score),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise WorkspaceError(f"{label} must be an integer")
            if not 0 <= value <= 0xFF:
                raise WorkspaceError(f"{label} must fit unsigned byte storage")
        if self.landing_result is not None:
            if isinstance(self.landing_result, bool) or not isinstance(self.landing_result, int):
                raise WorkspaceError("landing result must be an integer when present")
            if not 0 <= self.landing_result <= 0xFF:
                raise WorkspaceError("landing result must fit unsigned byte storage")


def condition_requires_landing(condition_id: int) -> bool:
    try:
        return GateConditionId(condition_id) is GateConditionId.LANDING_GATE_CARD_WON
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D condition ID: {condition_id}") from exc


def evaluate_gate_condition(
    condition_id: int,
    context: GateConditionContext,
    condition_value: int = 0,
) -> bool:
    context.validate_scores()
    try:
        condition = GateConditionId(condition_id)
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D condition ID: {condition_id}") from exc

    if condition is GateConditionId.NONE:
        return True
    if condition is GateConditionId.OWNER_BEHIND:
        return context.owner_side_score < context.opposing_side_score
    if condition is GateConditionId.OWNER_AHEAD:
        return context.owner_side_score > context.opposing_side_score
    if condition is GateConditionId.SCORE_TIED:
        return context.owner_side_score == context.opposing_side_score
    if condition is GateConditionId.OWNER_SCORE_ZERO:
        return context.owner_side_score == 0
    if condition is GateConditionId.OWNER_AT_MATCH_POINT:
        return 2 <= context.owner_side_score < VICTORY_SCORE
    if condition is GateConditionId.OPPONENT_AT_MATCH_POINT:
        return 2 <= context.opposing_side_score < VICTORY_SCORE
    if condition is GateConditionId.LANDING_GATE_CARD_WON:
        if condition_value not in (0, 1):
            raise WorkspaceError("Gate Card won condition value must be zero or one")
        return context.landing_result == 1
    raise AssertionError("condition enum dispatch is incomplete")
