from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.discovery import Presence, load_discovery_artifact
from bakugan_ds.gates.gate_state import GateStateKind, normalize_gate_state_artifact

ARTIFACT = Path("analysis/gates/gate-reuse-and-removal.json")
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


def test_gate_state_artifact_normalizes_confirmed_lifecycle() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    model = normalize_gate_state_artifact(payload)

    assert (
        model.state_for(GateStateKind.ACTIVATION_COUNT).presence
        is Presence.ABSENT
    )
    assert model.state_for(GateStateKind.REUSABLE).presence is Presence.PRESENT
    assert model.state_for(GateStateKind.CAPTURED).presence is Presence.PRESENT
    assert model.state_for(GateStateKind.REMOVED).presence is Presence.PRESENT
    assert model.state_for(GateStateKind.RESET).presence is Presence.PRESENT
    assert "activation_count_by_arena_entry[12]" in model.safe_extension_storage


def test_gate_state_artifact_satisfies_common_readiness_fields() -> None:
    artifact = load_discovery_artifact(ARTIFACT)

    assert artifact.domain == "gate-reuse-and-removal"
    assert artifact.unresolved == ()

    activation = artifact.field_by_name("gate_activation_count")
    assert activation is not None
    assert activation.presence is Presence.ABSENT
    activation.validate(required=True, allow_absent=True, allow_deferred=False)

    for name in ("gate_reuse_state", "gate_capture_state", "gate_removal_state"):
        field = artifact.field_by_name(name)
        assert field is not None
        assert field.presence is Presence.PRESENT
        field.validate(required=True, allow_absent=False, allow_deferred=False)


def test_gate_state_artifact_preserves_evidence_boundary() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert text.endswith("\n")
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))
    assert payload["safe_extension_storage"].endswith(
        "and is not implemented during Milestone 6B."
    )
    assert any(
        item["name"] == "gate_activation_count"
        and item["presence"] == "absent"
        and item["replacement_plan"]
        for item in payload["fields"]
    )
    assert any(
        item["name"] == "gate_removal_state"
        and "arena entry +0x02" in item["access"]
        for item in payload["fields"]
    )
