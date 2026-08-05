from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import load_gate_roster_authoring_document
from bakugan_ds.gates.balance import (
    ATTRIBUTE_NAMES,
    BATTLE_TYPE_NAMES,
    BattleWeightPressure,
    GateBalanceReport,
    analyze_gate_balance,
)
from bakugan_ds.gates.record import GateArchetype, GateRecordV1, serialize_record
from bakugan_ds.gates.roster_analysis import _evaluate_record
from bakugan_ds.gates.roster_metadata import (
    DesignTier,
    ReviewStatus,
    load_gate_roster_metadata,
    write_gate_roster_metadata,
)
from bakugan_ds.gates.roster_templates import (
    GateRosterTemplate,
    load_gate_roster_templates,
)
from bakugan_ds.gates.system2 import FallbackReason, record_fallback_reason

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
TEMPLATES = Path("config/gates/milestone-6e-archetype-templates.json")
SKILL_IDS = (16, 17, 18, *range(20, 32))
CONTROL_IDS = (*range(32, 40), *range(62, 69))

CONDITION_NAMES = {
    0: "unconditionally",
    1: "while the owner side is behind",
    2: "while the owner side is ahead",
    3: "while the score is tied",
    4: "while the owner side has no captures",
    5: "while the owner side is at match point",
    6: "while the opposing side is at match point",
    7: "after a winning Gate landing",
}
TARGET_NAMES = {
    0: "the current combatant",
    1: "the Gate owner",
    2: "the non-owner combatant",
}
SKILL_RULES = (
    ("template", None),
    ("battle-only", (0, 0, 0, 0, 0)),
    ("behind-owner", (1, 0, 1, 25, 1)),
    ("tied-current", (3, 0, 1, 25, 0)),
    ("zero-owner", (4, 0, 1, 25, 1)),
    ("opponent-matchpoint", (6, 0, 1, 25, 1)),
    ("landing-owner", (7, 1, 1, 25, 1)),
)
CONTROL_RULES = (
    ("template", None),
    ("nonowner-tax", (0, 0, 2, 25, 2)),
    ("owner-matchpoint-denial", (5, 0, 2, 25, 2)),
    ("opponent-matchpoint-reward", (6, 0, 1, 25, 1)),
    ("behind-owner", (1, 0, 1, 25, 1)),
    ("ahead-owner", (2, 0, 1, 25, 1)),
    ("tied-current", (3, 0, 1, 25, 0)),
    ("zero-owner", (4, 0, 1, 25, 1)),
    ("landing-owner", (7, 1, 1, 25, 1)),
    ("landing-nonowner", (7, 1, 2, 25, 2)),
)
CONTROL_REQUIREMENTS: tuple[tuple[int, int] | None, ...] = (
    (7, 1),
    (7, 2),
    (0, 2),
    (5, 2),
    (6, 1),
    (1, 1),
    (2, 1),
    (3, 0),
    (4, 1),
    None,
    None,
    None,
    None,
    None,
    None,
)


@dataclass(frozen=True)
class Candidate:
    record: GateRecordV1
    template_id: str
    balance: GateBalanceReport


@dataclass(frozen=True)
class EvaluatedCandidate:
    candidate: Candidate
    tier: DesignTier
    evaluation_signature: tuple[tuple[object, ...], ...]
    minimum: int
    maximum: int


def rotate_right(values: tuple[int, ...], shift: int) -> tuple[int, ...]:
    shift %= len(values)
    return values if shift == 0 else values[-shift:] + values[:-shift]


def tier_for(values: tuple[int, ...]) -> DesignTier | None:
    if not values:
        return None
    minimum = min(values)
    maximum = max(values)
    if minimum >= 70 and maximum <= 130:
        return DesignTier.EARLY_COMMON
    if minimum >= 110 and maximum <= 180:
        return DesignTier.MID
    if minimum >= 140 and maximum <= 220:
        return DesignTier.RARE_SPECIALIZED
    if maximum <= 250:
        return DesignTier.HIGH_RISK_CONDITIONAL
    return None


def apply_rule(
    prototype: GateRecordV1,
    rule: tuple[int, int, int, int, int] | None,
    effect_drop: int,
) -> GateRecordV1:
    if rule is None:
        return replace(
            prototype,
            effect_value=max(0, prototype.effect_value - effect_drop),
        )
    condition_id, condition_value, effect_id, effect_value, target_mode = rule
    return replace(
        prototype,
        condition_id=condition_id,
        condition_value=condition_value,
        effect_id=effect_id,
        effect_value=effect_value,
        target_mode=target_mode,
    )


