from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.discovery import Presence, load_discovery_artifact
from bakugan_ds.gates.match_state import CounterOwner, normalize_match_state_artifact

ARTIFACT = Path("analysis/gates/match-score-and-capture.json")
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


def test_match_state_artifact_normalizes_complete_confirmed_model() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    model = normalize_match_state_artifact(payload)

    assert model.victory_threshold == 3
    assert model.score_for(CounterOwner.PLAYER).access.endswith("+0xEE")
    assert model.score_for(CounterOwner.OPPONENT).access.endswith("+0xEE")
    assert "+0xF4" in model.capture_for(CounterOwner.PLAYER).access
    assert "+0xF4" in model.capture_for(CounterOwner.OPPONENT).access


def test_match_state_artifact_satisfies_common_readiness_fields() -> None:
    artifact = load_discovery_artifact(ARTIFACT)

    assert artifact.domain == "match-score-and-capture"
    assert artifact.unresolved == ()
    for name in ("match_score", "captured_gate_count", "victory_threshold"):
        field = artifact.field_by_name(name)
        assert field is not None
        assert field.presence is Presence.PRESENT
        field.validate(required=True, allow_absent=False, allow_deferred=False)


def test_match_state_artifact_preserves_evidence_boundary() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert text.endswith("\n")
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))
    assert any(
        item["name"] == "match_score" and "+0xEE" in item["access"]
        for item in payload["fields"]
    )
    assert any(
        item["name"] == "captured_gate_count" and "+0xF4" in item["access"]
        for item in payload["fields"]
    )
