from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.balance import GateBalanceReport, analyze_gate_balance
from bakugan_ds.gates.record import (
    GATE_RECORD_FIELD_NAMES,
    RECORD_COUNT,
    GateArchetype,
    GateRecordV1,
)
from bakugan_ds.gates.system2 import GateCalculationContext, calculate_gate_bonus

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


def _load_authoring_records(path: Path) -> tuple[GateRecordV1, ...]:
    try:
        root = _require_object(
            json.loads(path.read_text(encoding="utf-8")),
            "authoring document",
        )
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
    return tuple(
        _parse_record(value, index)
        for index, value in enumerate(_require_array(root["records"], "records"))
    )


def load_gate_roster_authoring_document(path: Path) -> tuple[GateRecordV1, ...]:
    records = _load_authoring_records(path)
    if len(records) != RECORD_COUNT:
        raise WorkspaceError("Gate authoring roster must contain exactly 103 records")
    expected_ids = tuple(range(1, RECORD_COUNT + 1))
    if tuple(record.card_id for record in records) != expected_ids:
        raise WorkspaceError("Gate authoring records must contain sorted IDs 1 through 103")
    return records


def load_authoring_document(path: Path) -> tuple[GateRecordV1, ...]:
    records = load_gate_roster_authoring_document(path)
    validate_milestone_6c_roster(records)
    return records


MILESTONE_6D_REFERENCE_CORE_G = (190, 400, 525, 650, 695)


def validate_milestone_6d_roster(
    records: tuple[GateRecordV1, ...],
) -> tuple[GateBalanceReport, ...]:
    if len(records) != RECORD_COUNT:
        raise WorkspaceError("Milestone 6D roster must contain exactly 103 records")
    expected_ids = tuple(range(1, RECORD_COUNT + 1))
    actual_ids = tuple(record.card_id for record in records)
    if actual_ids != expected_ids:
        raise WorkspaceError("Milestone 6D records must contain sorted IDs 1 through 103")

    reports: list[GateBalanceReport] = []
    for record in records:
        record.validate()
        if record.card_id == 19:
            if record != approved_juggernoid_record():
                raise WorkspaceError("Gate 19 does not match the approved Milestone 6D prototype")
            reports.append(analyze_gate_balance(record))
        elif record != legacy_passthrough_record(record.card_id):
            raise WorkspaceError(
                f"Gate {record.card_id} must remain canonical legacy passthrough in Milestone 6D"
            )
    return tuple(reports)


def load_milestone_6d_authoring_document(path: Path) -> tuple[GateRecordV1, ...]:
    records = _load_authoring_records(path)
    validate_milestone_6d_roster(records)
    return records


def _balance_report_dict(report: GateBalanceReport) -> dict[str, object]:
    payload = asdict(report)
    payload["archetype"] = report.archetype.value
    payload["attribute"]["tiers"] = [tier.value for tier in report.attribute.tiers]
    payload["battle_weights"]["pressure"] = report.battle_weights.pressure.value
    payload["attribute"]["modifiers"] = list(report.attribute.modifiers)
    payload["battle_weights"]["weights"] = list(report.battle_weights.weights)
    return payload


def _reference_case_results(record: GateRecordV1) -> tuple[int, ...]:
    values: list[int] = []
    score_cases = ((0, 1), (1, 1))
    participant_cases = ((1, 1), (0, 1))
    for core_g in MILESTONE_6D_REFERENCE_CORE_G:
        for attribute_id in range(6):
            for owner_score, opposing_score in score_cases:
                for current_participant, owner_participant in participant_cases:
                    result = calculate_gate_bonus(
                        record,
                        GateCalculationContext(
                            compressed_core_g=core_g,
                            attribute_id=attribute_id,
                            current_participant=current_participant,
                            owner_participant=owner_participant,
                            owner_side_score=owner_score,
                            opposing_side_score=opposing_score,
                            gate_id=record.card_id,
                        ),
                    )
                    if result.effective_gate_bonus is None:
                        raise WorkspaceError(
                            f"Gate {record.card_id} failed deterministic reference analysis: "
                            f"{result.fallback_reason.value}"
                        )
                    values.append(result.effective_gate_bonus)
    return tuple(values)


def build_milestone_6d_balance_report(
    records: tuple[GateRecordV1, ...],
) -> dict[str, object]:
    reports = validate_milestone_6d_roster(records)
    live_records = tuple(
        record for record in records if record.archetype != GateArchetype.LEGACY
    )
    cards: list[dict[str, object]] = []
    by_id = {report.card_id: report for report in reports}
    for record in live_records:
        report = by_id[record.card_id]
        values = _reference_case_results(record)
        cards.append(
            {
                "balance": _balance_report_dict(report),
                "card_id": record.card_id,
                "reference_cases": len(values),
                "effective_gate_bonus": {
                    "maximum": max(values),
                    "mean_denominator": len(values),
                    "mean_numerator": sum(values),
                    "minimum": min(values),
                },
            }
        )
    return {
        "format": "bakugan-ds-gate-milestone-6d-balance",
        "format_version": 1,
        "record_count": len(records),
        "live_card_ids": [record.card_id for record in live_records],
        "legacy_passthrough_count": len(records) - len(live_records),
        "reference_core_g": list(MILESTONE_6D_REFERENCE_CORE_G),
        "cards": cards,
        "valid": True,
    }


def write_milestone_6d_balance_report(
    path: Path,
    records: tuple[GateRecordV1, ...],
) -> None:
    payload = build_milestone_6d_balance_report(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
