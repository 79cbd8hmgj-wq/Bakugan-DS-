from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import approved_juggernoid_record
from bakugan_ds.gates.runtime_context import (
    BattleSnapshot,
    ParticipantSnapshot,
    build_gate_calculation_context,
    side_score,
)
from bakugan_ds.gates.system2 import FallbackScope, calculate_gate_bonus


def solo_snapshot(
    *,
    gate_owner: int = 0,
    owner_score: int = 1,
    opponent_score: int = 1,
) -> BattleSnapshot:
    scores = {gate_owner: owner_score, 1 - gate_owner: opponent_score}
    return BattleSnapshot(
        gate_id=19,
        gate_owner=gate_owner,
        team_mode=False,
        participants=(
            ParticipantSnapshot(0, scores[0], 1),
            ParticipantSnapshot(1, scores[1], 0),
        ),
    )


def team_snapshot() -> BattleSnapshot:
    return BattleSnapshot(
        gate_id=19,
        gate_owner=1,
        team_mode=True,
        participants=(
            ParticipantSnapshot(0, 1, 1),
            ParticipantSnapshot(1, 0, 0),
            ParticipantSnapshot(2, 1, 3),
            ParticipantSnapshot(3, 1, 2),
        ),
    )


def test_solo_score_ignores_teammate_field() -> None:
    snapshot = BattleSnapshot(
        gate_id=19,
        gate_owner=0,
        team_mode=False,
        participants=(
            ParticipantSnapshot(0, 2, None),
            ParticipantSnapshot(1, 1, 15),
        ),
    )

    assert side_score(snapshot, 0) == 2
    assert side_score(snapshot, 1) == 1


def test_team_owner_score_uses_teammate_index() -> None:
    snapshot = team_snapshot()

    assert side_score(snapshot, 1) == 1
    assert side_score(snapshot, 2) == 2


def test_human_owned_solo_context_uses_owner_and_opponent_scores() -> None:
    context = build_gate_calculation_context(
        solo_snapshot(gate_owner=0, owner_score=0, opponent_score=1),
        current_participant=0,
        compressed_core_g=190,
        attribute_id=0,
    )

    assert context.gate_id == 19
    assert context.owner_participant == 0
    assert context.owner_side_score == 0
    assert context.opposing_side_score == 1
    result = calculate_gate_bonus(approved_juggernoid_record(), context)
    assert result.effective_gate_bonus == 114


def test_ai_owned_solo_context_uses_same_contract() -> None:
    context = build_gate_calculation_context(
        solo_snapshot(gate_owner=1, owner_score=0, opponent_score=1),
        current_participant=1,
        compressed_core_g=190,
        attribute_id=1,
    )

    assert context.owner_participant == 1
    assert context.owner_side_score == 0
    assert context.opposing_side_score == 1
    result = calculate_gate_bonus(approved_juggernoid_record(), context)
    assert result.effective_gate_bonus == 144


def test_team_context_compares_owner_pair_with_other_pair() -> None:
    context = build_gate_calculation_context(
        team_snapshot(),
        current_participant=1,
        compressed_core_g=525,
        attribute_id=0,
    )

    assert context.owner_side_score == 1
    assert context.opposing_side_score == 2
    assert calculate_gate_bonus(
        approved_juggernoid_record(), context
    ).effective_gate_bonus == 141


def test_tied_team_score_does_not_activate_comeback() -> None:
    snapshot = replace(
        team_snapshot(),
        participants=(
            ParticipantSnapshot(0, 1, 1),
            ParticipantSnapshot(1, 0, 0),
            ParticipantSnapshot(2, 0, 3),
            ParticipantSnapshot(3, 1, 2),
        ),
    )
    context = build_gate_calculation_context(
        snapshot,
        current_participant=1,
        compressed_core_g=190,
        attribute_id=0,
    )

    assert context.owner_side_score == context.opposing_side_score == 1
    result = calculate_gate_bonus(approved_juggernoid_record(), context)
    assert result.effective_gate_bonus == 74
    assert result.trace.condition_result is False


