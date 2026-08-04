from __future__ import annotations

import json
from pathlib import Path

EVIDENCE = Path(
    "analysis/runtime-observations/gate-system2-milestone-6c-validation.json"
)
SOURCE_ROM_SHA256 = "7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b"
REBUILT_ROM_SHA256 = "78f9ac00bbfd1eed86ee2977016af3395198158bb25c12cef82eb55ac14eeceb"
TRAILER_SHA256 = "c67d3bad47ad318ea782a938fc3412a6244509e96b0d2fb75e3bf8424c9fe72b"
MODULE_SHA256 = "ed4c0f5c1779eed6028d9b5e525fa94581c68664f5e98419747f74ffacb843f2"
FORBIDDEN_KEYS = {
    "raw_bytes",
    "ram_dump",
    "save_state",
    "screenshot",
    "debugger_log",
    "rom_path",
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
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert EVIDENCE.read_text(encoding="utf-8").endswith("\n")
    assert FORBIDDEN_KEYS.isdisjoint(_walk_keys(payload))
    return payload


def test_runtime_evidence_identifies_exact_build_and_prototype() -> None:
    payload = _load()
    assert payload["format_version"] == 1
    assert payload["profile_id"] == "b6re_rev0"
    assert payload["source_rom_sha256"] == SOURCE_ROM_SHA256
    assert payload["rebuilt_rom_sha256"] == REBUILT_ROM_SHA256
    assert payload["trailer_sha256"] == TRAILER_SHA256
    assert payload["module_sha256"] == MODULE_SHA256
    assert payload["prototype"] == {
        "card_id": 19,
        "flat_bonus_g": 60,
        "percent_q8_8": 20,
        "attribute_modifiers": [0, 30, 0, 0, 0, 0],
        "battle_weights": [50, 30, 30, 30, 30, 30],
        "condition": "owner_behind",
        "effect_value": 40,
        "target": "gate_owner_combatant",
        "timing": "pre_gate",
    }


def test_runtime_evidence_proves_cache_lifecycle() -> None:
    cache = _load()["cache_lifecycle"]
    assert cache["load"]["card_id"] == 19
    assert cache["load"]["format_version"] == 1
    assert cache["load"]["valid_flag"] == 1
    assert 0 <= cache["load"]["arena_entry"] < 12
    assert len(cache["load"]["record_sha256"]) == 64
    assert cache["remained_valid_during_battle"] is True
    assert cache["completion"]["all_64_bytes_zero"] is True
    assert cache["completion"]["valid_flag"] == 0


def test_runtime_evidence_contains_complete_hybrid_controls() -> None:
    cases = {item["case"]: item for item in _load()["calculation_cases"]}
    assert {
        "non_aquos_normal",
        "aquos_normal",
        "owner_tied_or_leading",
        "owner_behind",
        "non_owner_while_owner_behind",
        "human_owned",
        "ai_owned",
    } <= set(cases)
    for case in cases.values():
        assert case["equation_valid"] is True
        assert case["target_total_g"] == min(
            0xFFFF, case["compressed_core_g"] + case["effective_gate_bonus"]
        )
        assert case["effective_gate_bonus"] == min(
            0x7FFF,
            max(
                -0x8000,
                case["flat_bonus_g"]
                + case["scaled_component"]
                + case["attribute_modifier"]
                + case["conditional_modifier"],
            ),
        )
    assert cases["aquos_normal"]["attribute_modifier"] == 30
    assert cases["owner_tied_or_leading"]["conditional_modifier"] == 0
    assert cases["owner_behind"]["conditional_modifier"] == 40
    assert cases["non_owner_while_owner_behind"]["conditional_modifier"] == 0
    assert cases["human_owned"]["owner_is_ai"] is False
    assert cases["ai_owned"]["owner_is_ai"] is True


def test_runtime_evidence_proves_weighting_and_precedence() -> None:
    weighted = _load()["weighted_cases"]
    assert len(weighted) >= 2
    assert len({item["final_type"] for item in weighted}) >= 2
    for item in weighted:
        assert item["helper_calls"] == 1
        assert item["weights"] == [50, 30, 30, 30, 30, 30]
        assert 0 <= item["final_type"] <= 5
        assert item["rng_state_before"] != item["rng_state_after"]
    precedence = _load()["precedence_controls"]
    assert precedence["explicit_constructor"]["weighted_helper_calls"] == 0
    assert precedence["explicit_constructor"]["final_type"] == (
        precedence["explicit_constructor"]["constructor_type"]
    )
    assert precedence["scripted_override"]["final_type"] == (
        precedence["scripted_override"]["scripted_type"]
    )


def test_runtime_evidence_proves_legacy_and_malformed_fallbacks() -> None:
    payload = _load()
    legacy = payload["legacy_gate_control"]
    assert legacy["card_id"] != 19
    assert legacy["system2_calculation_used"] is False
    assert legacy["weighted_helper_calls"] == 0
    assert legacy["legacy_bonus_equation_valid"] is True
    assert legacy["final_type"] == legacy["fixed_metadata_type"]
    malformed = payload["malformed_trailer_control"]
    assert malformed["cache_valid_flag"] == 0
    assert malformed["system2_calculation_used"] is False
    assert malformed["weighted_helper_calls"] == 0
    assert malformed["legacy_bonus_equation_valid"] is True
    assert malformed["final_type"] == 0


def test_runtime_evidence_proves_completion_and_persistent_controls() -> None:
    payload = _load()
    completion = payload["completion"]
    assert completion["battle_completed"] is True
    assert completion["returned_to_surrounding_state"] is True
    assert completion["post_exit_input_responsive"] is True
    assert completion["overlay_failure_observed"] is False
    controls = payload["persistent_controls"]
    assert controls == {
        "roster_g_unchanged": True,
        "gate_inventory_unchanged": True,
        "save_data_unchanged": True,
        "unrelated_battle_state_unchanged": True,
    }
    hashes = payload["local_evidence_hashes"]
    assert hashes
    assert all(len(value) == 64 for value in hashes.values())
    assert "not committed" in payload["repository_boundary"]
