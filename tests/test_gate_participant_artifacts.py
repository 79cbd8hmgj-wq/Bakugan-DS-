from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.discovery import Presence, load_discovery_artifact
from bakugan_ds.gates.participants import (
    ParticipantContext,
    ParticipantControl,
    ParticipantRole,
    TargetMode,
    normalize_participant_artifact,
)

ARTIFACT = Path("analysis/gates/ownership-and-participants.json")
DETAIL = Path("analysis/gates/effect-targeting-rules.json")
FORBIDDEN_KEYS = {
    "complete_gate_table",
    "ram_dump",
    "raw_bytes",
    "save_state",
    "screenshot",
}


def walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_normalized_participant_artifact_satisfies_readiness_fields() -> None:
    artifact = load_discovery_artifact(ARTIFACT)

    assert artifact.domain == "ownership-and-participants"
    assert artifact.unresolved == ()
    for name in (
        "gate_owner",
        "challenging_participant",
        "combatant_identity",
        "human_ai_identity",
        "effect_target",
    ):
        field = artifact.field_by_name(name)
        assert field is not None
        assert field.presence is Presence.PRESENT
        field.validate(required=True, allow_absent=False, allow_deferred=False)


def test_participant_artifact_defines_all_roles_and_target_modes() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    model = normalize_participant_artifact(payload)

    assert {entry.role for entry in model.entries} == set(ParticipantRole)
    assert {rule.mode for rule in model.target_modes} == set(TargetMode)
    assert len(model.scripted_paths) == 3


def test_committed_ai_owned_control_matches_target_resolver() -> None:
    context = ParticipantContext(
        gate_owner=1,
        defender=1,
        challenger=0,
        controls=(
            ParticipantControl(participant_index=0, is_ai=False),
            ParticipantControl(participant_index=1, is_ai=True),
        ),
        winner_record_index=1,
    )

    assert context.resolve(TargetMode.OWNER) == (1,)
    assert context.resolve(TargetMode.DEFENDER) == (1,)
    assert context.resolve(TargetMode.CHALLENGER) == (0,)
    assert context.resolve(TargetMode.BOTH) == (1, 0)
    assert context.resolve(TargetMode.HUMAN) == (0,)
    assert context.resolve(TargetMode.AI) == (1,)
    assert context.resolve(TargetMode.WINNER) == (0,)
    assert context.resolve(TargetMode.LOSER) == (1,)


def test_targeting_artifacts_preserve_evidence_boundary() -> None:
    for path in (ARTIFACT, DETAIL):
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        assert text.endswith("\n")
        assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))

    detail = json.loads(DETAIL.read_text(encoding="utf-8"))
    assert detail["confidence_boundary"].startswith(
        "The source identities and result index are confirmed"
    )
    assert {item["mode"] for item in detail["target_modes"]} == {
        mode.value for mode in TargetMode
    }
    assert detail["fail_closed_rules"]
