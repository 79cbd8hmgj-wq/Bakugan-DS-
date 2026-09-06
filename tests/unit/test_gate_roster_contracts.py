from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    load_gate_roster_authoring_document,
)
from bakugan_ds.gates.record import GateArchetype
from bakugan_ds.gates.roster_contracts import (
    build_balance_contract,
    build_roster_contract,
    write_contract,
)
from bakugan_ds.gates.roster_metadata import (
    ReviewStatus,
    load_gate_roster_metadata,
)
from bakugan_ds.gates.system2 import FallbackReason, record_fallback_reason

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
METADATA = Path("config/gates/milestone-6e-roster-metadata.json")
ROSTER_CONTRACT = Path("analysis/gates/milestone-6e-roster-contract.json")
BALANCE_CONTRACT = Path("analysis/gates/milestone-6e-balance-contract.json")


def test_final_roster_contract_covers_all_records_and_preserves_juggernoid() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA, final=True)
    contract = build_roster_contract(records, metadata)

    assert len(records) == 103
    assert all(record.archetype != GateArchetype.LEGACY for record in records)
    assert all(record_fallback_reason(record) is FallbackReason.NONE for record in records)
    assert all(entry.review_status is ReviewStatus.APPROVED for entry in metadata)
    assert records[18] == approved_juggernoid_record()
    assert contract == json.loads(ROSTER_CONTRACT.read_text(encoding="utf-8"))
    assert contract["record_count"] == 103
    assert contract["live_record_count"] == 103
    assert contract["unsupported_record_ids"] == []
    assert contract["deferred_state_record_ids"] == []
    assert contract["juggernoid_preserved"] is True
    assert contract["archetype_distribution"] == {
        "attribute": 22,
        "chaos": 8,
        "comeback": 14,
        "control": 15,
        "power": 15,
        "risk": 14,
        "skill": 15,
    }


def test_balance_contract_dispositions_every_dominance_finding() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA, final=True)
    contract = build_balance_contract(records, metadata)

    assert contract == json.loads(BALANCE_CONTRACT.read_text(encoding="utf-8"))
    assert contract["hard_duplicate_groups"] == []
    assert contract["identical_evaluation_groups"] == []
    assert contract["identity_conflicts"] == []
    assert contract["distribution_warnings"] == []
    assert contract["out_of_tier_card_ids"] == [19]
    assert contract["unresolved_dominance_pairs"] == []
    assert len(contract["dominance_dispositions"]) == len(
        contract["potential_dominance_pairs"]
    )
    assert all(
        disposition["disposition"] in {
            "accepted_cross_archetype_identity",
            "accepted_tier_progression",
        }
        for disposition in contract["dominance_dispositions"]
    )


def test_contract_generation_and_writing_are_deterministic(tmp_path: Path) -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = load_gate_roster_metadata(METADATA, final=True)

    first_roster = build_roster_contract(records, metadata)
    second_roster = build_roster_contract(records, metadata)
    first_balance = build_balance_contract(records, metadata)
    second_balance = build_balance_contract(records, metadata)
    assert first_roster == second_roster
    assert first_balance == second_balance

    roster_output = tmp_path / "roster.json"
    balance_output = tmp_path / "balance.json"
    write_contract(roster_output, first_roster)
    roster_bytes = roster_output.read_bytes()
    write_contract(roster_output, second_roster)
    assert roster_output.read_bytes() == roster_bytes

    write_contract(balance_output, first_balance)
    balance_bytes = balance_output.read_bytes()
    write_contract(balance_output, second_balance)
    assert balance_output.read_bytes() == balance_bytes
    assert roster_bytes.endswith(b"\n")
    assert balance_bytes.endswith(b"\n")
