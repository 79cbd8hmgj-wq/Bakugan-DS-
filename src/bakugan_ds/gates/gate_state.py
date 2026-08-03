from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.discovery import Presence
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID, Confidence


class GateStateKind(StrEnum):
    ACTIVATION_COUNT = "activation_count"
    REUSABLE = "reusable"
    CAPTURED = "captured"
    REMOVED = "removed"
    RESET = "reset"


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


@dataclass(frozen=True)
class GateStateEvidence:
    kind: GateStateKind
    presence: Presence
    owner_structure: str
    access: str
    initialization: str
    mutations: tuple[str, ...]
    reset: str
    confidence: Confidence
    evidence: str
    replacement_plan: str = ""

    def validate(self) -> None:
        if not isinstance(self.kind, GateStateKind):
            raise WorkspaceError("Gate state kind is invalid")
        if not isinstance(self.presence, Presence):
            raise WorkspaceError(f"Gate state {self.kind} has invalid presence")
        if self.presence is Presence.DEFERRED:
            raise WorkspaceError(f"Gate state {self.kind} cannot be deferred")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError(f"Gate state {self.kind} has invalid confidence")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError(f"Gate state {self.kind} must be confirmed")
        for label, value in (
            ("owner structure", self.owner_structure),
            ("access", self.access),
            ("initialization", self.initialization),
            ("reset", self.reset),
            ("evidence", self.evidence),
        ):
            _require_text(value, f"Gate state {self.kind} {label}")
        if not self.mutations or any(not value.strip() for value in self.mutations):
            raise WorkspaceError(
                f"Gate state {self.kind} mutations must contain nonempty entries"
            )
        if len(set(self.mutations)) != len(self.mutations):
            raise WorkspaceError(f"Gate state {self.kind} mutations must be unique")
        if self.presence is Presence.ABSENT:
            _require_text(
                self.replacement_plan,
                f"absent Gate state {self.kind} replacement plan",
            )
        elif self.replacement_plan.strip():
            raise WorkspaceError(
                f"present Gate state {self.kind} cannot define a replacement plan"
            )


@dataclass(frozen=True)
class GateStateModel:
    states: tuple[GateStateEvidence, ...]
    transitions: tuple[str, ...]
    safe_extension_storage: str

    def validate(self) -> None:
        by_kind: dict[GateStateKind, GateStateEvidence] = {}
        for state in self.states:
            state.validate()
            if state.kind in by_kind:
                raise WorkspaceError(f"duplicate Gate state kind: {state.kind}")
            by_kind[state.kind] = state

        expected = set(GateStateKind)
        actual = set(by_kind)
        if actual != expected:
            missing = sorted(kind.value for kind in expected - actual)
            extra = sorted(kind.value for kind in actual - expected)
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unexpected " + ", ".join(extra))
            raise WorkspaceError(
                "Gate state model requires all lifecycle kinds: " + "; ".join(details)
            )

        activation = by_kind[GateStateKind.ACTIVATION_COUNT]
        if activation.presence is not Presence.ABSENT:
            raise WorkspaceError("original activation count must be confirmed absent")
        for kind in (
            GateStateKind.REUSABLE,
            GateStateKind.CAPTURED,
            GateStateKind.REMOVED,
            GateStateKind.RESET,
        ):
            if by_kind[kind].presence is not Presence.PRESENT:
                raise WorkspaceError(f"Gate state {kind} must be present")

        if not self.transitions or any(
            not transition.strip() for transition in self.transitions
        ):
            raise WorkspaceError("Gate transitions must contain nonempty entries")
        if len(set(self.transitions)) != len(self.transitions):
            raise WorkspaceError("Gate transitions must be unique")
        _require_text(self.safe_extension_storage, "safe extension storage")

    def state_for(self, kind: GateStateKind) -> GateStateEvidence:
        if not isinstance(kind, GateStateKind):
            raise WorkspaceError("Gate state lookup kind is invalid")
        for state in self.states:
            if state.kind is kind:
                return state
        raise WorkspaceError(f"Gate state is unavailable: {kind}")


def _parse_state(value: object, index: int) -> GateStateEvidence:
    item = _require_object(value, f"states[{index}]")
    try:
        state = GateStateEvidence(
            kind=GateStateKind(str(item["kind"])),
            presence=Presence(str(item["presence"])),
            owner_structure=str(item["owner_structure"]),
            access=str(item["access"]),
            initialization=str(item["initialization"]),
            mutations=tuple(
                str(entry)
                for entry in _require_array(
                    item["mutations"], f"states[{index}].mutations"
                )
            ),
            reset=str(item["reset"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
            replacement_plan=str(item.get("replacement_plan", "")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid states[{index}]: {exc}") from exc
    state.validate()
    return state


def normalize_gate_state_artifact(payload: object) -> GateStateModel:
    root = _require_object(payload, "Gate-state artifact")
    if root.get("format_version") != 1:
        raise WorkspaceError("unsupported Gate-state artifact format")
    if root.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("unsupported Gate-state artifact profile")
    try:
        model = GateStateModel(
            states=tuple(
                _parse_state(value, index)
                for index, value in enumerate(
                    _require_array(root.get("states"), "states")
                )
            ),
            transitions=tuple(
                str(value)
                for value in _require_array(root.get("transitions"), "transitions")
            ),
            safe_extension_storage=str(root["safe_extension_storage"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid Gate-state artifact: {exc}") from exc
    model.validate()
    return model
