from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.discovery import Presence, RuntimeFieldEvidence
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID, Confidence

_VALID_WIDTHS = frozenset({8, 16, 32})
_REQUIRED_FIELDS = frozenset({"landing_result", "shot_condition"})


class LandingOutcome(StrEnum):
    UNOPPOSED_STAND = "unopposed_stand"
    BATTLE_STAND = "battle_stand"

    @property
    def raw_code(self) -> int:
        if self is LandingOutcome.UNOPPOSED_STAND:
            return 2
        return 3


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise WorkspaceError(f"{label} must be a boolean")
    return value


@dataclass(frozen=True)
class LandingFieldEvidence:
    name: str
    value_domain: str
    participant_source: str
    owner_structure: str
    access: str
    width_bits: int
    signed: bool
    initialization: str
    reset: str
    scripted_behavior: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        _require_text(self.name, "landing field name")
        if self.name not in _REQUIRED_FIELDS:
            raise WorkspaceError(f"unsupported landing field: {self.name}")
        if self.width_bits not in _VALID_WIDTHS:
            raise WorkspaceError(
                f"landing field {self.name} width must be 8, 16, or 32 bits"
            )
        if type(self.signed) is not bool:
            raise WorkspaceError(
                f"landing field {self.name} signed must be a boolean"
            )
        for label, value in (
            ("value domain", self.value_domain),
            ("participant source", self.participant_source),
            ("owner structure", self.owner_structure),
            ("access", self.access),
            ("initialization", self.initialization),
            ("reset", self.reset),
            ("scripted behavior", self.scripted_behavior),
            ("evidence", self.evidence),
        ):
            _require_text(value, f"landing field {self.name} {label}")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError(f"landing field {self.name} must be confirmed")


@dataclass(frozen=True)
class LandingContext:
    fields: tuple[LandingFieldEvidence, ...]
    evaluation_boundary: str
    arena_id: RuntimeFieldEvidence
    scripted_paths: tuple[str, ...]

    def validate(self) -> None:
        actual: set[str] = set()
        for field in self.fields:
            field.validate()
            if field.name in actual:
                raise WorkspaceError(f"duplicate landing field: {field.name}")
            actual.add(field.name)
        if actual != _REQUIRED_FIELDS:
            missing = sorted(_REQUIRED_FIELDS - actual)
            extra = sorted(actual - _REQUIRED_FIELDS)
            details: list[str] = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unexpected " + ", ".join(extra))
            raise WorkspaceError(
                "landing context requires landing_result and shot_condition: "
                + "; ".join(details)
            )
        _require_text(self.evaluation_boundary, "landing evaluation boundary")
        if self.arena_id.name != "arena_id":
            raise WorkspaceError("landing context deferred field must be arena_id")
        if self.arena_id.presence is not Presence.DEFERRED:
            raise WorkspaceError("landing context arena_id must remain deferred")
        self.arena_id.validate(required=True, allow_absent=False, allow_deferred=True)
        if not self.scripted_paths or any(
            not value.strip() for value in self.scripted_paths
        ):
            raise WorkspaceError("landing scripted paths must contain nonempty entries")
        if len(set(self.scripted_paths)) != len(self.scripted_paths):
            raise WorkspaceError("landing scripted paths must be unique")

    def field_by_name(self, name: str) -> LandingFieldEvidence:
        for field in self.fields:
            if field.name == name:
                return field
        raise WorkspaceError(f"landing field is unavailable: {name}")


def _parse_landing_field(value: object, index: int) -> LandingFieldEvidence:
    item = _require_object(value, f"landing_fields[{index}]")
    try:
        field = LandingFieldEvidence(
            name=str(item["name"]),
            value_domain=str(item["value_domain"]),
            participant_source=str(item["participant_source"]),
            owner_structure=str(item["owner_structure"]),
            access=str(item["access"]),
            width_bits=_require_integer(
                item["width_bits"], f"landing_fields[{index}].width_bits"
            ),
            signed=_require_bool(
                item["signed"], f"landing_fields[{index}].signed"
            ),
            initialization=str(item["initialization"]),
            reset=str(item["reset"]),
            scripted_behavior=str(item["scripted_behavior"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid landing_fields[{index}]: {exc}") from exc
    field.validate()
    return field


def _parse_arena_id(value: object) -> RuntimeFieldEvidence:
    item = _require_object(value, "arena_id")
    try:
        field = RuntimeFieldEvidence(
            name=str(item["name"]),
            presence=Presence(str(item["presence"])),
            width_bits=None,
            signed=None,
            owner_structure=str(item["owner_structure"]),
            access=str(item["access"]),
            initialization=str(item["initialization"]),
            mutations=tuple(
                str(entry)
                for entry in _require_array(item["mutations"], "arena_id.mutations")
            ),
            lifetime=str(item["lifetime"]),
            reset=str(item["reset"]),
            player_ai_behavior=str(item["player_ai_behavior"]),
            scripted_behavior=str(item["scripted_behavior"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
            allowed_exception=_require_bool(
                item["allowed_exception"], "arena_id.allowed_exception"
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid arena_id: {exc}") from exc
    return field


def normalize_landing_artifact(payload: object) -> LandingContext:
    root = _require_object(payload, "landing artifact")
    if root.get("format_version") != 1:
        raise WorkspaceError("unsupported landing artifact format")
    if root.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("unsupported landing artifact profile")
    try:
        context = LandingContext(
            fields=tuple(
                _parse_landing_field(value, index)
                for index, value in enumerate(
                    _require_array(root.get("landing_fields"), "landing_fields")
                )
            ),
            evaluation_boundary=str(root["evaluation_boundary"]),
            arena_id=_parse_arena_id(root.get("arena_id")),
            scripted_paths=tuple(
                str(value)
                for value in _require_array(
                    root.get("scripted_paths"), "scripted_paths"
                )
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid landing artifact: {exc}") from exc
    context.validate()
    return context
