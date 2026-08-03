from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.discovery import Presence, load_discovery_artifact
from bakugan_ds.gates.history import normalize_history_artifact

ARTIFACT = Path("analysis/gates/battle-history-and-rng.json")
FORBIDDEN_KEYS = {
    "complete_gate_table",
    "debugger_log",
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


def test_committed_history_artifact_normalizes() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    model = normalize_history_artifact(payload)
    assert model.rng.function.runtime_address == 0x02021A30
    assert model.history.presence is Presence.ABSENT
    assert model.selection.type_count == 6
    assert model.selection.total_max == 1530


def test_history_artifact_satisfies_common_readiness_fields() -> None:
    artifact = load_discovery_artifact(ARTIFACT)
    assert artifact.domain == "battle-history-and-rng"
    assert artifact.unresolved == ()

    weighted_rng = artifact.field_by_name("weighted_rng")
    assert weighted_rng is not None
    assert weighted_rng.presence is Presence.PRESENT
    weighted_rng.validate(required=True, allow_absent=False, allow_deferred=False)

    history = artifact.field_by_name("battle_type_history")
    assert history is not None
    assert history.presence is Presence.ABSENT
    history.validate(required=True, allow_absent=True, allow_deferred=False)


def test_history_artifact_preserves_cache_geometry_and_evidence_boundary() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    payload = json.loads(text)
    layout = payload["future_history_layout"]

    assert text.endswith("\n")
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))
    assert layout["previous_type_offset"] == 0x38
    assert layout["valid_count_offset"] == 0x3B
    assert layout["reserved_start_offset"] == 0x3C
    assert payload["unresolved"] == []
