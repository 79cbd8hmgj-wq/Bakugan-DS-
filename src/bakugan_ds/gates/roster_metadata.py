from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypeVar

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID
from bakugan_ds.gates.record import FIRST_CARD_ID, RECORD_COUNT, GateArchetype


class MappingConfidence(StrEnum):
    UNRESOLVED = "unresolved"
    CANDIDATE = "candidate"
    PROBABLE = "probable"
    CONFIRMED = "confirmed"


class RosterFamily(StrEnum):
    BAKUGAN_CHARACTER = "bakugan_character"
    ENVIRONMENTAL_FIELD = "environmental_field"
    TACTICAL_CONDITIONAL = "tactical_conditional"


class DesignTier(StrEnum):
    UNASSIGNED = "unassigned"
    EARLY_COMMON = "early_common"
    MID = "mid"
    RARE_SPECIALIZED = "rare_specialized"
    HIGH_RISK_CONDITIONAL = "high_risk_conditional"


class ReviewStatus(StrEnum):
    PROVISIONAL = "provisional"
    REVIEWED = "reviewed"
    APPROVED = "approved"


_PLACEHOLDER_MARKERS = frozenset({"unassigned", "pending"})
_EnumT = TypeVar("_EnumT", bound=StrEnum)
_ROOT_FIELDS = frozenset({"entries", "format_version", "profile_id"})
_ENTRY_FIELDS = frozenset(
    {
        "archetype",
        "battle_weight_summary",
        "card_id",
        "design_tier",
        "differentiation_rationale",
        "evidence_reference",
        "family",
        "g_influence_summary",
        "gameplay_identity",
        "mapping_confidence",
        "name",
        "net_budget",
        "review_status",
        "rule_summary",
    }
)
_ARCHETYPE_BUDGET_BANDS = {
    GateArchetype.COMEBACK: (85, 115),
    GateArchetype.POWER: (90, 110),
    GateArchetype.SKILL: (90, 110),
    GateArchetype.CONTROL: (85, 110),
    GateArchetype.RISK: (85, 120),
    GateArchetype.ATTRIBUTE: (90, 110),
    GateArchetype.CHAOS: (90, 120),
}


def _require_nonempty(value: str, label: str) -> None:
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")


def _require_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise WorkspaceError(f"{label} must be a string")
    return value


def _parse_enum(enum_type: type[_EnumT], value: object, label: str) -> _EnumT:
    if not isinstance(value, str):
        raise WorkspaceError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise WorkspaceError(f"invalid {label}: {value}") from exc


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def family_for_card_id(card_id: int) -> RosterFamily:
    if not FIRST_CARD_ID <= card_id <= RECORD_COUNT:
        raise WorkspaceError(
            f"Gate metadata card ID must be between {FIRST_CARD_ID} and "
            f"{RECORD_COUNT}, got {card_id}"
        )
    if card_id <= 39:
        return RosterFamily.BAKUGAN_CHARACTER
    if card_id <= 71:
        return RosterFamily.ENVIRONMENTAL_FIELD
    return RosterFamily.TACTICAL_CONDITIONAL