def test_team_mode_rejects_missing_teammate() -> None:
    snapshot = replace(
        team_snapshot(),
        participants=(
            ParticipantSnapshot(0, 1, None),
            *team_snapshot().participants[1:],
        ),
    )

    with pytest.raises(WorkspaceError, match="requires a teammate"):
        snapshot.validate()


def test_team_mode_rejects_nonreciprocal_teammate() -> None:
    snapshot = replace(
        team_snapshot(),
        participants=(
            ParticipantSnapshot(0, 1, 1),
            ParticipantSnapshot(1, 0, 2),
            ParticipantSnapshot(2, 1, 3),
            ParticipantSnapshot(3, 1, 2),
        ),
    )

    with pytest.raises(WorkspaceError, match="reciprocal"):
        snapshot.validate()


def test_team_mode_rejects_self_teammate() -> None:
    snapshot = replace(
        team_snapshot(),
        participants=(
            ParticipantSnapshot(0, 1, 0),
            *team_snapshot().participants[1:],
        ),
    )

    with pytest.raises(WorkspaceError, match="distinct"):
        snapshot.validate()


def test_team_mode_rejects_incomplete_or_ambiguous_pairs() -> None:
    snapshot = BattleSnapshot(
        gate_id=19,
        gate_owner=0,
        team_mode=True,
        participants=(
            ParticipantSnapshot(0, 0, 1),
            ParticipantSnapshot(1, 0, 0),
            ParticipantSnapshot(2, 0, 3),
        ),
    )

    with pytest.raises(WorkspaceError, match="exactly 4"):
        snapshot.validate()


def test_participant_indices_must_be_unique_and_scores_fit_u8() -> None:
    duplicate = BattleSnapshot(
        gate_id=19,
        gate_owner=0,
        team_mode=False,
        participants=(
            ParticipantSnapshot(0, 0, None),
            ParticipantSnapshot(0, 1, None),
        ),
    )
    with pytest.raises(WorkspaceError, match="duplicate participant"):
        duplicate.validate()

    invalid_score = replace(
        solo_snapshot(),
        participants=(
            ParticipantSnapshot(0, 0x100, None),
            ParticipantSnapshot(1, 0, None),
        ),
    )
    with pytest.raises(WorkspaceError, match="match score"):
        invalid_score.validate()


def test_build_context_rejects_nonparticipant_combatant() -> None:
    with pytest.raises(WorkspaceError, match="current participant"):
        build_gate_calculation_context(
            solo_snapshot(),
            current_participant=2,
            compressed_core_g=190,
            attribute_id=0,
        )


def test_build_context_preserves_selected_gate_identity() -> None:
    context = build_gate_calculation_context(
        replace(solo_snapshot(), gate_id=20),
        current_participant=0,
        compressed_core_g=190,
        attribute_id=0,
    )

    assert context.gate_id == 20
    result = calculate_gate_bonus(approved_juggernoid_record(), context)
    assert result.fallback_scope is FallbackScope.CALCULATION


def test_context_projection_is_independent_of_combatant_evaluation_order() -> None:
    snapshot = solo_snapshot(gate_owner=1, owner_score=0, opponent_score=1)
    contexts_first = (
        build_gate_calculation_context(
            snapshot,
            current_participant=0,
            compressed_core_g=190,
            attribute_id=0,
        ),
        build_gate_calculation_context(
            snapshot,
            current_participant=1,
            compressed_core_g=230,
            attribute_id=1,
        ),
    )
    contexts_reversed = tuple(
        reversed(
            (
                build_gate_calculation_context(
                    snapshot,
                    current_participant=1,
                    compressed_core_g=230,
                    attribute_id=1,
                ),
                build_gate_calculation_context(
                    snapshot,
                    current_participant=0,
                    compressed_core_g=190,
                    attribute_id=0,
                ),
            )
        )
    )

    assert contexts_first == contexts_reversed
    results = tuple(
        calculate_gate_bonus(approved_juggernoid_record(), context)
        for context in contexts_first
    )
    assert results[0].effective_gate_bonus == 74
    assert results[1].effective_gate_bonus == 147
