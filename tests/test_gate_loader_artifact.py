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


def test_loader_artifact_confirms_runtime_io_and_cache_lifecycle() -> None:
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

    lifecycle = payload["runtime_cache_lifecycle"]
    assert lifecycle["status"] == "confirmed"
    assert lifecycle["instrumented_rom_sha256"] == (
        "6e04b2ce3d31b9577cbee7d48084f6d1127467fb0b7c9b3e650038d539d5e5cb"
    )
    initialization = lifecycle["initialization"]
    assert initialization["breakpoint"] == 0x0228BE14
    assert initialization["selected_card_id"] == 21
    assert initialization["format_version"] == 1
    assert initialization["valid_flag"] == 1
    assert initialization["selected_arena_entry"] == 0
    assert initialization["cache_sha256"] == (
        "8ecef0a63d0ba161fe000ab688d847fe774bbbd4a5da412d281eb68d9d1b657d"
    )
    assert initialization["record_matches_raw_trailer"] is True

    invalidation = lifecycle["invalidation"]
    assert invalidation["entry_breakpoint"] == 0x0228C020
    assert invalidation["entry_cache_sha256"] == initialization["cache_sha256"]
    assert invalidation["post_clear_breakpoint"] == 0x0228C068
    assert invalidation["post_clear_cache_sha256"] == (
        "f5a5fd42d16a20302798ef6ed309979b43003d2320d9f0e8ea9831a92759fb4b"
    )
    assert invalidation["post_clear_all_zero"] is True
    assert invalidation["execution_resumed"] is True

    assert payload["unresolved"] == []
    assert payload["status"] == "complete"
