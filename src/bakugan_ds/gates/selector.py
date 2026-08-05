from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import AddressRef, Confidence

if TYPE_CHECKING:
    from bakugan_ds.gates.record import GateRecordV1
    from bakugan_ds.gates.system2 import FallbackReason, FallbackScope

_SELECTION_MODES = frozenset({"fixed_metadata", "weighted_random"})
_BATTLE_TYPE_COUNT = 6


@dataclass(frozen=True)
class BattleTypeEvidence:
    type_id: int
    label: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        if self.type_id < 0:
            raise WorkspaceError("battle type ID must be nonnegative")
        if not self.label.strip():
            raise WorkspaceError("battle type label must be nonempty")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("battle type confidence is invalid")
        if not self.evidence.strip():
            raise WorkspaceError("battle type evidence must be nonempty")


@dataclass(frozen=True)
class SelectorInput:
    name: str
    source: str
    influence: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        if not self.name.strip():
            raise WorkspaceError("selector input name must be nonempty")
        if not self.source.strip():
            raise WorkspaceError("selector input source must be nonempty")
        if not self.influence.strip():
            raise WorkspaceError("selector input influence must be nonempty")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("selector input confidence is invalid")
        if not self.evidence.strip():
            raise WorkspaceError("selector input evidence must be nonempty")


@dataclass(frozen=True)
class ForcedPath:
    name: str
    source: str
    mapping: tuple[tuple[int, int], ...]
    confidence: Confidence
    evidence: str

    def validate(self, valid_type_ids: set[int]) -> None:
        if not self.name.strip():
            raise WorkspaceError("forced path name must be nonempty")
        if not self.source.strip():
            raise WorkspaceError("forced path source must be nonempty")
        if not self.mapping:
            raise WorkspaceError("forced path mapping must be nonempty")
        codes: set[int] = set()
        for code, type_id in self.mapping:
            if code < 0:
                raise WorkspaceError("forced path code must be nonnegative")
            if code in codes:
                raise WorkspaceError(f"duplicate forced path code: {code}")
            if type_id not in valid_type_ids:
                raise WorkspaceError(f"forced path references unknown battle type ID: {type_id}")
            codes.add(code)
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("forced path confidence is invalid")
        if not self.evidence.strip():
            raise WorkspaceError("forced path evidence must be nonempty")


@dataclass(frozen=True)
class BattleTypeSelectorEvidence:
    selector: AddressRef
    selection_mode: str
    rng_calls: tuple[AddressRef, ...]
    random_range: tuple[int, int] | None
    types: tuple[BattleTypeEvidence, ...]
    inputs: tuple[SelectorInput, ...]
    result_storage: AddressRef
    forced_paths: tuple[ForcedPath, ...]

    def validate(self) -> None:
        self.selector.validate()
        self.result_storage.validate()
        if self.selection_mode not in _SELECTION_MODES:
            raise WorkspaceError(f"unsupported selector mode: {self.selection_mode}")
        if not self.types:
            raise WorkspaceError("selector must define at least one battle type")
        type_ids: set[int] = set()
        for battle_type in self.types:
            battle_type.validate()
            if battle_type.type_id in type_ids:
                raise WorkspaceError(f"duplicate battle type ID: {battle_type.type_id}")
            type_ids.add(battle_type.type_id)
        input_names: set[str] = set()
        for selector_input in self.inputs:
            selector_input.validate()
            if selector_input.name in input_names:
                raise WorkspaceError(f"duplicate selector input name: {selector_input.name}")
            input_names.add(selector_input.name)
        for rng_call in self.rng_calls:
            rng_call.validate()
        if self.random_range is not None:
            lower, upper = self.random_range
            if lower > upper:
                raise WorkspaceError(
                    f"random range lower bound {lower} exceeds upper bound {upper}"
                )
        if self.selection_mode == "fixed_metadata":
            if self.rng_calls or self.random_range is not None:
                raise WorkspaceError(
                    "fixed metadata selector cannot claim RNG calls or a random range"
                )
        elif not self.rng_calls or self.random_range is None:
            raise WorkspaceError("weighted random selector requires RNG calls and a random range")
        for forced_path in self.forced_paths:
            forced_path.validate(type_ids)


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _parse_integer(value: object, label: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value, 0)
        raise ValueError
    except ValueError as exc:
        raise WorkspaceError(f"{label} must be an integer") from exc


