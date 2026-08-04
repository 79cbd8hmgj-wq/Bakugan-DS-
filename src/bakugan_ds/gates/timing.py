from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID, Confidence

_COMPONENT_BASES = {
    "arm9": 0x02000000,
    "overlay_0007": 0x02219440,
}


class EffectPhase(StrEnum):
    PRE_GATE = "pre_gate"
    POST_GATE = "post_gate"
    PRE_BATTLE_TYPE = "pre_battle_type"
    POST_BATTLE_TYPE = "post_battle_type"
    BATTLE_START = "battle_start"
    ABILITY_ACTIVATION = "ability_activation"
    ABILITY_RESOLUTION = "ability_resolution"
    BATTLE_RESULT = "battle_result"
    GATE_CAPTURE = "gate_capture"
    GATE_REMOVAL = "gate_removal"
    ROUND_RESET = "round_reset"
    MATCH_RESET = "match_reset"


_PHASE_ORDER = tuple(EffectPhase)


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")


def _require_text_items(values: tuple[str, ...], label: str) -> None:
    if not values or any(not value.strip() for value in values):
        raise WorkspaceError(f"{label} must contain nonempty entries")
    normalized = tuple(value.strip().casefold() for value in values)
    if len(set(normalized)) != len(normalized):
        raise WorkspaceError(f"{label} must contain unique entries")


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
class TimingBoundaryEvidence:
    phase: EffectPhase
    component: str
    address: int
    component_offset: int
    live_registers: tuple[str, ...]
    owner_objects: tuple[str, ...]
    valid_fields: tuple[str, ...]
    mutations_allowed: str
    scripted_bypass: str
    rollback: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        if not isinstance(self.phase, EffectPhase):
            raise WorkspaceError("effect phase is invalid")
        _require_text(self.component, f"{self.phase} component")
        base = _COMPONENT_BASES.get(self.component)
        if base is None:
            raise WorkspaceError(
                f"unsupported timing component for {self.phase}: {self.component}"
            )
        if self.address < base:
            raise WorkspaceError(f"{self.phase} address precedes component base")
        if self.component_offset < 0:
            raise WorkspaceError(f"{self.phase} component offset must be nonnegative")
        if self.address - base != self.component_offset:
            raise WorkspaceError(
                f"{self.phase} address and component offset are inconsistent"
            )
        _require_text_items(self.live_registers, f"{self.phase} live registers")
        _require_text_items(self.owner_objects, f"{self.phase} owner objects")
        _require_text_items(self.valid_fields, f"{self.phase} valid fields")
        _require_text(self.mutations_allowed, f"{self.phase} mutation policy")
        _require_text(self.scripted_bypass, f"{self.phase} scripted bypass")
        _require_text(self.rollback, f"{self.phase} rollback")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError(f"{self.phase} confidence is invalid")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError(f"{self.phase} timing boundary must be confirmed")
        _require_text(self.evidence, f"{self.phase} evidence")


@dataclass(frozen=True)
class TimingModel:
    boundaries: tuple[TimingBoundaryEvidence, ...]

    def validate(self) -> None:
        required = frozenset(EffectPhase)
        phases: set[EffectPhase] = set()
        addresses: set[tuple[str, int]] = set()
        for boundary in self.boundaries:
            boundary.validate()
            if boundary.phase in phases:
                raise WorkspaceError(
                    f"duplicate effect timing phase: {boundary.phase.value}"
                )
            phases.add(boundary.phase)
            location = (boundary.component, boundary.address)
            if location in addresses:
                raise WorkspaceError(
                    "effect timing boundaries must use distinct instruction addresses"
                )
            addresses.add(location)
        missing = sorted(phase.value for phase in required - phases)
        if missing:
            raise WorkspaceError(
                "effect timing model is missing phases: " + ", ".join(missing)
            )
        extras = sorted(phase.value for phase in phases - required)
        if extras:
            raise WorkspaceError(
                "effect timing model has unsupported phases: " + ", ".join(extras)
            )
        if len(self.boundaries) != len(required):
            raise WorkspaceError("effect timing model must contain exactly 12 boundaries")
        if tuple(boundary.phase for boundary in self.boundaries) != _PHASE_ORDER:
            raise WorkspaceError("timing boundaries must use canonical phase order")

    def boundary_for(self, phase: EffectPhase) -> TimingBoundaryEvidence:
        if not isinstance(phase, EffectPhase):
            raise WorkspaceError("timing phase lookup is invalid")
        match = next(
            (boundary for boundary in self.boundaries if boundary.phase is phase),
            None,
        )
        if match is None:
            raise WorkspaceError(f"missing timing boundary: {phase.value}")
        return match


def _parse_text_tuple(value: object, label: str) -> tuple[str, ...]:
    return tuple(str(item) for item in _require_array(value, label))


def _parse_boundary(value: object, index: int) -> TimingBoundaryEvidence:
    item = _require_object(value, f"boundaries[{index}]")
    try:
        return TimingBoundaryEvidence(
            phase=EffectPhase(str(item["phase"])),
            component=str(item["component"]),
            address=_require_integer(item["address"], f"boundaries[{index}].address"),
            component_offset=_require_integer(
                item["component_offset"],
                f"boundaries[{index}].component_offset",
            ),
            live_registers=_parse_text_tuple(
                item["live_registers"],
                f"boundaries[{index}].live_registers",
            ),
            owner_objects=_parse_text_tuple(
                item["owner_objects"],
                f"boundaries[{index}].owner_objects",
            ),
            valid_fields=_parse_text_tuple(
                item["valid_fields"],
                f"boundaries[{index}].valid_fields",
            ),
            mutations_allowed=str(item["mutations_allowed"]),
            scripted_bypass=str(item["scripted_bypass"]),
            rollback=str(item["rollback"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid boundaries[{index}]: {exc}") from exc


def normalize_timing_artifact(payload: object) -> TimingModel:
    root = _require_object(payload, "timing artifact")
    if root.get("format_version") != 1:
        raise WorkspaceError("unsupported timing artifact format")
    if root.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("unsupported timing artifact profile")
    model = TimingModel(
        boundaries=tuple(
            _parse_boundary(value, index)
            for index, value in enumerate(
                _require_array(root.get("boundaries"), "boundaries")
            )
        )
    )
    model.validate()
    return model
