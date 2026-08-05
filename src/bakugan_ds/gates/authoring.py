from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.record import GATE_RECORD_FIELD_NAMES, RECORD_COUNT, GateRecordV1

_RECORD_FIELDS = frozenset(GATE_RECORD_FIELD_NAMES)
_ROOT_FIELDS = frozenset({"format_version", "records"})


def legacy_passthrough_record(card_id: int) -> GateRecordV1:
    record = GateRecordV1(
        card_id=card_id,
        archetype=0,
        flags=0,
        flat_bonus_g=0,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        battle_weights=(0, 0, 0, 0, 0, 0),
        preferred_type=0xFF,
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
    record.validate()
    return record


def approved_juggernoid_record() -> GateRecordV1:
    record = GateRecordV1(
        card_id=19,
        archetype=1,
        flags=0,
        flat_bonus_g=60,
        percent_q8_8=20,
        attribute_modifiers=(0, 30, 0, 0, 0, 0),
        battle_weights=(50, 30, 30, 30, 30, 30),
        preferred_type=0,
        condition_id=1,
        effect_id=1,
        drawback_id=0,
        effect_value=40,
        drawback_value=0,
        activation_limit=0,
        fatigue_rate=0,
        target_mode=1,
        timing_phase=0,
        condition_value=0,
        secondary_effect_id=0,
        secondary_condition_id=0,
        secondary_value=0,
        reserved=0,
    )
    record.validate()
    return record


def validate_milestone_6c_roster(records: tuple[GateRecordV1, ...]) -> None:
    if len(records) != RECORD_COUNT:
        raise WorkspaceError("Milestone 6C roster must contain exactly 103 records")
    expected_ids = tuple(range(1, RECORD_COUNT + 1))
    actual_ids = tuple(record.card_id for record in records)
    if actual_ids != expected_ids:
        raise WorkspaceError("Milestone 6C records must contain sorted IDs 1 through 103")
    for record in records:
        record.validate()
        if record.card_id == 19:
            if record != approved_juggernoid_record():
                raise WorkspaceError("Gate 19 does not match the approved prototype")
        elif record != legacy_passthrough_record(record.card_id):
            raise WorkspaceError(f"Gate {record.card_id} must remain canonical legacy passthrough")


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


def _vector(value: object, label: str) -> tuple[int, ...]:
    items = _require_array(value, label)
    return tuple(_integer(item, f"{label}[{index}]") for index, item in enumerate(items))


def _parse_record(value: object, index: int) -> GateRecordV1:
    item = _require_object(value, f"records[{index}]")
    actual_fields = frozenset(item)
    if actual_fields != _RECORD_FIELDS:
        missing = sorted(_RECORD_FIELDS - actual_fields)
        extra = sorted(actual_fields - _RECORD_FIELDS)
        raise WorkspaceError(
            f"records[{index}] record fields mismatch; missing={missing}, extra={extra}"
        )
    try:
        record = GateRecordV1(
            card_id=_integer(item["card_id"], f"records[{index}].card_id"),
            archetype=_integer(item["archetype"], f"records[{index}].archetype"),
            flags=_integer(item["flags"], f"records[{index}].flags"),
            flat_bonus_g=_integer(item["flat_bonus_g"], f"records[{index}].flat_bonus_g"),
            percent_q8_8=_integer(item["percent_q8_8"], f"records[{index}].percent_q8_8"),
            attribute_modifiers=_vector(
                item["attribute_modifiers"],
                f"records[{index}].attribute_modifiers",
            ),
            battle_weights=_vector(item["battle_weights"], f"records[{index}].battle_weights"),
            preferred_type=_integer(item["preferred_type"], f"records[{index}].preferred_type"),
            condition_id=_integer(item["condition_id"], f"records[{index}].condition_id"),
            effect_id=_integer(item["effect_id"], f"records[{index}].effect_id"),
            drawback_id=_integer(item["drawback_id"], f"records[{index}].drawback_id"),
            effect_value=_integer(item["effect_value"], f"records[{index}].effect_value"),
            drawback_value=_integer(item["drawback_value"], f"records[{index}].drawback_value"),
            activation_limit=_integer(
                item["activation_limit"], f"records[{index}].activation_limit"
            ),
            fatigue_rate=_integer(item["fatigue_rate"], f"records[{index}].fatigue_rate"),
            target_mode=_integer(item["target_mode"], f"records[{index}].target_mode"),
            timing_phase=_integer(item["timing_phase"], f"records[{index}].timing_phase"),
            condition_value=_integer(item["condition_value"], f"records[{index}].condition_value"),
            secondary_effect_id=_integer(
                item["secondary_effect_id"],
                f"records[{index}].secondary_effect_id",
            ),
            secondary_condition_id=_integer(
                item["secondary_condition_id"],
                f"records[{index}].secondary_condition_id",
            ),
            secondary_value=_integer(item["secondary_value"], f"records[{index}].secondary_value"),
            reserved=_integer(item["reserved"], f"records[{index}].reserved"),
        )
    except KeyError as exc:
        raise WorkspaceError(f"records[{index}] missing field: {exc}") from exc
    record.validate()
    return record


def load_authoring_document(path: Path) -> tuple[GateRecordV1, ...]:
    try:
        root = _require_object(json.loads(path.read_text(encoding="utf-8")), "authoring document")
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"cannot load Gate authoring document {path}: {exc}") from exc
    actual_root_fields = frozenset(root)
    if actual_root_fields != _ROOT_FIELDS:
        missing = sorted(_ROOT_FIELDS - actual_root_fields)
        extra = sorted(actual_root_fields - _ROOT_FIELDS)
        raise WorkspaceError(
            f"authoring document fields mismatch; missing={missing}, extra={extra}"
        )
    if _integer(root["format_version"], "format_version") != 1:
        raise WorkspaceError("unsupported Gate authoring format version")
    records = tuple(
        _parse_record(value, index)
        for index, value in enumerate(_require_array(root["records"], "records"))
    )
    validate_milestone_6c_roster(records)
    return records
