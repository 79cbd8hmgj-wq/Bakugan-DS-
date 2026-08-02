import csv
import json
from pathlib import Path


OBSERVATION = Path("analysis/runtime-observations/level_experience_storage.json")
SYMBOLS = Path("analysis/symbols/level_experience.csv")
DOCUMENT = Path("docs/level-experience-storage.md")


def load_observation() -> dict[str, object]:
    return json.loads(OBSERVATION.read_text(encoding="utf-8"))


def test_auxiliary_record_packs_zero_based_level_and_experience() -> None:
    payload = load_observation()
    auxiliary = payload["persistent_auxiliary_record"]
    assert auxiliary["helper_address"] == "0x02023248"
    assert auxiliary["record_offset"] == "0x0088"
    assert auxiliary["record_size_bytes"] == 4
    packed = auxiliary["packed_level_experience"]
    assert packed["level_bits"] == "0-3"
    assert packed["experience_bits"] == "4-15"
    assert packed["level_encoding"] == "zero_based; displayed_level = stored_nibble + 1"
    assert packed["decode_formula"] == {
        "level_index": "packed & 0x000F",
        "experience": "packed >> 4",
    }
    assert packed["encode_formula"] == "(experience << 4) | level_index"
    assert packed["maximum_experience"] == 4095
    assert auxiliary["field_stats"]["packed_stat_count"] == 5
    assert auxiliary["field_stats"]["bits_per_stat"] == 3


def test_experience_boost_rule_is_exact() -> None:
    boost = load_observation()["experience_boost"]
    assert boost["primary_handler_address"] == "0x0222B600"
    assert boost["primary_update_range"] == "0x0222B668-0x0222B6A0"
    assert boost["secondary_update_range"] == "0x0222CB98-0x0222CBC8"
    assert boost["award_xp"] == 40
    assert boost["pre_add_guard"] == "current_xp < 4055"
    assert boost["packed_experience_limit"] == 4095
    assert boost["preserves_level_nibble"] is True


def test_normal_battle_reward_accumulates_xp_without_promotion() -> None:
    result = load_observation()["normal_battle_experience"]
    assert result["state_function_address"] == "0x0223F918"
    assert result["update_range"] == "0x0224224C-0x02242280"
    assert result["overflow_guard"] == "current_xp <= 4095 - reward_xp"
    assert result["preserves_level_nibble"] is True
    assert result["performs_level_promotion"] is False


def test_runtime_anchor_decodes_level_one_and_near_cap_experience() -> None:
    anchor = load_observation()["tutorial_runtime_anchor"]
    assert anchor["bakugan"] == "Pyrus Serpenoid"
    assert anchor["persistent_packed_address"] == "0x020D4688"
    assert anchor["persistent_g_address"] == "0x020D48D4"
    assert anchor["battle_packed_address"] == "0x022E24EC"
    assert anchor["forced_packed_value"] == "0xFD70"
    assert anchor["decoded_level_index"] == 0
    assert anchor["decoded_displayed_level"] == 1
    assert anchor["decoded_experience"] == 4055
    assert anchor["persistent_g"] == 190


def test_symbols_document_and_confidence_boundary_match() -> None:
    with SYMBOLS.open(newline="", encoding="utf-8") as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)}
    assert rows["PlayerBakuganAux_GetRecord"]["address"] == "0x02023248"
    assert rows["BattleExperienceBoost_Add40"]["address"] == "0x0222B668"
    assert rows["BattleResult_AddExperience"]["address"] == "0x0224224C"
    boundaries = load_observation()["confidence_boundaries"]
    assert boundaries["packed_level_experience_layout"] == "confirmed"
    assert boundaries["normal_level_promotion_path"] == "unresolved"
    assert boundaries["persistent_g_update_on_promotion"] == "unresolved"
    text = DOCUMENT.read_text(encoding="utf-8")
    for required in (
        "zero-based level",
        "current_xp < 4055",
        "4095 - reward_xp",
        "does **not** promote",
        "No gameplay patch is included",
    ):
        assert required in text
    assert all(token not in text for token in ("TODO", "TBD", "FIXME"))
