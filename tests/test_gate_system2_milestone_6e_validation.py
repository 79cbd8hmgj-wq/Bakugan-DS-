from __future__ import annotations

import json
from pathlib import Path


def test_milestone_6e_runtime_evidence_preserves_claim_boundary() -> None:
    payload = json.loads(
        Path(
            "analysis/runtime-observations/gate-system2-milestone-6e-validation.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["milestone"] == "6E"
    assert payload["status"] == "runtime_representative_capture_pending"
    matrix = payload["milestone_6e_representative_matrix"]
    assert matrix["exact_emitted_arm_complete_roster"] is True
    assert matrix["natural_emulator_representatives_complete"] is False
    assert len(matrix["required_archetypes"]) == 7
    assert payload["rejected_claims"]
    assert payload["blocker"]
