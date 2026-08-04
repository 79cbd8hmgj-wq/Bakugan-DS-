from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    legacy_passthrough_record,
    load_authoring_document,
    validate_milestone_6c_roster,
)
from bakugan_ds.gates.record import TRAILER_SIZE, build_trailer, parse_trailer

PROTOTYPE_PATH = Path("config/gates/milestone-6c-system2-v1.json")


def test_approved_roster_has_one_live_record() -> None:
    records = load_authoring_document(PROTOTYPE_PATH)
    assert len(records) == 103
    live = [record for record in records if record.archetype != 0]
    assert [record.card_id for record in live] == [19]
    juggernoid = live[0]
    assert juggernoid == approved_juggernoid_record()
    assert juggernoid.flat_bonus_g == 60
    assert juggernoid.percent_q8_8 == 20
    assert juggernoid.attribute_modifiers == (0, 30, 0, 0, 0, 0)
    assert juggernoid.battle_weights == (50, 30, 30, 30, 30, 30)
    assert juggernoid.effect_value == 40


def test_other_records_are_canonical_legacy_passthrough() -> None:
    records = load_authoring_document(PROTOTYPE_PATH)
    for record in records:
        if record.card_id != 19:
            assert record == legacy_passthrough_record(record.card_id)


def test_approved_roster_builds_repeatable_exact_trailer() -> None:
    records = load_authoring_document(PROTOTYPE_PATH)
    first = build_trailer(records)
    second = build_trailer(load_authoring_document(PROTOTYPE_PATH))
    assert first == second
    assert len(first) == TRAILER_SIZE == 4152
    header, parsed = parse_trailer(first)
    assert parsed == records
    assert header.record_count == 103
    assert len(hashlib.sha256(first).hexdigest()) == 64


def test_changed_prototype_changes_hash_and_fails_semantic_validator() -> None:
    records = list(load_authoring_document(PROTOTYPE_PATH))
    original = build_trailer(tuple(records))
    records[18] = replace(records[18], flat_bonus_g=61)
    changed = build_trailer(tuple(records))
    assert hashlib.sha256(changed).digest() != hashlib.sha256(original).digest()
    with pytest.raises(WorkspaceError, match="Gate 19"):
        validate_milestone_6c_roster(tuple(records))


def test_authoring_loader_rejects_unknown_or_missing_record_fields(
    tmp_path: Path,
) -> None:
    payload = json.loads(PROTOTYPE_PATH.read_text(encoding="utf-8"))
    payload["records"][0]["unknown"] = 1
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WorkspaceError, match="record fields"):
        load_authoring_document(path)

    payload = json.loads(PROTOTYPE_PATH.read_text(encoding="utf-8"))
    del payload["records"][0]["flags"]
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WorkspaceError, match="record fields"):
        load_authoring_document(path)


def test_authoring_loader_rejects_boolean_integer(tmp_path: Path) -> None:
    payload = json.loads(PROTOTYPE_PATH.read_text(encoding="utf-8"))
    payload["records"][0]["flat_bonus_g"] = True
    path = tmp_path / "boolean.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WorkspaceError, match="integer"):
        load_authoring_document(path)
