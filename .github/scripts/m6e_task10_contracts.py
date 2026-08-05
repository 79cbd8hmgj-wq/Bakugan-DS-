from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from bakugan_ds.gates.authoring import load_gate_roster_authoring_document
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


def main() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = tuple(
        replace(entry, review_status=ReviewStatus.APPROVED)
        for entry in load_gate_roster_metadata(METADATA)
    )
    write_gate_roster_metadata(METADATA, metadata, final=True)

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
