from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.balance import analyze_gate_balance
from bakugan_ds.gates.record import (
    RECORD_COUNT,
    GateArchetype,
    GateEffectId,
    GateRecordV1,
    serialize_record,
)
from bakugan_ds.gates.roster_metadata import (
    DesignTier,
    GateRosterMetadataEntry,
)
from bakugan_ds.gates.system2 import (
    FallbackReason,
    FallbackScope,
    GateCalculationContext,
    calculate_gate_bonus,
)

REFERENCE_CORE_G = (190, 400, 525, 650, 695)
REFERENCE_ATTRIBUTES = tuple(range(6))
REFERENCE_TARGET_CASES = (
    ("owner", 1, 1),
    ("non_owner", 0, 1),
)
REFERENCE_SCORE_CASES = (
    ("owner_zero", 0, 1),
    ("owner_behind", 1, 2),
    ("tied", 1, 1),
    ("owner_ahead", 2, 1),
    ("owner_at_match_point", 2, 0),
    ("opponent_at_match_point", 0, 2),
)
REFERENCE_LANDING_CASES = (
    ("missing", None),
    ("nonwinning", 0),
    ("winning", 1),
)
REFERENCE_CASE_COUNT = (
    len(REFERENCE_CORE_G)
    * len(REFERENCE_ATTRIBUTES)
    * len(REFERENCE_TARGET_CASES)
    * len(REFERENCE_SCORE_CASES)
    * len(REFERENCE_LANDING_CASES)
)

_ARCHETYPE_DISTRIBUTION_BANDS = {
    GateArchetype.POWER: (12, 18),
    GateArchetype.SKILL: (14, 20),
    GateArchetype.CONTROL: (14, 20),
    GateArchetype.COMEBACK: (10, 16),
    GateArchetype.RISK: (12, 18),
    GateArchetype.ATTRIBUTE: (18, 26),
    GateArchetype.CHAOS: (6, 12),
}
_TIER_SWING_BANDS: dict[DesignTier, tuple[int | None, int]] = {
    DesignTier.EARLY_COMMON: (70, 130),
    DesignTier.MID: (110, 180),
    DesignTier.RARE_SPECIALIZED: (140, 220),
    DesignTier.HIGH_RISK_CONDITIONAL: (None, 250),
}


@dataclass(frozen=True)
class _Scenario:
    core_g: int
    attribute_id: int
    target_name: str
    current_participant: int
    owner_participant: int
    score_name: str
    owner_score: int
    opposing_score: int
    landing_name: str
    landing_result: int | None


@dataclass(frozen=True)
class _CaseResult:
    effective_gate_bonus: int | None
    target_total_g: int | None
    fallback_scope: FallbackScope
    fallback_reason: FallbackReason

    def signature(self) -> tuple[object, ...]:
        return (
            self.effective_gate_bonus,
            self.target_total_g,
            self.fallback_scope.value,
            self.fallback_reason.value,
        )


@dataclass(frozen=True)
class _RecordEvaluation:
    record: GateRecordV1
    cases: tuple[_CaseResult, ...]
    owner_values: tuple[int, ...]
    non_owner_values: tuple[int, ...]

    @property
    def values(self) -> tuple[int, ...]:
        return self.owner_values + self.non_owner_values

    def signature(self) -> tuple[tuple[object, ...], ...]:
        return tuple(case.signature() for case in self.cases)


def _iter_reference_scenarios() -> Iterable[_Scenario]:
    for core_g in REFERENCE_CORE_G:
        for attribute_id in REFERENCE_ATTRIBUTES:
            for target_name, current_participant, owner_participant in REFERENCE_TARGET_CASES:
                for score_name, owner_score, opposing_score in REFERENCE_SCORE_CASES:
                    for landing_name, landing_result in REFERENCE_LANDING_CASES:
                        yield _Scenario(
                            core_g=core_g,
                            attribute_id=attribute_id,
                            target_name=target_name,
                            current_participant=current_participant,
                            owner_participant=owner_participant,
                            score_name=score_name,
                            owner_score=owner_score,
                            opposing_score=opposing_score,
                            landing_name=landing_name,
                            landing_result=landing_result,
                        )


