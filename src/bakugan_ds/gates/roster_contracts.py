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
    DesignTier,
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


def build_balance_contract(
    records: tuple[GateRecordV1, ...],
    metadata: tuple[GateRosterMetadataEntry, ...],
) -> dict[str, JsonValue]:
    _validate_inputs(records, metadata)
    analysis = build_roster_analysis(records, metadata)
    raw_pairs = analysis["potential_dominance_pairs"]
    if not isinstance(raw_pairs, list):
        raise WorkspaceError("roster analysis dominance pairs must be a list")
    pairs = [
        {
            "dominant_card_id": int(pair["dominant_card_id"]),
            "dominated_card_id": int(pair["dominated_card_id"]),
        }
        for pair in raw_pairs
        if isinstance(pair, dict)
    ]
    metadata_by_id = {entry.card_id: entry for entry in metadata}
    dispositions = [
        _dominance_disposition(pair, metadata_by_id) for pair in pairs
    ]
    unresolved = [
        {
            "dominant_card_id": int(item["dominant_card_id"]),
            "dominated_card_id": int(item["dominated_card_id"]),
        }
        for item in dispositions
        if item["disposition"] == "unresolved_same_archetype_same_tier"
    ]
    cards = analysis["cards"]
    if not isinstance(cards, list):
        raise WorkspaceError("roster analysis cards must be a list")
    out_of_tier = sorted(
        int(card["card_id"])
        for card in cards
        if isinstance(card, dict) and card.get("out_of_tier") is True
    )
    contract: dict[str, JsonValue] = {
        "analysis_sha256": _sha256(_canonical_json_bytes(analysis)),
        "distribution_warnings": list(analysis["archetype_distribution_warnings"]),
        "dominance_dispositions": dispositions,
        "format": "bakugan-ds-gate-milestone-6e-balance-contract",
        "format_version": 1,
        "hard_duplicate_groups": list(analysis["hard_duplicate_groups"]),
        "identical_evaluation_groups": list(
            analysis["identical_evaluation_groups"]
        ),
        "identity_conflicts": list(analysis["identity_conflicts"]),
        "out_of_tier_card_ids": out_of_tier,
        "potential_dominance_pairs": pairs,
        "reference_case_count_per_record": int(
            analysis["matrix"]["case_count_per_record"]  # type: ignore[index]
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