@dataclass(frozen=True)
class GateRosterMetadataEntry:
    card_id: int
    name: str
    mapping_confidence: MappingConfidence
    evidence_reference: str
    family: RosterFamily
    archetype: GateArchetype
    design_tier: DesignTier
    gameplay_identity: str
    g_influence_summary: str
    battle_weight_summary: str
    rule_summary: str
    net_budget: int | None
    differentiation_rationale: str
    review_status: ReviewStatus

    def validate(self, *, final: bool = False) -> None:
        expected_family = family_for_card_id(self.card_id)
        _require_nonempty(self.name, "Gate metadata name")
        if not isinstance(self.mapping_confidence, MappingConfidence):
            raise WorkspaceError("invalid mapping confidence")
        if (
            self.mapping_confidence is MappingConfidence.UNRESOLVED
            and "provisional" not in self.name.casefold()
        ):
            raise WorkspaceError(
                "unresolved Gate metadata names must be explicitly marked provisional"
            )
        _require_nonempty(self.evidence_reference, "Gate metadata evidence reference")
        if not isinstance(self.family, RosterFamily):
            raise WorkspaceError("invalid roster family")
        if self.family is not expected_family:
            raise WorkspaceError(
                f"Gate metadata {self.card_id} family must be {expected_family.value}"
            )
        if not isinstance(self.archetype, GateArchetype):
            raise WorkspaceError("invalid archetype")
        if not isinstance(self.design_tier, DesignTier):
            raise WorkspaceError("invalid design tier")
        _require_nonempty(self.gameplay_identity, "Gate gameplay identity")
        _require_nonempty(self.g_influence_summary, "Gate G influence summary")
        _require_nonempty(self.battle_weight_summary, "Gate battle-weight summary")
        _require_nonempty(self.rule_summary, "Gate rule summary")
        _require_nonempty(
            self.differentiation_rationale, "Gate differentiation rationale"
        )
        if self.net_budget is not None:
            _require_integer(self.net_budget, "Gate net budget")
        if not isinstance(self.review_status, ReviewStatus):
            raise WorkspaceError("invalid review status")

        if self.archetype is GateArchetype.LEGACY:
            if self.design_tier is not DesignTier.UNASSIGNED:
                raise WorkspaceError("legacy metadata must use unassigned design tier")
            if self.net_budget is not None:
                raise WorkspaceError("legacy metadata net budget must be null")
            if self.review_status is not ReviewStatus.PROVISIONAL:
                raise WorkspaceError("legacy metadata must remain provisional")
        else:
            if self.design_tier is DesignTier.UNASSIGNED:
                raise WorkspaceError("live metadata cannot use unassigned design tier")
            if self.net_budget is None:
                raise WorkspaceError("live metadata must define a net budget")
            minimum, maximum = _ARCHETYPE_BUDGET_BANDS[self.archetype]
            if not minimum <= self.net_budget <= maximum:
                raise WorkspaceError(
                    f"Gate net budget must be between {minimum} and {maximum} "
                    f"for {self.archetype.name.lower()}, got {self.net_budget}"
                )
            if self.review_status is ReviewStatus.PROVISIONAL and not final:
                raise WorkspaceError("live metadata must be reviewed or approved")

        if final:
            if self.archetype is GateArchetype.LEGACY:
                raise WorkspaceError("final roster metadata cannot use legacy archetype")
            if self.review_status is not ReviewStatus.APPROVED:
                raise WorkspaceError(
                    f"final Gate metadata {self.card_id} must be approved"
                )
            authored_fields = (
                self.gameplay_identity,
                self.g_influence_summary,
                self.battle_weight_summary,
                self.rule_summary,
                self.differentiation_rationale,
            )
            for value in authored_fields:
                normalized = value.casefold()
                if any(marker in normalized for marker in _PLACEHOLDER_MARKERS):
                    raise WorkspaceError(
                        f"final Gate metadata {self.card_id} contains placeholder text"
                    )

    def to_json(self) -> dict[str, object]:
        return {
            "archetype": int(self.archetype),
            "battle_weight_summary": self.battle_weight_summary,
            "card_id": self.card_id,
            "design_tier": self.design_tier.value,
            "differentiation_rationale": self.differentiation_rationale,
            "evidence_reference": self.evidence_reference,
            "family": self.family.value,
            "g_influence_summary": self.g_influence_summary,
            "gameplay_identity": self.gameplay_identity,
            "mapping_confidence": self.mapping_confidence.value,
            "name": self.name,
            "net_budget": self.net_budget,
            "review_status": self.review_status.value,
            "rule_summary": self.rule_summary,
        }


