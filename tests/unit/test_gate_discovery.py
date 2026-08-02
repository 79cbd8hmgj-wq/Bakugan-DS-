from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from bakugan_ds.gates.discovery import (
    BehaviorCheck,
    DiscoveryArtifact,
    Presence,
    RuntimeFieldEvidence,
    load_discovery_artifact,
)

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence


def confirmed_field(name: str = "gate_owner") -> RuntimeFieldEvidence:
    return RuntimeFieldEvidence(
        name=name,
        presence=Presence.PRESENT,
        width_bits=8,
        signed=False,
        owner_structure="battle object",
        access="+0x20",
        initialization="battle constructor",
        mutations=("Gate capture",),
        lifetime="match",
        reset="match reset",
        player_ai_behavior="shared representation",
        scripted_behavior="tutorial override documented",
        confidence=Confidence.CONFIRMED,
        evidence="controlled runtime watchpoint",
    )


def test_required_field_rejects_probable_evidence() -> None:
    field = replace(confirmed_field(), confidence=Confidence.PROBABLE)

    with pytest.raises(WorkspaceError, match="must be confirmed"):
        field.validate(required=True)


def test_deferred_non_arena_field_is_rejected() -> None:
    field = RuntimeFieldEvidence(
        name="difficulty",
        presence=Presence.DEFERRED,
        width_bits=None,
        signed=None,
        owner_structure="unresolved",
        access="unresolved",
        initialization="unresolved",
        mutations=("unresolved",),
        lifetime="persistent",
        reset="profile change",
        player_ai_behavior="unresolved",
        scripted_behavior="unresolved",
        confidence=Confidence.PROBABLE,
        evidence="candidate settings reference",
        allowed_exception=True,
    )

    with pytest.raises(WorkspaceError, match="only arena_id"):
        field.validate(required=True, allow_deferred=True)


def test_confirmed_absent_field_requires_replacement_plan() -> None:
    field = RuntimeFieldEvidence(
        name="battle_type_history",
        presence=Presence.ABSENT,
        width_bits=None,
        signed=None,
        owner_structure="no original field",
        access="none",
        initialization="none",
        mutations=("none",),
        lifetime="match",
        reset="match reset",
        player_ai_behavior="shared absence",
        scripted_behavior="shared absence",
        confidence=Confidence.CONFIRMED,
        evidence="bounded executable scan and runtime controls",
        replacement_plan="",
    )

    with pytest.raises(WorkspaceError, match="replacement plan"):
        field.validate(required=True, allow_absent=True)


def test_confirmed_absent_field_is_valid_with_replacement_plan() -> None:
    field = RuntimeFieldEvidence(
        name="battle_type_history",
        presence=Presence.ABSENT,
        width_bits=None,
        signed=None,
        owner_structure="no original field",
        access="none",
        initialization="none",
        mutations=("none",),
        lifetime="match",
        reset="match reset",
        player_ai_behavior="shared absence",
        scripted_behavior="shared absence",
        confidence=Confidence.CONFIRMED,
        evidence="bounded executable scan and runtime controls",
        replacement_plan="reserve six bytes in the match-local System 2.0 cache",
    )

    field.validate(required=True, allow_absent=True)


def test_discovery_artifact_rejects_duplicate_names() -> None:
    artifact = DiscoveryArtifact(
        domain="ownership-and-participants",
        fields=(confirmed_field(), confirmed_field()),
        checks=(),
        unresolved=(),
    )

    with pytest.raises(WorkspaceError, match="duplicate discovery entry"):
        artifact.validate()


def test_behavior_check_requires_confirmed_evidence_when_required() -> None:
    check = BehaviorCheck(
        name="nitrofs_open",
        confidence=Confidence.CANDIDATE,
        evidence="static call candidate",
    )

    with pytest.raises(WorkspaceError, match="must be confirmed"):
        check.validate(required=True)


def test_load_discovery_artifact_normalizes_fields_and_checks(tmp_path: Path) -> None:
    path = tmp_path / "ownership.json"
    path.write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "confidence": "confirmed",
                        "evidence": "runtime control",
                        "name": "targeting_verified",
                    }
                ],
                "domain": "ownership-and-participants",
                "fields": [
                    {
                        "access": "+0x20",
                        "allowed_exception": False,
                        "confidence": "confirmed",
                        "evidence": "runtime watchpoint",
                        "initialization": "battle constructor",
                        "lifetime": "match",
                        "mutations": ["capture"],
                        "name": "gate_owner",
                        "owner_structure": "battle object",
                        "player_ai_behavior": "shared",
                        "presence": "present",
                        "replacement_plan": "",
                        "reset": "match reset",
                        "scripted_behavior": "override documented",
                        "signed": False,
                        "width_bits": 8,
                    }
                ],
                "format_version": 1,
                "unresolved": [],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    artifact = load_discovery_artifact(path)

    assert artifact.domain == "ownership-and-participants"
    assert artifact.fields[0].name == "gate_owner"
    assert artifact.checks[0].name == "targeting_verified"
