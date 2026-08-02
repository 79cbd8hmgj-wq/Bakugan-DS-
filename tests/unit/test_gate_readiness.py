from __future__ import annotations

import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.discovery import (
    DiscoveryArtifact,
    Presence,
    RuntimeFieldEvidence,
)
from bakugan_ds.gates.model import Confidence
from bakugan_ds.gates.readiness import (
    Requirement,
    evaluate_readiness,
    load_requirements,
)


def field(
    name: str,
    *,
    presence: Presence = Presence.PRESENT,
    confidence: Confidence = Confidence.CONFIRMED,
    allowed_exception: bool = False,
    replacement_plan: str = "",
) -> RuntimeFieldEvidence:
    width_bits = 8 if presence is Presence.PRESENT else None
    signed = False if presence is Presence.PRESENT else None
    return RuntimeFieldEvidence(
        name=name,
        presence=presence,
        width_bits=width_bits,
        signed=signed,
        owner_structure="battle object" if presence is Presence.PRESENT else "unresolved",
        access="+0x20" if presence is Presence.PRESENT else "unresolved",
        initialization="constructor" if presence is Presence.PRESENT else "unresolved",
        mutations=("capture",) if presence is Presence.PRESENT else ("unresolved",),
        lifetime="match",
        reset="match reset",
        player_ai_behavior="shared" if presence is Presence.PRESENT else "unresolved",
        scripted_behavior="documented" if presence is Presence.PRESENT else "unresolved",
        confidence=confidence,
        evidence="controlled runtime evidence",
        replacement_plan=replacement_plan,
        allowed_exception=allowed_exception,
    )


def artifact(domain: str, *fields: RuntimeFieldEvidence) -> DiscoveryArtifact:
    return DiscoveryArtifact(domain=domain, fields=fields, checks=(), unresolved=tuple(
        item.name for item in fields if item.presence is Presence.DEFERRED
    ))


def test_readiness_allows_only_arena_id_to_be_deferred() -> None:
    requirements = (
        Requirement("gate_owner", "ownership", "gate_owner", False, False),
        Requirement("arena_id", "landing", "arena_id", False, True),
    )
    artifacts = {
        "ownership": artifact("ownership", field("gate_owner")),
        "landing": artifact(
            "landing",
            field(
                "arena_id",
                presence=Presence.DEFERRED,
                confidence=Confidence.PROBABLE,
                allowed_exception=True,
            ),
        ),
    }

    result = evaluate_readiness(requirements, artifacts)

    assert result.ready is True
    assert result.confirmed == ("gate_owner",)
    assert result.deferred == ("arena_id",)
    assert result.failures == ()


def test_readiness_rejects_probable_required_field() -> None:
    requirements = (
        Requirement("gate_owner", "ownership", "gate_owner", False, False),
        Requirement("arena_id", "landing", "arena_id", False, True),
    )
    artifacts = {
        "ownership": artifact(
            "ownership",
            field("gate_owner", confidence=Confidence.PROBABLE),
        ),
        "landing": artifact(
            "landing",
            field(
                "arena_id",
                presence=Presence.DEFERRED,
                confidence=Confidence.CANDIDATE,
                allowed_exception=True,
            ),
        ),
    }

    result = evaluate_readiness(requirements, artifacts)

    assert result.ready is False
    assert any(item.requirement == "gate_owner" for item in result.failures)


def test_readiness_rejects_missing_artifact() -> None:
    requirements = (
        Requirement("gate_owner", "ownership", "gate_owner", False, False),
        Requirement("arena_id", "landing", "arena_id", False, True),
    )

    result = evaluate_readiness(requirements, {})

    assert result.ready is False
    assert {item.requirement for item in result.failures} == {"arena_id", "gate_owner"}


def test_readiness_rejects_non_arena_unresolved_entry() -> None:
    requirements = (
        Requirement("gate_owner", "ownership", "gate_owner", False, False),
        Requirement("arena_id", "landing", "arena_id", False, True),
    )
    artifacts = {
        "ownership": DiscoveryArtifact(
            domain="ownership",
            fields=(field("gate_owner"),),
            checks=(),
            unresolved=("effect_target",),
        ),
        "landing": artifact(
            "landing",
            field(
                "arena_id",
                presence=Presence.DEFERRED,
                confidence=Confidence.PROBABLE,
                allowed_exception=True,
            ),
        ),
    }

    result = evaluate_readiness(requirements, artifacts)

    assert result.ready is False
    assert any(item.requirement == "effect_target" for item in result.failures)


def test_requirement_rejects_deferred_non_arena_field() -> None:
    requirement = Requirement(
        name="difficulty",
        artifact="difficulty-context",
        field="difficulty",
        allow_absent=False,
        allow_deferred=True,
    )

    with pytest.raises(WorkspaceError, match="only arena_id"):
        requirement.validate()


def test_load_requirements_rejects_duplicate_names(tmp_path: Path) -> None:
    path = tmp_path / "requirements.json"
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "requirements": [
                    {
                        "allow_absent": False,
                        "allow_deferred": False,
                        "artifact": "ownership",
                        "field": "gate_owner",
                        "name": "gate_owner",
                    },
                    {
                        "allow_absent": False,
                        "allow_deferred": False,
                        "artifact": "ownership",
                        "field": "gate_owner",
                        "name": "gate_owner",
                    },
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceError, match="duplicate requirement"):
        load_requirements(path)


def test_committed_manifest_has_arena_as_only_deferred_requirement() -> None:
    requirements = load_requirements(
        Path("analysis/gates/milestone-6b-requirements.json")
    )

    deferred = tuple(item.name for item in requirements if item.allow_deferred)
    names = {item.name for item in requirements}

    assert deferred == ("arena_id",)
    assert {
        "gate_owner",
        "challenging_participant",
        "combatant_identity",
        "human_ai_identity",
        "effect_target",
        "match_score",
        "captured_gate_count",
        "victory_threshold",
        "gate_activation_count",
        "gate_reuse_state",
        "gate_capture_state",
        "gate_removal_state",
        "battle_type_history",
        "weighted_rng",
        "ability_available",
        "ability_selected",
        "ability_used",
        "ability_resolved",
        "landing_result",
        "shot_condition",
        "difficulty",
        "arena_id",
    } <= names
