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
    participant: AbilityParticipant, phase: AbilityPhase
) -> AbilityStateEvidence:
    return AbilityStateEvidence(
        participant=participant,
        phase=phase,
        owner_structure=f"{participant.value} authoritative Ability state",
        access="participant or effect-scene field",
        width_bits=8,
        value_domain="confirmed executable value domain",
        initialization="confirmed constructor boundary",
        mutation="confirmed gameplay mutation",
        reset="confirmed participant or scene reset",
        confidence=Confidence.CONFIRMED,
        evidence="exact executable and controlled runtime evidence",
    )


def confirmed_model() -> AbilityModel:
    return AbilityModel(
        states=tuple(
            confirmed_state(participant, phase)
            for participant in AbilityParticipant
            for phase in AbilityPhase
        ),
        timing=AbilityTimingEvidence(
            selection_boundary="selection boundary",
            activation_boundary="activation boundary",
            resolution_boundary="resolution boundary",
            gate_bonus_relation="after Gate bonus construction",
            battle_type_relation="separate from battle-type selection",
            minigame_relation="immediate or deferred before use",
            result_relation="before ordinary result bookkeeping",
        ),
        scripted_paths=("scripted no-card path", "special-card branch"),
        no_ability_control="selector returned 0xFF with every slot unavailable",
    )


def test_ability_model_requires_both_participants_and_every_phase() -> None:
    model = confirmed_model()

    model.validate()
    assert (
        model.state_for(AbilityParticipant.PLAYER, AbilityPhase.RESOLVED).phase
        is AbilityPhase.RESOLVED
    )
    assert (
        model.state_for(AbilityParticipant.OPPONENT, AbilityPhase.USED).participant
        is AbilityParticipant.OPPONENT
    )


def test_ability_model_rejects_missing_phase() -> None:
    model = confirmed_model()

    with pytest.raises(WorkspaceError, match="every participant and phase"):
        replace(model, states=model.states[:-1]).validate()


def test_ability_model_rejects_probable_state() -> None:
    model = confirmed_model()
    probable = replace(model.states[0], confidence=Confidence.PROBABLE)

    with pytest.raises(WorkspaceError, match="must be confirmed"):
        replace(model, states=(probable, *model.states[1:])).validate()


def test_ability_model_requires_canonical_phase_order() -> None:
    model = confirmed_model()
    states = list(model.states)
    states[0], states[1] = states[1], states[0]

    with pytest.raises(WorkspaceError, match="canonical order"):
        replace(model, states=tuple(states)).validate()


def test_ability_model_rejects_duplicate_scripted_paths() -> None:
    model = confirmed_model()

    with pytest.raises(WorkspaceError, match="must be unique"):
        replace(model, scripted_paths=("same", "same")).validate()


def test_ability_state_rejects_presentation_only_evidence() -> None:
    state = replace(
        confirmed_state(AbilityParticipant.PLAYER, AbilityPhase.ACTIVATED),
        mutation="",
        evidence="UI highlight only",
    )

    with pytest.raises(WorkspaceError, match="mutation must be nonempty"):
        state.validate()
