from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    load_gate_roster_authoring_document,
)
from bakugan_ds.gates.balance import (
    ATTRIBUTE_NAMES,
    BATTLE_TYPE_NAMES,
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

BASELINE = Path("config/gates/milestone-6d-system2-v1.json")
OUTPUT = Path("config/gates/milestone-6e-system2-v1.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
TEMPLATES = Path("config/gates/milestone-6e-archetype-templates.json")
POWER_IDS = tuple(range(1, 16))
ATTRIBUTE_IDS = tuple(range(40, 62))

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


@dataclass(frozen=True)
class Behavior:
    record: GateRecordV1
    template_id: str
    tier: DesignTier
    balance: GateBalanceReport
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


def build_behaviors(
    templates: tuple[GateRosterTemplate, ...],
    archetype: GateArchetype,
) -> tuple[Behavior, ...]:
    by_evaluation: dict[tuple[tuple[object, ...], ...], Behavior] = {}
    for template in templates:
        if template.archetype is not archetype:
            continue
        prototype = template.prototype
        for flat_drop, percent_drop, effect_drop in product(
            (0, 25), (0, 16), (0, 25)
        ):
            for attribute_shift in range(6):
                record = replace(
                    prototype,
                    card_id=1,
                    flat_bonus_g=max(0, prototype.flat_bonus_g - flat_drop),
                    percent_q8_8=max(0, prototype.percent_q8_8 - percent_drop),
                    effect_value=max(0, prototype.effect_value - effect_drop),
                    attribute_modifiers=rotate_right(
                        prototype.attribute_modifiers, attribute_shift
                    ),
                )
                try:
                    balance = analyze_gate_balance(record)
                except WorkspaceError:
                    continue
                if record_fallback_reason(record) is not FallbackReason.NONE:
                    continue
                evaluation = _evaluate_record(record)
                tier = tier_for(evaluation.values)
                if tier is None:
                    continue
                behavior = Behavior(
                    record=record,
                    template_id=template.template_id,
                    tier=tier,
                    balance=balance,
                    evaluation_signature=evaluation.signature(),
                    minimum=min(evaluation.values),
                    maximum=max(evaluation.values),
                )
                existing = by_evaluation.get(behavior.evaluation_signature)
                if existing is None or (
                    abs(behavior.balance.budget.net_budget - 100),
                    behavior.maximum,
                    behavior.template_id,
                ) < (
                    abs(existing.balance.budget.net_budget - 100),
                    existing.maximum,
                    existing.template_id,
                ):
                    by_evaluation[behavior.evaluation_signature] = behavior
    return tuple(
        sorted(
            by_evaluation.values(),
            key=lambda item: (
                item.template_id,
                item.record.condition_id,
                item.record.target_mode,
                abs(item.balance.budget.net_budget - 100),
                item.maximum,
                item.minimum,
                serialize_record(item.record),
            ),
        )
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
    behaviors: tuple[Behavior, ...],
    card_ids: tuple[int, ...],
    used_runtime: set[bytes],
    used_evaluations: set[tuple[tuple[object, ...], ...]],
) -> tuple[tuple[int, Behavior, GateRecordV1], ...]:
    chosen: list[tuple[int, Behavior, GateRecordV1]] = []
    template_use: Counter[str] = Counter()
    condition_use: Counter[int] = Counter()
    for index, card_id in enumerate(card_ids):
        preferred_type = index % 6
        options: list[tuple[Behavior, GateRecordV1, bytes]] = []
        for behavior in behaviors:
            if behavior.evaluation_signature in used_evaluations:
                continue
            record = with_preferred_type(behavior.record, preferred_type)
            runtime = serialize_record(replace(record, card_id=1))
            if runtime in used_runtime:
                continue
            options.append((behavior, record, runtime))
        if not options:
            raise WorkspaceError(f"no distinct behavior remains for Gate {card_id}")
        behavior, record, runtime = min(
            options,
            key=lambda item: (
                template_use[item[0].template_id],
                condition_use[item[0].record.condition_id],
                abs(item[0].balance.budget.net_budget - 100),
                item[0].maximum,
                item[0].minimum,
                item[0].template_id,
                item[2],
            ),
        )
        used_runtime.add(runtime)
        used_evaluations.add(behavior.evaluation_signature)
        template_use[behavior.template_id] += 1
        condition_use[behavior.record.condition_id] += 1
        chosen.append((card_id, behavior, replace(record, card_id=card_id)))
    return tuple(chosen)


def metadata_copy(behavior: Behavior, record: GateRecordV1) -> tuple[str, ...]:
    balance = analyze_gate_balance(record)
    primary_index = max(range(6), key=lambda index: record.attribute_modifiers[index])
    primary_attribute = ATTRIBUTE_NAMES[primary_index]
    preferred_battle = BATTLE_TYPE_NAMES[record.preferred_type]
    gameplay = (
        f"{GateArchetype(record.archetype).name.title()} Gate using "
        f"{behavior.template_id} with {primary_attribute} emphasis."
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
    rule = (
        f"{CONDITION_NAMES[record.condition_id]}, applies {record.effect_value} G "
        f"through effect {record.effect_id} to {TARGET_NAMES[record.target_mode]}."
    )
    rationale = (
        f"Unique {behavior.template_id} variation with {primary_attribute} as its "
        f"highest relationship, {preferred_battle} preference, condition "
        f"{record.condition_id}, and evaluated swing "
        f"{behavior.minimum}..{behavior.maximum} G."
    )
    return gameplay, g_summary, weight_summary, rule, rationale


def main() -> None:
    records = list(load_gate_roster_authoring_document(BASELINE))
    metadata = list(load_gate_roster_metadata(METADATA))
    templates = load_gate_roster_templates(TEMPLATES)
    juggernoid = approved_juggernoid_record()
    used_runtime = {serialize_record(replace(juggernoid, card_id=1))}
    used_evaluations = {_evaluate_record(juggernoid).signature()}

    power_behaviors = build_behaviors(templates, GateArchetype.POWER)
    attribute_behaviors = build_behaviors(templates, GateArchetype.ATTRIBUTE)
    power_batch = choose_batch(
        power_behaviors, POWER_IDS, used_runtime, used_evaluations
    )
    attribute_batch = choose_batch(
        attribute_behaviors, ATTRIBUTE_IDS, used_runtime, used_evaluations
    )

    for card_id, behavior, record in (*power_batch, *attribute_batch):
        records[card_id - 1] = record
        gameplay, g_summary, weights, rule, rationale = metadata_copy(behavior, record)
        metadata[card_id - 1] = replace(
            metadata[card_id - 1],
            archetype=GateArchetype(record.archetype),
            design_tier=behavior.tier,
            gameplay_identity=gameplay,
            g_influence_summary=g_summary,
            battle_weight_summary=weights,
            rule_summary=rule,
            net_budget=analyze_gate_balance(record).budget.net_budget,
            differentiation_rationale=rationale,
            review_status=ReviewStatus.REVIEWED,
        )

    if records[18] != juggernoid:
        raise WorkspaceError("Gate 19 changed during Task 6 authoring")

    OUTPUT.write_text(
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
                "attribute_behaviors": len(attribute_behaviors),
                "attribute_records": len(attribute_batch),
                "power_behaviors": len(power_behaviors),
                "power_records": len(power_batch),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
