from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.discovery import Presence
from bakugan_ds.gates.model import SUPPORTED_PROFILE_ID, AddressRef, Confidence

TYPE_COUNT = 6
WEIGHT_WIDTH_BITS = 8
WEIGHT_MAX = 0xFF
TOTAL_MAX = TYPE_COUNT * WEIGHT_MAX


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


def _parse_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise WorkspaceError(f"{label} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError as exc:
            raise WorkspaceError(f"{label} must be an integer") from exc
    raise WorkspaceError(f"{label} must be an integer")


def _parse_address(value: object, label: str) -> AddressRef:
    item = _require_object(value, label)
    try:
        result = AddressRef(
            component=str(item["component"]),
            runtime_address=_parse_int(item["runtime_address"], f"{label}.runtime_address"),
            component_offset=_parse_int(item["component_offset"], f"{label}.component_offset"),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid {label}: {exc}") from exc
    result.validate()
    return result


@dataclass(frozen=True)
class RngEvidence:
    function: AddressRef
    calling_convention: str
    output_width_bits: int
    output_range: str
    seed_source: str
    deterministic_controls: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        self.function.validate()
        for label, value in (
            ("RNG calling convention", self.calling_convention),
            ("RNG output range", self.output_range),
            ("RNG seed source", self.seed_source),
            ("RNG deterministic controls", self.deterministic_controls),
            ("RNG evidence", self.evidence),
        ):
            _require_text(value, label)
        if self.output_width_bits not in {8, 16, 32, 64}:
            raise WorkspaceError("RNG output width must be 8, 16, 32, or 64 bits")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError("weighted RNG evidence must be confirmed")
        if self.function.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError("weighted RNG function must be confirmed")


@dataclass(frozen=True)
class HistoryEvidence:
    presence: Presence
    storage: str
    entry_width_bits: int | None
    capacity: int | None
    update_timing: str
    reset_timing: str
    player_ai_behavior: str
    confidence: Confidence
    evidence: str
    replacement_plan: str

    def validate(self) -> None:
        if self.presence is Presence.DEFERRED:
            raise WorkspaceError("battle-type history cannot be deferred")
        for label, value in (
            ("history storage", self.storage),
            ("history update timing", self.update_timing),
            ("history reset timing", self.reset_timing),
            ("history player/AI behavior", self.player_ai_behavior),
            ("history evidence", self.evidence),
        ):
            _require_text(value, label)
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError("battle-type history evidence must be confirmed")
        if self.presence is Presence.ABSENT:
            if self.entry_width_bits is not None or self.capacity is not None:
                raise WorkspaceError("absent original history cannot define original geometry")
            _require_text(self.replacement_plan, "absent history replacement plan")
            return
        if self.entry_width_bits not in {8, 16, 32}:
            raise WorkspaceError("history entry width must be 8, 16, or 32 bits")
        if self.capacity is None or self.capacity <= 0:
            raise WorkspaceError("history capacity must be positive")
        if self.replacement_plan.strip():
            raise WorkspaceError("present history cannot define a replacement plan")


@dataclass(frozen=True)
class WeightedSelectionSpec:
    type_count: int = TYPE_COUNT
    weight_width_bits: int = WEIGHT_WIDTH_BITS
    total_max: int = TOTAL_MAX
    fallback: str = "legacy_fixed_metadata"

    def validate(self) -> None:
        if self.type_count != TYPE_COUNT:
            raise WorkspaceError("weighted selection requires exactly six battle types")
        if self.weight_width_bits != WEIGHT_WIDTH_BITS:
            raise WorkspaceError("weighted selection weights must be 8-bit")
        if self.total_max != TOTAL_MAX:
            raise WorkspaceError(f"weighted selection total maximum must be {TOTAL_MAX}")
        if self.fallback != "legacy_fixed_metadata":
            raise WorkspaceError("weighted selection fallback must be legacy_fixed_metadata")


@dataclass(frozen=True)
class HistoryModel:
    rng: RngEvidence
    history: HistoryEvidence
    selection: WeightedSelectionSpec
    precedence: tuple[str, ...]

    def validate(self) -> None:
        self.rng.validate()
        self.history.validate()
        self.selection.validate()
        if len(self.precedence) != 4 or any(not value.strip() for value in self.precedence):
            raise WorkspaceError("selector precedence must contain four nonempty stages")
        if len(set(self.precedence)) != len(self.precedence):
            raise WorkspaceError("selector precedence stages must be unique")


def validate_weight_vector(weights: tuple[int, ...]) -> None:
    if len(weights) != TYPE_COUNT:
        raise WorkspaceError("weight vector must contain exactly six entries")
    if any(isinstance(weight, bool) or not isinstance(weight, int) for weight in weights):
        raise WorkspaceError("weights must be integers")
    if any(weight < 0 for weight in weights):
        raise WorkspaceError("weights cannot be negative")
    if any(weight > WEIGHT_MAX for weight in weights):
        raise WorkspaceError("weights must fit in unsigned 8-bit values")
    total = sum(weights)
    if total == 0:
        raise WorkspaceError("weight vector cannot contain six zero weights")
    if total > TOTAL_MAX:
        raise WorkspaceError(f"weight total cannot exceed {TOTAL_MAX}")


def weighted_index(weights: tuple[int, ...], roll: int) -> int:
    validate_weight_vector(weights)
    total = sum(weights)
    if isinstance(roll, bool) or not isinstance(roll, int):
        raise WorkspaceError("roll must be an integer")
    if not 0 <= roll < total:
        raise WorkspaceError(f"roll must be in [0, {total})")
    cumulative = 0
    for index, weight in enumerate(weights):
        cumulative += weight
        if roll < cumulative:
            return index
    raise WorkspaceError("weighted selection failed despite a valid roll")


def _optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    return _parse_int(value, label)


def normalize_history_artifact(payload: object) -> HistoryModel:
    root = _require_object(payload, "history artifact")
    if root.get("format_version") != 1:
        raise WorkspaceError("unsupported history artifact format")
    if root.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("unsupported history artifact profile")
    rng_raw = _require_object(root.get("rng"), "rng")
    history_raw = _require_object(root.get("history"), "history")
    selection_raw = _require_object(root.get("weighted_selection"), "weighted_selection")
    try:
        rng = RngEvidence(
            function=_parse_address(rng_raw["function"], "rng.function"),
            calling_convention=str(rng_raw["calling_convention"]),
            output_width_bits=_parse_int(rng_raw["output_width_bits"], "rng.output_width_bits"),
            output_range=str(rng_raw["output_range"]),
            seed_source=str(rng_raw["seed_source"]),
            deterministic_controls=str(rng_raw["deterministic_controls"]),
            confidence=Confidence(str(rng_raw["confidence"])),
            evidence=str(rng_raw["evidence"]),
        )
        history = HistoryEvidence(
            presence=Presence(str(history_raw["presence"])),
            storage=str(history_raw["storage"]),
            entry_width_bits=_optional_int(
                history_raw.get("entry_width_bits"),
                "history.entry_width_bits",
            ),
            capacity=_optional_int(history_raw.get("capacity"), "history.capacity"),
            update_timing=str(history_raw["update_timing"]),
            reset_timing=str(history_raw["reset_timing"]),
            player_ai_behavior=str(history_raw["player_ai_behavior"]),
            confidence=Confidence(str(history_raw["confidence"])),
            evidence=str(history_raw["evidence"]),
            replacement_plan=str(history_raw.get("replacement_plan", "")),
        )
        selection = WeightedSelectionSpec(
            type_count=_parse_int(selection_raw["type_count"], "weighted_selection.type_count"),
            weight_width_bits=_parse_int(
                selection_raw["weight_width_bits"],
                "weighted_selection.weight_width_bits",
            ),
            total_max=_parse_int(selection_raw["total_max"], "weighted_selection.total_max"),
            fallback=str(selection_raw["fallback"]),
        )
        precedence = tuple(
            str(value) for value in _require_array(root.get("precedence"), "precedence")
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid history artifact: {exc}") from exc
    model = HistoryModel(
        rng=rng,
        history=history,
        selection=selection,
        precedence=precedence,
    )
    model.validate()
    return model


WEIGHTED_SELECTOR_ADDRESS = 0x02021A30

_WEIGHTED_LCG_MULTIPLIER = 0x5D588B656C078965
_WEIGHTED_LCG_ADDEND = 0x00269EC3
_U64_MASK = 0xFFFFFFFFFFFFFFFF
_U32_MAX = 0xFFFFFFFF


def advance_weighted_lcg(seed: int) -> int:
    """Advance the confirmed ARM9 64-bit weighted-selection LCG once."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise WorkspaceError("weighted RNG state must be an integer")
    if not 0 <= seed <= _U64_MASK:
        raise WorkspaceError("weighted RNG state must fit unsigned 64-bit")
    return (seed * _WEIGHTED_LCG_MULTIPLIER + _WEIGHTED_LCG_ADDEND) & _U64_MASK


def weighted_roll_from_state(seed: int, total: int) -> tuple[int, int]:
    """Advance the LCG and scale its high word into the half-open total range."""

    if isinstance(total, bool) or not isinstance(total, int):
        raise WorkspaceError("weighted total must be an integer")
    if not 0 < total <= _U32_MAX:
        raise WorkspaceError("weighted total must be between 1 and 0xFFFFFFFF")
    next_state = advance_weighted_lcg(seed)
    high_word = next_state >> 32
    roll = (high_word * total) >> 32
    return next_state, roll
