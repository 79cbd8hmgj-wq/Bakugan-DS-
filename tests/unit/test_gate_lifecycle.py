from __future__ import annotations

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.lifecycle import (
    LifecycleState,
    normalize_lifecycle_capture,
    validate_lifecycle,
)


def transition(sequence: int, start: str, end: str, scenario: str = "normal") -> dict[str, object]:
    return {
        "scenario": scenario,
        "sequence": sequence,
        "from_state": start,
        "to_state": end,
        "trigger": f"trigger-{sequence}",
        "address": "0x02200000",
        "component": "overlay_0007",
        "component_base": "0x02200000",
        "component_offset": 0,
        "owner_source": "participant.owner",
        "card_id_source": "participant.card_id",
        "confidence": "confirmed",
        "evidence": f"evidence-{sequence}",
    }


def test_lifecycle_requires_continuous_transition_chain() -> None:
    payload = {
        "transitions": [
            transition(0, "placed", "selected"),
            transition(1, "activated", "battle_started"),
        ]
    }
    transitions = normalize_lifecycle_capture(payload)
    with pytest.raises(WorkspaceError, match="disconnected"):
        validate_lifecycle(transitions)


def test_lifecycle_rejects_duplicate_sequence_in_scenario() -> None:
    payload = {
        "transitions": [
            transition(0, "placed", "selected"),
            transition(0, "selected", "activated"),
        ]
    }
    with pytest.raises(WorkspaceError, match="duplicate sequence"):
        normalize_lifecycle_capture(payload)


def test_lifecycle_accepts_normal_and_scripted_scenarios() -> None:
    payload = {
        "transitions": [
            transition(0, "placed", "selected"),
            transition(1, "selected", "activated"),
            transition(2, "activated", "battle_started"),
            transition(0, "selected", "activated", "tutorial"),
            transition(1, "activated", "battle_started", "tutorial"),
        ]
    }
    transitions = normalize_lifecycle_capture(payload)
    validate_lifecycle(transitions)
    assert transitions[0].from_state is LifecycleState.PLACED


def test_lifecycle_requires_evidence_and_sources() -> None:
    item = transition(0, "placed", "selected")
    item["evidence"] = ""
    with pytest.raises(WorkspaceError, match="evidence"):
        normalize_lifecycle_capture({"transitions": [item]})


def test_lifecycle_component_offset_must_match_runtime_address() -> None:
    item = transition(0, "selected", "activated")
    item["component"] = "overlay_0007"
    item["component_base"] = "0x02219440"
    item["component_offset"] = "0x00000004"
    item["address"] = "0x02219448"
    with pytest.raises(WorkspaceError, match="component offset"):
        normalize_lifecycle_capture({"transitions": [item]})
