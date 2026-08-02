from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence, SUPPORTED_PROFILE_ID

_MAX_PARTICIPANT_INDEX = 15
_UNRESOLVED_WINNER = -1


class ParticipantRole(StrEnum):
    GATE_OWNER = "gate_owner"
    DEFENDER = "defender"
    CHALLENGER = "challenger"
    COMBATANT_0 = "combatant_0"
    COMBATANT_1 = "combatant_1"
    HUMAN = "human"
    AI = "ai"
    WINNER = "winner"
    LOSER = "loser"
    EFFECT_TARGET = "effect_target"


class TargetMode(StrEnum):
    OWNER = "owner"
    DEFENDER = "defender"
    CHALLENGER = "challenger"
    SELF = "self"
    OPPONENT = "opponent"
    BOTH = "both"
    WINNER = "winner"
    LOSER = "loser"
    HUMAN = "human"
    AI = "ai"


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")


def _participant_index(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    if not 0 <= value <= _MAX_PARTICIPANT_INDEX:
        raise WorkspaceError(
            f"{label} must be between 0 and {_MAX_PARTICIPANT_INDEX}, got {value}"
        )
    return value


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise WorkspaceError(f"{label} must be a boolean")
    return value


@dataclass(frozen=True)
class ParticipantEvidence:
    role: ParticipantRole
    identity_source: str
    owner_structure: str
    access: str
    initialization: str
    transfer: str
    reset: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        if not isinstance(self.role, ParticipantRole):
            raise WorkspaceError("participant role is invalid")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError(f"participant role {self.role} has invalid confidence")
        for label, value in (
            ("identity source", self.identity_source),
            ("owner structure", self.owner_structure),
            ("access", self.access),
            ("initialization", self.initialization),
            ("transfer", self.transfer),
            ("reset", self.reset),
            ("evidence", self.evidence),
        ):
            _require_text(value, f"participant role {self.role} {label}")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError(f"participant role {self.role} must be confirmed")


@dataclass(frozen=True)
class TargetRule:
    mode: TargetMode
    availability: str
    resolution: str
    requires_source: bool
    requires_result: bool
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        if not isinstance(self.mode, TargetMode):
            raise WorkspaceError("target mode is invalid")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError(f"target mode {self.mode} has invalid confidence")
        for label, value in (
            ("availability", self.availability),
            ("resolution", self.resolution),
            ("evidence", self.evidence),
        ):
            _require_text(value, f"target mode {self.mode} {label}")
        if type(self.requires_source) is not bool:
            raise WorkspaceError(f"target mode {self.mode} requires_source must be boolean")
        if type(self.requires_result) is not bool:
            raise WorkspaceError(f"target mode {self.mode} requires_result must be boolean")
        if self.mode in (TargetMode.SELF, TargetMode.OPPONENT) and not self.requires_source:
            raise WorkspaceError(f"target mode {self.mode} must require an explicit source")
        if self.mode in (TargetMode.WINNER, TargetMode.LOSER) and not self.requires_result:
            raise WorkspaceError(f"target mode {self.mode} must require a settled result")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError(f"target mode {self.mode} must be confirmed")


@dataclass(frozen=True)
class ParticipantModel:
    entries: tuple[ParticipantEvidence, ...]
    target_modes: tuple[TargetRule, ...]
    scripted_paths: tuple[str, ...]

    def validate(self) -> None:
        required_roles = frozenset(ParticipantRole)
        roles: set[ParticipantRole] = set()
        for entry in self.entries:
            entry.validate()
            if entry.role in roles:
                raise WorkspaceError(f"duplicate participant role: {entry.role}")
            roles.add(entry.role)
        missing_roles = sorted(role.value for role in required_roles - roles)
        if missing_roles:
            raise WorkspaceError(
                "participant model is missing roles: " + ", ".join(missing_roles)
            )

        required_modes = frozenset(TargetMode)
        modes: set[TargetMode] = set()
        for rule in self.target_modes:
            rule.validate()
            if rule.mode in modes:
                raise WorkspaceError(f"duplicate target mode: {rule.mode}")
            modes.add(rule.mode)
        missing_modes = sorted(mode.value for mode in required_modes - modes)
        if missing_modes:
            raise WorkspaceError(
                "participant model is missing target modes: " + ", ".join(missing_modes)
            )

        if not self.scripted_paths or any(not value.strip() for value in self.scripted_paths):
            raise WorkspaceError("participant model scripted paths must be nonempty")
        if len(set(self.scripted_paths)) != len(self.scripted_paths):
            raise WorkspaceError("participant model scripted paths must be unique")


@dataclass(frozen=True)
class ParticipantControl:
    participant_index: int
    is_ai: bool

    def validate(self) -> None:
        _participant_index(self.participant_index, "control participant index")
        if type(self.is_ai) is not bool:
            raise WorkspaceError("participant control is_ai must be boolean")


@dataclass(frozen=True)
class ParticipantContext:
    gate_owner: int
    defender: int
    challenger: int
    controls: tuple[ParticipantControl, ...]
    winner_record_index: int = _UNRESOLVED_WINNER

    def validate(self) -> None:
        _participant_index(self.gate_owner, "Gate owner")
        _participant_index(self.defender, "defender")
        _participant_index(self.challenger, "challenger")
        if self.winner_record_index not in (_UNRESOLVED_WINNER, 0, 1):
            raise WorkspaceError("winner record index must be -1, 0, or 1")

        control_indices: set[int] = set()
        for control in self.controls:
            control.validate()
            if control.participant_index in control_indices:
                raise WorkspaceError(
                    f"duplicate participant control: {control.participant_index}"
                )
            control_indices.add(control.participant_index)
        for participant in self._ordered_combatants():
            if participant not in control_indices:
                raise WorkspaceError(
                    f"missing human/AI control for combatant participant {participant}"
                )

    def resolve(
        self,
        mode: TargetMode,
        *,
        source_participant: int | None = None,
        combatant_only: bool = False,
    ) -> tuple[int, ...]:
        self.validate()
        if not isinstance(mode, TargetMode):
            raise WorkspaceError("target mode is invalid")

        combatants = self._ordered_combatants()
        if mode is TargetMode.OWNER:
            if combatant_only and self.gate_owner not in combatants:
                raise WorkspaceError("Gate owner is not a live combatant")
            return (self.gate_owner,)
        if mode is TargetMode.DEFENDER:
            self._require_distinct_combatants(mode)
            return (self.defender,)
        if mode is TargetMode.CHALLENGER:
            self._require_distinct_combatants(mode)
            return (self.challenger,)
        if mode is TargetMode.SELF:
            source = self._require_source(source_participant)
            if combatant_only and source not in combatants:
                raise WorkspaceError("source participant is not a live combatant")
            return (source,)
        if mode is TargetMode.OPPONENT:
            self._require_distinct_combatants(mode)
            source = self._require_source(source_participant)
            if source == self.defender:
                return (self.challenger,)
            if source == self.challenger:
                return (self.defender,)
            raise WorkspaceError("source participant is not exactly one live combatant")
        if mode is TargetMode.BOTH:
            self._require_distinct_combatants(mode)
            return combatants
        if mode is TargetMode.WINNER:
            self._require_distinct_combatants(mode)
            return (self._result_participant(loser=False),)
        if mode is TargetMode.LOSER:
            self._require_distinct_combatants(mode)
            return (self._result_participant(loser=True),)
        if mode is TargetMode.HUMAN:
            return self._filter_control(is_ai=False)
        if mode is TargetMode.AI:
            return self._filter_control(is_ai=True)
        raise WorkspaceError(f"unsupported target mode: {mode}")

    def _ordered_combatants(self) -> tuple[int, ...]:
        if self.defender == self.challenger:
            return (self.defender,)
        return (self.defender, self.challenger)

    def _require_distinct_combatants(self, mode: TargetMode) -> None:
        if self.defender == self.challenger:
            raise WorkspaceError(f"target mode {mode} requires distinct combatants")

    def _require_source(self, value: int | None) -> int:
        if value is None:
            raise WorkspaceError("target mode requires an explicit source participant")
        return _participant_index(value, "source participant")

    def _result_participant(self, *, loser: bool) -> int:
        if self.winner_record_index == _UNRESOLVED_WINNER:
            raise WorkspaceError("battle result is unresolved")
        index = self.winner_record_index ^ int(loser)
        return self.defender if index == 0 else self.challenger

    def _filter_control(self, *, is_ai: bool) -> tuple[int, ...]:
        controls = {entry.participant_index: entry.is_ai for entry in self.controls}
        return tuple(
            participant
            for participant in self._ordered_combatants()
            if controls[participant] is is_ai
        )


def _parse_participant_evidence(value: object, index: int) -> ParticipantEvidence:
    item = _require_object(value, f"roles[{index}]")
    try:
        entry = ParticipantEvidence(
            role=ParticipantRole(str(item["role"])),
            identity_source=str(item["identity_source"]),
            owner_structure=str(item["owner_structure"]),
            access=str(item["access"]),
            initialization=str(item["initialization"]),
            transfer=str(item["transfer"]),
            reset=str(item["reset"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid roles[{index}]: {exc}") from exc
    entry.validate()
    return entry


def _parse_target_rule(value: object, index: int) -> TargetRule:
    item = _require_object(value, f"target_modes[{index}]")
    try:
        rule = TargetRule(
            mode=TargetMode(str(item["mode"])),
            availability=str(item["availability"]),
            resolution=str(item["resolution"]),
            requires_source=_require_bool(
                item["requires_source"], f"target_modes[{index}].requires_source"
            ),
            requires_result=_require_bool(
                item["requires_result"], f"target_modes[{index}].requires_result"
            ),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid target_modes[{index}]: {exc}") from exc
    rule.validate()
    return rule


def normalize_participant_artifact(payload: object) -> ParticipantModel:
    root = _require_object(payload, "participant artifact")
    if root.get("format_version") != 1:
        raise WorkspaceError("unsupported participant artifact format")
    if root.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("unsupported participant artifact profile")
    try:
        model = ParticipantModel(
            entries=tuple(
                _parse_participant_evidence(value, index)
                for index, value in enumerate(
                    _require_array(root.get("roles"), "roles")
                )
            ),
            target_modes=tuple(
                _parse_target_rule(value, index)
                for index, value in enumerate(
                    _require_array(root.get("target_modes"), "target_modes")
                )
            ),
            scripted_paths=tuple(
                str(value)
                for value in _require_array(
                    root.get("scripted_paths"), "scripted_paths"
                )
            ),
        )
    except (TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid participant artifact: {exc}") from exc
    model.validate()
    return model
