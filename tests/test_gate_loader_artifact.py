from __future__ import annotations

import json
from pathlib import Path

ARTIFACT = Path("analysis/gates/loader-and-cache.json")


def test_loader_foundation_artifact_preserves_exact_geometry() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert payload["carrier"]["file_id"] == 2762
    assert payload["carrier"]["raw_size"] == 2840
    assert payload["carrier"]["trailer_size"] == 4152
    assert payload["overlay"]["original_payload_size"] == 0x721A0
    assert payload["overlay"]["original_bss_size"] == 0x640
    assert payload["overlay"]["module_size"] == 0x8000
    assert payload["overlay"]["expanded_payload_size"] == 0x7A7E0
    assert payload["cache_layout"]["cache_size"] == 0x40


def test_loader_artifact_does_not_claim_runtime_io_complete() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    runtime_io = payload["runtime_io"]
    assert runtime_io["status"] == "runtime_confirmation_required"
    assert runtime_io["open"] is None
    assert runtime_io["seek"] is None
    assert runtime_io["read"] is None
    assert runtime_io["close"] is None
    assert len(payload["unresolved"]) == 5
    assert payload["status"].endswith("runtime_io_pending")
