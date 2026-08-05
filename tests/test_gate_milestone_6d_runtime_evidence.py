from __future__ import annotations

import json
from pathlib import Path

EVIDENCE = Path(
    "analysis/runtime-observations/gate-system2-milestone-6d-validation.json"
)
SOURCE_ROM_SHA256 = "7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b"
REBUILT_ROM_SHA256 = "519edbd5f4e17db3513cff0451109036ad411b44f1f2fd8f8e635fb68d0ffc7c"
MODULE_SHA256 = "8fa90c244d3710479e94903e099f9dbbe71b5ce8d86c52603383d2e4f42e7a1c"
FORBIDDEN_KEYS = {
    "raw_bytes",
    "ram_dump",
    "save_state",
    "screenshot",
    "debugger_log",
    "rom_path",
    "local_path",
}


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _load() -> dict[str, object]:
    text = EVIDENCE.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert isinstance(payload, dict)
    assert text.endswith("\n")
    assert FORBIDDEN_KEYS.isdisjoint(_walk_keys(payload))
    return payload


def test_evidence_identifies_exact_source_build_and_scope() -> None:
    payload = _load()
    assert payload["format_version"] == 1
    assert payload["milestone"] == "6D"
    assert payload["profile_id"] == "b6re_rev0"
    assert payload["source"]["rom_sha256"] == SOURCE_ROM_SHA256
    assert payload["source"]["rom_size"] == 134_217_728
    build = payload["build"]
    assert build["deterministic_double_build"] is True
    assert build["rebuilt_rom_sha256"] == REBUILT_ROM_SHA256
    assert build["module_sha256"] == MODULE_SHA256
    assert build["rom_size"] == 134_217_728
    assert build["guarded_change_count"] == 7
    assert build["live_system2_gate_ids"] == [19]
    assert build["legacy_passthrough_count"] == 102
    assert build["unrelated_fat_payloads_byte_identical"] is True
    assert build["protected_core_g_bytes_unchanged"] is True


def test_evidence_records_passing_host_and_exact_counts() -> None:
    verification = _load()["verification"]
    assert verification["host_suite"] == {
        "command": "PYTHONPATH=src python -m pytest -q",
        "passed": 670,
        "expected_environment_skips": 41,
        "failures": 0,
    }
    assert verification["exact_focus"]["passed"] == 43
    assert verification["exact_focus"]["failures"] == 0


def test_evidence_separates_emitted_parity_from_live_observation() -> None:
    payload = _load()
    parity = payload["emitted_module_parity"]
    assert parity["module_sha256"] == MODULE_SHA256
    assert parity["test_count"] == 31
    assert parity["condition_vectors"] == 12
    assert parity["target_vectors"] == 6
    assert parity["effect_vectors"] == 9
    assert parity["juggernoid_vectors_preserved"] is True
    assert parity["generic_reward_and_drawback_parity"] is True
    assert parity["negative_component_parity"] is True
    assert parity["landing_condition_parity"] is True
    assert parity["unrelated_gate_uses_legacy_without_weighted_rng"] is True
    assert parity["history_bytes_unchanged"] is True
    assert parity["activation_counters_unchanged"] is True
    assert parity["ability_state_unchanged"] is True
    live = payload["live_runtime"]
    assert live["juggernoid_path"]["card_id"] == 19
    assert live["juggernoid_path"]["card_presented_in_tutorial"] is True
    assert live["juggernoid_path"]["naturally_observed_vector_claimed"] is False


def test_evidence_proves_live_module_legacy_control_and_cache_clear() -> None:
    live = _load()["live_runtime"]
    assert live["module"] == {
        "base": "0x0228BC20",
        "size": 32768,
        "sha256": MODULE_SHA256,
        "present": True,
    }
    control = live["unrelated_gate_control"]
    assert control["card_id"] == 21
    assert control["cache_record_id"] == 21
    assert control["selected_card_id"] == 21
    assert control["format_version"] == 1
    assert control["valid_flag"] == 1
    assert control["canonical_legacy_passthrough"] is True
    completion = live["completion"]
    assert completion["tutorial_supported_path_completed"] is True
    assert completion["returned_to_responsive_tutorial_state"] is True
    assert completion["post_exit_input_responsive"] is True
    assert completion["all_64_cache_bytes_zero"] is True
    assert completion["cache_valid_flag"] == 0
    assert completion["overlay_failure_observed"] is False


def test_evidence_preserves_persistent_and_deferred_boundaries() -> None:
    payload = _load()
    controls = payload["live_runtime"]["persistent_controls"]
    assert controls["serpenoid_persistent_raw_g"] == 19
    assert controls["serpenoid_displayed_g"] == 190
    assert controls["persistent_roster_g_unchanged"] is True
    assert controls["save_file_created"] is False
    assert controls["save_data_changed"] is False
    assert controls["ability_state_write_observed"] is False
    assert controls["activation_counter_write_observed"] is False
    assert controls["history_byte_write_observed"] is False
    rejected = payload["rejected_claims"]
    assert any("103-card roster" in item for item in rejected)
    assert any("Arena ID" in item for item in rejected)
    assert "not committed" in payload["repository_boundary"]
    hashes = payload["local_evidence_hashes"]
    assert hashes
    assert all(len(value) == 64 for value in hashes.values())
