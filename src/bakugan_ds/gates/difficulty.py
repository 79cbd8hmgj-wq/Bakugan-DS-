from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID, Confidence

_VALID_WIDTHS = frozenset({8, 16, 32})


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")


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


@dataclass(frozen=True)
class DifficultyValue:
    value: int
    label: str
    evidence: str

    def validate(self, *, width_bits: int) -> None:
        if self.value < 0 or self.value >= (1 << width_bits):
            raise WorkspaceError(
                f"difficulty value {self.value} does not fit {width_bits} bits"
            )
        _require_text(self.label, "difficulty label")
        _require_text(self.evidence, f"difficulty value {self.value} evidence")


@dataclass(frozen=True)
class DifficultyEvidence:
    owner_structure: str
    access: str
    width_bits: int
    values: tuple[DifficultyValue, ...]
    initialization: str
    profile_change: str
    battle_load: str
    ai_consumers: tuple[str, ...]
    reset: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        for label, value in (
            ("difficulty owner structure", self.owner_structure),
            ("difficulty access", self.access),
            ("difficulty initialization", self.initialization),
            ("difficulty profile change", self.profile_change),
            ("difficulty battle load", self.battle_load),
            ("difficulty reset", self.reset),
            ("difficulty evidence", self.evidence),
        ):
            _require_text(value, label)
        if self.width_bits not in _VALID_WIDTHS:
            raise WorkspaceError("difficulty width must be 8, 16, or 32 bits")
        if len(self.values) < 2:
            raise WorkspaceError("difficulty requires at least two confirmed values")

        raw_values: set[int] = set()
        labels: set[str] = set()
        for entry in self.values:
            entry.validate(width_bits=self.width_bits)
            if entry.value in raw_values:
                raise WorkspaceError(
                    f"duplicate difficulty value: {entry.value}"
                )
            raw_values.add(entry.value)
            normalized_label = entry.label.strip().casefold()
            if normalized_label in labels:
                raise WorkspaceError(
                    f"duplicate difficulty label: {entry.label}"
                )
            labels.add(normalized_label)

        if not self.ai_consumers:
            raise WorkspaceError("difficulty AI consumers must not be empty")
        normalized_consumers: set[str] = set()
        for consumer in self.ai_consumers:
            _require_text(consumer, "difficulty AI consumer")
            normalized = consumer.strip().casefold()
            if normalized in normalized_consumers:
                raise WorkspaceError(
                    f"duplicate difficulty AI consumer: {consumer}"
                )
            normalized_consumers.add(normalized)

        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError("difficulty evidence must be confirmed")


def _parse_value(value: object, index: int) -> DifficultyValue:
    item = _require_object(value, f"values[{index}]")
    try:
        return DifficultyValue(
            value=_require_integer(item["value"], f"values[{index}].value"),
            label=str(item["label"]),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid values[{index}]: {exc}") from exc


def normalize_difficulty_artifact(payload: object) -> DifficultyEvidence:
    root = _require_object(payload, "difficulty artifact")
    if root.get("format_version") != 1:
        raise WorkspaceError("unsupported difficulty artifact format")
    if root.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("unsupported difficulty artifact profile")
    try:
        evidence = DifficultyEvidence(
            owner_structure=str(root["owner_structure"]),
            access=str(root["access"]),
            width_bits=_require_integer(root["width_bits"], "width_bits"),
            values=tuple(
                _parse_value(value, index)
                for index, value in enumerate(
                    _require_array(root.get("values"), "values")
                )
            ),
            initialization=str(root["initialization"]),
            profile_change=str(root["profile_change"]),
            battle_load=str(root["battle_load"]),
            ai_consumers=tuple(
                str(value)
                for value in _require_array(
                    root.get("ai_consumers"), "ai_consumers"
                )
            ),
            reset=str(root["reset"]),
            confidence=Confidence(str(root["confidence"])),
            evidence=str(root["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid difficulty artifact: {exc}") from exc
    evidence.validate()
    return evidence
