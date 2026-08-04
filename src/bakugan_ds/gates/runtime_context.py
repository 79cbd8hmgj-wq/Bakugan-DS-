from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.system2 import GateCalculationContext

_MAX_PARTICIPANT_INDEX = 15
_MAX_MATCH_SCORE = 0xFF
_MIN_GATE_ID = 1
_MAX_GATE_ID = 103


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


def _participant_index(value: object, label: str) -> int:
    result = _require_int(value, label)
    if not 0 <= result <= _MAX_PARTICIPANT_INDEX:
        raise WorkspaceError(
            f"{label} must be between 0 and {_MAX_PARTICIPANT_INDEX}"
        )
    return result


@dataclass(frozen=True)
class ParticipantSnapshot:
    index: int
    match_score: int
    teammate_index: int | None

    def validate(self) -> None:
        _participant_index(self.index, "participant index")
        score = _require_int(self.match_score, "participant match score")
        if not 0 <= score <= _MAX_MATCH_SCORE:
            raise WorkspaceError("participant match score must fit unsigned 8-bit")
        if self.teammate_index is not None:
            _participant_index(self.teammate_index, "teammate participant index")


@dataclass(frozen=True)
class BattleSnapshot:
    gate_id: int
    gate_owner: int
    team_mode: bool
    participants: tuple[ParticipantSnapshot, ...]

    def validate(self) -> None:
        gate_id = _require_int(self.gate_id, "Gate ID")
        if not _MIN_GATE_ID <= gate_id <= _MAX_GATE_ID:
            raise WorkspaceError("Gate ID must be between 1 and 103")
        owner = _participant_index(self.gate_owner, "Gate owner")
        if type(self.team_mode) is not bool:
            raise WorkspaceError("team mode must be a boolean")

        expected_count = 4 if self.team_mode else 2
        if len(self.participants) != expected_count:
            label = "team mode" if self.team_mode else "solo mode"
            raise WorkspaceError(
                f"{label} requires exactly {expected_count} participants"
            )

        by_index: dict[int, ParticipantSnapshot] = {}
        for participant in self.participants:
            participant.validate()
            if participant.index in by_index:
                raise WorkspaceError(
                    f"duplicate participant index: {participant.index}"
                )
            by_index[participant.index] = participant
        if owner not in by_index:
            raise WorkspaceError("Gate owner is not an active participant")

        if not self.team_mode:
            return

        pairs: set[frozenset[int]] = set()
        for participant in self.participants:
            teammate_index = participant.teammate_index
            if teammate_index is None:
                raise WorkspaceError(
                    f"team participant {participant.index} requires a teammate"
                )
            if teammate_index == participant.index:
                raise WorkspaceError("team participants require distinct teammates")
            teammate = by_index.get(teammate_index)
            if teammate is None:
                raise WorkspaceError(
                    f"team participant {participant.index} references an inactive teammate"
                )
            if teammate.teammate_index != participant.index:
                raise WorkspaceError("team participant links must be reciprocal")
            pairs.add(frozenset((participant.index, teammate_index)))
        if len(pairs) != 2 or any(len(pair) != 2 for pair in pairs):
            raise WorkspaceError("team mode requires exactly two complete teammate pairs")

    def participant(self, participant_index: int) -> ParticipantSnapshot:
        self.validate()
        index = _participant_index(participant_index, "participant lookup index")
        for participant in self.participants:
            if participant.index == index:
                return participant
        raise WorkspaceError(f"participant {index} is not active")

    def team_pairs(self) -> tuple[frozenset[int], ...]:
        self.validate()
        if not self.team_mode:
            raise WorkspaceError("solo mode has no teammate pairs")
        pairs = {
            frozenset((participant.index, participant.teammate_index))
            for participant in self.participants
        }
        return tuple(sorted(pairs, key=lambda pair: tuple(sorted(pair))))


def side_score(snapshot: BattleSnapshot, participant_index: int) -> int:
    participant = snapshot.participant(participant_index)
    if not snapshot.team_mode:
        return participant.match_score
    teammate_index = participant.teammate_index
    if teammate_index is None:
        raise WorkspaceError("team participant requires a teammate")
    teammate = snapshot.participant(teammate_index)
    return participant.match_score + teammate.match_score


def _opposing_side_score(snapshot: BattleSnapshot) -> int:
    snapshot.validate()
    if not snapshot.team_mode:
        opponents = [
            participant
            for participant in snapshot.participants
            if participant.index != snapshot.gate_owner
        ]
        if len(opponents) != 1:
            raise WorkspaceError("solo mode requires one opposing participant")
        return opponents[0].match_score

    owner = snapshot.participant(snapshot.gate_owner)
    if owner.teammate_index is None:
        raise WorkspaceError("Gate-owner team is incomplete")
    owner_pair = frozenset((owner.index, owner.teammate_index))
    other_pairs = [pair for pair in snapshot.team_pairs() if pair != owner_pair]
    if len(other_pairs) != 1:
        raise WorkspaceError("team mode has an ambiguous opposing side")
    opponent_index = min(other_pairs[0])
    return side_score(snapshot, opponent_index)


def build_gate_calculation_context(
    snapshot: BattleSnapshot,
    *,
    current_participant: int,
    compressed_core_g: int,
    attribute_id: int,
) -> GateCalculationContext:
    snapshot.validate()
    current = _participant_index(current_participant, "current participant")
    active_indices = {participant.index for participant in snapshot.participants}
    if current not in active_indices:
        raise WorkspaceError("current participant is not active")
    context = GateCalculationContext(
        compressed_core_g=compressed_core_g,
        attribute_id=attribute_id,
        current_participant=current,
        owner_participant=snapshot.gate_owner,
        owner_side_score=side_score(snapshot, snapshot.gate_owner),
        opposing_side_score=_opposing_side_score(snapshot),
        gate_id=snapshot.gate_id,
    )
    context.validate()
    return context