def build_candidates(
    templates: tuple[GateRosterTemplate, ...],
    archetype: GateArchetype,
) -> tuple[Candidate, ...]:
    rules = SKILL_RULES if archetype is GateArchetype.SKILL else CONTROL_RULES
    candidates: dict[bytes, Candidate] = {}
    for template in templates:
        if template.archetype is not archetype:
            continue
        prototype = template.prototype
        for flat_drop, percent_drop, attribute_shift in product(
            (0, 25, 50), (0, 16, 32), range(6)
        ):
            for rule_name, rule in rules:
                effect_drops = (0, 25, 50) if rule is None else (0,)
                for effect_drop in effect_drops:
                    ruled = apply_rule(prototype, rule, effect_drop)
                    record = replace(
                        ruled,
                        card_id=1,
                        flat_bonus_g=max(0, ruled.flat_bonus_g - flat_drop),
                        percent_q8_8=max(0, ruled.percent_q8_8 - percent_drop),
                        attribute_modifiers=rotate_right(
                            ruled.attribute_modifiers, attribute_shift
                        ),
                    )
                    try:
                        balance = analyze_gate_balance(record)
                    except WorkspaceError:
                        continue
                    if record_fallback_reason(record) is not FallbackReason.NONE:
                        continue
                    if archetype is GateArchetype.SKILL and balance.battle_weights.pressure not in {
                        BattleWeightPressure.STRONG,
                        BattleWeightPressure.EXTREME_BOUNDED,
                    }:
                        continue
                    signature = serialize_record(record)
                    candidates.setdefault(
                        signature,
                        Candidate(
                            record=record,
                            template_id=f"{template.template_id}:{rule_name}",
                            balance=balance,
                        ),
                    )
    return tuple(
        sorted(
            candidates.values(),
            key=lambda item: (
                item.template_id,
                item.record.condition_id,
                item.record.target_mode,
                abs(item.balance.budget.net_budget - 100),
                serialize_record(item.record),
            ),
        )
    )


def evaluate_candidate(candidate: Candidate) -> EvaluatedCandidate | None:
    evaluation = _evaluate_record(candidate.record)
    tier = tier_for(evaluation.values)
    if tier is None:
        return None
    return EvaluatedCandidate(
        candidate=candidate,
        tier=tier,
        evaluation_signature=evaluation.signature(),
        minimum=min(evaluation.values),
        maximum=max(evaluation.values),
    )


def with_preferred_type(record: GateRecordV1, preferred_type: int) -> GateRecordV1:
    shift = (preferred_type - record.preferred_type) % 6
    updated = replace(
        record,
        battle_weights=rotate_right(record.battle_weights, shift),
        preferred_type=preferred_type,
    )
    analyze_gate_balance(updated)
    return updated


def choose_batch(
    candidates: tuple[Candidate, ...],
    card_ids: tuple[int, ...],
    used_runtime: set[bytes],
    used_evaluations: set[tuple[tuple[object, ...], ...]],
    requirements: tuple[tuple[int, int] | None, ...] | None = None,
) -> tuple[tuple[int, EvaluatedCandidate, GateRecordV1], ...]:
    chosen: list[tuple[int, EvaluatedCandidate, GateRecordV1]] = []
    template_use: Counter[str] = Counter()
    condition_use: Counter[int] = Counter()
    target_use: Counter[int] = Counter()
    evaluation_cache: dict[bytes, EvaluatedCandidate | None] = {}

    for index, card_id in enumerate(card_ids):
        preferred_type = index % 6
        required = requirements[index] if requirements is not None else None
        ranked = sorted(
            candidates,
            key=lambda item: (
                template_use[item.template_id],
                condition_use[item.record.condition_id],
                target_use[item.record.target_mode],
                abs(item.balance.budget.net_budget - 100),
                item.template_id,
                serialize_record(item.record),
            ),
        )
        selected: tuple[EvaluatedCandidate, GateRecordV1, bytes] | None = None
        for candidate in ranked:
            if required is not None and (
                candidate.record.condition_id,
                candidate.record.target_mode,
            ) != required:
                continue
            behavior_key = serialize_record(candidate.record)
            evaluated = evaluation_cache.get(behavior_key)
            if behavior_key not in evaluation_cache:
                evaluated = evaluate_candidate(candidate)
                evaluation_cache[behavior_key] = evaluated
            if evaluated is None:
                continue
            if evaluated.evaluation_signature in used_evaluations:
                continue
            record = with_preferred_type(candidate.record, preferred_type)
            runtime = serialize_record(replace(record, card_id=1))
            if runtime in used_runtime:
                continue
            selected = evaluated, record, runtime
            break
        if selected is None:
            raise WorkspaceError(f"no distinct behavior remains for Gate {card_id}")

        evaluated, record, runtime = selected
        used_runtime.add(runtime)
        used_evaluations.add(evaluated.evaluation_signature)
        template_use[evaluated.candidate.template_id] += 1
        condition_use[evaluated.candidate.record.condition_id] += 1
        target_use[evaluated.candidate.record.target_mode] += 1
        chosen.append((card_id, evaluated, replace(record, card_id=card_id)))
    return tuple(chosen)


