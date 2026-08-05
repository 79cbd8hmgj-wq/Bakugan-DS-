from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypeAlias

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import approved_juggernoid_record
from bakugan_ds.gates.record import (
    RECORD_COUNT,
    GateArchetype,
    GateRecordV1,
    serialize_record,
)
from bakugan_ds.gates.roster_analysis import build_roster_analysis
from bakugan_ds.gates.roster_metadata import (
    GateRosterMetadataEntry,
    ReviewStatus,
)
from bakugan_ds.gates.system2 import FallbackReason, record_fallback_reason

JsonScalar: TypeAlias = str | int | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

_DEFERRED_FIELDS = (
    "activation_limit",
    "fatigue_rate",
    "timing_phase",
    "secondary_effect_id",
    "secondary_condition_id",
    "secondary_value",
    "reserved",
)


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise WorkspaceError(f"{label} contains a non-string key")
        result[key] = item
    return result


def _require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a list")
    return list(value)


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


def _normalize_json(value: object, label: str) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, list):
        return [
            _normalize_json(item, f"{label}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise WorkspaceError(f"{label} contains a non-string key")
            result[key] = _normalize_json(item, f"{label}.{key}")
        return result
    raise WorkspaceError(f"{label} contains a non-JSON value")


def _validate_inputs(
    records: tuple[GateRecordV1, ...],
    metadata: tuple[GateRosterMetadataEntry, ...],
) -> None:
    if len(records) != RECORD_COUNT or len(metadata) != RECORD_COUNT:
        raise WorkspaceError(
            f"final Gate contracts require exactly {RECORD_COUNT} records and entries"
        )
    expected_ids = tuple(range(1, RECORD_COUNT + 1))
    if tuple(record.card_id for record in records) != expected_ids:
        raise WorkspaceError("final Gate records must use sorted IDs 1 through 103")
    if tuple(entry.card_id for entry in metadata) != expected_ids:
        raise WorkspaceError("final Gate metadata must use sorted IDs 1 through 103")
    for record, entry in zip(records, metadata, strict=True):
        record.validate()
        entry.validate(final=True)
        if record.archetype == GateArchetype.LEGACY:
            raise WorkspaceError(f"final Gate record {record.card_id} remains legacy")
        if record.archetype != entry.archetype:
            raise WorkspaceError(
                f"Gate {record.card_id} record and metadata archetypes disagree"
            )
        reason = record_fallback_reason(record)
        if reason is not FallbackReason.NONE:
            raise WorkspaceError(
                f"Gate {record.card_id} uses unsupported runtime semantics: {reason.value}"
            )
    if records[18] != approved_juggernoid_record():
        raise WorkspaceError("Gate 19 no longer matches the approved Juggernoid fixture")


def _metadata_payload(
    metadata: tuple[GateRosterMetadataEntry, ...],
) -> list[dict[str, object]]:
    return [entry.to_json() for entry in metadata]


def _distribution(records: tuple[GateRecordV1, ...]) -> dict[str, int]:
    return {
        archetype.name.lower(): sum(
            record.archetype == archetype for record in records
        )
        for archetype in GateArchetype
        if archetype is not GateArchetype.LEGACY
    }


def build_roster_contract(
    records: tuple[GateRecordV1, ...],
    metadata: tuple[GateRosterMetadataEntry, ...],
) -> dict[str, JsonValue]:
    _validate_inputs(records, metadata)
    unsupported = [
        record.card_id
        for record in records
        if record_fallback_reason(record) is not FallbackReason.NONE
    ]
    deferred = [
        record.card_id
        for record in records
        if any(getattr(record, field) != 0 for field in _DEFERRED_FIELDS)
    ]
    serialized = b"".join(serialize_record(record) for record in records)
    metadata_payload = _metadata_payload(metadata)
    return {
        "archetype_distribution": _distribution(records),
        "deferred_state_record_ids": deferred,
        "format": "bakugan-ds-gate-milestone-6e-roster-contract",
        "format_version": 1,
        "juggernoid_preserved": records[18] == approved_juggernoid_record(),
        "live_record_count": sum(
            record.archetype != GateArchetype.LEGACY for record in records
        ),
        "metadata_sha256": _sha256(_canonical_json_bytes(metadata_payload)),
        "profile_id": "b6re_rev0",
        "record_count": len(records),
        "records_sha256": _sha256(serialized),
        "review_status_counts": {
            status.value: sum(entry.review_status is status for entry in metadata)
            for status in ReviewStatus
        },
        "unsupported_record_ids": unsupported,
    }


def _dominance_disposition(
    pair: dict[str, int],
    metadata_by_id: dict[int, GateRosterMetadataEntry],
) -> dict[str, JsonValue]:
    dominant = metadata_by_id[pair["dominant_card_id"]]
    dominated = metadata_by_id[pair["dominated_card_id"]]
    if dominant.archetype is not dominated.archetype:
        disposition = "accepted_cross_archetype_identity"
        rationale = (
            f"{dominant.name} is {dominant.archetype.name.lower()} while "
            f"{dominated.name} is {dominated.archetype.name.lower()}; their authored "
            "roles and budget allocations are intentionally different."
        )
    elif dominant.design_tier is not dominated.design_tier:
        disposition = "accepted_tier_progression"
        rationale = (
            f"{dominant.name} uses {dominant.design_tier.value} while "
            f"{dominated.name} uses {dominated.design_tier.value}; the stronger "
            "evaluated profile is an explicit tier progression."
        )
    else:
        disposition = "unresolved_same_archetype_same_tier"
        rationale = (
            f"{dominant.name} and {dominated.name} share archetype "
            f"{dominant.archetype.name.lower()} and tier {dominant.design_tier.value}."
        )
    return {
        "disposition": disposition,
        "dominant_card_id": dominant.card_id,
        "dominated_card_id": dominated.card_id,
        "rationale": rationale,
    }


def _parse_dominance_pairs(value: object) -> list[dict[str, int]]:
    pairs: list[dict[str, int]] = []
    for index, raw_pair in enumerate(
        _require_list(value, "roster analysis potential_dominance_pairs")
    ):
        pair = _require_object(raw_pair, f"potential_dominance_pairs[{index}]")
        pairs.append(
            {
                "dominant_card_id": _require_int(
                    pair.get("dominant_card_id"),
                    f"potential_dominance_pairs[{index}].dominant_card_id",
                ),
                "dominated_card_id": _require_int(
                    pair.get("dominated_card_id"),
                    f"potential_dominance_pairs[{index}].dominated_card_id",
                ),
            }
        )
    return pairs


def _parse_out_of_tier_card_ids(value: object) -> list[int]:
    card_ids: list[int] = []
    for index, raw_card in enumerate(_require_list(value, "roster analysis cards")):
        card = _require_object(raw_card, f"cards[{index}]")
        if card.get("out_of_tier") is True:
            card_ids.append(
                _require_int(card.get("card_id"), f"cards[{index}].card_id")
            )
    return sorted(card_ids)


def build_balance_contract(
    records: tuple[GateRecordV1, ...],
    metadata: tuple[GateRosterMetadataEntry, ...],
) -> dict[str, JsonValue]:
    _validate_inputs(records, metadata)
    analysis = build_roster_analysis(records, metadata)
    pairs = _parse_dominance_pairs(analysis.get("potential_dominance_pairs"))
    metadata_by_id = {entry.card_id: entry for entry in metadata}
    dispositions = [
        _dominance_disposition(pair, metadata_by_id) for pair in pairs
    ]
    unresolved = [
        {
            "dominant_card_id": _require_int(
                item.get("dominant_card_id"),
                "dominance disposition dominant_card_id",
            ),
            "dominated_card_id": _require_int(
                item.get("dominated_card_id"),
                "dominance disposition dominated_card_id",
            ),
        }
        for item in dispositions
        if item.get("disposition") == "unresolved_same_archetype_same_tier"
    ]
    matrix = _require_object(analysis.get("matrix"), "roster analysis matrix")
    contract: dict[str, JsonValue] = {
        "analysis_sha256": _sha256(_canonical_json_bytes(analysis)),
        "distribution_warnings": _normalize_json(
            analysis.get("archetype_distribution_warnings"),
            "roster analysis archetype_distribution_warnings",
        ),
        "dominance_dispositions": dispositions,
        "format": "bakugan-ds-gate-milestone-6e-balance-contract",
        "format_version": 1,
        "hard_duplicate_groups": _normalize_json(
            analysis.get("hard_duplicate_groups"),
            "roster analysis hard_duplicate_groups",
        ),
        "identical_evaluation_groups": _normalize_json(
            analysis.get("identical_evaluation_groups"),
            "roster analysis identical_evaluation_groups",
        ),
        "identity_conflicts": _normalize_json(
            analysis.get("identity_conflicts"),
            "roster analysis identity_conflicts",
        ),
        "out_of_tier_card_ids": _parse_out_of_tier_card_ids(
            analysis.get("cards")
        ),
        "potential_dominance_pairs": pairs,
        "reference_case_count_per_record": _require_int(
            matrix.get("case_count_per_record"),
            "roster analysis matrix.case_count_per_record",
        ),
        "unresolved_dominance_pairs": unresolved,
    }
    if unresolved:
        formatted = ", ".join(
            f"{item['dominant_card_id']}>{item['dominated_card_id']}"
            for item in unresolved
        )
        raise WorkspaceError(
            "same-archetype same-tier dominance findings require record revision: "
            f"{formatted}"
        )
    return contract


def write_contract(path: Path, contract: dict[str, JsonValue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
