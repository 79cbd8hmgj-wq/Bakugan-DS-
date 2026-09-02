from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.balance import analyze_gate_balance
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID
from bakugan_ds.gates.record import (
    FIRST_CARD_ID,
    GATE_RECORD_FIELD_NAMES,
    RECORD_COUNT,
    GateArchetype,
    GateRecordV1,
    serialize_record,
)
from bakugan_ds.gates.system2 import FallbackReason, record_fallback_reason

_TEMPLATE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_ROOT_FIELDS = frozenset({"format_version", "profile_id", "templates"})
_TEMPLATE_FIELDS = frozenset({"archetype", "description", "record", "template_id"})
_RECORD_FIELDS = frozenset(GATE_RECORD_FIELD_NAMES) - {"card_id", "archetype"}
_LIVE_ARCHETYPES = tuple(
    archetype for archetype in GateArchetype if archetype is not GateArchetype.LEGACY
)
_MINIMUM_TEMPLATES_PER_ARCHETYPE = 2


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise WorkspaceError(f"{label} must be a string")
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")
    return value


def _require_vector(value: object, label: str) -> tuple[int, ...]:
    items = _require_array(value, label)
    return tuple(_require_integer(item, f"{label}[{index}]") for index, item in enumerate(items))


@dataclass(frozen=True)
class GateRosterTemplate:
    template_id: str
    archetype: GateArchetype
    description: str
    prototype: GateRecordV1

    @property
    def net_budget(self) -> int:
        return analyze_gate_balance(self.prototype).budget.net_budget

    def validate(self) -> None:
        if not _TEMPLATE_ID.fullmatch(self.template_id):
            raise WorkspaceError("Gate roster template ID must use lowercase kebab-case")
        if not self.description.strip():
            raise WorkspaceError("Gate roster template description must be nonempty")
        if self.archetype is GateArchetype.LEGACY:
            raise WorkspaceError("Gate roster templates require a live archetype")
        if self.prototype.card_id != FIRST_CARD_ID:
            raise WorkspaceError("Gate roster template prototype must use placeholder card ID 1")
        try:
            prototype_archetype = GateArchetype(self.prototype.archetype)
        except ValueError as exc:
            raise WorkspaceError(
                f"unsupported Gate roster template archetype: {self.prototype.archetype}"
            ) from exc
        if prototype_archetype is not self.archetype:
            raise WorkspaceError("Gate roster template archetype does not match its prototype")
        reason = record_fallback_reason(self.prototype)
        if reason is not FallbackReason.NONE:
            raise WorkspaceError(
                f"Gate roster template uses unsupported runtime semantics: {reason.value}"
            )
        analyze_gate_balance(self.prototype)

    def instantiate(self, *, card_id: int) -> GateRecordV1:
        if (
            isinstance(card_id, bool)
            or not isinstance(card_id, int)
            or not FIRST_CARD_ID <= card_id <= RECORD_COUNT
        ):
            raise WorkspaceError(f"card ID must be between {FIRST_CARD_ID} and {RECORD_COUNT}")
        record = replace(self.prototype, card_id=card_id)
        reason = record_fallback_reason(record)
        if reason is not FallbackReason.NONE:
            raise WorkspaceError(
                f"instantiated Gate roster template is unsupported: {reason.value}"
            )
        analyze_gate_balance(record)
        return record

    def runtime_signature(self) -> bytes:
        """Return exact version-1 runtime bytes excluding the assigned card ID."""
        return serialize_record(self.prototype)[1:]

    def to_json(self) -> dict[str, object]:
        record = {
            field: getattr(self.prototype, field)
            for field in GATE_RECORD_FIELD_NAMES
            if field not in {"card_id", "archetype"}
        }
        record["attribute_modifiers"] = list(self.prototype.attribute_modifiers)
        record["battle_weights"] = list(self.prototype.battle_weights)
        return {
            "archetype": int(self.archetype),
            "description": self.description,
            "record": record,
            "template_id": self.template_id,
        }


def _parse_record(
    value: object,
    *,
    archetype: GateArchetype,
    label: str,
) -> GateRecordV1:
    item = _require_object(value, label)
    actual_fields = frozenset(item)
    if actual_fields != _RECORD_FIELDS:
        missing = sorted(_RECORD_FIELDS - actual_fields)
        extra = sorted(actual_fields - _RECORD_FIELDS)
        raise WorkspaceError(f"{label} record fields mismatch; missing={missing}, extra={extra}")
    try:
        record = GateRecordV1(
            card_id=FIRST_CARD_ID,
            archetype=int(archetype),
            flags=_require_integer(item["flags"], f"{label}.flags"),
            flat_bonus_g=_require_integer(item["flat_bonus_g"], f"{label}.flat_bonus_g"),
            percent_q8_8=_require_integer(item["percent_q8_8"], f"{label}.percent_q8_8"),
            attribute_modifiers=_require_vector(
                item["attribute_modifiers"], f"{label}.attribute_modifiers"
            ),
            battle_weights=_require_vector(item["battle_weights"], f"{label}.battle_weights"),
            preferred_type=_require_integer(item["preferred_type"], f"{label}.preferred_type"),
            condition_id=_require_integer(item["condition_id"], f"{label}.condition_id"),
            effect_id=_require_integer(item["effect_id"], f"{label}.effect_id"),
            drawback_id=_require_integer(item["drawback_id"], f"{label}.drawback_id"),
            effect_value=_require_integer(item["effect_value"], f"{label}.effect_value"),
            drawback_value=_require_integer(item["drawback_value"], f"{label}.drawback_value"),
            activation_limit=_require_integer(
                item["activation_limit"], f"{label}.activation_limit"
            ),
            fatigue_rate=_require_integer(item["fatigue_rate"], f"{label}.fatigue_rate"),
            target_mode=_require_integer(item["target_mode"], f"{label}.target_mode"),
            timing_phase=_require_integer(item["timing_phase"], f"{label}.timing_phase"),
            condition_value=_require_integer(item["condition_value"], f"{label}.condition_value"),
            secondary_effect_id=_require_integer(
                item["secondary_effect_id"], f"{label}.secondary_effect_id"
            ),
            secondary_condition_id=_require_integer(
                item["secondary_condition_id"],
                f"{label}.secondary_condition_id",
            ),
            secondary_value=_require_integer(item["secondary_value"], f"{label}.secondary_value"),
            reserved=_require_integer(item["reserved"], f"{label}.reserved"),
        )
    except KeyError as exc:
        raise WorkspaceError(f"{label} is missing field {exc.args[0]}") from exc
    return record


