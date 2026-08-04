from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.discovery import Presence, load_discovery_artifact
from bakugan_ds.gates.timing import EffectPhase, normalize_timing_artifact

ARTIFACT = Path("analysis/gates/effect-timing.json")


def test_committed_timing_artifact_normalizes_all_phases() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    model = normalize_timing_artifact(payload)

    assert tuple(boundary.phase for boundary in model.boundaries) == tuple(EffectPhase)
    assert len(model.boundaries) == 12
    assert all(boundary.component == "overlay_0007" for boundary in model.boundaries)


def test_timing_artifact_satisfies_all_readiness_fields() -> None:
    artifact = load_discovery_artifact(ARTIFACT)
    artifact.validate()

    assert artifact.domain == "effect-timing"
    assert artifact.unresolved == ()
    assert {field.name for field in artifact.fields} == {
        f"timing_{phase.value}" for phase in EffectPhase
    }
    assert all(field.presence is Presence.PRESENT for field in artifact.fields)
    assert all(field.width_bits == 32 for field in artifact.fields)


def test_timing_artifact_records_unique_addresses_and_exact_regions() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    addresses = [boundary["address"] for boundary in payload["boundaries"]]

    assert len(addresses) == len(set(addresses)) == 12
    assert len(payload["exact_regions"]) == 12
    assert {region["phase"] for region in payload["exact_regions"]} == {
        phase.value for phase in EffectPhase
    }


def test_timing_artifact_documents_mutation_and_rollback_for_every_phase() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    for boundary in payload["boundaries"]:
        assert boundary["valid_fields"]
        assert boundary["mutations_allowed"].strip()
        assert boundary["scripted_bypass"].strip()
        assert boundary["rollback"].strip()
        assert boundary["confidence"] == "confirmed"


def test_timing_artifact_commits_no_runtime_binary_material() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = payload["runtime_capture_source"]

    assert all(value is False for value in source.values())
    assert ARTIFACT.read_text(encoding="utf-8").endswith("\n")
