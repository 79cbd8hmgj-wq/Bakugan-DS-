from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, replace

from bakugan_ds.errors import WorkspaceError

G2DT_MAGIC = b"G2DT"
G2DT_VERSION = 1
G2DT_HEADER_SIZE = 32
GATE_RECORD_SIZE = 40
FIRST_CARD_ID = 1
RECORD_COUNT = 103
PAYLOAD_SIZE = GATE_RECORD_SIZE * RECORD_COUNT
TRAILER_SIZE = G2DT_HEADER_SIZE + PAYLOAD_SIZE
NO_PREFERRED_TYPE = 0xFF
RESERVED_ID = 0xFF

_HEADER = struct.Struct("<4s6H4I")
_RECORD = struct.Struct("<BBHhh6b6B4Bhh4Bh2BhH")

if _HEADER.size != G2DT_HEADER_SIZE:
    raise AssertionError("G2DT header struct size is not 32 bytes")
if _RECORD.size != GATE_RECORD_SIZE:
    raise AssertionError("Gate record struct size is not 40 bytes")


def _require_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")


def _require_range(value: int, minimum: int, maximum: int, label: str) -> None:
    _require_int(value, label)
    if not minimum <= value <= maximum:
        raise WorkspaceError(
            f"{label} must be between {minimum} and {maximum}, got {value}"
        )


def _require_id(value: int, label: str) -> None:
    _require_range(value, 0, RESERVED_ID - 1, label)


def _require_vector(
    values: tuple[int, ...],
    *,
    minimum: int,
    maximum: int,
    label: str,
) -> None:
    if len(values) != 6:
        raise WorkspaceError(f"{label} must contain exactly six entries")
    for index, value in enumerate(values):
        _require_range(value, minimum, maximum, f"{label}[{index}]")


@dataclass(frozen=True)
class G2DTHeader:
    version: int
    header_size: int
    record_size: int
    first_card_id: int
    record_count: int
    flags: int
    payload_size: int
    payload_crc32: int
    header_crc32: int
    reserved: int

    def validate(self) -> None:
        if self.version != G2DT_VERSION:
            raise WorkspaceError(f"unsupported G2DT version: {self.version}")
        if self.header_size != G2DT_HEADER_SIZE:
            raise WorkspaceError("G2DT header size must be 32")
        if self.record_size != GATE_RECORD_SIZE:
            raise WorkspaceError("G2DT record size must be 40")
        if self.first_card_id != FIRST_CARD_ID:
            raise WorkspaceError("G2DT first card ID must be 1")
        if self.record_count != RECORD_COUNT:
            raise WorkspaceError("G2DT record count must be 103")
        if self.flags != 0:
            raise WorkspaceError("G2DT version 1 header flags must be zero")
        if self.payload_size != PAYLOAD_SIZE:
            raise WorkspaceError("G2DT payload size must be 4120")
        _require_range(self.payload_crc32, 0, 0xFFFFFFFF, "payload CRC32")
        _require_range(self.header_crc32, 0, 0xFFFFFFFF, "header CRC32")
        if self.reserved != 0:
            raise WorkspaceError("G2DT header reserved field must be zero")


@dataclass(frozen=True)
class GateRecordV1:
    card_id: int
    archetype: int
    flags: int
    flat_bonus_g: int
    percent_q8_8: int
    attribute_modifiers: tuple[int, ...]
    battle_weights: tuple[int, ...]
    preferred_type: int
    condition_id: int
    effect_id: int
    drawback_id: int
    effect_value: int
    drawback_value: int
    activation_limit: int
    fatigue_rate: int
    target_mode: int
    timing_phase: int
    condition_value: int
    secondary_effect_id: int
    secondary_condition_id: int
    secondary_value: int
    reserved: int = 0

    def validate(self) -> None:
        _require_range(self.card_id, FIRST_CARD_ID, RECORD_COUNT, "card ID")
        _require_id(self.archetype, "archetype ID")
        if self.flags != 0:
            raise WorkspaceError("Gate record version 1 flags must be zero")
        _require_range(self.flat_bonus_g, -0x8000, 0x7FFF, "flat bonus G")
        _require_range(self.percent_q8_8, -0x8000, 0x7FFF, "Q8.8 percentage")
        _require_vector(
            self.attribute_modifiers,
            minimum=-0x80,
            maximum=0x7F,
            label="attribute modifiers",
        )
        _require_vector(
            self.battle_weights,
            minimum=0,
            maximum=0xFF,
            label="battle weights",
        )
        if self.preferred_type != NO_PREFERRED_TYPE:
            _require_range(self.preferred_type, 0, 5, "preferred battle type")
        for label, value in (
            ("condition ID", self.condition_id),
            ("effect ID", self.effect_id),
            ("drawback ID", self.drawback_id),
            ("secondary effect ID", self.secondary_effect_id),
            ("secondary condition ID", self.secondary_condition_id),
        ):
            _require_id(value, label)
        for label, value in (
            ("effect value", self.effect_value),
            ("drawback value", self.drawback_value),
            ("condition value", self.condition_value),
            ("secondary value", self.secondary_value),
        ):
            _require_range(value, -0x8000, 0x7FFF, label)
        _require_range(self.activation_limit, 0, 0xFF, "activation limit")
        _require_range(self.fatigue_rate, 0, 0xFF, "fatigue rate")
        _require_range(self.target_mode, 0, 6, "target mode")
        _require_range(self.timing_phase, 0, 11, "timing phase")
        if self.reserved != 0:
            raise WorkspaceError("Gate record reserved field must be zero")


