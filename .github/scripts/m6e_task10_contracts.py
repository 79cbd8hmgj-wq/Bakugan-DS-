from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import load_gate_roster_authoring_document
from bakugan_ds.gates.balance import ATTRIBUTE_NAMES, analyze_gate_balance
from bakugan_ds.gates.record import GateArchetype, GateRecordV1
from bakugan_ds.gates.roster_contracts import (
    build_balance_contract,
    build_roster_contract,
    write_contract,
)
from bakugan_ds.gates.roster_metadata import (
    GateRosterMetadataEntry,
    ReviewStatus,
    load_gate_roster_metadata,
    write_gate_roster_metadata,
)

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
ROSTER_CONTRACT = Path("analysis/gates/milestone-6e-roster-contract.json")
BALANCE_CONTRACT = Path("analysis/gates/milestone-6e-balance-contract.json")
BATCH_TESTS = (
    Path("tests/unit/test_gate_milestone_6e_power_attribute.py"),
    Path("tests/unit/test_gate_milestone_6e_skill_control.py"),
    Path("tests/unit/test_gate_milestone_6e_comeback.py"),
    Path("tests/unit/test_gate_milestone_6e_risk_chaos.py"),
)
METADATA_TEST = Path("tests/unit/test_gate_roster_metadata.py")


def _revised_records() -> tuple[GateRecordV1, ...]:
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


def _approved_metadata(
    records: tuple[GateRecordV1, ...],
) -> tuple[GateRosterMetadataEntry, ...]:
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


def _advance_test_expectations() -> None:
    reviewed_assertion = (
        "assert entry.review_status is ReviewStatus.REVIEWED"
    )
    cumulative_assertion = (
        "assert entry.review_status in {ReviewStatus.REVIEWED, ReviewStatus.APPROVED}"
    )
    for path in BATCH_TESTS:
        text = path.read_text(encoding="utf-8")
        occurrence_count = text.count(reviewed_assertion)
        if occurrence_count == 0:
            raise WorkspaceError(
                f"Task 10 could not find intermediate review assertions in {path}"
            )
        path.write_text(
            text.replace(reviewed_assertion, cumulative_assertion),
            encoding="utf-8",
        )

    metadata_text = METADATA_TEST.read_text(encoding="utf-8")
    reviewed_line = (
        "    reviewed = [entry for entry in entries if entry.review_status is "
        "ReviewStatus.REVIEWED]\n"
    )
    approved_line = (
        "    approved = [entry for entry in entries if entry.review_status is "
        "ReviewStatus.APPROVED]\n"
    )
    if reviewed_line not in metadata_text:
        raise WorkspaceError("Task 10 metadata reviewed-count anchor is missing")
    metadata_text = metadata_text.replace(
        reviewed_line,
        reviewed_line + approved_line,
        1,
    )
    old_count = "    assert len(reviewed) == 102\n"
    new_counts = (
        "    assert len(reviewed) == 0\n"
        "    assert len(approved) == 103\n"
    )
    if old_count not in metadata_text:
        raise WorkspaceError("Task 10 metadata reviewed-count expectation is missing")
    METADATA_TEST.write_text(
        metadata_text.replace(old_count, new_counts, 1),
        encoding="utf-8",
    )


def main() -> None:
    records = _revised_records()
    metadata = _approved_metadata(records)
    _advance_test_expectations()

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
