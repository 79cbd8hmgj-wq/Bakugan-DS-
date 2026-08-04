from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.difficulty import normalize_difficulty_artifact
from bakugan_ds.gates.discovery import Presence, load_discovery_artifact

ARTIFACT = Path("analysis/gates/difficulty-context.json")


def test_committed_difficulty_artifact_normalizes_confirmed_values() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    evidence = normalize_difficulty_artifact(payload)

    assert evidence.owner_structure == (
        "shared Battle Arena configuration rooted at 0x020D433C"
    )
    assert evidence.width_bits == 8
    assert [(value.value, value.label) for value in evidence.values] == [
        (0, "easy"),
        (1, "normal"),
    ]
    assert len(evidence.ai_consumers) == 2


def test_difficulty_artifact_satisfies_readiness_field() -> None:
    artifact = load_discovery_artifact(ARTIFACT)
    artifact.validate()

    assert artifact.domain == "difficulty-context"
    assert artifact.unresolved == ()
    assert {field.name for field in artifact.fields} == {"difficulty"}
    field = artifact.field_by_name("difficulty")
    assert field is not None
    assert field.presence is Presence.PRESENT
    assert field.width_bits == 8
    assert field.signed is False


def test_difficulty_artifact_records_two_controlled_settings() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    controls = {
        control["difficulty_label"]: control
        for control in payload["runtime_controls"]
    }

    assert set(controls) == {"easy", "normal"}
    easy = controls["easy"]
    normal = controls["normal"]
    assert easy["difficulty_after_read"] == 0
    assert normal["difficulty_after_read"] == 1
    assert easy["difficulty_read_pc"] == normal["difficulty_read_pc"] == (
        "0x02232664"
    )
    assert easy["config_base_register"] == normal["config_base_register"] == (
        "r4=0x020D433C"
    )
    assert easy["ai_output_first_three_halfwords"] == [0, 24576, 2730]
    assert normal["ai_output_first_three_halfwords"] == [0, 24576, 4551]
    assert easy["ai_output_prefix_sha256"] != normal["ai_output_prefix_sha256"]
    assert "natural Battle Arena Easy" in easy["execution_path"]
    assert "reversible live write" in normal["execution_path"]


def test_difficulty_artifact_preserves_locked_menu_evidence_boundary() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    text = ARTIFACT.read_text(encoding="utf-8")

    assert text.endswith("\n")
    assert payload["status"] == "complete_with_locked_menu_limitations"
    assert payload["unresolved"] == []
    assert [entry["label"] for entry in payload["values"]] == [
        "easy",
        "normal",
    ]
    assert "hard" not in {entry["label"] for entry in payload["values"]}
    hard_check = next(
        check
        for check in payload["checks"]
        if check["name"] == "hard_value_remains_outside_confirmed_value_list"
    )
    assert hard_check["confidence"] == "confirmed"
    assert "locked" in hard_check["evidence"]
    assert "Persistent profile or save ownership was not established" in (
        payload["fields"][0]["reset"]
    )


def test_difficulty_artifact_records_direct_and_derived_boundaries() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    names = {region["name"] for region in payload["exact_regions"]}

    assert names == {
        "difficulty_selection_decode",
        "difficulty_config_store",
        "difficulty_config_literal",
        "ai_parameter_builder_prologue",
        "difficulty_direct_ai_read",
        "difficulty_derived_output_store",
    }
    assert len(payload["exact_regions"]) == 7
    assert payload["component_images"]["overlay_0001"]["size"] == 65056
    assert payload["component_images"]["overlay_0007"]["size"] == 467360


def test_difficulty_artifact_commits_no_runtime_binary_material() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = payload["runtime_capture_source"]

    assert source["raw_debugger_logs_committed"] is False
    assert source["save_or_state_committed"] is False
    assert source["screenshots_committed"] is False
    for key, value in source.items():
        if key.endswith("_sha256"):
            assert len(value) == 64
