import json
from pathlib import Path


VALIDATION = Path(
    "analysis/runtime-observations/core_g_compression_validation.json"
)


def load_validation() -> dict[str, object]:
    return json.loads(VALIDATION.read_text(encoding="utf-8"))


def test_structural_verification_matches_rebuilt_rom_evidence() -> None:
    payload = load_validation()
    structural = payload["structural_verification"]
    assert payload["rom_profile"] == "b6re_rev0"
    assert structural == {
        "rom_size_bytes": 134217728,
        "overlay_id": 7,
        "overlay_load_address": "0x02219440",
        "overlay_decoded_size_bytes": 467360,
        "overlay_bss_size_bytes": 1600,
        "overlay_output_encoding": "uncompressed-overlay",
        "changed_instruction_bytes": 41,
        "unchanged_fat_payloads_verified": 11004,
        "code_cave_used": False,
        "branch_hook_used": False,
        "bss_moved": False,
    }


def test_constructor_cases_cover_threshold_rounding_and_symmetry() -> None:
    cases = {item["name"]: item for item in load_validation()["constructor_cases"]}
    mixed = cases["mixed_low_high_symmetry"]
    assert mixed["player"]["core_input"] == 190
    assert mixed["player"]["base_snapshot_output"] == 190
    assert mixed["opponent"]["core_input"] == 650
    assert mixed["opponent"]["base_snapshot_output"] == 525

    threshold = cases["threshold_and_mutable_modifiers"]
    assert threshold["player"]["base_snapshot_output"] == 430
    assert threshold["opponent"]["base_snapshot_output"] == 450

    boundary = cases["boundary_and_small_excess"]
    assert boundary["player"]["core_input"] == 401
    assert boundary["player"]["base_snapshot_output"] == 400
    assert boundary["opponent"]["core_input"] == 410
    assert boundary["opponent"]["base_snapshot_output"] == 405

    odd = cases["odd_core_rounds_down"]
    assert odd["player"]["core_input"] == 441
    assert odd["player"]["base_snapshot_output"] == 420
    assert odd["opponent"]["core_input"] == 651
    assert odd["opponent"]["base_snapshot_output"] == 525


def test_gate_and_modifier_contributions_remain_unscaled() -> None:
    payload = load_validation()
    isolation = payload["contribution_isolation"]
    assert isolation == {
        "low_core_preserved": True,
        "high_core_compressed": True,
        "both_combatants_symmetric": True,
        "mutable_modifier_unscaled": True,
        "gate_bonus_unscaled": True,
        "persistent_roster_rewritten": False,
        "field_pickup_handlers_modified": False,
    }

    gate_cases = {
        item["name"]: item for item in payload["gate_addition_cases"]
    }
    assert gate_cases["low_gate_total"]["target_total"] == 290
    assert gate_cases["high_gate_total"]["target_total"] == 625
    assert gate_cases["modifier_gate_total"]["target_total"] == 655


def test_boot_observation_remains_bounded() -> None:
    observation = load_validation()["boot_and_exit_observation"]
    assert observation["patched_overlay_loaded"] is True
    assert observation["gate_reveal_reached"] is True
    assert observation["battle_transition_animation_reached"] is True
    assert observation["exit_destination"] == "title_new_game_menu"
    assert observation["surrounding_story_state_reached"] is False
    assert "rather than a story hub" in observation["bounded_note"]