_REFERENCE_SCENARIOS = tuple(_iter_reference_scenarios())
if len(_REFERENCE_SCENARIOS) != REFERENCE_CASE_COUNT:
    raise AssertionError("Milestone 6E reference matrix size is inconsistent")


def _evaluate_record(record: GateRecordV1) -> _RecordEvaluation:
    cases: list[_CaseResult] = []
    owner_values: list[int] = []
    non_owner_values: list[int] = []
    for scenario in _REFERENCE_SCENARIOS:
        result = calculate_gate_bonus(
            record,
            GateCalculationContext(
                compressed_core_g=scenario.core_g,
                attribute_id=scenario.attribute_id,
                current_participant=scenario.current_participant,
                owner_participant=scenario.owner_participant,
                owner_side_score=scenario.owner_score,
                opposing_side_score=scenario.opposing_score,
                gate_id=record.card_id,
                landing_result=scenario.landing_result,
            ),
        )
        case = _CaseResult(
            effective_gate_bonus=result.effective_gate_bonus,
            target_total_g=result.target_total_g,
            fallback_scope=result.fallback_scope,
            fallback_reason=result.fallback_reason,
        )
        cases.append(case)
        if result.effective_gate_bonus is not None:
            if scenario.target_name == "owner":
                owner_values.append(result.effective_gate_bonus)
            else:
                non_owner_values.append(result.effective_gate_bonus)
    return _RecordEvaluation(
        record=record,
        cases=tuple(cases),
        owner_values=tuple(owner_values),
        non_owner_values=tuple(non_owner_values),
    )


def _runtime_signature(record: GateRecordV1) -> bytes:
    return serialize_record(replace(record, card_id=1))


def _group_ids_by_signature(
    records: Iterable[GateRecordV1],
) -> tuple[tuple[int, ...], ...]:
    groups: dict[bytes, list[int]] = defaultdict(list)
    for record in records:
        groups[_runtime_signature(record)].append(record.card_id)
    return tuple(
        tuple(card_ids)
        for card_ids in sorted(groups.values(), key=lambda group: group[0])
        if len(card_ids) > 1
    )


def find_exact_runtime_duplicate_groups(
    records: tuple[GateRecordV1, ...],
    *,
    include_legacy: bool = False,
) -> tuple[tuple[int, ...], ...]:
    selected = (
        records
        if include_legacy
        else tuple(record for record in records if record.archetype != GateArchetype.LEGACY)
    )
    return _group_ids_by_signature(selected)


def _evaluation_duplicate_groups(
    evaluations: tuple[_RecordEvaluation, ...],
) -> tuple[tuple[int, ...], ...]:
    groups: dict[tuple[tuple[object, ...], ...], list[int]] = defaultdict(list)
    for evaluation in evaluations:
        if evaluation.record.archetype == GateArchetype.LEGACY:
            continue
        groups[evaluation.signature()].append(evaluation.record.card_id)
    return tuple(
        tuple(card_ids)
        for card_ids in sorted(groups.values(), key=lambda group: group[0])
        if len(card_ids) > 1
    )


def _median_fraction(values: tuple[int, ...]) -> dict[str, int] | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return {"denominator": 1, "numerator": ordered[midpoint]}
    return {
        "denominator": 2,
        "numerator": ordered[midpoint - 1] + ordered[midpoint],
    }