def serialize_header(header: G2DTHeader, *, zero_crc: bool = False) -> bytes:
    header.validate()
    header_crc = 0 if zero_crc else header.header_crc32
    return _HEADER.pack(
        G2DT_MAGIC,
        header.version,
        header.header_size,
        header.record_size,
        header.first_card_id,
        header.record_count,
        header.flags,
        header.payload_size,
        header.payload_crc32,
        header_crc,
        header.reserved,
    )


def parse_header(data: bytes) -> G2DTHeader:
    if len(data) < G2DT_HEADER_SIZE:
        raise WorkspaceError("G2DT header is truncated")
    unpacked = _HEADER.unpack_from(data)
    magic = unpacked[0]
    if magic != G2DT_MAGIC:
        raise WorkspaceError("G2DT magic does not match")
    header = G2DTHeader(*unpacked[1:])
    header.validate()
    expected = zlib.crc32(serialize_header(header, zero_crc=True)) & 0xFFFFFFFF
    if header.header_crc32 != expected:
        raise WorkspaceError("G2DT header CRC does not match")
    return header


def serialize_record(record: GateRecordV1) -> bytes:
    record.validate()
    return _RECORD.pack(
        record.card_id,
        record.archetype,
        record.flags,
        record.flat_bonus_g,
        record.percent_q8_8,
        *record.attribute_modifiers,
        *record.battle_weights,
        record.preferred_type,
        record.condition_id,
        record.effect_id,
        record.drawback_id,
        record.effect_value,
        record.drawback_value,
        record.activation_limit,
        record.fatigue_rate,
        record.target_mode,
        record.timing_phase,
        record.condition_value,
        record.secondary_effect_id,
        record.secondary_condition_id,
        record.secondary_value,
        record.reserved,
    )


def parse_record(data: bytes) -> GateRecordV1:
    if len(data) != GATE_RECORD_SIZE:
        raise WorkspaceError("Gate record must be exactly 40 bytes")
    values = _RECORD.unpack(data)
    record = GateRecordV1(
        card_id=values[0],
        archetype=values[1],
        flags=values[2],
        flat_bonus_g=values[3],
        percent_q8_8=values[4],
        attribute_modifiers=tuple(values[5:11]),
        battle_weights=tuple(values[11:17]),
        preferred_type=values[17],
        condition_id=values[18],
        effect_id=values[19],
        drawback_id=values[20],
        effect_value=values[21],
        drawback_value=values[22],
        activation_limit=values[23],
        fatigue_rate=values[24],
        target_mode=values[25],
        timing_phase=values[26],
        condition_value=values[27],
        secondary_effect_id=values[28],
        secondary_condition_id=values[29],
        secondary_value=values[30],
        reserved=values[31],
    )
    record.validate()
    return record


def _validate_roster(records: tuple[GateRecordV1, ...]) -> None:
    expected = tuple(range(FIRST_CARD_ID, FIRST_CARD_ID + RECORD_COUNT))
    actual = tuple(record.card_id for record in records)
    if actual != expected:
        raise WorkspaceError("Gate records must contain sorted IDs 1 through 103")


def build_trailer(records: tuple[GateRecordV1, ...]) -> bytes:
    if len(records) != RECORD_COUNT:
        raise WorkspaceError("G2DT trailer requires exactly 103 records")
    for record in records:
        record.validate()
    _validate_roster(records)
    payload = b"".join(serialize_record(record) for record in records)
    payload_crc = zlib.crc32(payload) & 0xFFFFFFFF
    provisional = G2DTHeader(
        version=G2DT_VERSION,
        header_size=G2DT_HEADER_SIZE,
        record_size=GATE_RECORD_SIZE,
        first_card_id=FIRST_CARD_ID,
        record_count=RECORD_COUNT,
        flags=0,
        payload_size=len(payload),
        payload_crc32=payload_crc,
        header_crc32=0,
        reserved=0,
    )
    header_crc = zlib.crc32(serialize_header(provisional, zero_crc=True)) & 0xFFFFFFFF
    header = replace(provisional, header_crc32=header_crc)
    trailer = serialize_header(header) + payload
    if len(trailer) != TRAILER_SIZE:
        raise WorkspaceError("G2DT trailer geometry is inconsistent")
    return trailer


def parse_trailer(data: bytes) -> tuple[G2DTHeader, tuple[GateRecordV1, ...]]:
    if len(data) != TRAILER_SIZE:
        raise WorkspaceError("G2DT trailer must be exactly 4152 bytes")
    header = parse_header(data[:G2DT_HEADER_SIZE])
    payload = data[G2DT_HEADER_SIZE:]
    actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if actual_crc != header.payload_crc32:
        raise WorkspaceError("G2DT payload CRC does not match")
    records = tuple(
        parse_record(payload[offset : offset + GATE_RECORD_SIZE])
        for offset in range(0, len(payload), GATE_RECORD_SIZE)
    )
    _validate_roster(records)
    return header, records
