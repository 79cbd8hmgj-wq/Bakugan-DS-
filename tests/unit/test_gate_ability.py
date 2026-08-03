from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.ability import (
    AbilityModel,
    AbilityParticipant,
    AbilityPhase,
    AbilityStateEvidence,
    AbilityTimingEvidence,
)
from bakugan_ds.gates.model import Confidence


def confirmed_state(
    participant: AbilityParticipant,
    phase: AbilityPhase,
) -> AbilityStateEvidence:
    return AbilityStateEvidence(
        participant=participant,
        phase=phase,
        owner_structure="authoritative battle object",
        access="confirmed byte field",
        width_bits=8,
        value_domain="confirmed finite values",
        initialization="constructor",
        mutation="gameplay state transition",
        reset="new participant or effect scene",
        confidence=Confidence.CONFIRMED,
        evidence="exact executable and runtime evidence",
    )


def confirmed_timing() -> AbilityTimingEvidence:
    return AbilityTimingEvidence(
        selection_boundary="after Gate total construction",
        activation_boundary="before effect execution",
        resolution_boundary="terminal effect-scene state",
        gate_bonus_relation="Gate total exists before Ability selection",
        battle_type_relation="selection precedes battle-type execution",
        minigame_relation="immediate and deferred effects are distinguished",
        result_relation="resolution precedes result finalization",
    )


def complete_states() -> tuple[AbilityStateEvidence, ...]:
    return tuple(
        confirmed_state(participant, phase)
        for participant in AbilityParticipant
        for phase in AbilityPhase
    )


def complete_model() -> AbilityModel:
    return AbilityModel(
        states=complete_states(),
        timing=confirmed_timing(),
        scripted_paths=("tutorial no-card override",),
        no_ability_control="selector returned 0xFF and no effect scene was created",
    )


def test_ability_model_requires_both_participants_and_every_phase() -> None:
    states = tuple(
        state
        for state in complete_states()
        if not (
            state.participant is AbilityParticipant.OPPONENT
            and state.phase is AbilityPhase.RESOLVED
        )
    )
    with pytest.raises(WorkspaceError, match="opponent/resolved"):
        replace(complete_model(), states=states).validate()


def test_ui_selection_alone_cannot_satisfy_later_ability_phases() -> None:
    selected_only = tuple(
        confirmed_state(participant, AbilityPhase.SELECTED)
        for participant in AbilityParticipant
    )
    with pytest.raises(WorkspaceError, match="activated"):
        replace(complete_model(), states=selected_only).validate()


def test_ability_model_rejects_duplicate_participant_phase() -> None:
    duplicate = (
        *complete_states(),
        confirmed_state(AbilityParticipant.PLAYER, AbilityPhase.USED),
    )
    with pytest.raises(WorkspaceError, match="duplicate Ability state"):
        replace(complete_model(), states=duplicate).validate()


def test_ability_state_requires_confirmed_authoritative_evidence() -> None:
    state = replace(
        confirmed_state(AbilityParticipant.PLAYER, AbilityPhase.ACTIVATED),
        confidence=Confidence.PROBABLE,
    )
    with pytest.raises(WorkspaceError, match="must be confirmed"):
        state.validate()


def test_ability_phases_must_use_canonical_order_per_participant() -> None:
    states = list(complete_states())
    states[0], states[1] = states[1], states[0]
    with pytest.raises(WorkspaceError, match="canonical order"):
        replace(complete_model(), states=tuple(states)).validate()


def test_complete_ability_model_validates() -> None:
    complete_model().validate()
