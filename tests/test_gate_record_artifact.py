from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.discovery import Presence, load_discovery_artifact

ARTIFACT = Path("analysis/gates/system2-record-v1.json")
SCHEMA = Path("schemas/gate-system2-v1.schema.json")


def test_record_artifact_has_exact_geometry_and_no_unresolved_fields() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert payload["header"]["header_size"] == 32
    assert payload["header"]["record_size"] == 40
    assert payload["header"]["record_count"] == 103
    assert payload["header"]["payload_size"] == 4120
    assert payload["unresolved"] == []


def test_record_offsets_fill_exactly_40_bytes_without_overlap() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    offsets = {name: offset for name, _kind, offset in payload["record_fields"]}
    assert offsets["card_id"] == 0
    assert offsets["battle_weights"] == 14
    assert offsets["reserved"] == 38


def test_authoring_schema_requires_103_closed_records() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    records = schema["properties"]["records"]
    record = schema["$defs"]["record"]
    assert records["minItems"] == records["maxItems"] == 103
    assert record["additionalProperties"] is False
    assert record["properties"]["reserved"]["const"] == 0
    assert record["properties"]["preferred_type"]["enum"][-1] == 255


def test_record_artifact_satisfies_common_readiness_fields() -> None:
    artifact = load_discovery_artifact(ARTIFACT)
    assert artifact.domain == "system2-record-v1"
    assert artifact.unresolved == ()
    for name in (
        "g2dt_header_geometry",
        "gate_record_geometry",
        "authoring_schema",
        "serializer",
        "validator",
        "calculation_trace_format",
    ):
        field = artifact.field_by_name(name)
        assert field is not None
        assert field.presence is Presence.PRESENT
        field.validate(required=True, allow_absent=False, allow_deferred=False)
