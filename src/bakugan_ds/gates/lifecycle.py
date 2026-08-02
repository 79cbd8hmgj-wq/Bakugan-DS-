from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence


class LifecycleState(StrEnum):
    PLACED = "placed"
    SELECTED = "selected"
    ACTIVATED = "activated"
    BATTLE_STARTED = "battle_started"
    RESOLVED = "resolved"
    CAPTURED = "captured"
    REMOVED = "removed"
    REUSED = "reused"
    RESET = "reset"


@dataclass(frozen=True)
class LifecycleTransition:
    scenario: str
    sequence: int
    from_state: LifecycleState
    to_state: LifecycleState
    trigger: str
    address: int
    component: str
    component_base: int
    component_offset: int
    owner_source: str
    card_id_source: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        if not self.scenario.strip():
            raise WorkspaceError("lifecycle scenario must be nonempty")
        if self.sequence < 0:
            raise WorkspaceError("lifecycle sequence must be nonnegative")
        if not self.trigger.strip():
            raise WorkspaceError("lifecycle trigger must be nonempty")
        if self.address < 0:
            raise WorkspaceError("lifecycle address must be nonnegative")
        if not self.component.strip():
            raise WorkspaceError("lifecycle component must be nonempty")
        if self.component_base < 0 or self.component_offset < 0:
            raise WorkspaceError("lifecycle component address fields must be nonnegative")
        if self.address - self.component_base != self.component_offset:
            raise WorkspaceError(
                f"lifecycle component offset 0x{self.component_offset:X} does not match "
                f"address 0x{self.address:X} and base 0x{self.component_base:X}"
            )
        if not self.owner_source.strip():
            raise WorkspaceError("lifecycle owner source must be nonempty")
        if not self.card_id_source.strip():
            raise WorkspaceError("lifecycle card ID source must be nonempty")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("lifecycle confidence is invalid")
        if not self.evidence.strip():
            raise WorkspaceError("lifecycle evidence must be nonempty")


def _parse_address(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError


def normalize_lifecycle_capture(payload: dict[str, object]) -> tuple[LifecycleTransition, ...]:
    raw = payload.get("transitions")
    if not isinstance(raw, list):
        raise WorkspaceError("transitions must be a JSON array")
    transitions: list[LifecycleTransition] = []
    seen: set[tuple[str, int]] = set()
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            raise WorkspaceError(f"transitions[{index}] must be a JSON object")
        try:
            item = LifecycleTransition(
                scenario=str(value["scenario"]),
                sequence=int(value["sequence"]),
                from_state=LifecycleState(str(value["from_state"])),
                to_state=LifecycleState(str(value["to_state"])),
                trigger=str(value["trigger"]),
                address=_parse_address(value["address"]),
                component=str(value["component"]),
                component_base=_parse_address(value["component_base"]),
                component_offset=_parse_address(value["component_offset"]),
                owner_source=str(value["owner_source"]),
                card_id_source=str(value["card_id_source"]),
                confidence=Confidence(str(value["confidence"])),
                evidence=str(value["evidence"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid transitions[{index}]: {exc}") from exc
        item.validate()
        key = (item.scenario, item.sequence)
        if key in seen:
            raise WorkspaceError(
                f"duplicate sequence {item.sequence} in lifecycle scenario {item.scenario}"
            )
        seen.add(key)
        transitions.append(item)
    return tuple(sorted(transitions, key=lambda item: (item.scenario, item.sequence)))


def validate_lifecycle(transitions: tuple[LifecycleTransition, ...]) -> None:
    if not transitions:
        raise WorkspaceError("lifecycle must contain at least one transition")
    by_scenario: dict[str, list[LifecycleTransition]] = {}
    for transition in transitions:
        transition.validate()
        by_scenario.setdefault(transition.scenario, []).append(transition)
    for scenario, items in by_scenario.items():
        ordered = sorted(items, key=lambda item: item.sequence)
        expected_sequences = list(range(len(ordered)))
        if [item.sequence for item in ordered] != expected_sequences:
            raise WorkspaceError(f"lifecycle scenario {scenario} has non-contiguous sequences")
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.to_state is not current.from_state:
                raise WorkspaceError(
                    f"lifecycle scenario {scenario} is disconnected between sequence "
                    f"{previous.sequence} and {current.sequence}"
                )
