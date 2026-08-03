from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.discovery import Presence, load_discovery_artifact
from bakugan_ds.gates.landing import LandingOutcome, normalize_landing_artifact

ARTIFACT = Path("analysis/gates/landing-and-shot-context.json")


def test_committed_landing_artifact_normalizes_complete_context() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    context = normalize_landing_artifact(payload)

    assert context.field_by_name("landing_result").access == (
        "throw controller +0x1D2"
    )
    assert context.field_by_name("shot_condition").access == (
        "shot controller +0x6198 copied to throw controller +0x1DF"
    )
    assert context.arena_id.name == "arena_id"
    assert context.arena_id.presence is Presence.DEFERRED


def test_landing_artifact_satisfies_readiness_with_arena_only_deferred() -> None:
    artifact = load_discovery_artifact(ARTIFACT)
    artifact.validate()

    assert artifact.domain == "landing-and-shot-context"
    assert artifact.unresolved == ("arena_id",)
    assert {field.name for field in artifact.fields} == {
        "landing_result",
        "shot_condition",
        "arena_id",
    }
    assert artifact.field_by_name("landing_result") is not None
    assert artifact.field_by_name("shot_condition") is not None
    arena = artifact.field_by_name("arena_id")
    assert arena is not None
    assert arena.presence is Presence.DEFERRED
    assert arena.allowed_exception is True


def test_landing_artifact_records_two_named_stand_outcomes() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    controls = {
        control["outcome"]: control
        for control in payload["runtime_controls"]
        if control["outcome"] is not None
    }

    assert set(controls) == {
        LandingOutcome.UNOPPOSED_STAND.value,
        LandingOutcome.BATTLE_STAND.value,
    }
    assert controls[LandingOutcome.UNOPPOSED_STAND.value]["landing_result"] == 2
    assert controls[LandingOutcome.UNOPPOSED_STAND.value]["active_participant"] == 1
    assert controls[LandingOutcome.BATTLE_STAND.value]["landing_result"] == 3
    assert controls[LandingOutcome.BATTLE_STAND.value]["active_participant"] == 0
    assert all(control["shot_condition"] == 0 for control in controls.values())


def test_landing_artifact_preserves_unnamed_codes() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    codes = payload["outcome_codes"]

    assert codes["0"]["label"] is None
    assert "tutorial" in codes["0"]["runtime_observation"]
    assert codes["1"]["label"] == "gate_card_won"
    assert codes["2"]["label"] == LandingOutcome.UNOPPOSED_STAND.value
    assert codes["3"]["label"] == LandingOutcome.BATTLE_STAND.value
    assert codes["4"]["label"] is None


def test_landing_artifact_records_tutorial_retry_path() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    tutorial = next(
        control
        for control in payload["runtime_controls"]
        if control.get("path") == "clean battery-save tutorial guided throw and retry"
    )

    assert tutorial["controller"] == "0x022F1E80"
    assert tutorial["copy_boundary"] == "0x0226B5C4"
    assert tutorial["shot_condition"] == 0
    assert tutorial["landing_result"] == 0
    assert tutorial["attachment_index"] == 0
    assert tutorial["throw_fields_zero_after_retry_reset"] is True


def test_landing_artifact_preserves_evidence_boundary() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    payload = json.loads(text)
    source = payload["runtime_capture_source"]

    assert text.endswith("\n")
    assert payload["status"] == "complete_with_arena_id_deferred"
    assert payload["unresolved"] == ["arena_id"]
    assert source["raw_debugger_logs_committed"] is False
    assert source["save_or_state_committed"] is False
    assert source["screenshots_committed"] is False
    for key, value in source.items():
        if key.endswith("_sha256"):
            assert len(value) == 64


def test_landing_artifact_preserves_exact_regions_and_call_inventory() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert len(payload["exact_regions"]) == 12
    inventory = payload["direct_call_inventory"]
    assert inventory["throw_controller_constructor_0x02252730"] == [
        "0x0226BDAC"
    ]
    assert inventory["primary_landing_evaluator_0x02259AF0"] == [
        "0x02255670"
    ]
    assert inventory["alternate_landing_evaluator_0x0225A278"] == [
        "0x02255680"
    ]
    assert len(inventory["arena_descriptor_attachment_0x02262768"]) == 13
