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
    assert (
        model.state_for(AbilityParticipant.PLAYER, AbilityPhase.SELECTED).access
        == "selection +0x53; descriptor +0x11 slot and +0x12 ID"
    )
    assert (
        model.state_for(AbilityParticipant.OPPONENT, AbilityPhase.RESOLVED).access
        == "scene +0x4D terminal 20"
    )


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


def test_ability_artifact_has_use_and_no_card_runtime_controls() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert payload["complete_runtime_ability_use_capture_committed"] is True
    runtime = payload["runtime_ability_use_capture"]
    assert runtime["profile_id"] == "b6re_rev0"
    assert runtime["selected_slot"] in (0, 1, 2)
    assert runtime["selected_ability_id"] > 0
    assert runtime["slot_state_before"] == 0
    assert runtime["slot_state_after_selection"] == 2
    assert runtime["activation_pc"] == 0x0221A6B4
    assert runtime["resolution_pc"] == 0x0221B8D0
    assert runtime["terminal_scene_state"] == 20
    assert runtime["emulator_alive_after_resolution"] is True
    assert "0xFF" in payload["no_ability_control"]


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
