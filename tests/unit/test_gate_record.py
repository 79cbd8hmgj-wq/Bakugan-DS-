from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.record import (
    G2DT_HEADER_SIZE,
    G2DT_MAGIC,
    G2DT_VERSION,
    GATE_RECORD_SIZE,
    GateRecordV1,
    build_trailer,
    parse_record,
    parse_trailer,
    serialize_record,
)


def record(card_id: int) -> GateRecordV1:
    return GateRecordV1(
        card_id=card_id,
        archetype=0,
        flags=0,
        flat_bonus_g=-25 if card_id == 40 else 0,
        percent_q8_8=0x0800,
        attribute_modifiers=(-10, 0, 10, 20, 30, 40),
        battle_weights=(1, 2, 3, 4, 5, 6),
        preferred_type=2,
        condition_id=0,
        effect_id=0,
        drawback_id=0,
        effect_value=0,
        drawback_value=0,
        activation_limit=0,
        fatigue_rate=0,
        target_mode=0,
        timing_phase=0,
        condition_value=0,
        secondary_effect_id=0,
        secondary_condition_id=0,
        secondary_value=0,
        reserved=0,
    )


def test_gate_record_v1_is_exactly_40_bytes() -> None:
    encoded = serialize_record(record(40))
    assert len(encoded) == GATE_RECORD_SIZE == 40
    assert parse_record(encoded).flat_bonus_g == -25


def test_trailer_round_trip_has_exact_geometry_and_crc() -> None:
    encoded = build_trailer(tuple(record(card_id) for card_id in range(1, 104)))
    header, records = parse_trailer(encoded)
    assert encoded[:4] == G2DT_MAGIC
    assert header.version == G2DT_VERSION == 1
    assert header.header_size == G2DT_HEADER_SIZE == 32
    assert header.record_size == GATE_RECORD_SIZE
    assert header.record_count == 103
    assert len(encoded) == 4152
    assert records[39].card_id == 40


def test_trailer_rejects_duplicate_or_unsorted_ids() -> None:
    records = [record(card_id) for card_id in range(1, 104)]
    records[1] = record(1)
    with pytest.raises(WorkspaceError, match="IDs 1 through 103"):
        build_trailer(tuple(records))


def test_record_rejects_nonzero_reserved_and_unsupported_target() -> None:
    with pytest.raises(WorkspaceError, match="reserved"):
        serialize_record(replace(record(1), reserved=1))
    with pytest.raises(WorkspaceError, match="target mode"):
        serialize_record(replace(record(1), target_mode=7))


def test_trailer_rejects_payload_corruption() -> None:
    encoded = bytearray(
        build_trailer(tuple(record(card_id) for card_id in range(1, 104)))
    )
    encoded[-1] ^= 1
    with pytest.raises(WorkspaceError, match="payload CRC"):
        parse_trailer(bytes(encoded))
