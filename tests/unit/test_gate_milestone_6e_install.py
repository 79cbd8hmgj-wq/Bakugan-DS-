from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.authoring import load_gate_roster_authoring_document
from bakugan_ds.gates.loader import CACHE_ADDRESS, CACHE_SIZE, SYSTEM2_MODULE_SIZE
from bakugan_ds.gates.runtime_module import MODULE_BASE


def test_milestone_6e_runtime_contract_matches_frozen_geometry() -> None:
    payload = json.loads(Path("analysis/gates/milestone-6e-runtime-contract.json").read_text())
    records = load_gate_roster_authoring_document(
        Path("config/gates/milestone-6e-system2-v1.json")
    )
    assert payload["live_record_count"] == len(records) == 103
    assert payload["module_size"] == SYSTEM2_MODULE_SIZE == 0x8000
    assert payload["module_base"] == f"0x{MODULE_BASE:08X}"
    assert payload["cache_range"] == [
        f"0x{CACHE_ADDRESS:08X}",
        f"0x{CACHE_ADDRESS + CACHE_SIZE:08X}",
    ]
    assert payload["runtime_semantics"] == "milestone-6d-frozen"
    assert payload["unsupported_record_ids"] == []
