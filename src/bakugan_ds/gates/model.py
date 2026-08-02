from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError

ATTRIBUTE_COUNT = 6
SUPPORTED_PROFILE_ID = "b6re_rev0"
_VALID_ELEMENT_WIDTHS = frozenset({1, 2, 4})
_HEX_DIGITS = frozenset("0123456789abcdef")


class Confidence(StrEnum):
    CANDIDATE = "candidate"
    PROBABLE = "probable"
    CONFIRMED = "confirmed"


def _require_nonempty(value: str, label: str) -> None:
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")


def _require_nonnegative(value: int, label: str) -> None:
    if value < 0:
        raise WorkspaceError(f"{label} must be nonnegative")


def _validate_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in _HEX_DIGITS for character in value):
        raise WorkspaceError(f"{label} must be a 64-character lowercase SHA-256 value")


@dataclass(frozen=True)
class AddressRef:
    component: str
    runtime_address: int
    component_offset: int
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        _require_nonempty(self.component, "component")
        _require_nonnegative(self.runtime_address, "runtime address")
        _require_nonnegative(self.component_offset, "component offset")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("confidence must be candidate, probable, or confirmed")
        _require_nonempty(self.evidence, "evidence")


@dataclass(frozen=True)
class GateControlCase:
    card_id: int
    attribute_id: int
    expected_bonus_g: int
    evidence_id: str

    def validate(self) -> None:
        _require_nonnegative(self.card_id, "card ID")
        if not 0 <= self.attribute_id < ATTRIBUTE_COUNT:
            raise WorkspaceError(
                f"attribute ID must be between 0 and {ATTRIBUTE_COUNT - 1}, got {self.attribute_id}"
            )
        if self.expected_bonus_g % 10 != 0:
            raise WorkspaceError("expected Gate bonus G must be divisible by 10")
        _require_nonempty(self.evidence_id, "evidence ID")


@dataclass(frozen=True)
class LegacyGateTableSpec:
    profile_id: str
    runtime_address: int
    element_width: int
    signed: bool
    record_stride: int
    record_count: int
    attribute_order: tuple[str, ...]
    region_sha256: str
    confidence: Confidence
    control_cases: tuple[GateControlCase, ...]

    @property
    def table_size(self) -> int:
        return self.record_stride * self.record_count

    def validate(self) -> None:
        if self.profile_id != SUPPORTED_PROFILE_ID:
            raise WorkspaceError(
                "unsupported Gate table profile: "
                f"expected {SUPPORTED_PROFILE_ID}, got {self.profile_id}"
            )
        _require_nonnegative(self.runtime_address, "runtime address")
        if self.element_width not in _VALID_ELEMENT_WIDTHS:
            raise WorkspaceError("element width must be 1, 2, or 4 bytes")
        if type(self.signed) is not bool:
            raise WorkspaceError("signed must be a boolean")
        expected_stride = self.element_width * ATTRIBUTE_COUNT
        if self.record_stride != expected_stride:
            raise WorkspaceError(
                f"record stride must equal element width * 6 ({expected_stride}), "
                f"got {self.record_stride}"
            )
        if self.record_count <= 0:
            raise WorkspaceError("record count must be positive")
        if len(self.attribute_order) != ATTRIBUTE_COUNT:
            raise WorkspaceError("attribute order must contain exactly six entries")
        normalized_attributes = tuple(value.strip().lower() for value in self.attribute_order)
        if any(not value for value in normalized_attributes):
            raise WorkspaceError("attribute order entries must be nonempty")
        if len(set(normalized_attributes)) != ATTRIBUTE_COUNT:
            raise WorkspaceError("attribute order entries must be unique")
        _validate_sha256(self.region_sha256, "region_sha256")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("confidence must be candidate, probable, or confirmed")

        evidence_ids: set[str] = set()
        for control_case in self.control_cases:
            control_case.validate()
            if control_case.card_id >= self.record_count:
                raise WorkspaceError(
                    f"control case card ID {control_case.card_id} is outside record count "
                    f"{self.record_count}"
                )
            if control_case.evidence_id in evidence_ids:
                raise WorkspaceError(
                    f"duplicate control-case evidence ID: {control_case.evidence_id}"
                )
            evidence_ids.add(control_case.evidence_id)
