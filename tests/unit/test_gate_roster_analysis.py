from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    load_gate_roster_authoring_document,
)
from bakugan_ds.gates.roster_analysis import (
    REFERENCE_CASE_COUNT,
    build_roster_analysis,
    find_exact_runtime_duplicate_groups,
    validate_hard_duplicate_classes,
    write_roster_analysis,
)
from bakugan_ds.gates.roster_metadata import load_gate_roster_metadata

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
POWER_IDS = set(range(1, 16))
ATTRIBUTE_IDS = set(range(40, 62))
LIVE_IDS = sorted(POWER_IDS | ATTRIBUTE_IDS | {19})
LEGACY_IDS = sorted(set(range(1, 104)) - set(LIVE_IDS))


def test_whole_roster_analysis_uses_complete_deterministic_matrix() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)

    report = build_roster_analysis(records, metadata)

    assert report["format"] == "bakugan-ds-gate-milestone-6e-roster-analysis"
    assert report["record_count"] == 103
    assert report["live_card_ids"] == LIVE_IDS
    assert report["legacy_passthrough_count"] == 65
    assert report["matrix"]["case_count_per_record"] == REFERENCE_CASE_COUNT == 1080
    assert report["matrix"]["core_g"] == [190, 400, 525, 650, 695]
    assert report["matrix"]["attributes"] == [0, 1, 2, 3, 4, 5]
    assert report["matrix"]["landing_contexts"] == ["missing", "nonwinning", "winning"]

    by_id = {item["card_id"]: item for item in report["cards"]}
    juggernoid = by_id[19]
    assert juggernoid["valid_case_count"] == 1080
    assert juggernoid["fallback_case_count"] == 0
    assert juggernoid["effective_gate_bonus"]["minimum"] == 74
    assert juggernoid["effective_gate_bonus"]["maximum"] == 184
    assert juggernoid["effective_gate_bonus"]["owner_maximum"] == 184
    assert juggernoid["effective_gate_bonus"]["non_owner_maximum"] == 144
    assert juggernoid["out_of_tier"] is True

    assert report["hard_duplicate_groups"] == []
    assert report["identical_evaluation_groups"] == []
    assert report["identity_conflicts"] == []
    assert report["legacy_duplicate_groups"] == [LEGACY_IDS]
    assert report["archetype_distribution"]["comeback"] == 1
    assert report["archetype_distribution"]["power"] == 15
    assert report["archetype_distribution"]["attribute"] == 22
    assert report["archetype_distribution_warnings"]


def test_exact_runtime_duplicate_detection_ignores_card_id_but_separates_legacy() -> None:
    juggernoid = approved_juggernoid_record()
    duplicate = replace(juggernoid, card_id=20)

    assert find_exact_runtime_duplicate_groups((juggernoid, duplicate)) == ((19, 20),)
    assert find_exact_runtime_duplicate_groups(
        (juggernoid, duplicate), include_legacy=True
    ) == ((19, 20),)


def test_hard_duplicate_validator_rejects_exact_and_identical_live_classes() -> None:
    report = {
        "hard_duplicate_groups": [[19, 20]],
        "identical_evaluation_groups": [],
    }
    with pytest.raises(WorkspaceError, match="exact runtime duplicate"):
        validate_hard_duplicate_classes(report)

    report = {
        "hard_duplicate_groups": [],
        "identical_evaluation_groups": [[19, 20]],
    }
    with pytest.raises(WorkspaceError, match="identical evaluation"):
        validate_hard_duplicate_classes(report)


def test_roster_analysis_writer_is_deterministic(tmp_path: Path) -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA)
    output = tmp_path / "roster-analysis.json"

    write_roster_analysis(output, records, metadata)
    first = output.read_bytes()
    write_roster_analysis(output, records, metadata)

    assert output.read_bytes() == first
    assert first.endswith(b"\n")
    payload = json.loads(first)
    assert payload["record_count"] == 103
