from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.discovery import Presence, RuntimeFieldEvidence
from bakugan_ds.gates.landing import (
    LandingContext,
    LandingFieldEvidence,
    LandingOutcome,
)
from bakugan_ds.gates.model import Confidence


def confirmed_field(name: str) -> LandingFieldEvidence:
    return LandingFieldEvidence(
        name=name,
        value_domain="confirmed unsigned-byte codes",
        participant_source="throw controller active participant byte",
        owner_structure="throw controller",
        access="confirmed byte offset",
        width_bits=8,
        signed=False,
        initialization="throw-controller construction",
        reset="new throw controller",
        scripted_behavior="scripted source path documented",
        confidence=Confidence.CONFIRMED,
        evidence="exact executable and controlled runtime evidence",
    )


def deferred_arena() -> RuntimeFieldEvidence:
    return RuntimeFieldEvidence(
        name="arena_id",
        presence=Presence.DEFERRED,
        width_bits=None,
        signed=None,
        owner_structure="arena context not yet mapped",
        access="deferred by the approved Milestone 6B exception",
        initialization="not confirmed",
        mutations=("not confirmed",),
        lifetime="not confirmed",
        reset="not confirmed",
        player_ai_behavior="not confirmed",
        scripted_behavior="not confirmed",
        confidence=Confidence.CANDIDATE,
        evidence="arena ID is the sole approved discovery deferral",
        allowed_exception=True,
    )


def complete_context() -> LandingContext:
    return LandingContext(
        fields=(
            confirmed_field("landing_result"),
            confirmed_field("shot_condition"),
        ),
        evaluation_boundary=(
            "landing resolver exit after result and participant association commit"
        ),
        arena_id=deferred_arena(),
        scripted_paths=("tutorial and AI source path",),
    )


def test_landing_context_requires_confirmed_result_and_shot_condition() -> None:
    context = replace(
        complete_context(),
        fields=(confirmed_field("landing_result"),),
    )
    with pytest.raises(WorkspaceError, match="shot_condition"):
        context.validate()


def test_landing_context_rejects_duplicate_fields() -> None:
    duplicate = (
        confirmed_field("landing_result"),
        confirmed_field("landing_result"),
        confirmed_field("shot_condition"),
    )
    with pytest.raises(WorkspaceError, match="duplicate landing field"):
        replace(complete_context(), fields=duplicate).validate()


def test_landing_field_requires_confirmed_evidence() -> None:
    field = replace(
        confirmed_field("landing_result"),
        confidence=Confidence.PROBABLE,
    )
    with pytest.raises(WorkspaceError, match="must be confirmed"):
        field.validate()


def test_landing_context_allows_only_deferred_arena_id() -> None:
    complete_context().validate()

    invalid = replace(deferred_arena(), name="landing_result")
    with pytest.raises(WorkspaceError, match="arena_id"):
        replace(complete_context(), arena_id=invalid).validate()


def test_landing_outcomes_include_only_runtime_proven_stand_paths() -> None:
    assert tuple(LandingOutcome) == (
        LandingOutcome.UNOPPOSED_STAND,
        LandingOutcome.BATTLE_STAND,
    )
    assert LandingOutcome.UNOPPOSED_STAND.value == "unopposed_stand"
    assert LandingOutcome.UNOPPOSED_STAND.raw_code == 2
    assert LandingOutcome.BATTLE_STAND.value == "battle_stand"
    assert LandingOutcome.BATTLE_STAND.raw_code == 3
