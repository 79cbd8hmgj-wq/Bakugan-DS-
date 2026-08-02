from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.discovery import Presence
from bakugan_ds.gates.gate_state import (
    GateStateEvidence,
    GateStateKind,
    GateStateModel,
    normalize_gate_state_artifact,
)
from bakugan_ds.gates.model import Confidence


def confirmed_state(
    kind: GateStateKind,
    *,
    presence: Presence = Presence.PRESENT,
    replacement_plan: str = "",
) -> GateStateEvidence:
    return GateStateEvidence(
        kind=kind,
        presence=presence,
        owner_structure="confirmed owner structure",
        access="confirmed runtime access",
        initialization="confirmed initialization",
        mutations=("confirmed mutation",),
        reset="confirmed reset",
        confidence=Confidence.CONFIRMED,
        evidence="runtime and exact-binary evidence",
        replacement_plan=replacement_plan,
    )


def confirmed_model() -> GateStateModel:
    return GateStateModel(
        states=(
            confirmed_state(
                GateStateKind.ACTIVATION_COUNT,
                presence=Presence.ABSENT,
                replacement_plan="new match-local System 2.0 cache",
            ),
            confirmed_state(GateStateKind.REUSABLE),
            confirmed_state(GateStateKind.CAPTURED),
            confirmed_state(GateStateKind.REMOVED),
            confirmed_state(GateStateKind.RESET),
        ),
        transitions=(
            "participant and session construction",
            "arena placement allocation",
            "result capture and arena removal",
            "active placement transfer",
        ),
        safe_extension_storage=(
            "activation_count_by_arena_entry[12] at future cache offsets 0x2C..0x37"
        ),
    )


def payload() -> dict[str, object]:
    model = confirmed_model()

    def item(state: GateStateEvidence) -> dict[str, object]:
        return {
            "access": state.access,
            "confidence": state.confidence.value,
            "evidence": state.evidence,
            "initialization": state.initialization,
            "kind": state.kind.value,
            "mutations": list(state.mutations),
            "owner_structure": state.owner_structure,
            "presence": state.presence.value,
            "replacement_plan": state.replacement_plan,
            "reset": state.reset,
        }

    return {
        "format_version": 1,
        "profile_id": "b6re_rev0",
        "safe_extension_storage": model.safe_extension_storage,
        "states": [item(state) for state in model.states],
        "transitions": list(model.transitions),
    }


def test_gate_state_accepts_confirmed_lifecycle_and_absence() -> None:
    model = confirmed_model()

    model.validate()
    assert (
        model.state_for(GateStateKind.ACTIVATION_COUNT).presence
        is Presence.ABSENT
    )
    assert model.state_for(GateStateKind.REMOVED).presence is Presence.PRESENT


def test_absent_activation_counter_requires_replacement_plan() -> None:
    state = confirmed_state(
        GateStateKind.ACTIVATION_COUNT,
        presence=Presence.ABSENT,
        replacement_plan="",
    )

    with pytest.raises(WorkspaceError, match="replacement plan"):
        state.validate()


def test_gate_state_rejects_duplicate_or_missing_kind() -> None:
    model = confirmed_model()
    duplicate = replace(model.states[-1], kind=GateStateKind.REMOVED)

    with pytest.raises(WorkspaceError, match="duplicate Gate state kind"):
        replace(model, states=model.states[:-1] + (duplicate,)).validate()

    with pytest.raises(WorkspaceError, match="requires all lifecycle kinds"):
        replace(model, states=model.states[:-1]).validate()


def test_gate_state_rejects_absent_required_lifecycle_state() -> None:
    model = confirmed_model()
    captured = replace(
        model.state_for(GateStateKind.CAPTURED),
        presence=Presence.ABSENT,
        replacement_plan="not allowed for capture state",
    )
    states = tuple(
        captured if state.kind is GateStateKind.CAPTURED else state
        for state in model.states
    )

    with pytest.raises(WorkspaceError, match="captured must be present"):
        replace(model, states=states).validate()


def test_gate_state_rejects_probable_or_deferred_evidence() -> None:
    state = confirmed_state(GateStateKind.REUSABLE)

    with pytest.raises(WorkspaceError, match="must be confirmed"):
        replace(state, confidence=Confidence.PROBABLE).validate()
    with pytest.raises(WorkspaceError, match="cannot be deferred"):
        replace(state, presence=Presence.DEFERRED).validate()


def test_gate_state_rejects_empty_or_duplicate_transitions() -> None:
    model = confirmed_model()

    with pytest.raises(WorkspaceError, match="nonempty"):
        replace(model, transitions=()).validate()
    with pytest.raises(WorkspaceError, match="must be unique"):
        replace(model, transitions=("same", "same")).validate()


def test_normalize_gate_state_artifact_accepts_dual_schema_payload() -> None:
    data = payload()
    data["domain"] = "gate-reuse-and-removal"
    data["fields"] = []
    model = normalize_gate_state_artifact(data)

    assert model.state_for(GateStateKind.REUSABLE).presence is Presence.PRESENT
    assert "0x2C..0x37" in model.safe_extension_storage


def test_normalize_gate_state_artifact_rejects_wrong_profile() -> None:
    data = payload()
    data["profile_id"] = "unsupported"

    with pytest.raises(WorkspaceError, match="unsupported Gate-state artifact profile"):
        normalize_gate_state_artifact(data)