def _evaluation_sha256(evaluation: _RecordEvaluation) -> str:
    encoded = json.dumps(
        evaluation.signature(),
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _tier_out_of_bounds(
    metadata: GateRosterMetadataEntry,
    values: tuple[int, ...],
) -> bool:
    if metadata.design_tier is DesignTier.UNASSIGNED or not values:
        return False
    minimum, maximum = _TIER_SWING_BANDS[metadata.design_tier]
    return (minimum is not None and min(values) < minimum) or max(values) > maximum


def _card_report(
    evaluation: _RecordEvaluation,
    metadata: GateRosterMetadataEntry,
) -> dict[str, object]:
    values = evaluation.values
    valid_case_count = len(values)
    fallback_case_count = len(evaluation.cases) - valid_case_count
    if evaluation.record.archetype == GateArchetype.LEGACY:
        pressure = "legacy"
        net_budget = 0
    else:
        balance = analyze_gate_balance(evaluation.record)
        pressure = balance.battle_weights.pressure.value
        net_budget = balance.budget.net_budget
    return {
        "archetype": GateArchetype(evaluation.record.archetype).name.lower(),
        "battle_weight_pressure": pressure,
        "card_id": evaluation.record.card_id,
        "design_tier": metadata.design_tier.value,
        "effective_gate_bonus": {
            "maximum": max(values) if values else None,
            "median": _median_fraction(values),
            "minimum": min(values) if values else None,
            "non_owner_maximum": (
                max(evaluation.non_owner_values) if evaluation.non_owner_values else None
            ),
            "owner_maximum": (max(evaluation.owner_values) if evaluation.owner_values else None),
        },
        "evaluation_sha256": _evaluation_sha256(evaluation),
        "fallback_case_count": fallback_case_count,
        "mapping_confidence": metadata.mapping_confidence.value,
        "name": metadata.name,
        "net_budget": net_budget,
        "out_of_tier": _tier_out_of_bounds(metadata, values),
        "runtime_signature_sha256": hashlib.sha256(
            _runtime_signature(evaluation.record)
        ).hexdigest(),
        "valid_case_count": valid_case_count,
    }


def _drawback_magnitude(record: GateRecordV1) -> int:
    drawback = GateEffectId(record.drawback_id)
    if drawback is GateEffectId.NONE:
        return 0
    if drawback is GateEffectId.ADD_SIGNED_G:
        return max(-record.drawback_value, 0)
    return abs(record.drawback_value)


def _maximum_probability_basis_points(record: GateRecordV1) -> int:
    if record.archetype == GateArchetype.LEGACY:
        return 0
    total = sum(record.battle_weights)
    return max(record.battle_weights) * 10_000 // total


def _potential_dominance_pairs(
    evaluations: tuple[_RecordEvaluation, ...],
) -> tuple[dict[str, int], ...]:
    live = tuple(
        evaluation
        for evaluation in evaluations
        if evaluation.record.archetype != GateArchetype.LEGACY
    )
    findings: list[dict[str, int]] = []
    for candidate in live:
        for other in live:
            if candidate.record.card_id == other.record.card_id:
                continue
            if (
                candidate.record.condition_id != other.record.condition_id
                or candidate.record.target_mode != other.record.target_mode
                or candidate.record.preferred_type != other.record.preferred_type
                or candidate.record.drawback_id != other.record.drawback_id
            ):
                continue
            paired = tuple(
                (left.effective_gate_bonus, right.effective_gate_bonus)
                for left, right in zip(candidate.cases, other.cases, strict=True)
                if left.effective_gate_bonus is not None and right.effective_gate_bonus is not None
            )
            if not paired:
                continue
            if not all(left >= right for left, right in paired):
                continue
            if not any(left > right for left, right in paired):
                continue
            if _maximum_probability_basis_points(candidate.record) < (
                _maximum_probability_basis_points(other.record)
            ):
                continue
            if _drawback_magnitude(candidate.record) > _drawback_magnitude(other.record):
                continue
            findings.append(
                {
                    "dominant_card_id": candidate.record.card_id,
                    "dominated_card_id": other.record.card_id,
                }
            )
    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding["dominant_card_id"],
                finding["dominated_card_id"],
            ),
        )
    )


def _identity_conflicts(
    records: tuple[GateRecordV1, ...],
    metadata: tuple[GateRosterMetadataEntry, ...],
) -> list[dict[str, object]]:
    conflicts: list[dict[str, object]] = []
    if len(records) != len(metadata):
        conflicts.append(
            {
                "kind": "record_metadata_count",
                "metadata_count": len(metadata),
                "record_count": len(records),
            }
        )
        return conflicts
    for record, entry in zip(records, metadata, strict=True):
        if record.card_id != entry.card_id:
            conflicts.append(
                {
                    "kind": "card_id",
                    "metadata_card_id": entry.card_id,
                    "record_card_id": record.card_id,
                }
            )
        if record.archetype != entry.archetype:
            conflicts.append(
                {
                    "card_id": record.card_id,
                    "kind": "archetype",
                    "metadata_archetype": int(entry.archetype),
                    "record_archetype": record.archetype,
                }
            )
    return conflicts


