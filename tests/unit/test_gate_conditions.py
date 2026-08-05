from __future__ import annotations

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.conditions import GateConditionContext, evaluate_gate_condition
from bakugan_ds.gates.record import GateConditionId


@pytest.mark.parametrize(
    ("condition", "context", "expected"),
    [
        (GateConditionId.NONE, GateConditionContext(1, 1), True),
        (GateConditionId.OWNER_BEHIND, GateConditionContext(0, 1), True),
        (GateConditionId.OWNER_BEHIND, GateConditionContext(1, 1), False),
        (GateConditionId.OWNER_AHEAD, GateConditionContext(2, 1), True),
        (GateConditionId.OWNER_AHEAD, GateConditionContext(1, 2), False),
        (GateConditionId.SCORE_TIED, GateConditionContext(1, 1), True),
        (GateConditionId.SCORE_TIED, GateConditionContext(1, 2), False),
        (GateConditionId.OWNER_SCORE_ZERO, GateConditionContext(0, 2), True),
        (GateConditionId.OWNER_SCORE_ZERO, GateConditionContext(1, 2), False),
        (GateConditionId.OWNER_AT_MATCH_POINT, GateConditionContext(2, 0), True),
        (GateConditionId.OWNER_AT_MATCH_POINT, GateConditionContext(3, 0), False),
        (GateConditionId.OPPONENT_AT_MATCH_POINT, GateConditionContext(0, 2), True),
        (GateConditionId.OPPONENT_AT_MATCH_POINT, GateConditionContext(0, 3), False),
        (GateConditionId.LANDING_GATE_CARD_WON, GateConditionContext(0, 0, 1), True),
        (GateConditionId.LANDING_GATE_CARD_WON, GateConditionContext(0, 0, 0), False),
        (GateConditionId.LANDING_GATE_CARD_WON, GateConditionContext(0, 0, None), False),
    ],
)
def test_condition_truth_table(
    condition: GateConditionId,
    context: GateConditionContext,
    expected: bool,
) -> None:
    assert evaluate_gate_condition(condition, context) is expected


@pytest.mark.parametrize("score", [-1, 256])
def test_condition_context_rejects_invalid_scores(score: int) -> None:
    with pytest.raises(WorkspaceError, match="unsigned byte"):
        evaluate_gate_condition(
            GateConditionId.OWNER_BEHIND,
            GateConditionContext(score, 0),
        )


def test_landing_condition_rejects_unsupported_condition_value() -> None:
    with pytest.raises(WorkspaceError, match="zero or one"):
        evaluate_gate_condition(
            GateConditionId.LANDING_GATE_CARD_WON,
            GateConditionContext(0, 0, 1),
            condition_value=2,
        )


def test_unknown_condition_does_not_default_true() -> None:
    with pytest.raises(WorkspaceError, match="condition ID"):
        evaluate_gate_condition(99, GateConditionContext(0, 0))