def _parse_template(value: object, index: int) -> GateRosterTemplate:
    label = f"templates[{index}]"
    item = _require_object(value, label)
    actual_fields = frozenset(item)
    if actual_fields != _TEMPLATE_FIELDS:
        missing = sorted(_TEMPLATE_FIELDS - actual_fields)
        extra = sorted(actual_fields - _TEMPLATE_FIELDS)
        raise WorkspaceError(f"{label} template fields mismatch; missing={missing}, extra={extra}")
    try:
        archetype_value = _require_integer(item["archetype"], f"{label}.archetype")
        try:
            archetype = GateArchetype(archetype_value)
        except ValueError as exc:
            raise WorkspaceError(
                f"unsupported Gate roster template archetype: {archetype_value}"
            ) from exc
        template = GateRosterTemplate(
            template_id=_require_string(item["template_id"], f"{label}.template_id"),
            archetype=archetype,
            description=_require_string(item["description"], f"{label}.description"),
            prototype=_parse_record(item["record"], archetype=archetype, label=f"{label}.record"),
        )
    except KeyError as exc:
        raise WorkspaceError(f"{label} is missing field {exc.args[0]}") from exc
    template.validate()
    return template


def parse_gate_roster_templates(payload: object) -> tuple[GateRosterTemplate, ...]:
    document = _require_object(payload, "Gate roster template document")
    actual_fields = frozenset(document)
    if actual_fields != _ROOT_FIELDS:
        missing = sorted(_ROOT_FIELDS - actual_fields)
        extra = sorted(actual_fields - _ROOT_FIELDS)
        raise WorkspaceError(
            f"Gate roster template document fields mismatch; missing={missing}, extra={extra}"
        )
    if document.get("format_version") != 1:
        raise WorkspaceError("Gate roster template format_version must be 1")
    if document.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError(f"Gate roster template profile_id must be {SUPPORTED_PROFILE_ID}")

    raw_templates = _require_array(document.get("templates"), "templates")
    templates: list[GateRosterTemplate] = []
    template_ids: set[str] = set()
    signatures: dict[bytes, str] = {}
    for index, raw_template in enumerate(raw_templates):
        template = _parse_template(raw_template, index)
        if template.template_id in template_ids:
            raise WorkspaceError(f"duplicate Gate roster template ID: {template.template_id}")
        signature = template.runtime_signature()
        if signature in signatures:
            raise WorkspaceError(
                "duplicate runtime signature for Gate roster templates "
                f"{signatures[signature]} and {template.template_id}"
            )
        template_ids.add(template.template_id)
        signatures[signature] = template.template_id
        templates.append(template)

    counts = Counter(template.archetype for template in templates)
    for archetype in _LIVE_ARCHETYPES:
        if counts[archetype] < _MINIMUM_TEMPLATES_PER_ARCHETYPE:
            raise WorkspaceError(
                "each live archetype requires at least two templates; "
                f"{archetype.name.lower()} has {counts[archetype]}"
            )
    extra_archetypes = set(counts) - set(_LIVE_ARCHETYPES)
    if extra_archetypes:
        raise WorkspaceError("Gate roster templates contain a non-live archetype")

    canonical_order = sorted(
        templates, key=lambda template: (int(template.archetype), template.template_id)
    )
    if templates != canonical_order:
        raise WorkspaceError("Gate roster templates must use canonical archetype/template order")
    return tuple(templates)


def load_gate_roster_templates(path: Path) -> tuple[GateRosterTemplate, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"could not load Gate roster templates {path}: {exc}") from exc
    return parse_gate_roster_templates(payload)


def write_gate_roster_templates(
    path: Path,
    templates: tuple[GateRosterTemplate, ...],
) -> None:
    payload = {
        "format_version": 1,
        "profile_id": SUPPORTED_PROFILE_ID,
        "templates": [template.to_json() for template in templates],
    }
    normalized = parse_gate_roster_templates(payload)
    output = {
        "format_version": 1,
        "profile_id": SUPPORTED_PROFILE_ID,
        "templates": [template.to_json() for template in normalized],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
