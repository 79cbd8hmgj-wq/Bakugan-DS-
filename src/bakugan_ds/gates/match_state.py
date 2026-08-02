from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID, Confidence

_VALID_COUNTER_WIDTHS = frozenset({8, 16, 32})


class CounterOwner(StrEnum):
    PLAYER = "player"
    OPPONENT = "opponent"
    SHARED = "shared"


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise WorkspaceError(f"{label} must be nonempty")


def _require_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


@dataclass(frozen=True)
class CounterEvidence:
    name: str
    owner: CounterOwner
    width_bits: int
    access: str
    initial_value: int
    update_function: str
    reset_function: str
    lifetime: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        _require_text(self.name, "counter name")
        if not isinstance(self.owner, CounterOwner):
            raise WorkspaceError(f"counter {self.name} has invalid owner")
        if self.width_bits not in _VALID_COUNTER_WIDTHS:
            raise WorkspaceError(
                f"counter {self.name} width must be 8, 16, or 32 bits"
            )
        initial_value = _require_integer(
            self.initial_value, f"counter {self.name} initial value"
        )
        if not 0 <= initial_value < (1 << self.width_bits):
            raise WorkspaceError(
                f"counter {self.name} initial value does not fit its width"
            )
        for label, value in (
            ("access", self.access),
            ("update function", self.update_function),
            ("reset function", self.reset_function),
            ("lifetime", self.lifetime),
            ("evidence", self.evidence),
        ):
            _require_text(value, f"counter {self.name} {label}")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError(f"counter {self.name} has invalid confidence")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError(f"counter {self.name} must be confirmed")


@dataclass(frozen=True)
class MatchStateEvidence:
    score_counters: tuple[CounterEvidence, ...]
    capture_counters: tuple[CounterEvidence, ...]
    victory_threshold: int
    result_timing: str
    scripted_paths: tuple[str, ...]

    def validate(self) -> None:
        self._validate_counter_group(self.score_counters, "score")
        self._validate_counter_group(self.capture_counters, "capture")

        threshold = _require_integer(self.victory_threshold, "victory threshold")
        if threshold <= 0:
            raise WorkspaceError("victory threshold must be positive")
        score_width = self.score_counters[0].width_bits
        if threshold >= (1 << score_width):
            raise WorkspaceError("victory threshold does not fit score-counter width")

        _require_text(self.result_timing, "result timing")
        if not self.scripted_paths or any(
            not value.strip() for value in self.scripted_paths
        ):
            raise WorkspaceError("scripted paths must contain nonempty entries")
        if len(set(self.scripted_paths)) != len(self.scripted_paths):
            raise WorkspaceError("scripted paths must be unique")

    def score_for(self, owner: CounterOwner) -> CounterEvidence:
        return self._counter_for(self.score_counters, owner, "score")

    def capture_for(self, owner: CounterOwner) -> CounterEvidence:
        return self._counter_for(self.capture_counters, owner, "capture")

    @staticmethod
    def _validate_counter_group(
        counters: tuple[CounterEvidence, ...], label: str
    ) -> None:
        if len(counters) != 2:
            raise WorkspaceError(f"{label} counters must contain exactly two entries")
        names: set[str] = set()
        owners: set[CounterOwner] = set()
        widths: set[int] = set()
        for counter in counters:
            counter.validate()
            if counter.name in names:
                raise WorkspaceError(f"duplicate {label} counter name: {counter.name}")
            if counter.owner in owners:
                raise WorkspaceError(
                    f"duplicate {label} counter owner: {counter.owner}"
                )
            names.add(counter.name)
            owners.add(counter.owner)
            widths.add(counter.width_bits)
        expected = {CounterOwner.PLAYER, CounterOwner.OPPONENT}
        if owners != expected:
            missing = sorted(owner.value for owner in expected - owners)
            extra = sorted(owner.value for owner in owners - expected)
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unexpected " + ", ".join(extra))
            raise WorkspaceError(
                f"{label} counters require player and opponent owners: "
                + "; ".join(details)
            )
        if len(widths) != 1:
            raise WorkspaceError(f"{label} counter widths must match")

    @staticmethod
    def _counter_for(
        counters: tuple[CounterEvidence, ...],
        owner: CounterOwner,
        label: str,
    ) -> CounterEvidence:
        if not isinstance(owner, CounterOwner):
            raise WorkspaceError(f"{label} counter owner is invalid")
        for counter in counters:
            if counter.owner is owner:
                return counter
        raise WorkspaceError(f"{label} counter owner is unavailable: {owner}")


def _parse_counter(value: object, index: int, label: str) -> CounterEvidence:
    item = _require_object(value, f"{label}_counters[{index}]")
    try:
        counter = CounterEvidence(
            name=str(item["name"]),
            owner=CounterOwner(str(item["owner"])),
            width_bits=_require_integer(
                item["width_bits"], f"{label}_counters[{index}].width_bits"
            ),
            access=str(item["access"]),
            initial_value=_require_integer(
                item["initial_value"],
                f"{label}_counters[{index}].initial_value",
            ),
            update_function=str(item["update_function"]),
            reset_function=str(item["reset_function"]),
            lifetime=str(item["lifetime"]),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid {label}_counters[{index}]: {exc}") from exc
    counter.validate()
    return counter


def normalize_match_state_artifact(payload: object) -> MatchStateEvidence:
    root = _require_object(payload, "match-state artifact")
    if root.get("format_version") != 1:
        raise WorkspaceError("unsupported match-state artifact format")
    if root.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("unsupported match-state artifact profile")
    try:
        model = MatchStateEvidence(
            score_counters=tuple(
                _parse_counter(value, index, "score")
                for index, value in enumerate(
                    _require_array(root.get("score_counters"), "score_counters")
                )
            ),
            capture_counters=tuple(
                _parse_counter(value, index, "capture")
                for index, value in enumerate(
                    _require_array(root.get("capture_counters"), "capture_counters")
                )
            ),
            victory_threshold=_require_integer(
                root.get("victory_threshold"), "victory_threshold"
            ),
            result_timing=str(root["result_timing"]),
            scripted_paths=tuple(
                str(value)
                for value in _require_array(
                    root.get("scripted_paths"), "scripted_paths"
                )
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid match-state artifact: {exc}") from exc
    model.validate()
    return model
