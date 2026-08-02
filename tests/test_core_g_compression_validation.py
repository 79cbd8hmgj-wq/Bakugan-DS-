from pathlib import Path

from bakugan_ds.gates.io import load_json_object

VALIDATION = Path(
    "analysis/runtime-observations/core_g_compression_validation.json"
)


def load_validation() -> dict[str, object]:
    return load_json_object(VALIDATION)


def test_structural_verification_matches_rebuilt_rom_evidence() -> None:
    payload = load_validation()
    build = payload["build_verification"]
    overlay = payload["overlay"]

    assert payload["profile_id"] == "b6re_rev0"
    assert build == {
        "free_bytes_after_repack": 3040652,
        "layout_mismatches": 0,
        "overlay_compressed_size": 0,
        "overlay_flags": 0,
        "overlay_output_encoding": "uncompressed-overlay",
        "rom_size": 134217728,
        "unchanged_fat_payloads_verified": 11004,
    }
    assert overlay["overlay_id"] == 7
    assert overlay["load_address"] == "0x02219440"
    assert overlay["decoded_size"] == 467360
    assert overlay["bss_size"] == 1600
    assert overlay["changed_byte_count"] == 41


def test_constructor_cases_cover_low_high_modifier_and_symmetry() -> None:
    cases = {
        item["case"]: item
        for item in load_validation()["controlled_constructor_cases"]
    }

    low = cases["low_unchanged"]
    assert low["inputs"]["player"] == {"core_g": 190, "mutable_modifier_g": 0}
    assert low["outputs"]["player"]["base_snapshot_g"] == 190
    assert low["inputs"]["opponent"] == {"core_g": 230, "mutable_modifier_g": 0}
    assert low["outputs"]["opponent"]["base_snapshot_g"] == 230

    high = cases["high_modifier_and_symmetry"]
    assert high["inputs"]["player"] == {"core_g": 650, "mutable_modifier_g": 0}
    assert high["outputs"]["player"]["compressed_core_g"] == 525
    assert high["outputs"]["player"]["base_snapshot_g"] == 525
    assert high["inputs"]["opponent"] == {"core_g": 650, "mutable_modifier_g": 30}
    assert high["outputs"]["opponent"]["compressed_core_g"] == 525
    assert high["outputs"]["opponent"]["base_snapshot_g"] == 555


def test_gate_and_modifier_contributions_remain_unscaled() -> None:
    payload = load_validation()
    patch = payload["patch"]
    preserves = set(patch["preserves"])

    assert patch["applies_to"] == "both combatants core G before the mutable modifier"
    assert patch["threshold_g"] == 400
    assert patch["low_curve"] == "core_g"
    assert patch["high_curve"] == "200 + floor(core_g / 2)"
    assert preserves == {
        "persistent roster G values",
        "general mutable G modifier",
        "field G-Power pickups",
        "Gate Card and attribute bonuses",
    }

    gate_cases = {
        item["case"]: item for item in payload["controlled_gate_cases"]
    }
    assert gate_cases["high_player_gate"]["target_total_g"] == 625
    assert gate_cases["high_player_gate"]["equation"] == "525 + 100 = 625"
    assert gate_cases["high_modifier_gate"]["target_total_g"] == 655
    assert gate_cases["high_modifier_gate"]["equation"] == "555 + 100 = 655"


def test_clean_game_smoke_reaches_responsive_story_exit() -> None:
    smoke = load_validation()["clean_game_smoke"]

    assert smoke["title_screen_reached"] is True
    assert smoke["profile_created"] is True
    assert smoke["first_battle_entered"] is True
    assert smoke["attribute_minigame_entered"] is True
    assert smoke["tutorial_completion_dialogue_observed"] is True
    assert smoke["returned_to_surrounding_story"] is True
    assert smoke["post_exit_input_responsive"] is True
    assert smoke["overlay_failure_observed"] is False
    assert smoke["tutorial_exit_method"] == "built_in_skip_after_failed_rub_retry"
    assert "does not claim a natural win" in smoke["scope_note"]

    gate_result = smoke["gate_result"]
    assert gate_result["opponent"] == {
        "base_snapshot_g": 230,
        "gate_bonus_g": 180,
        "target_total_g": 410,
    }
    assert gate_result["player"] == {
        "base_snapshot_g": 190,
        "gate_bonus_g": 100,
        "target_total_g": 290,
    }
