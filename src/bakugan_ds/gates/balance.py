from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.record import (
    NO_PREFERRED_TYPE,
    GateArchetype,
    GateConditionId,
    GateEffectId,
    GateRecordV1,
    GateTargetMode,
)

ATTRIBUTE_NAMES = (
    "pyrus",
    "aquos",
    "subterra",
    "haos",
    "darkus",
    "ventus",
)
BATTLE_TYPE_NAMES = (
    "scratch",
    "timing",
    "pop",
    "spin",
    "trace",
    "bound",
)


class AttributeRelation(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    NEUTRAL = "neutral"
    OPPOSED = "opposed"


class BattleWeightPressure(StrEnum):
    NEUTRAL = "neutral"
    MILD = "mild"
    STRONG = "strong"
    EXTREME_BOUNDED = "extreme_bounded"


@dataclass(frozen=True)
class AttributeProfileReport:
    modifiers: tuple[int, ...]
    tiers: tuple[AttributeRelation, ...]
    minimum: int
    maximum: int
    spread: int
    positive_count: int
    negative_count: int


@dataclass(frozen=True)
class BattleWeightReport:
    weights: tuple[int, ...]
    total: int
    maximum: int
    minimum: int
    preferred_type: int
    pressure: BattleWeightPressure
    budget_cost: int
    maximum_probability_basis_points: int


@dataclass(frozen=True)
class GateBudgetBreakdown:
    flat_cost: int
    percentage_cost: int
    attribute_cost: int
    effect_cost: int
    battle_weight_cost: int
    negative_attribute_credit: int
    drawback_credit: int
    gross_budget: int
    net_budget: int


@dataclass(frozen=True)
class GateBalanceReport:
    card_id: int
    archetype: GateArchetype
    attribute: AttributeProfileReport
    battle_weights: BattleWeightReport
    budget: GateBudgetBreakdown


def _as_archetype(record: GateRecordV1) -> GateArchetype:
    try:
        return GateArchetype(record.archetype)
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D archetype ID: {record.archetype}") from exc


def _ceil_div_nonnegative(value: int, divisor: int) -> int:
    if value < 0:
        raise WorkspaceError("ceiling division input must be nonnegative")
    if divisor <= 0:
        raise WorkspaceError("ceiling division divisor must be positive")
    return (value + divisor - 1) // divisor


def classify_attribute_modifier(value: int) -> AttributeRelation:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError("attribute modifier must be an integer")
    if not -100 <= value <= 100:
        raise WorkspaceError("attribute modifier must be between -100 and 100")
    if value <= -10:
        return AttributeRelation.OPPOSED
    if value <= 9:
        return AttributeRelation.NEUTRAL
    if value <= 40:
        return AttributeRelation.SECONDARY
    return AttributeRelation.PRIMARY


def analyze_attribute_profile(record: GateRecordV1) -> AttributeProfileReport:
    modifiers = tuple(record.attribute_modifiers)
    if len(modifiers) != 6:
        raise WorkspaceError("attribute modifiers must contain exactly six entries")
    tiers = tuple(classify_attribute_modifier(value) for value in modifiers)
    minimum = min(modifiers)
    maximum = max(modifiers)
    return AttributeProfileReport(
        modifiers=modifiers,
        tiers=tiers,
        minimum=minimum,
        maximum=maximum,
        spread=maximum - minimum,
        positive_count=sum(value > 9 for value in modifiers),
        negative_count=sum(value < -9 for value in modifiers),
    )


def validate_attribute_profile(record: GateRecordV1) -> None:
    report = analyze_attribute_profile(record)
    archetype = _as_archetype(record)
    if archetype is GateArchetype.LEGACY:
        if any(report.modifiers):
            raise WorkspaceError("legacy Gate attribute modifiers must all be zero")
        return
    if archetype is GateArchetype.ATTRIBUTE:
        if report.maximum < 40:
            raise WorkspaceError("Attribute Gate requires a modifier of at least +40 G")
        if report.minimum > -20:
            raise WorkspaceError("Attribute Gate requires a modifier of at most -20 G")
        if report.spread < 60:
            raise WorkspaceError("Attribute Gate modifier spread must be at least 60 G")
        return
    if report.positive_count > 2:
        raise WorkspaceError("non-Attribute Gate may have at most two positive affinities")


def _probability_at_most(maximum: int, total: int, basis_points: int) -> bool:
    return maximum * 10_000 <= total * basis_points


def analyze_battle_weights(record: GateRecordV1) -> BattleWeightReport:
    archetype = _as_archetype(record)
    weights = tuple(record.battle_weights)
    if len(weights) != 6:
        raise WorkspaceError("battle weights must contain exactly six entries")
    if archetype is GateArchetype.LEGACY:
        if any(weights) or record.preferred_type != NO_PREFERRED_TYPE:
            raise WorkspaceError("legacy Gate battle weights must be canonical passthrough")
        return BattleWeightReport(
            weights=weights,
            total=0,
            maximum=0,
            minimum=0,
            preferred_type=NO_PREFERRED_TYPE,
            pressure=BattleWeightPressure.NEUTRAL,
            budget_cost=0,
            maximum_probability_basis_points=0,
        )

    if any(isinstance(value, bool) or not isinstance(value, int) for value in weights):
        raise WorkspaceError("battle weights must be integers")
    if any(value < 10 or value > 80 for value in weights):
        raise WorkspaceError("System 2.0 battle weights must be between 10 and 80")
    total = sum(weights)
    if not 120 <= total <= 300:
        raise WorkspaceError("System 2.0 battle weight total must be between 120 and 300")
    maximum = max(weights)
    minimum = min(weights)
    if maximum > minimum * 4:
        raise WorkspaceError("System 2.0 battle weight ratio must not exceed 4:1")
    if not _probability_at_most(maximum, total, 4_000):
        raise WorkspaceError("System 2.0 battle type probability must not exceed 40 percent")
    if not 0 <= record.preferred_type <= 5:
        raise WorkspaceError("System 2.0 preferred battle type must be 0 through 5")
    if weights[record.preferred_type] != maximum:
        raise WorkspaceError("preferred battle type must reference a maximum-weight entry")

    if _probability_at_most(maximum, total, 2_000):
        pressure = BattleWeightPressure.NEUTRAL
        budget_cost = 0
    elif _probability_at_most(maximum, total, 2_500):
        pressure = BattleWeightPressure.MILD
        budget_cost = 10
    elif _probability_at_most(maximum, total, 3_334):
        pressure = BattleWeightPressure.STRONG
        budget_cost = 20
    else:
        pressure = BattleWeightPressure.EXTREME_BOUNDED
        budget_cost = 30

    maximum_probability_basis_points = maximum * 10_000 // total
    return BattleWeightReport(
        weights=weights,
        total=total,
        maximum=maximum,
        minimum=minimum,
        preferred_type=record.preferred_type,
        pressure=pressure,
        budget_cost=budget_cost,
        maximum_probability_basis_points=maximum_probability_basis_points,
    )


def validate_battle_weights(record: GateRecordV1) -> None:
    analyze_battle_weights(record)


def _condition_rate(condition_id: int) -> int:
    try:
        condition = GateConditionId(condition_id)
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D condition ID: {condition_id}") from exc
    if condition in (
        GateConditionId.NONE,
        GateConditionId.OWNER_AHEAD,
        GateConditionId.SCORE_TIED,
    ):
        return 10
    if condition in (
        GateConditionId.OWNER_BEHIND,
        GateConditionId.OWNER_SCORE_ZERO,
    ):
        return 7
    if condition in (
        GateConditionId.OWNER_AT_MATCH_POINT,
        GateConditionId.OPPONENT_AT_MATCH_POINT,
    ):
        return 6
    if condition is GateConditionId.LANDING_GATE_CARD_WON:
        return 5
    raise AssertionError("condition enum dispatch is incomplete")


def _positive_effect_magnitude(record: GateRecordV1) -> int:
    try:
        effect = GateEffectId(record.effect_id)
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D effect ID: {record.effect_id}") from exc
    if effect is GateEffectId.NONE:
        return 0
    if effect is GateEffectId.ADD_SIGNED_G:
        return max(record.effect_value, 0)
    if effect is GateEffectId.SUBTRACT_MAGNITUDE_G:
        return 0
    raise AssertionError("effect enum dispatch is incomplete")


def _drawback_magnitude(record: GateRecordV1) -> int:
    try:
        drawback = GateEffectId(record.drawback_id)
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D drawback ID: {record.drawback_id}") from exc
    if drawback is GateEffectId.NONE:
        return 0
    if drawback is GateEffectId.ADD_SIGNED_G:
        return max(-record.drawback_value, 0)
    if drawback is GateEffectId.SUBTRACT_MAGNITUDE_G:
        return abs(record.drawback_value)
    raise AssertionError("drawback enum dispatch is incomplete")


def calculate_gate_budget(record: GateRecordV1) -> GateBudgetBreakdown:
    archetype = _as_archetype(record)
    attribute_report = analyze_attribute_profile(record)
    weight_report = analyze_battle_weights(record)
    if archetype is GateArchetype.LEGACY:
        return GateBudgetBreakdown(0, 0, 0, 0, 0, 0, 0, 0, 0)

    flat_cost = _ceil_div_nonnegative(max(record.flat_bonus_g, 0), 25) * 15
    percentage_cost = _ceil_div_nonnegative(max(record.percent_q8_8, 0), 16) * 5
    attribute_cost = sum(
        _ceil_div_nonnegative(value, 25) * 6
        for value in attribute_report.modifiers
        if value > 0
    )
    negative_attribute_credit = min(
        18,
        sum(
            _ceil_div_nonnegative(abs(value), 25) * 3
            for value in attribute_report.modifiers
            if value < 0
        ),
    )
    positive_effect = _positive_effect_magnitude(record)
    effect_cost = (
        _ceil_div_nonnegative(positive_effect, 25) * _condition_rate(record.condition_id)
        if positive_effect
        else 0
    )
    drawback_magnitude = _drawback_magnitude(record)
    drawback_credit = min(
        30,
        _ceil_div_nonnegative(drawback_magnitude, 25) * 5 if drawback_magnitude else 0,
    )
    gross_budget = flat_cost + percentage_cost + attribute_cost + effect_cost + weight_report.budget_cost
    net_budget = gross_budget - negative_attribute_credit - drawback_credit
    return GateBudgetBreakdown(
        flat_cost=flat_cost,
        percentage_cost=percentage_cost,
        attribute_cost=attribute_cost,
        effect_cost=effect_cost,
        battle_weight_cost=weight_report.budget_cost,
        negative_attribute_credit=negative_attribute_credit,
        drawback_credit=drawback_credit,
        gross_budget=gross_budget,
        net_budget=net_budget,
    )


def _require_budget_band(value: int, minimum: int, maximum: int, label: str) -> None:
    if not minimum <= value <= maximum:
        raise WorkspaceError(f"{label} net budget must be between {minimum} and {maximum}, got {value}")


def validate_archetype_invariants(
    record: GateRecordV1,
    attribute_report: AttributeProfileReport,
    weight_report: BattleWeightReport,
    budget: GateBudgetBreakdown,
) -> None:
    archetype = _as_archetype(record)
    if archetype is GateArchetype.LEGACY:
        if budget.net_budget != 0:
            raise WorkspaceError("legacy Gate budget must be zero")
        return

    if record.timing_phase != 0:
        raise WorkspaceError("Milestone 6D supports only pre-Gate calculation timing")
    if record.activation_limit or record.fatigue_rate or record.reserved:
        raise WorkspaceError("Milestone 6D deferred state fields must be zero")
    if record.secondary_effect_id or record.secondary_condition_id or record.secondary_value:
        raise WorkspaceError("Milestone 6D live records must not use secondary effects")
    try:
        target = GateTargetMode(record.target_mode)
    except ValueError as exc:
        raise WorkspaceError(f"unsupported Milestone 6D target mode: {record.target_mode}") from exc

    direct_g = budget.flat_cost + budget.percentage_cost + budget.attribute_cost

    if archetype is GateArchetype.COMEBACK:
        _require_budget_band(budget.net_budget, 85, 115, "Comeback")
        if record.condition_id not in (
            GateConditionId.OWNER_BEHIND,
            GateConditionId.OWNER_SCORE_ZERO,
        ):
            raise WorkspaceError("Comeback Gate requires an approved disadvantage condition")
        if _positive_effect_magnitude(record) <= 0:
            raise WorkspaceError("Comeback Gate requires a positive primary effect")
    elif archetype is GateArchetype.POWER:
        _require_budget_band(budget.net_budget, 90, 110, "Power")
        if weight_report.pressure is BattleWeightPressure.EXTREME_BOUNDED:
            raise WorkspaceError("Power Gate cannot use extreme-bounded battle weighting")
        if budget.gross_budget == 0 or direct_g * 100 < budget.gross_budget * 70:
            raise WorkspaceError("Power Gate requires at least 70 percent direct G budget")
    elif archetype is GateArchetype.SKILL:
        _require_budget_band(budget.net_budget, 90, 110, "Skill")
        if weight_report.budget_cost < 20:
            raise WorkspaceError("Skill Gate requires strong battle-type weighting")
    elif archetype is GateArchetype.CONTROL:
        _require_budget_band(budget.net_budget, 85, 110, "Control")
        if target is GateTargetMode.CURRENT_COMBATANT and record.condition_id == GateConditionId.NONE:
            raise WorkspaceError("Control Gate requires constrained targeting or a condition")
    elif archetype is GateArchetype.RISK:
        _require_budget_band(budget.net_budget, 85, 120, "Risk")
        if budget.gross_budget < 110:
            raise WorkspaceError("Risk Gate gross budget must be at least 110")
        if budget.drawback_credit <= 0:
            raise WorkspaceError("Risk Gate requires an explicit drawback")
    elif archetype is GateArchetype.ATTRIBUTE:
        _require_budget_band(budget.net_budget, 90, 110, "Attribute")
        if budget.gross_budget and (budget.flat_cost + budget.percentage_cost) * 100 > budget.gross_budget * 60:
            raise WorkspaceError("Attribute Gate cannot spend more than 60 percent on universal G")
        if attribute_report.maximum < 40 or attribute_report.minimum > -20 or attribute_report.spread < 60:
            raise WorkspaceError("Attribute Gate profile does not satisfy relationship rules")
    elif archetype is GateArchetype.CHAOS:
        _require_budget_band(budget.net_budget, 90, 120, "Chaos")
        if weight_report.pressure not in (
            BattleWeightPressure.STRONG,
            BattleWeightPressure.EXTREME_BOUNDED,
        ):
            raise WorkspaceError("Chaos Gate requires strong asymmetric battle weighting")
        if budget.drawback_credit <= 0:
            raise WorkspaceError("Chaos Gate requires an explicit drawback")
    else:
        raise AssertionError("archetype enum dispatch is incomplete")


def analyze_gate_balance(record: GateRecordV1) -> GateBalanceReport:
    record.validate()
    attribute_report = analyze_attribute_profile(record)
    validate_attribute_profile(record)
    weight_report = analyze_battle_weights(record)
    budget = calculate_gate_budget(record)
    validate_archetype_invariants(record, attribute_report, weight_report, budget)
    return GateBalanceReport(
        card_id=record.card_id,
        archetype=_as_archetype(record),
        attribute=attribute_report,
        battle_weights=weight_report,
        budget=budget,
    )