def metadata_copy(
    evaluated: EvaluatedCandidate,
    record: GateRecordV1,
) -> tuple[str, ...]:
    balance = analyze_gate_balance(record)
    primary_index = max(range(6), key=lambda index: record.attribute_modifiers[index])
    primary_attribute = ATTRIBUTE_NAMES[primary_index]
    preferred_battle = BATTLE_TYPE_NAMES[record.preferred_type]
    gameplay = (
        f"{GateArchetype(record.archetype).name.title()} Gate using "
        f"{evaluated.candidate.template_id} with {primary_attribute} emphasis."
    )
    g_summary = (
        f"{record.flat_bonus_g} flat G, {record.percent_q8_8}/256 "
        f"compressed-core scaling, {balance.attribute.positive_count} positive and "
        f"{balance.attribute.negative_count} opposed attribute relationships."
    )
    weight_summary = (
        f"{balance.battle_weights.pressure.value.replace('_', ' ').title()} "
        f"{preferred_battle} preference; every battle type remains reachable."
    )
    rule_summary = (
        f"{CONDITION_NAMES[record.condition_id]}, applies {record.effect_value} G "
        f"through effect {record.effect_id} to {TARGET_NAMES[record.target_mode]}."
    )
    rationale = (
        f"Unique {evaluated.candidate.template_id} variation with "
        f"{primary_attribute} as its highest relationship, {preferred_battle} "
        f"preference, condition {record.condition_id}, target {record.target_mode}, "
        f"and evaluated swing {evaluated.minimum}..{evaluated.maximum} G."
    )
    return gameplay, g_summary, weight_summary, rule_summary, rationale


def main() -> None:
    records = list(load_gate_roster_authoring_document(AUTHORING))
    metadata = list(load_gate_roster_metadata(METADATA))
    templates = load_gate_roster_templates(TEMPLATES)
    used_runtime: set[bytes] = set()
    used_evaluations: set[tuple[tuple[object, ...], ...]] = set()
    for record in records:
        if record.archetype == GateArchetype.LEGACY:
            continue
        used_runtime.add(serialize_record(replace(record, card_id=1)))
        used_evaluations.add(_evaluate_record(record).signature())

    skill_candidates = build_candidates(templates, GateArchetype.SKILL)
    control_candidates = build_candidates(templates, GateArchetype.CONTROL)
    skill_batch = choose_batch(
        skill_candidates,
        SKILL_IDS,
        used_runtime,
        used_evaluations,
    )
    control_batch = choose_batch(
        control_candidates,
        CONTROL_IDS,
        used_runtime,
        used_evaluations,
        CONTROL_REQUIREMENTS,
    )

    for card_id, evaluated, record in (*skill_batch, *control_batch):
        records[card_id - 1] = record
        gameplay, g_summary, weights, rule_summary, rationale = metadata_copy(
            evaluated, record
        )
        metadata[card_id - 1] = replace(
            metadata[card_id - 1],
            archetype=GateArchetype(record.archetype),
            design_tier=evaluated.tier,
            gameplay_identity=gameplay,
            g_influence_summary=g_summary,
            battle_weight_summary=weights,
            rule_summary=rule_summary,
            net_budget=analyze_gate_balance(record).budget.net_budget,
            differentiation_rationale=rationale,
            review_status=ReviewStatus.REVIEWED,
        )

    AUTHORING.write_text(
        json.dumps(
            {
                "format_version": 1,
                "records": [asdict(record) for record in records],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_gate_roster_metadata(METADATA, tuple(metadata))
    print(
        json.dumps(
            {
                "control_candidates": len(control_candidates),
                "control_records": len(control_batch),
                "skill_candidates": len(skill_candidates),
                "skill_records": len(skill_batch),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
