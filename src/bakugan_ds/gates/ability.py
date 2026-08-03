from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence, SUPPORTED_PROFILE_ID


class AbilityParticipant(StrEnum):
    PLAYER = "player"
    OPPONENT = "opponent"


class AbilityPhase(StrEnum):
    AVAILABLE = "available"
    SELECTED = "selected"
    ACTIVATED = "activated"
    RESOLVED = "resolved"
    USED = "used"
    RESET = "reset"


_PHASE_ORDER = tuple(AbilityPhase)
_VALID_WIDTHS = frozenset({8, 16, 32})


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


@dataclass(frozen=True)
class AbilityStateEvidence:
    participant: AbilityParticipant
    phase: AbilityPhase
    owner_structure: str
    access: str
    width_bits: int
    value_domain: str
    initialization: str
    mutation: str
    reset: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        if not isinstance(self.participant, AbilityParticipant):
            raise WorkspaceError("Ability participant is invalid")
        if not isinstance(self.phase, AbilityPhase):
            raise WorkspaceError("Ability phase is invalid")
        if self.width_bits not in _VALID_WIDTHS:
            raise WorkspaceError("Ability state width must be 8, 16, or 32 bits")
        for label, value in (
            ("owner structure", self.owner_structure),
            ("access", self.access),
            ("value domain", self.value_domain),
            ("initialization", self.initialization),
            ("mutation", self.mutation),
            ("reset", self.reset),
            ("evidence", self.evidence),
        ):
            _require_text(value, f"Ability {self.participant}/{self.phase} {label}")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError(
                f"Ability {self.participant}/{self.phase} must be confirmed"
            )


@dataclass(frozen=True)
class AbilityTimingEvidence:
    selection_boundary: str
    activation_boundary: str
    resolution_boundary: str
    gate_bonus_relation: str
    battle_type_relation: str
    minigame_relation: str
    result_relation: str

    def validate(self) -> None:
        for label, value in (
            ("selection boundary", self.selection_boundary),
            ("activation boundary", self.activation_boundary),
            ("resolution boundary", self.resolution_boundary),
            ("Gate-bonus relation", self.gate_bonus_relation),
            ("battle-type relation", self.battle_type_relation),
            ("minigame relation", self.minigame_relation),
            ("result relation", self.result_relation),
        ):
            _require_text(value, f"Ability timing {label}")


@dataclass(frozen=True)
class AbilityModel:
    states: tuple[AbilityStateEvidence, ...]
    timing: AbilityTimingEvidence
    scripted_paths: tuple[str, ...]
    no_ability_control: str

    def validate(self) -> None:
        expected = {
            (participant, phase)
            for participant in AbilityParticipant
            for phase in AbilityPhase
        }
        actual: set[tuple[AbilityParticipant, AbilityPhase]] = set()
        for state in self.states:
            state.validate()
            key = (state.participant, state.phase)
            if key in actual:
                raise WorkspaceError(
                    f"duplicate Ability state: {state.participant}/{state.phase}"
                )
            actual.add(key)
        if actual != expected:
            missing = sorted(
                f"{participant.value}/{phase.value}"
                for participant, phase in expected - actual
            )
            extra = sorted(
                f"{participant.value}/{phase.value}"
                for participant, phase in actual - expected
            )
            details: list[str] = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unexpected " + ", ".join(extra))
            raise WorkspaceError(
                "Ability model requires every participant and phase: "
                + "; ".join(details)
            )
        for participant in AbilityParticipant:
            phases = tuple(
                state.phase
                for state in self.states
                if state.participant is participant
            )
            if phases != _PHASE_ORDER:
                raise WorkspaceError(
                    f"Ability phases for {participant} must use canonical order"
                )
        self.timing.validate()
        if not self.scripted_paths or any(
            not value.strip() for value in self.scripted_paths
        ):
            raise WorkspaceError("Ability scripted paths must be nonempty")
        if len(set(self.scripted_paths)) != len(self.scripted_paths):
            raise WorkspaceError("Ability scripted paths must be unique")
        _require_text(self.no_ability_control, "Ability no-card control")

    def state_for(
        self, participant: AbilityParticipant, phase: AbilityPhase
    ) -> AbilityStateEvidence:
        if not isinstance(participant, AbilityParticipant):
            raise WorkspaceError("Ability participant lookup is invalid")
        if not isinstance(phase, AbilityPhase):
            raise WorkspaceError("Ability phase lookup is invalid")
        for state in self.states:
            if state.participant is participant and state.phase is phase:
                return state
        raise WorkspaceError(
            f"Ability state is unavailable: {participant.value}/{phase.value}"
        )


def _parse_state(value: object, index: int) -> AbilityStateEvidence:
    item = _require_object(value, f"states[{index}]")
    try:
        state = AbilityStateEvidence(
            participant=AbilityParticipant(str(item["participant"])),
            phase=AbilityPhase(str(item["phase"])),
            owner_structure=str(item["owner_structure"]),
            access=str(item["access"]),
            width_bits=_require_integer(
                item["width_bits"], f"states[{index}].width_bits"
            ),
            value_domain=str(item["value_domain"]),
            initialization=str(item["initialization"]),
            mutation=str(item["mutation"]),
            reset=str(item["reset"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid states[{index}]: {exc}") from exc
    state.validate()
    return state


def normalize_ability_artifact(payload: object) -> AbilityModel:
    root = _require_object(payload, "Ability artifact")
    if root.get("format_version") != 1:
        raise WorkspaceError("unsupported Ability artifact format")
    if root.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("unsupported Ability artifact profile")
    timing_raw = _require_object(root.get("timing"), "timing")
    try:
        model = AbilityModel(
            states=tuple(
                _parse_state(value, index)
                for index, value in enumerate(
                    _require_array(root.get("states"), "states")
                )
            ),
            timing=AbilityTimingEvidence(
                selection_boundary=str(timing_raw["selection_boundary"]),
                activation_boundary=str(timing_raw["activation_boundary"]),
                resolution_boundary=str(timing_raw["resolution_boundary"]),
                gate_bonus_relation=str(timing_raw["gate_bonus_relation"]),
                battle_type_relation=str(timing_raw["battle_type_relation"]),
                minigame_relation=str(timing_raw["minigame_relation"]),
                result_relation=str(timing_raw["result_relation"]),
            ),
            scripted_paths=tuple(
                str(value)
                for value in _require_array(
                    root.get("scripted_paths"), "scripted_paths"
                )
            ),
            no_ability_control=str(root["no_ability_control"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid Ability artifact: {exc}") from exc
    model.validate()
    return model
