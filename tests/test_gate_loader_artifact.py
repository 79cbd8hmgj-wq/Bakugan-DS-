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


def test_loader_artifact_confirms_runtime_io_but_not_cache_lifecycle() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    runtime_io = payload["runtime_io"]
    assert runtime_io["status"] == "confirmed"
    assert runtime_io["fs_file_size"] == 72
    assert runtime_io["rom_archive_address"] == 0x020BFCB4
    assert runtime_io["init_file"]["function"] == 0x0200A7B4
    assert runtime_io["open"]["function"] == 0x0200AA24
    assert runtime_io["read"]["function"] == 0x0200AC30
    assert runtime_io["seek"]["function"] == 0x0200AC40
    assert runtime_io["close"]["function"] == 0x0200AADC
    capture = runtime_io["runtime_capture"]
    assert capture["read"]["requested"] == 88040
    assert capture["read"]["returned"] == 88040
    assert capture["read"]["position_delta"] == 88040
    assert capture["read"]["file_pointer"] == capture["read"]["stack_pointer"] + 4
    assert capture["close"]["return_value"] == 1
    assert capture["close"]["arc_after"] == 0
    assert capture["close"]["command_after"] == 14
    assert len(payload["unresolved"]) == 2
    assert payload["status"].endswith("cache_lifecycle_pending")