def _address_ref(value: object, label: str) -> AddressRef:
    item = _require_object(value, label)
    try:
        result = AddressRef(
            component=str(item["component"]),
            runtime_address=_parse_integer(item["runtime_address"], f"{label}.runtime_address"),
            component_offset=_parse_integer(item["component_offset"], f"{label}.component_offset"),
            confidence=Confidence(str(item["confidence"])),
            evidence=str(item["evidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid {label}: {exc}") from exc
    result.validate()
    return result


def normalize_selector_capture(payload: dict[str, object]) -> BattleTypeSelectorEvidence:
    try:
        types = tuple(
            BattleTypeEvidence(
                type_id=_parse_integer(item["type_id"], f"types[{index}].type_id"),
                label=str(item["label"]),
                confidence=Confidence(str(item["confidence"])),
                evidence=str(item["evidence"]),
            )
            for index, raw in enumerate(_require_array(payload["types"], "types"))
            for item in (_require_object(raw, f"types[{index}]"),)
        )
        inputs = tuple(
            SelectorInput(
                name=str(item["name"]),
                source=str(item["source"]),
                influence=str(item["influence"]),
                confidence=Confidence(str(item["confidence"])),
                evidence=str(item["evidence"]),
            )
            for index, raw in enumerate(_require_array(payload["inputs"], "inputs"))
            for item in (_require_object(raw, f"inputs[{index}]"),)
        )
        rng_calls = tuple(
            _address_ref(raw, f"rng_calls[{index}]")
            for index, raw in enumerate(_require_array(payload["rng_calls"], "rng_calls"))
        )
        raw_range = payload.get("random_range")
        random_range = None
        if raw_range is not None:
            bounds = _require_array(raw_range, "random_range")
            if len(bounds) != 2:
                raise WorkspaceError("random_range must contain exactly two integers")
            random_range = (
                _parse_integer(bounds[0], "random_range[0]"),
                _parse_integer(bounds[1], "random_range[1]"),
            )
        forced_paths: list[ForcedPath] = []
        for index, raw in enumerate(_require_array(payload["forced_paths"], "forced_paths")):
            item = _require_object(raw, f"forced_paths[{index}]")
            raw_mapping = _require_object(item["mapping"], f"forced_paths[{index}].mapping")
            mapping = tuple(
                sorted(
                    (
                        _parse_integer(code, f"forced_paths[{index}].mapping key"),
                        _parse_integer(
                            type_id,
                            f"forced_paths[{index}].mapping[{code}]",
                        ),
                    )
                    for code, type_id in raw_mapping.items()
                )
            )
            forced_paths.append(
                ForcedPath(
                    name=str(item["name"]),
                    source=str(item["source"]),
                    mapping=mapping,
                    confidence=Confidence(str(item["confidence"])),
                    evidence=str(item["evidence"]),
                )
            )
        evidence = BattleTypeSelectorEvidence(
            selector=_address_ref(payload["selector"], "selector"),
            selection_mode=str(payload["selection_mode"]),
            rng_calls=rng_calls,
            random_range=random_range,
            types=tuple(sorted(types, key=lambda item: item.type_id)),
            inputs=tuple(sorted(inputs, key=lambda item: item.name)),
            result_storage=_address_ref(payload["result_storage"], "result_storage"),
            forced_paths=tuple(sorted(forced_paths, key=lambda item: item.name)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid battle-type selector evidence: {exc}") from exc
    evidence.validate()
    return evidence


def _validate_type_id(value: int, label: str, *, allow_sentinel: bool = False) -> None:
    minimum = -1 if allow_sentinel else 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    if not minimum <= value < _BATTLE_TYPE_COUNT:
        if allow_sentinel:
            raise WorkspaceError(f"{label} must be -1 or a battle type ID 0-5")
        raise WorkspaceError(f"{label} must be a battle type ID 0-5")


def resolve_battle_type_precedence(
    constructor_type: int,
    fallback_type: int,
    scripted_override: int | None,
) -> int:
    """Model the confirmed original selector precedence without changing gameplay."""

    _validate_type_id(constructor_type, "constructor type", allow_sentinel=True)
    _validate_type_id(fallback_type, "fallback type")
    if scripted_override is not None:
        _validate_type_id(scripted_override, "scripted override")

    provisional = fallback_type if constructor_type == -1 else constructor_type
    return provisional if scripted_override is None else scripted_override


@dataclass(frozen=True)
class System2BattleTypeTrace:
    explicit_type_argument: int
    record_valid: bool
    weights: tuple[int, ...]
    weight_total: int
    weighted_result: int | None
    scripted_override: int | None
    final_type: int
    legacy_fallback: bool
    fallback_scope: FallbackScope
    fallback_reason: FallbackReason

    def to_dict(self) -> dict[str, object]:
        return {
            "explicit_type_argument": self.explicit_type_argument,
            "record_valid": self.record_valid,
            "weights": list(self.weights),
            "weight_total": self.weight_total,
            "weighted_result": self.weighted_result,
            "scripted_override": self.scripted_override,
            "final_type": self.final_type,
            "legacy_fallback": self.legacy_fallback,
            "fallback_scope": self.fallback_scope.value,
            "fallback_reason": self.fallback_reason.value,
        }


@dataclass(frozen=True)
class System2BattleTypeResult:
    final_type: int
    next_rng_state: int
    weighted_result: int | None
    fallback_scope: FallbackScope
    fallback_reason: FallbackReason
    trace: System2BattleTypeTrace


def _validate_rng_state(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError("weighted RNG state must be an integer")
    if not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise WorkspaceError("weighted RNG state must fit unsigned 64-bit")


def _battle_type_result(
    *,
    constructor_type: int,
    record_valid: bool,
    weights: tuple[int, ...],
    weighted_result: int | None,
    scripted_override: int | None,
    provisional_type: int,
    rng_state: int,
    fallback_scope: FallbackScope,
    fallback_reason: FallbackReason,
    legacy_fallback: bool,
) -> System2BattleTypeResult:
    final_type = provisional_type if scripted_override is None else scripted_override
    trace = System2BattleTypeTrace(
        explicit_type_argument=constructor_type,
        record_valid=record_valid,
        weights=weights,
        weight_total=sum(weights),
        weighted_result=weighted_result,
        scripted_override=scripted_override,
        final_type=final_type,
        legacy_fallback=legacy_fallback,
        fallback_scope=fallback_scope,
        fallback_reason=fallback_reason,
    )
    return System2BattleTypeResult(
        final_type=final_type,
        next_rng_state=rng_state,
        weighted_result=weighted_result,
        fallback_scope=fallback_scope,
        fallback_reason=fallback_reason,
        trace=trace,
    )


def select_system2_battle_type(
    record: GateRecordV1,
    constructor_type: int,
    scripted_override: int | None,
    rng_state: int,
    legacy_type: int,
) -> System2BattleTypeResult:
    """Apply confirmed constructor, weighted fallback, and script precedence."""

    from bakugan_ds.gates.history import (
        validate_weight_vector,
        weighted_index,
        weighted_roll_from_state,
    )
    from bakugan_ds.gates.system2 import (
        FallbackReason,
        FallbackScope,
        record_fallback_reason,
    )

    _validate_type_id(constructor_type, "constructor type", allow_sentinel=True)
    _validate_type_id(legacy_type, "legacy type")
    if scripted_override is not None:
        _validate_type_id(scripted_override, "scripted override")
    _validate_rng_state(rng_state)

    record_reason = record_fallback_reason(record)
    record_valid = record_reason is FallbackReason.NONE
    weights = tuple(record.battle_weights) if record_valid else (0, 0, 0, 0, 0, 0)

    if constructor_type != -1:
        return _battle_type_result(
            constructor_type=constructor_type,
            record_valid=record_valid,
            weights=weights,
            weighted_result=None,
            scripted_override=scripted_override,
            provisional_type=constructor_type,
            rng_state=rng_state,
            fallback_scope=FallbackScope.NONE,
            fallback_reason=FallbackReason.NONE,
            legacy_fallback=False,
        )

    if not record_valid:
        return _battle_type_result(
            constructor_type=constructor_type,
            record_valid=False,
            weights=weights,
            weighted_result=None,
            scripted_override=scripted_override,
            provisional_type=legacy_type,
            rng_state=rng_state,
            fallback_scope=FallbackScope.RECORD,
            fallback_reason=record_reason,
            legacy_fallback=True,
        )

    try:
        validate_weight_vector(weights)
    except WorkspaceError:
        return _battle_type_result(
            constructor_type=constructor_type,
            record_valid=True,
            weights=weights,
            weighted_result=None,
            scripted_override=scripted_override,
            provisional_type=legacy_type,
            rng_state=rng_state,
            fallback_scope=FallbackScope.BATTLE_TYPE,
            fallback_reason=FallbackReason.INVALID_WEIGHT_VECTOR,
            legacy_fallback=True,
        )

    next_state, roll = weighted_roll_from_state(rng_state, sum(weights))
    weighted_result = weighted_index(weights, roll)
    return _battle_type_result(
        constructor_type=constructor_type,
        record_valid=True,
        weights=weights,
        weighted_result=weighted_result,
        scripted_override=scripted_override,
        provisional_type=weighted_result,
        rng_state=next_state,
        fallback_scope=FallbackScope.NONE,
        fallback_reason=FallbackReason.NONE,
        legacy_fallback=False,
    )
