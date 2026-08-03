from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.ability import (
    AbilityParticipant,
    AbilityPhase,
    normalize_ability_artifact,
)
from bakugan_ds.gates.discovery import load_discovery_artifact

ARTIFACT = Path("analysis/gates/ability-card-state.json")


def test_committed_ability_artifact_normalizes_complete_model() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    model = normalize_ability_artifact(payload)

    assert len(model.states) == 12
    assert model.state_for(
        AbilityParticipant.PLAYER, AbilityPhase.SELECTED
    ).access.startswith("+0x53")
    assert model.state_for(
        AbilityParticipant.OPPONENT, AbilityPhase.RESOLVED
    ).access == "+0x4D state 20"


def test_ability_artifact_satisfies_readiness_fields() -> None:
    artifact = load_discovery_artifact(ARTIFACT)
    artifact.validate()

    assert artifact.domain == "ability-card-state"
    assert artifact.unresolved == ()
    required = {
        "ability_available",
        "ability_selected",
        "ability_activated",
        "ability_resolved",
        "ability_used",
        "ability_reset",
    }
    assert {field.name for field in artifact.fields} == required


def test_ability_artifact_has_two_natural_use_captures_and_no_card_control() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert payload["complete_runtime_ability_use_capture_committed"] is True
    captures = {
        capture["capture_id"]: capture
        for capture in payload["runtime_ability_use_captures"]
    }
    assert set(captures) == {"natural_combatant_0", "natural_combatant_1"}

    first = captures["natural_combatant_0"]
    second = captures["natural_combatant_1"]
    assert first["participant_object"] == "0x022E2640"
    assert first["selected_slot"] == 2
    assert first["selected_ability_id"] == 169
    assert first["slot_states_before"] == [0, 0, 0]
    assert first["slot_states_after"] == [0, 0, 2]
    assert second["participant_object"] == "0x022E24E0"
    assert second["selected_slot"] == 0
    assert second["selected_ability_id"] == 126
    assert second["slot_states_before"] == [0, 0, 0]
    assert second["slot_states_after"] == [2, 0, 0]

    for capture in captures.values():
        assert capture["selected_ability_id"] == capture["ability_ids"][
            capture["selected_slot"]
        ]
        assert capture["available_count_before"] == 3
        assert capture["available_count_after"] == 2
        assert capture["requested_slot_state"] == 2
        assert capture["activation_pc"] == "0x0221A6B4"
        assert capture["setter_pc"] == "0x0226A448"
        assert capture["resolution_pc"] == "0x0221B8D0"
        assert capture["terminal_scene_state"] == 20
        assert capture["execution_resumed_after_resolution"] is True

    assert "0xFF" in payload["no_ability_control"]


def test_ability_artifact_preserves_evidence_boundary() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    payload = json.loads(text)
    source = payload["runtime_capture_source"]

    assert text.endswith("\n")
    assert payload["status"] == "complete"
    assert source["raw_debugger_log_committed"] is False
    assert source["save_or_state_committed"] is False
    assert source["screenshot_committed"] is False
    assert len(source["event_log_sha256"]) == 64
    assert len(source["post_resolution_participants_sha256"]) == 64


def test_ability_artifact_preserves_exact_regions_and_call_inventories() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert len(payload["exact_regions"]) == 7
    assert payload["direct_calls"]["ability_state_setter"] == [
        35759912,
        35762480,
        35925196,
        35925296,
        35925412,
        35925536,
        35931660,
    ]
    assert payload["direct_calls"]["ability_slot_selector"] == [
        35918576,
        35918988,
        35931568,
    ]
