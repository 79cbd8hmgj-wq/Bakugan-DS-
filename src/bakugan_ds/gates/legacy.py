from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.io import write_evidence
from bakugan_ds.gates.model import Confidence, GateControlCase, LegacyGateTableSpec
from bakugan_ds.gates.runtime_image import RuntimeImage, RuntimeStoredMapping, runtime_slice
from bakugan_ds.workspace.manifest import sha256_bytes


@dataclass(frozen=True)
class LegacyGateRecord:
    card_id: int
    raw_values: tuple[int, ...]
    bonuses_g: tuple[int, ...]


def _require_sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _parse_integer(value: object, label: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value, 0)
        raise ValueError
    except ValueError as exc:
        raise WorkspaceError(f"{label} must be an integer") from exc


def legacy_spec_from_dict(payload: dict[str, object]) -> LegacyGateTableSpec:
    try:
        raw_attributes = _require_sequence(payload["attribute_order"], "attribute_order")
        attributes = tuple(str(value) for value in raw_attributes)
        raw_controls = _require_sequence(payload.get("control_cases", []), "control_cases")
        controls: list[GateControlCase] = []
        for index, value in enumerate(raw_controls):
            if not isinstance(value, dict):
                raise WorkspaceError(f"control_cases[{index}] must be a JSON object")
            controls.append(
                GateControlCase(
                    card_id=_parse_integer(value["card_id"], f"control_cases[{index}].card_id"),
                    attribute_id=_parse_integer(
                        value["attribute_id"], f"control_cases[{index}].attribute_id"
                    ),
                    expected_bonus_g=_parse_integer(
                        value["expected_bonus_g"],
                        f"control_cases[{index}].expected_bonus_g",
                    ),
                    evidence_id=str(value["evidence_id"]),
                )
            )
        spec = LegacyGateTableSpec(
            profile_id=str(payload["profile_id"]),
            runtime_address=_parse_integer(payload["runtime_address"], "runtime_address"),
            element_width=_parse_integer(payload["element_width"], "element_width"),
            signed=cast(bool, payload["signed"]),
            record_stride=_parse_integer(payload["record_stride"], "record_stride"),
            record_count=_parse_integer(payload["record_count"], "record_count"),
            attribute_order=attributes,
            region_sha256=str(payload["region_sha256"]),
            confidence=Confidence(str(payload["confidence"])),
            control_cases=tuple(controls),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid legacy Gate metadata: {exc}") from exc
    spec.validate()
    return spec


def parse_legacy_table(
    image: RuntimeImage,
    spec: LegacyGateTableSpec,
    *,
    verify_hash: bool = True,
) -> tuple[LegacyGateRecord, ...]:
    spec.validate()
    region = runtime_slice(image, spec.runtime_address, spec.table_size)
    actual_hash = sha256_bytes(region)
    if verify_hash and actual_hash != spec.region_sha256:
        raise WorkspaceError(
            f"legacy Gate table region hash mismatch: expected {spec.region_sha256}, "
            f"got {actual_hash}"
        )

    records: list[LegacyGateRecord] = []
    for card_id in range(spec.record_count):
        row_start = card_id * spec.record_stride
        raw_values = tuple(
            int.from_bytes(
                region[
                    row_start + attribute_id * spec.element_width :
                    row_start + (attribute_id + 1) * spec.element_width
                ],
                "little",
                signed=spec.signed,
            )
            for attribute_id in range(6)
        )
        records.append(
            LegacyGateRecord(
                card_id=card_id,
                raw_values=raw_values,
                bonuses_g=tuple(value * 10 for value in raw_values),
            )
        )
    return tuple(records)


def legacy_metadata(
    image: RuntimeImage,
    spec: LegacyGateTableSpec,
    mapping: RuntimeStoredMapping,
) -> dict[str, object]:
    spec.validate()
    if mapping.runtime_address != spec.runtime_address:
        raise WorkspaceError("legacy Gate mapping address does not match table specification")
    if mapping.decoded_sha256 != image.sha256:
        raise WorkspaceError("legacy Gate mapping decoded hash does not match runtime image")
    return {
        "format_version": 1,
        "schema": "legacy_gate_attribute_bonus_v1",
        "profile_id": spec.profile_id,
        "runtime_address": spec.runtime_address,
        "runtime_address_hex": f"0x{spec.runtime_address:08X}",
        "end_address": spec.runtime_address + spec.table_size,
        "end_address_hex": f"0x{spec.runtime_address + spec.table_size:08X}",
        "element_width": spec.element_width,
        "signed": spec.signed,
        "record_stride": spec.record_stride,
        "record_count": spec.record_count,
        "table_size": spec.table_size,
        "attribute_order": list(spec.attribute_order),
        "region_sha256": spec.region_sha256,
        "confidence": spec.confidence,
        "control_cases": [asdict(value) for value in spec.control_cases],
        "mapping": asdict(mapping),
        "complete_table_committed": False,
    }


def export_legacy_table(
    path: Path,
    records: tuple[LegacyGateRecord, ...],
    spec: LegacyGateTableSpec,
) -> None:
    spec.validate()
    if len(records) != spec.record_count:
        raise WorkspaceError(
            f"legacy Gate export requires {spec.record_count} records, got {len(records)}"
        )
    for expected_id, record in enumerate(records):
        if record.card_id != expected_id:
            raise WorkspaceError(
                f"legacy Gate export record {expected_id} has card ID {record.card_id}"
            )
    write_evidence(
        path,
        {
            "format_version": 1,
            "schema": "legacy_gate_attribute_bonus_v1",
            "profile_id": spec.profile_id,
            "local_only": True,
            "runtime_address": spec.runtime_address,
            "attribute_order": list(spec.attribute_order),
            "records": [
                {
                    "card_id": record.card_id,
                    "raw_values": list(record.raw_values),
                    "bonuses_g": list(record.bonuses_g),
                }
                for record in records
            ],
        },
    )
