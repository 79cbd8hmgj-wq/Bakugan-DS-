from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import load_gate_roster_authoring_document
from bakugan_ds.gates.balance import ATTRIBUTE_NAMES, analyze_gate_balance
from bakugan_ds.gates.record import GateArchetype
from bakugan_ds.gates.roster_contracts import (
    build_balance_contract,
    build_roster_contract,
    write_contract,
)
from bakugan_ds.gates.roster_metadata import (
    ReviewStatus,
    load_gate_roster_metadata,
    write_gate_roster_metadata,
)

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
ROSTER_CONTRACT = Path("analysis/gates/milestone-6e-roster-contract.json")
BALANCE_CONTRACT = Path("analysis/gates/milestone-6e-balance-contract.json")


def _revised_records() -> tuple[object, ...]:
    records = list(load_gate_roster_authoring_document(AUTHORING))
    expected_attribute = (0, 0, 100, 50, -50, -25)
    expected_comeback = (0, 0, 0, 0, 0, 30)
    for card_id in (52, 58):
        record = records[card_id - 1]
        if record.attribute_modifiers != expected_attribute:
            raise WorkspaceError(
                f"Gate {card_id} dominance revision original attributes changed"
            )
        records[card_id - 1] = replace(
            record,
            attribute_modifiers=(0, 0, 100, 50, 0, -25),
        )
    comeback_revisions = {
        75: (30, 0, 0, 0, 0, 0),
        76: (0, 30, 0, 0, 0, 0),
    }
    for card_id, attributes in comeback_revisions.items():
        record = records[card_id - 1]
        if record.attribute_modifiers != expected_comeback:
            raise WorkspaceError(
                f"Gate {card_id} dominance revision original attributes changed"
            )
        records[card_id - 1] = replace(record, attribute_modifiers=attributes)
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
    return tuple(records)


def _approved_metadata(records: tuple[object, ...]) -> tuple[object, ...]:
    metadata = list(load_gate_roster_metadata(METADATA))
    revision_reasons = {
        52: (
            "Task 10 relationship revision removes strict dominance by retaining "
            "its strongest Subterra relationship while neutralizing one former "
            "opposition matchup."
        ),
        58: (
            "Task 10 relationship revision removes strict dominance by pairing "
            "its smaller tied-score rider with a safer Haos relationship matchup."
        ),
        75: (
            "Task 10 affinity rotation removes strict dominance by shifting the "
            "owner-behind bonus profile to Pyrus."
        ),
        76: (
            "Task 10 affinity rotation removes strict dominance by shifting the "
            "owner-score-zero bonus profile to Aquos."
        ),
    }
    for card_id, rationale in revision_reasons.items():
        record = records[card_id - 1]
        balance = analyze_gate_balance(record)
        primary_index = max(
            range(6), key=lambda index: record.attribute_modifiers[index]
        )
        primary_attribute = ATTRIBUTE_NAMES[primary_index]
        archetype = GateArchetype(record.archetype).name.title()
        metadata[card_id - 1] = replace(
            metadata[card_id - 1],
            gameplay_identity=(
                f"{archetype} Gate with {primary_attribute} relationship emphasis."
            ),
            g_influence_summary=(
                f"{record.flat_bonus_g} flat G, {record.percent_q8_8}/256 "
                f"compressed-core scaling, {balance.attribute.positive_count} "
                f"positive and {balance.attribute.negative_count} opposed "
                "attribute relationships."
            ),
            net_budget=balance.budget.net_budget,
            differentiation_rationale=rationale,
        )
    approved = tuple(
        replace(entry, review_status=ReviewStatus.APPROVED) for entry in metadata
    )
    write_gate_roster_metadata(METADATA, approved, final=True)
    return approved


def main() -> None:
    records = _revised_records()
    metadata = _approved_metadata(records)

    roster_contract = build_roster_contract(records, metadata)
    balance_contract = build_balance_contract(records, metadata)
    write_contract(ROSTER_CONTRACT, roster_contract)
    write_contract(BALANCE_CONTRACT, balance_contract)

    print(
        {
            "dominance_findings": len(
                balance_contract["potential_dominance_pairs"]
            ),
            "records": roster_contract["record_count"],
            "unresolved_dominance": len(
                balance_contract["unresolved_dominance_pairs"]
            ),
        }
    )


if __name__ == "__main__":
    main()