def _distribution(
    records: tuple[GateRecordV1, ...],
) -> tuple[dict[str, int], list[str]]:
    counts = {
        archetype.name.lower(): sum(record.archetype == archetype for record in records)
        for archetype in GateArchetype
        if archetype is not GateArchetype.LEGACY
    }
    warnings: list[str] = []
    for archetype, (minimum, maximum) in _ARCHETYPE_DISTRIBUTION_BANDS.items():
        count = counts[archetype.name.lower()]
        if count < minimum or count > maximum:
            warnings.append(
                f"{archetype.name.lower()} count {count} is outside {minimum}..{maximum}"
            )
    return counts, warnings


def build_roster_analysis(
    records: tuple[GateRecordV1, ...],
    metadata: tuple[GateRosterMetadataEntry, ...],
) -> dict[str, object]:
    if len(records) != RECORD_COUNT:
        raise WorkspaceError(
            f"Milestone 6E roster analysis requires exactly {RECORD_COUNT} records"
        )
    expected_ids = tuple(range(1, RECORD_COUNT + 1))
    if tuple(record.card_id for record in records) != expected_ids:
        raise WorkspaceError("Milestone 6E records must use sorted IDs 1 through 103")
    for record in records:
        record.validate()

    evaluations = tuple(_evaluate_record(record) for record in records)
    live_records = tuple(record for record in records if record.archetype != GateArchetype.LEGACY)
    legacy_records = tuple(record for record in records if record.archetype == GateArchetype.LEGACY)
    exact_live = find_exact_runtime_duplicate_groups(records)
    legacy_duplicates = _group_ids_by_signature(legacy_records)
    evaluation_duplicates = _evaluation_duplicate_groups(evaluations)
    distribution, distribution_warnings = _distribution(records)
    conflicts = _identity_conflicts(records, metadata)
    cards = (
        [
            _card_report(evaluation, entry)
            for evaluation, entry in zip(evaluations, metadata, strict=True)
        ]
        if not conflicts
        else []
    )

    return {
        "archetype_distribution": distribution,
        "archetype_distribution_warnings": distribution_warnings,
        "cards": cards,
        "format": "bakugan-ds-gate-milestone-6e-roster-analysis",
        "format_version": 1,
        "hard_duplicate_groups": [list(group) for group in exact_live],
        "identical_evaluation_groups": [list(group) for group in evaluation_duplicates],
        "identity_conflicts": conflicts,
        "legacy_duplicate_groups": [list(group) for group in legacy_duplicates],
        "legacy_passthrough_count": len(legacy_records),
        "live_card_ids": [record.card_id for record in live_records],
        "matrix": {
            "attributes": list(REFERENCE_ATTRIBUTES),
            "case_count_per_record": REFERENCE_CASE_COUNT,
            "core_g": list(REFERENCE_CORE_G),
            "landing_contexts": [name for name, _ in REFERENCE_LANDING_CASES],
            "score_contexts": [name for name, _, _ in REFERENCE_SCORE_CASES],
            "targets": [name for name, _, _ in REFERENCE_TARGET_CASES],
        },
        "potential_dominance_pairs": list(_potential_dominance_pairs(evaluations)),
        "record_count": len(records),
        "valid_for_draft": not exact_live and not evaluation_duplicates and not conflicts,
    }


def validate_hard_duplicate_classes(report: dict[str, object]) -> None:
    exact = report.get("hard_duplicate_groups")
    if isinstance(exact, list) and exact:
        raise WorkspaceError(f"exact runtime duplicate Gate classes: {exact}")
    evaluation = report.get("identical_evaluation_groups")
    if isinstance(evaluation, list) and evaluation:
        raise WorkspaceError(f"identical evaluation Gate classes: {evaluation}")


def write_roster_analysis(
    path: Path,
    records: tuple[GateRecordV1, ...],
    metadata: tuple[GateRosterMetadataEntry, ...],
) -> None:
    report = build_roster_analysis(records, metadata)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
