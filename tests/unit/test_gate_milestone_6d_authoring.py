from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    build_milestone_6d_balance_report,
    legacy_passthrough_record,
    load_milestone_6d_authoring_document,
    validate_milestone_6d_roster,
    write_milestone_6d_balance_report,
)
from bakugan_ds.gates.record import (
    GateArchetype,
    GateConditionId,
    GateEffectId,
    GateTargetMode,
    GateTimingPhase,
    parse_record,
    serialize_record,
)

AUTHORING = Path("config/gates/milestone-6d-system2-v1.json")


def test_milestone_6d_semantic_ids_are_frozen() -> None:
    assert [int(item) for item in GateArchetype] == list(range(8))
    assert int(GateConditionId.LANDING_GATE_CARD_WON) == 7
    assert int(GateEffectId.SUBTRACT_MAGNITUDE_G) == 2
    assert int(GateTargetMode.GATE_NON_OWNER) == 2
    assert int(GateTimingPhase.PRE_GATE_CALCULATION) == 0


def test_signed_effect_values_round_trip_through_record_bytes() -> None:
    record = replace(
        legacy_passthrough_record(7),
        effect_value=-40,
        drawback_value=-25,
        secondary_value=-10,
    )
    decoded = parse_record(serialize_record(record))
    assert decoded.effect_value == -40
    assert decoded.drawback_value == -25
    assert decoded.secondary_value == -10


def test_milestone_6d_authoring_keeps_only_juggernoid_live() -> None:
    records = load_milestone_6d_authoring_document(AUTHORING)
    assert len(records) == 103
    assert records[18] == approved_juggernoid_record()
    assert [record.card_id for record in records if record.archetype != 0] == [19]
    assert all(
        record == legacy_passthrough_record(record.card_id)
        for record in records
        if record.card_id != 19
    )


def test_milestone_6d_rejects_an_extra_live_record() -> None:
    records = list(load_milestone_6d_authoring_document(AUTHORING))
    records[0] = replace(approved_juggernoid_record(), card_id=1)
    with pytest.raises(WorkspaceError, match="canonical legacy passthrough"):
        validate_milestone_6d_roster(tuple(records))


def test_balance_report_is_deterministic_and_integer_only(tmp_path: Path) -> None:
    records = load_milestone_6d_authoring_document(AUTHORING)
    first = build_milestone_6d_balance_report(records)
    second = build_milestone_6d_balance_report(records)
    assert first == second
    assert first["live_card_ids"] == [19]
    assert first["legacy_passthrough_count"] == 102
    card = first["cards"][0]
    assert card["reference_cases"] == 120
    assert isinstance(card["effective_gate_bonus"]["mean_numerator"], int)
    assert isinstance(card["effective_gate_bonus"]["mean_denominator"], int)

    output = tmp_path / "balance.json"
    write_milestone_6d_balance_report(output, records)
    first_bytes = output.read_bytes()
    write_milestone_6d_balance_report(output, records)
    assert output.read_bytes() == first_bytes
    assert json.loads(first_bytes)["valid"] is True
