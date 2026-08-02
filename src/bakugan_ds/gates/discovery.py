from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.io import load_json_object
from bakugan_ds.gates.model import Confidence

_VALID_WIDTHS = frozenset({8, 16, 32, 64})


class Presence(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    DEFERRED = "deferred"


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")


def _require_text_items(values: tuple[str, ...], label: str) -> None:
    if not values or any(not value.strip() for value in values):
        raise WorkspaceError(f"{label} must contain nonempty entries")


@dataclass(frozen=True)
class RuntimeFieldEvidence:
    name: str
    presence: Presence
    width_bits: int | None
    signed: bool | None
    owner_structure: str
    access: str
    initialization: str
    mutations: tuple[str, ...]
    lifetime: str
    reset: str
    player_ai_behavior: str
    scripted_behavior: str
    confidence: Confidence
    evidence: str
    replacement_plan: str = ""
    allowed_exception: bool = False

    def validate(
        self,
        *,
        required: bool = False,
        allow_absent: bool = True,
        allow_deferred: bool = True,
    ) -> None:
        _require_text(self.name, "runtime field name")
        if not isinstance(self.presence, Presence):
            raise WorkspaceError(f"runtime field {self.name} has invalid presence")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError(f"runtime field {self.name} has invalid confidence")
        for label, value in (
            ("owner structure", self.owner_structure),
            ("access", self.access),
            ("initialization", self.initialization),
            ("lifetime", self.lifetime),
            ("reset", self.reset),
            ("player/AI behavior", self.player_ai_behavior),
            ("scripted behavior", self.scripted_behavior),
            ("evidence", self.evidence),
        ):
            _require_text(value, f"runtime field {self.name} {label}")
        _require_text_items(self.mutations, f"runtime field {self.name} mutations")

        if self.presence is Presence.PRESENT:
            if self.width_bits not in _VALID_WIDTHS:
                raise WorkspaceError(
                    f"runtime field {self.name} width must be 8, 16, 32, or 64 bits"
                )
            if type(self.signed) is not bool:
                raise WorkspaceError(
                    f"runtime field {self.name} signed must be a boolean"
                )
            if self.allowed_exception:
                raise WorkspaceError(
                    f"present runtime field {self.name} cannot use an exception"
                )
            if required and self.confidence is not Confidence.CONFIRMED:
                raise WorkspaceError(
                    f"required runtime field {self.name} must be confirmed"
                )
            return

        if self.width_bits is not None or self.signed is not None:
            raise WorkspaceError(
                f"non-present runtime field {self.name} cannot define width or signedness"
            )

        if self.presence is Presence.ABSENT:
            if required and not allow_absent:
                raise WorkspaceError(
                    f"required runtime field {self.name} cannot be absent"
                )
            if self.confidence is not Confidence.CONFIRMED:
                raise WorkspaceError(
                    f"absent runtime field {self.name} must be confirmed"
                )
            _require_text(
                self.replacement_plan,
                f"absent runtime field {self.name} replacement plan",
            )
            if self.allowed_exception:
                raise WorkspaceError(
                    f"absent runtime field {self.name} cannot use an exception"
                )
            return

        if self.name != "arena_id":
            raise WorkspaceError("only arena_id may be deferred")
        if required and not allow_deferred:
            raise WorkspaceError("required runtime field arena_id cannot be deferred")
        if not self.allowed_exception:
            raise WorkspaceError("deferred arena_id must set allowed_exception")
        if self.confidence is Confidence.CONFIRMED:
            raise WorkspaceError("deferred arena_id cannot be marked confirmed")
        if self.replacement_plan.strip():
            raise WorkspaceError("deferred arena_id cannot define a replacement plan")


@dataclass(frozen=True)
class BehaviorCheck:
    name: str
    confidence: Confidence
    evidence: str

    def validate(self, *, required: bool = False) -> None:
        _require_text(self.name, "behavior-check name")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError(f"behavior check {self.name} has invalid confidence")
        _require_text(self.evidence, f"behavior check {self.name} evidence")
        if required and self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError(f"required behavior check {self.name} must be confirmed")


@dataclass(frozen=True)
class DiscoveryArtifact:
    domain: str
    fields: tuple[RuntimeFieldEvidence, ...]
    checks: tuple[BehaviorCheck, ...]
    unresolved: tuple[str, ...]

    def validate(self) -> None:
        _require_text(self.domain, "discovery domain")
        names: set[str] = set()
        for field in self.fields:
            field.validate()
            if field.name in names:
                raise WorkspaceError(f"duplicate discovery entry: {field.name}")
            names.add(field.name)
        for check in self.checks:
            check.validate()
            if check.name in names:
                raise WorkspaceError(f"duplicate discovery entry: {check.name}")
            names.add(check.name)
        if len(set(self.unresolved)) != len(self.unresolved):
            raise WorkspaceError("discovery unresolved entries must be unique")
        if any(not value.strip() for value in self.unresolved):
            raise WorkspaceError("discovery unresolved entries must be nonempty")
        unresolved = set(self.unresolved)
        for field in self.fields:
            if field.presence is Presence.DEFERRED and field.name not in unresolved:
                raise WorkspaceError(
                    f"deferred field {field.name} must appear in unresolved"
                )

    def field_by_name(self, name: str) -> RuntimeFieldEvidence | None:
        return next((field for field in self.fields if field.name == name), None)

    def check_by_name(self, name: str) -> BehaviorCheck | None:
        return next((check for check in self.checks if check.name == name), None)


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise WorkspaceError(f"{label} must be a boolean")
    return value


def _optional_integer(value: object, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer or null")
    return value


def _optional_bool(value: object, label: str) -> bool | None:
    if value is None:
        return None
    return _require_bool(value, label)


def _parse_field(value: object, index: int) -> RuntimeFieldEvidence:
    item = _require_object(value, f"fields[{index}]")
    try:
        field = RuntimeFieldEvidence(
            name=str(item["name"]),
            presence=Presence(str(item["presence"])),
            width_bits=_optional_integer(
                item.get("width_bits"), f"fields[{index}].width_bits"
            ),
            signed=_optional_bool(item.get("signed"), f"fields[{index}].signed"),
            owner_structure=str(item["owner_structure"]),
            access=str(item["access"]),
            initialization=str(item["initialization"]),
            mutations=tuple(
                str(entry)
                for entry in _require_array(
                    item["mutations"], f"fields[{index}].mutations"
                )
            ),
            lifetime=str(item["lifetime"]),
            reset=str(item["reset"]),
            player_ai_behavior=str(item["player_ai_behavior"]),
            scripted_behavior=str(item["scripted_behavior"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
            replacement_plan=str(item.get("replacement_plan", "")),
            allowed_exception=_require_bool(
                item.get("allowed_exception", False),
                f"fields[{index}].allowed_exception",
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid fields[{index}]: {exc}") from exc
    field.validate()
    return field


def _parse_check(value: object, index: int) -> BehaviorCheck:
    item = _require_object(value, f"checks[{index}]")
    try:
        check = BehaviorCheck(
            name=str(item["name"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid checks[{index}]: {exc}") from exc
    check.validate()
    return check


def load_discovery_artifact(path: Path) -> DiscoveryArtifact:
    payload = load_json_object(path)
    if payload.get("format_version") != 1:
        raise WorkspaceError(f"unsupported discovery format in {path}")
    try:
        artifact = DiscoveryArtifact(
            domain=str(payload["domain"]),
            fields=tuple(
                _parse_field(value, index)
                for index, value in enumerate(
                    _require_array(payload.get("fields"), "fields")
                )
            ),
            checks=tuple(
                _parse_check(value, index)
                for index, value in enumerate(
                    _require_array(payload.get("checks"), "checks")
                )
            ),
            unresolved=tuple(
                str(value)
                for value in _require_array(payload.get("unresolved"), "unresolved")
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid discovery artifact {path}: {exc}") from exc
    artifact.validate()
    return artifact
