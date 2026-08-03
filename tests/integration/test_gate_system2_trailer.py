from __future__ import annotations

import pytest

from bakugan_ds.compression.lz10 import compress_lz10, decompress_lz10
from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.record import GateRecordV1, build_trailer, parse_trailer
from bakugan_ds.gates.storage import append_lz10_trailer


def empty_record(card_id: int) -> GateRecordV1:
    return GateRecordV1(
        card_id=card_id,
        archetype=0,
        flags=0,
        flat_bonus_g=0,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        battle_weights=(0, 0, 0, 0, 0, 0),
        preferred_type=255,
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


def test_g2dt_trailer_preserves_native_lz10_output() -> None:
    original = b"unchanged original card-name payload"
    raw = compress_lz10(original)
    trailer = build_trailer(tuple(empty_record(card_id) for card_id in range(1, 104)))
    combined = append_lz10_trailer(raw, trailer, maximum_size=4152)

    assert decompress_lz10(combined) == original
    header, records = parse_trailer(combined[-4152:])
    assert header.record_count == 103
    assert records[-1].card_id == 103


def test_g2dt_parser_rejects_corrupted_header_crc() -> None:
    trailer = bytearray(
        build_trailer(tuple(empty_record(card_id) for card_id in range(1, 104)))
    )
    trailer[8] ^= 1
    with pytest.raises(WorkspaceError, match=r"header CRC|record size"):
        parse_trailer(bytes(trailer))
