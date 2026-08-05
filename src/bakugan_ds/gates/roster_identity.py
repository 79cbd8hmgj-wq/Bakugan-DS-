from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID
from bakugan_ds.gates.record import FIRST_CARD_ID, RECORD_COUNT
from bakugan_ds.gates.roster_metadata import MappingConfidence

_ROOT_FIELDS = frozenset(
    {
        "complete_name_table_committed",
        "entries",
        "format_version",
        "guide_order_used_for_ids",
        "profile_id",
        "source_evidence",
    }
)
_ENTRY_FIELDS = frozenset(
    {
        "card_id",
        "evidence_reference",
        "mapping_confidence",
        "name",
    }
)


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise WorkspaceError(f"{label} must be a string")
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")
    return value


def _require_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


@dataclass(frozen=True)
class GateRosterIdentityEntry:
    card_id: int
    name: str
    mapping_confidence: MappingConfidence
    evidence_reference: str

    def validate(self) -> None:
        if not FIRST_CARD_ID <= self.card_id <= RECORD_COUNT:
            raise WorkspaceError(
                f"Gate identity card ID must be between {FIRST_CARD_ID} and "
                f"{RECORD_COUNT}, got {self.card_id}"
            )
        _require_string(self.name, "Gate identity name")
        if not isinstance(self.mapping_confidence, MappingConfidence):
            raise WorkspaceError("invalid Gate identity mapping confidence")
        if (
            self.mapping_confidence is MappingConfidence.UNRESOLVED
            and "provisional" not in self.name.casefold()
        ):
            raise WorkspaceError(
                "unresolved Gate identity names must be explicitly marked provisional"
            )
        _require_string(self.evidence_reference, "Gate identity evidence reference")

    def to_json(self) -> dict[str, object]:
        return {
            "card_id": self.card_id,
            "evidence_reference": self.evidence_reference,
            "mapping_confidence": self.mapping_confidence.value,
            "name": self.name,
        }


@dataclass(frozen=True)
class GateRosterIdentityMap:
    complete_name_table_committed: bool
    guide_order_used_for_ids: bool
    source_evidence: str
    entries: tuple[GateRosterIdentityEntry, ...]

    def validate(self) -> None:
        if self.complete_name_table_committed:
            raise WorkspaceError(
                "Milestone 6E identity map must not commit the complete name table"
            )
        if self.guide_order_used_for_ids:
            raise WorkspaceError("guide order must not be used to assign Gate IDs")
        _require_string(self.source_evidence, "Gate identity source evidence")
        if len(self.entries) != RECORD_COUNT:
            raise WorkspaceError(
                f"Gate identity map must contain exactly {RECORD_COUNT} entries"
            )

        card_ids: set[int] = set()
        names: set[str] = set()
        for entry in self.entries:
            entry.validate()
            if entry.card_id in card_ids:
                raise WorkspaceError(
                    f"duplicate Gate identity card ID: {entry.card_id}"
                )
            normalized_name = entry.name.strip().casefold()
            if normalized_name in names:
                raise WorkspaceError(f"duplicate Gate identity name: {entry.name}")
            card_ids.add(entry.card_id)
            names.add(normalized_name)

        expected = tuple(range(FIRST_CARD_ID, RECORD_COUNT + 1))
        if tuple(entry.card_id for entry in self.entries) != expected:
            raise WorkspaceError("Gate identity entries must use canonical ID order")

    def to_json(self) -> dict[str, object]:
        return {
            "complete_name_table_committed": self.complete_name_table_committed,
            "entries": [entry.to_json() for entry in self.entries],
            "format_version": 1,
            "guide_order_used_for_ids": self.guide_order_used_for_ids,
            "profile_id": SUPPORTED_PROFILE_ID,
            "source_evidence": self.source_evidence,
        }


def _parse_entry(value: object, index: int) -> GateRosterIdentityEntry:
    item = _require_object(value, f"entries[{index}]")
    fields = frozenset(item)
    if fields != _ENTRY_FIELDS:
        missing = sorted(_ENTRY_FIELDS - fields)
        extra = sorted(fields - _ENTRY_FIELDS)
        raise WorkspaceError(
            f"entries[{index}] fields mismatch; missing={missing}, extra={extra}"
        )
    try:
        confidence = MappingConfidence(
            _require_string(
                item["mapping_confidence"],
                f"entries[{index}].mapping_confidence",
            )
        )
    except ValueError as exc:
        raise WorkspaceError(
            f"invalid entries[{index}].mapping_confidence"
        ) from exc
    entry = GateRosterIdentityEntry(
        card_id=_require_integer(item["card_id"], f"entries[{index}].card_id"),
        name=_require_string(item["name"], f"entries[{index}].name"),
        mapping_confidence=confidence,
        evidence_reference=_require_string(
            item["evidence_reference"],
            f"entries[{index}].evidence_reference",
        ),
    )
    entry.validate()
    return entry


def parse_gate_roster_identity_map(payload: object) -> GateRosterIdentityMap:
    document = _require_object(payload, "Gate roster identity document")
    fields = frozenset(document)
    if fields != _ROOT_FIELDS:
        missing = sorted(_ROOT_FIELDS - fields)
        extra = sorted(fields - _ROOT_FIELDS)
        raise WorkspaceError(
            "Gate roster identity document fields mismatch; "
            f"missing={missing}, extra={extra}"
        )
    if document.get("format_version") != 1:
        raise WorkspaceError("Gate roster identity format_version must be 1")
    if document.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError(
            f"Gate roster identity profile_id must be {SUPPORTED_PROFILE_ID}"
        )
    complete = document.get("complete_name_table_committed")
    guide_order = document.get("guide_order_used_for_ids")
    if not isinstance(complete, bool):
        raise WorkspaceError("complete_name_table_committed must be a boolean")
    if not isinstance(guide_order, bool):
        raise WorkspaceError("guide_order_used_for_ids must be a boolean")
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list):
        raise WorkspaceError("Gate roster identity entries must be a JSON array")
    identity_map = GateRosterIdentityMap(
        complete_name_table_committed=complete,
        guide_order_used_for_ids=guide_order,
        source_evidence=_require_string(
            document.get("source_evidence"), "Gate identity source evidence"
        ),
        entries=tuple(
            _parse_entry(raw_entry, index)
            for index, raw_entry in enumerate(raw_entries)
        ),
    )
    identity_map.validate()
    return identity_map


def load_gate_roster_identity_map(path: Path) -> GateRosterIdentityMap:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"could not load Gate roster identity map {path}: {exc}") from exc
    return parse_gate_roster_identity_map(payload)


def write_gate_roster_identity_map(
    path: Path, identity_map: GateRosterIdentityMap
) -> None:
    identity_map.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(identity_map.to_json(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