def _parse_entry(
    value: object, index: int, *, final: bool = False
) -> GateRosterMetadataEntry:
    item = _require_object(value, f"entries[{index}]")
    label = f"entries[{index}]"
    actual_fields = frozenset(item)
    if actual_fields != _ENTRY_FIELDS:
        missing = sorted(_ENTRY_FIELDS - actual_fields)
        extra = sorted(actual_fields - _ENTRY_FIELDS)
        raise WorkspaceError(
            f"{label} entry fields mismatch; missing={missing}, extra={extra}"
        )
    try:
        archetype_value = _require_integer(item["archetype"], f"{label}.archetype")
        try:
            archetype = GateArchetype(archetype_value)
        except ValueError as exc:
            raise WorkspaceError(f"invalid archetype: {archetype_value}") from exc
        raw_budget = item["net_budget"]
        net_budget = (
            None
            if raw_budget is None
            else _require_integer(raw_budget, f"{label}.net_budget")
        )
        entry = GateRosterMetadataEntry(
            card_id=_require_integer(item["card_id"], f"{label}.card_id"),
            name=_require_string(item["name"], f"{label}.name"),
            mapping_confidence=_parse_enum(
                MappingConfidence,
                item["mapping_confidence"],
                "mapping confidence",
            ),
            evidence_reference=_require_string(
                item["evidence_reference"], f"{label}.evidence_reference"
            ),
            family=_parse_enum(
                RosterFamily, item["family"], "roster family"
            ),
            archetype=archetype,
            design_tier=_parse_enum(
                DesignTier, item["design_tier"], "design tier"
            ),
            gameplay_identity=_require_string(
                item["gameplay_identity"], f"{label}.gameplay_identity"
            ),
            g_influence_summary=_require_string(
                item["g_influence_summary"], f"{label}.g_influence_summary"
            ),
            battle_weight_summary=_require_string(
                item["battle_weight_summary"], f"{label}.battle_weight_summary"
            ),
            rule_summary=_require_string(
                item["rule_summary"], f"{label}.rule_summary"
            ),
            net_budget=net_budget,
            differentiation_rationale=_require_string(
                item["differentiation_rationale"],
                f"{label}.differentiation_rationale",
            ),
            review_status=_parse_enum(
                ReviewStatus, item["review_status"], "review status"
            ),
        )
    except KeyError as exc:
        raise WorkspaceError(f"{label} is missing field {exc.args[0]}") from exc
    entry.validate(final=final)
    return entry


def parse_gate_roster_metadata(
    payload: object, *, final: bool = False
) -> tuple[GateRosterMetadataEntry, ...]:
    document = _require_object(payload, "Gate roster metadata document")
    actual_fields = frozenset(document)
    if actual_fields != _ROOT_FIELDS:
        missing = sorted(_ROOT_FIELDS - actual_fields)
        extra = sorted(actual_fields - _ROOT_FIELDS)
        raise WorkspaceError(
            "Gate roster metadata document fields mismatch; "
            f"missing={missing}, extra={extra}"
        )
    if document.get("format_version") != 1:
        raise WorkspaceError("Gate roster metadata format_version must be 1")
    if document.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError(
            f"Gate roster metadata profile_id must be {SUPPORTED_PROFILE_ID}"
        )
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list):
        raise WorkspaceError("Gate roster metadata entries must be a JSON array")
    if len(raw_entries) != RECORD_COUNT:
        raise WorkspaceError(
            f"Gate roster metadata must contain exactly {RECORD_COUNT} entries"
        )

    entries: list[GateRosterMetadataEntry] = []
    card_ids: set[int] = set()
    normalized_names: set[str] = set()
    for index, raw in enumerate(raw_entries):
        entry = _parse_entry(raw, index, final=final)
        if entry.card_id in card_ids:
            raise WorkspaceError(f"duplicate Gate metadata card ID: {entry.card_id}")
        normalized_name = entry.name.strip().casefold()
        if normalized_name in normalized_names:
            raise WorkspaceError(f"duplicate Gate metadata name: {entry.name}")
        card_ids.add(entry.card_id)
        normalized_names.add(normalized_name)
        entries.append(entry)

    expected_ids = set(range(FIRST_CARD_ID, RECORD_COUNT + 1))
    if card_ids != expected_ids:
        missing_ids = sorted(expected_ids - card_ids)
        extra_ids = sorted(card_ids - expected_ids)
        raise WorkspaceError(
            "Gate roster metadata ID coverage is invalid: "
            f"missing={missing_ids}, extra={extra_ids}"
        )
    if tuple(entry.card_id for entry in entries) != tuple(
        range(FIRST_CARD_ID, RECORD_COUNT + 1)
    ):
        raise WorkspaceError("Gate roster metadata entries must use canonical ID order")

    return tuple(entries)


def load_gate_roster_metadata(
    path: Path, *, final: bool = False
) -> tuple[GateRosterMetadataEntry, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"could not load Gate roster metadata {path}: {exc}") from exc
    return parse_gate_roster_metadata(payload, final=final)


def write_gate_roster_metadata(
    path: Path, entries: tuple[GateRosterMetadataEntry, ...], *, final: bool = False
) -> None:
    payload = {
        "entries": [entry.to_json() for entry in entries],
        "format_version": 1,
        "profile_id": SUPPORTED_PROFILE_ID,
    }
    normalized = parse_gate_roster_metadata(payload, final=final)
    output = {
        "entries": [entry.to_json() for entry in normalized],
        "format_version": 1,
        "profile_id": SUPPORTED_PROFILE_ID,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
