from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.discovery import load_discovery_artifact

ARTIFACT = Path("analysis/gates/loader-and-cache.json")


def test_loader_artifact_is_complete_discovery_evidence() -> None:
    discovery = load_discovery_artifact(ARTIFACT)
    discovery.validate()
    assert discovery.domain == "loader-and-cache"
    assert discovery.unresolved == ()
    required = {
        "cache_initialization",
        "cache_invalidation",
        "cache_reset",
        "malformed_fallback",
        "nitrofs_close",
        "nitrofs_open",
        "nitrofs_read",
        "nitrofs_seek",
        "original_bss_preservation",
        "overlay_growth",
        "trailer_validation",
    }
    assert {check.name for check in discovery.checks} == required


def test_loader_artifact_preserves_exact_geometry() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert payload["carrier"]["file_id"] == 2762
    assert payload["carrier"]["raw_size"] == 2840
    assert payload["carrier"]["trailer_size"] == 4152
    assert payload["overlay"]["original_payload_size"] == 0x721A0
    assert payload["overlay"]["original_bss_size"] == 0x640
    assert payload["overlay"]["module_size"] == 0x8000
    assert payload["overlay"]["expanded_payload_size"] == 0x7A7E0
    assert payload["overlay"]["arena_low_original"] == 0x0228BC20
    assert payload["cache_layout"]["module_start"] == 0x0228BC20
    assert payload["cache_layout"]["cache_size"] == 0x40
    assert payload["cache_layout"]["cache_start"] == 0x02293C20
    assert payload["cache_layout"]["arena_low"] == 0x02293C60


def test_loader_artifact_confirms_runtime_io_and_cache_lifecycle() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    runtime_io = payload["runtime_io"]
    assert runtime_io["status"] == "confirmed"
    assert runtime_io["fs_file_size"] == 72
    assert runtime_io["rom_archive_address"] == 0x020BFCB4
    assert runtime_io["init_file"] == 0x0200A7B4
    assert runtime_io["open"] == 0x0200AA24
    assert runtime_io["read"] == 0x0200AC30
    assert runtime_io["seek"] == 0x0200AC40
    assert runtime_io["close"] == 0x0200AADC

    lifecycle = payload["runtime_cache_lifecycle"]
    assert lifecycle["status"] == "confirmed"
    assert lifecycle["instrumented_rom_sha256"] == (
        "8177aff2ca1c6cfe401c4401ccfca954e17d1d546612628d0bc6e032b2d15388"
    )
    assert lifecycle["module"]["address"] == 0x0228BC20
    assert lifecycle["module"]["size"] == 576
    assert lifecycle["module"]["runtime_sha256"] == (
        "d18dd0f7eba1279295e2314fa2d125030f0d382e577fad2fd9d712a623202ca6"
    )
    assert lifecycle["arena_relocation"]["literal_address"] == 0x02006264
    assert lifecycle["arena_relocation"]["literal_bytes"] == "603c2902"

    initialization = lifecycle["initialization"]
    assert initialization["hook_address"] == 0x0223D1CC
    assert initialization["hook_bytes"] == "933a01eb"
    assert initialization["return_pc"] == 0x0223D1D0
    assert initialization["record_card_id"] == 21
    assert initialization["selected_card_id"] == 21
    assert initialization["format_version"] == 1
    assert initialization["valid_flag"] == 1
    assert initialization["arena_entry"] == 0
    assert initialization["cache_sha256"] == (
        "8ecef0a63d0ba161fe000ab688d847fe774bbbd4a5da412d281eb68d9d1b657d"
    )
    assert initialization["record_sha256"] == (
        "53c0e7267b47cbc24937e7759ffa501195ce03a9a0adba320ecdf5d914720188"
    )

    invalidation = lifecycle["invalidation"]
    assert invalidation["hook_address"] == 0x022424B4
    assert invalidation["hook_bytes"] == "4f2601eb"
    assert invalidation["return_pc"] == 0x022424B8
    assert invalidation["post_clear_all_zero"] is True
    assert invalidation["valid_flag"] == 0
    assert invalidation["cache_sha256"] == (
        "f5a5fd42d16a20302798ef6ed309979b43003d2320d9f0e8ea9831a92759fb4b"
    )
    assert lifecycle["raw_debugger_log_committed"] is False
    assert lifecycle["save_or_state_committed"] is False
    assert lifecycle["screenshot_committed"] is False
    assert payload["status"] == "complete"
    assert payload["unresolved"] == []
