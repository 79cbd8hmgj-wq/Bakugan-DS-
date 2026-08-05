from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from bakugan_ds.gates.authoring import load_gate_roster_authoring_document
from bakugan_ds.gates.roster_analysis import build_roster_analysis
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
DIAGNOSTIC_IDS = {40, 52, 58, 69, 70, 75, 76}


def main() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    metadata = tuple(
        replace(entry, review_status=ReviewStatus.APPROVED)
        for entry in load_gate_roster_metadata(METADATA)
    )
    write_gate_roster_metadata(METADATA, metadata, final=True)

    analysis = build_roster_analysis(records, metadata)
    card_reports = {
        int(card["card_id"]): card
        for card in analysis["cards"]
        if isinstance(card, dict) and isinstance(card.get("card_id"), int)
    }
    print(
        json.dumps(
            {
                "dominance_pairs": analysis["potential_dominance_pairs"],
                "records": {
                    str(record.card_id): asdict(record)
                    for record in records
                    if record.card_id in DIAGNOSTIC_IDS
                },
                "reports": {
                    str(card_id): card_reports[card_id]
                    for card_id in sorted(DIAGNOSTIC_IDS)
                },
            },
            indent=2,
            sort_keys=True,
        )
    )

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
