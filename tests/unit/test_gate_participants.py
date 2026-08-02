from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence
from bakugan_ds.gates.participants import (
    ParticipantContext,
    ParticipantControl,
    ParticipantRole,
    TargetMode,
    TargetRule,
    normalize_participant_artifact,
)


def participant_payload() -> dict[str, object]:
    roles: list[object] = []
    for role in ParticipantRole:
        roles.append(
            {
                "access": "+0x00",
                "confidence": "confirmed",
                "evidence": f"confirmed evidence for {role.value}",
                "identity_source": role.value,
                "initialization": "battle setup",
                "owner_structure": "confirmed runtime structure",
                "reset": "owning object reset",
                "role": role.value,
                "transfer": "copied into live battle context",
            }
        )

    target_modes: list[object] = []
    for mode in TargetMode:
        target_modes.append(
            {
                "availability": "documented timing boundary",
                "confidence": "confirmed",
                "evidence": f"confirmed resolver evidence for {mode.value}",
                "mode": mode.value,
                "requires_result": mode in (TargetMode.WINNER, TargetMode.LOSER),
                "requires_source": mode in (TargetMode.SELF, TargetMode.OPPONENT),
                "resolution": "deterministic participant-index resolution",
            }
        )

    return {
        "format_version": 1,
        "profile_id": "b6re_rev0",
        "roles": roles,
        "scripted_paths": [
            "normal local battle",
            "tutorial and story battle",
            "multiplayer participant construction",
        ],
        "target_modes": target_modes,
    }


def ai_owned_context(*, winner_record_index: int = 1) -> ParticipantContext:
    return ParticipantContext(
        gate_owner=1,
        defender=1,
        challenger=0,
        controls=(
            ParticipantControl(participant_index=0, is_ai=False),
            ParticipantControl(participant_index=1, is_ai=True),
        ),
        winner_record_index=winner_record_index,
    )


def test_normalize_participant_artifact_requires_complete_confirmed_model() -> None:
    model = normalize_participant_artifact(participant_payload())

    assert {entry.role for entry in model.entries} == set(ParticipantRole)
    assert {rule.mode for rule in model.target_modes} == set(TargetMode)


def test_normalize_participant_artifact_rejects_missing_role() -> None:
    payload = participant_payload()
    roles = list(cast(list[object], payload["roles"]))
    roles.pop()
    payload["roles"] = roles

    with pytest.raises(WorkspaceError, match="missing roles"):
        normalize_participant_artifact(payload)


def test_normalize_participant_artifact_rejects_probable_role() -> None:
    payload = participant_payload()
    roles = list(cast(list[object], payload["roles"]))
    first = dict(cast(dict[str, object], roles[0]))
    first["confidence"] = "probable"
    roles[0] = first
    payload["roles"] = roles

    with pytest.raises(WorkspaceError, match="must be confirmed"):
        normalize_participant_artifact(payload)


def test_target_rule_rejects_implicit_opponent_source() -> None:
    rule = TargetRule(
        mode=TargetMode.OPPONENT,
        availability="live battle",
        resolution="other combatant",
        requires_source=False,
        requires_result=False,
        confidence=Confidence.CONFIRMED,
        evidence="confirmed participant mapping",
    )

    with pytest.raises(WorkspaceError, match="explicit source"):
        rule.validate()


def test_ai_owned_control_resolves_all_target_classes() -> None:
    context = ai_owned_context()

    assert context.resolve(TargetMode.OWNER) == (1,)
    assert context.resolve(TargetMode.DEFENDER) == (1,)
    assert context.resolve(TargetMode.CHALLENGER) == (0,)
    assert context.resolve(TargetMode.BOTH) == (1, 0)
    assert context.resolve(TargetMode.HUMAN) == (0,)
    assert context.resolve(TargetMode.AI) == (1,)
    assert context.resolve(TargetMode.SELF, source_participant=0) == (0,)
    assert context.resolve(TargetMode.OPPONENT, source_participant=0) == (1,)
    assert context.resolve(TargetMode.WINNER) == (0,)
    assert context.resolve(TargetMode.LOSER) == (1,)


def test_winner_and_loser_reject_unresolved_result() -> None:
    context = ai_owned_context(winner_record_index=-1)

    with pytest.raises(WorkspaceError, match="result is unresolved"):
        context.resolve(TargetMode.WINNER)
    with pytest.raises(WorkspaceError, match="result is unresolved"):
        context.resolve(TargetMode.LOSER)


def test_opponent_rejects_missing_or_noncombatant_source() -> None:
    context = ai_owned_context()

    with pytest.raises(WorkspaceError, match="explicit source"):
        context.resolve(TargetMode.OPPONENT)
    with pytest.raises(WorkspaceError, match="not exactly one live combatant"):
        context.resolve(TargetMode.OPPONENT, source_participant=2)


def test_distinct_pair_modes_reject_equal_descriptor_fallback() -> None:
    context = replace(ai_owned_context(), defender=0, challenger=0)

    with pytest.raises(WorkspaceError, match="requires distinct combatants"):
        context.resolve(TargetMode.BOTH)
    with pytest.raises(WorkspaceError, match="requires distinct combatants"):
        context.resolve(TargetMode.OPPONENT, source_participant=0)


def test_combatant_only_owner_rejects_noncombatant_gate_owner() -> None:
    context = replace(ai_owned_context(), gate_owner=2)

    assert context.resolve(TargetMode.OWNER) == (2,)
    with pytest.raises(WorkspaceError, match="not a live combatant"):
        context.resolve(TargetMode.OWNER, combatant_only=True)


def test_context_rejects_missing_human_ai_control() -> None:
    context = replace(
        ai_owned_context(),
        controls=(ParticipantControl(participant_index=0, is_ai=False),),
    )

    with pytest.raises(WorkspaceError, match="missing human/AI control"):
        context.validate()
