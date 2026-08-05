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
from bakugan_ds.gates.record import (
    GateArchetype,
    GateConditionId,
    GateEffectId,
    GateRecordV1,
    GateTargetMode,
    serialize_record,
)
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
RISK_IDS = tuple(range(82, 96))
CHAOS_IDS = tuple(range(96, 104))

CONDITION_NAMES = {
    GateConditionId.NONE: "unconditionally",
    GateConditionId.OWNER_BEHIND: "while the owner side is behind",
    GateConditionId.OWNER_AHEAD: "while the owner side is ahead",
    GateConditionId.SCORE_TIED: "while the score is tied",
    GateConditionId.OWNER_SCORE_ZERO: "while the owner side has no captures",
    GateConditionId.OWNER_AT_MATCH_POINT: "while the owner side is at match point",
    GateConditionId.OPPONENT_AT_MATCH_POINT: "while the opposing side is at match point",
    GateConditionId.LANDING_GATE_CARD_WON: "after a winning Gate landing",
}
TARGET_NAMES = {
    GateTargetMode.CURRENT_COMBATANT: "the current combatant",
    GateTargetMode.GATE_OWNER: "the Gate owner",
    GateTargetMode.GATE_NON_OWNER: "the non-owner combatant",
}
RULES = (
    ("unconditional-owner", GateConditionId.NONE, 0, GateTargetMode.GATE_OWNER),
    ("behind-owner", GateConditionId.OWNER_BEHIND, 0, GateTargetMode.GATE_OWNER),
    ("ahead-owner", GateConditionId.OWNER_AHEAD, 0, GateTargetMode.GATE_OWNER),
    ("tied-current", GateConditionId.SCORE_TIED, 0, GateTargetMode.CURRENT_COMBATANT),
    ("zero-owner", GateConditionId.OWNER_SCORE_ZERO, 0, GateTargetMode.GATE_OWNER),
    ("owner-matchpoint", GateConditionId.OWNER_AT_MATCH_POINT, 0, GateTargetMode.GATE_OWNER),
    (
        "opponent-matchpoint",
        GateConditionId.OPPONENT_AT_MATCH_POINT,
        0,
        GateTargetMode.GATE_OWNER,
    ),
    (
        "landing-owner",
        GateConditionId.LANDING_GATE_CARD_WON,
        1,
        GateTargetMode.GATE_OWNER,
    ),
    (
        "landing-nonowner",
        GateConditionId.LANDING_GATE_CARD_WON,
        1,
        GateTargetMode.GATE_NON_OWNER,
    ),
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
    if minimum >= 25 and maximum <= 250:
        return DesignTier.HIGH_RISK_CONDITIONAL
    return None


def build_candidates(
    templates: tuple[GateRosterTemplate, ...],
    archetype: GateArchetype,
) -> tuple[Candidate, ...]:
    candidates: dict[bytes, Candidate] = {}
    for template in templates:
        if template.archetype is not archetype:
            continue
        prototype = template.prototype
        for (
            flat_drop,
            percent_drop,
            attribute_shift,
            rule,
            effect_value,
            drawback_value,
        ) in product(
            (0, 25, 50),
            (0, 16, 32),
            range(6),
            RULES,
            (25, 50, 75, 100),
            (25, 50, 75, 100),
        ):
            rule_name, condition_id, condition_value, target_mode = rule
            record = replace(
                prototype,
                card_id=1,
                flat_bonus_g=max(25, prototype.flat_bonus_g - flat_drop),
                percent_q8_8=max(0, prototype.percent_q8_8 - percent_drop),
                attribute_modifiers=rotate_right(
                    prototype.attribute_modifiers, attribute_shift
                ),
                condition_id=condition_id,
                condition_value=condition_value,
                effect_id=GateEffectId.ADD_SIGNED_G,
                effect_value=effect_value,
                drawback_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
                drawback_value=drawback_value,
                target_mode=target_mode,
            )
            try:
                balance = analyze_gate_balance(record)
            except WorkspaceError:
                continue
            if record_fallback_reason(record) is not FallbackReason.NONE:
                continue
            if archetype is GateArchetype.RISK and balance.budget.gross_budget < 110:
                continue
            if archetype is GateArchetype.CHAOS and balance.battle_weights.pressure not in {
                BattleWeightPressure.STRONG,
                BattleWeightPressure.EXTREME_BOUNDED,
            }:
                continue
            signature = serialize_record(record)
            candidates.setdefault(
                signature,
                Candidate(
                    record=record,
                    template_id=(
                        f"{template.template_id}:{rule_name}:"
                        f"up-{effect_value}:down-{drawback_value}"
                    ),
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
) -> tuple[tuple[int, EvaluatedCandidate, GateRecordV1], ...]:
    chosen: list[tuple[int, EvaluatedCandidate, GateRecordV1]] = []
    template_use: Counter[str] = Counter()
    condition_use: Counter[int] = Counter()
    target_use: Counter[int] = Counter()
    evaluation_cache: dict[bytes, EvaluatedCandidate | None] = {}

    for index, card_id in enumerate(card_ids):
        preferred_type = index % 6
        ranked = sorted(
            candidates,
            key=lambda item: (
                condition_use[item.record.condition_id],
                target_use[item.record.target_mode],
                template_use[item.template_id],
                abs(item.balance.budget.net_budget - 100),
                item.template_id,
                serialize_record(item.record),
            ),
        )
        selected: tuple[EvaluatedCandidate, GateRecordV1, bytes] | None = None
        for candidate in ranked:
            key = serialize_record(candidate.record)
            evaluated = evaluation_cache.get(key)
            if key not in evaluation_cache:
                evaluated = evaluate_candidate(candidate)
                evaluation_cache[key] = evaluated
            if evaluated is None or evaluated.evaluation_signature in used_evaluations:
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
    condition = CONDITION_NAMES[GateConditionId(record.condition_id)]
    target = TARGET_NAMES[GateTargetMode(record.target_mode)]
    archetype = GateArchetype(record.archetype).name.title()
    gameplay = (
        f"{archetype} Gate using {evaluated.candidate.template_id} with "
        f"{primary_attribute} emphasis."
    )
    g_summary = (
        f"{record.flat_bonus_g} flat G, {record.percent_q8_8}/256 compressed-core "
        f"scaling, {balance.attribute.positive_count} positive and "
        f"{balance.attribute.negative_count} opposed attribute relationships."
    )
    weight_summary = (
        f"{balance.battle_weights.pressure.value.replace('_', ' ').title()} "
        f"{preferred_battle} preference; every battle type remains reachable."
    )
    rule_summary = (
        f"{condition}, adds {record.effect_value} G to {target} and then applies "
        f"a {record.drawback_value} G drawback."
    )
    rationale = (
        f"Unique {evaluated.candidate.template_id} tradeoff with "
        f"{primary_attribute} as its highest relationship, {preferred_battle} "
        f"preference, and evaluated swing "
        f"{evaluated.minimum}..{evaluated.maximum} G."
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

    risk_candidates = build_candidates(templates, GateArchetype.RISK)
    chaos_candidates = build_candidates(templates, GateArchetype.CHAOS)
    risk_batch = choose_batch(
        risk_candidates,
        RISK_IDS,
        used_runtime,
        used_evaluations,
    )
    chaos_batch = choose_batch(
        chaos_candidates,
        CHAOS_IDS,
        used_runtime,
        used_evaluations,
    )

    for card_id, evaluated, record in (*risk_batch, *chaos_batch):
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
                "chaos_candidates": len(chaos_candidates),
                "chaos_records": len(chaos_batch),
                "risk_candidates": len(risk_candidates),
                "risk_records": len(risk_batch),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
