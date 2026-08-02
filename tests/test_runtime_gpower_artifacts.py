import csv
import json
from pathlib import Path


def load_observation() -> dict[str, object]:
    return json.loads(
        Path("analysis/runtime-observations/gpower_tutorial.json").read_text(
            encoding="utf-8"
        )
    )


def test_runtime_observation_records_controlled_formula() -> None:
    payload = load_observation()

    assert payload["rom_profile"] == "b6re_rev0"
    assert payload["confidence"] == "confirmed"
    assert payload["record_layout"]["participant_entry_stride_bytes"] == 20
    assert payload["record_layout"]["gpower_fields_offset"] == 12
    assert payload["record_layout"]["fields"] == {
        "0x00": "animated_current_g",
        "0x02": "target_total_g",
        "0x04": "base_snapshot_g",
        "0x06": "gate_attribute_bonus_g",
    }

    cases = {record["side"]: record for record in payload["controlled_records"]}
    assert cases["player"]["equation"] == "190 + 100 = 290"
    assert cases["opponent"]["equation"] == "230 + 180 = 410"

    formula = payload["formula"]
    assert formula["initial_base_snapshot"] == "source_u16_04 + source_u16_06"
    assert formula["target_total"] == "base_snapshot_g + gate_attribute_bonus_g"
    assert formula["display_animation_step"] == 3


def test_runtime_observation_preserves_exact_instruction_and_source_evidence() -> None:
    payload = load_observation()
    formula = payload["formula"]

    target_words = {
        item["address"]: item["word"] for item in formula["target_total_instructions"]
    }
    assert target_words == {
        "0x0223D278": "0xE1D520BC",
        "0x0223D27C": "0xE1D511B2",
        "0x0223D288": "0xE0820001",
        "0x0223D28C": "0xE1C500BE",
    }

    capture = payload["stat_source_capture"]
    assert capture["breakpoint_pc"] == "0x0223D0F0"
    assert capture["first_record"]["u16_04_form_base_g"] == 230
    assert capture["first_record"]["u16_06_progression_bonus_g"] == 0
    assert capture["second_record"]["u16_04_form_base_g"] == 190
    assert capture["second_record"]["u16_06_progression_bonus_g"] == 0


def test_runtime_evidence_promotes_gate_lookup_but_preserves_semantic_boundaries() -> None:
    payload = load_observation()

    assert payload["gate_bonus_source"]["helper_confidence"] == "confirmed"
    assert payload["gate_bonus_source"]["table_confidence"] == "confirmed"
    assert payload["gate_bonus_source"]["table_address"] == "0x020A15AC"
    assert payload["gate_bonus_source"]["row_width"] == 6
    assert payload["gate_bonus_source"]["value_scale"] == 10

    boundaries = payload["confidence_boundaries"]
    assert boundaries["source_u16_04"]["confidence"] == "confirmed"
    assert boundaries["source_u16_06"]["confidence"] == (
        "confirmed_function_probable_semantics"
    )
    assert boundaries["evolution_representation"]["confidence"] == "probable"
    assert boundaries["later_battle_modifier"]["confidence"] == "candidate"


def test_runtime_symbols_include_confirmed_constructor_math_tween_and_lookup() -> None:
    with Path("analysis/symbols/runtime_gpower.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)}

    assert rows["BattleGPowerRecord_Init"]["address"] == "0x0223CFE8"
    assert rows["BattleGPowerRecord_Init"]["confidence"] == "confirmed"
    assert rows["BattleGPower_AddGateBonus"]["address"] == "0x0223D288"
    assert rows["BattleGPower_StoreTarget"]["address"] == "0x0223D28C"
    assert rows["BattleGPower_DisplayTween"]["address"] == "0x0223DDAC"
    assert rows["GateAttributeBonus_Lookup"]["address"] == "0x02065BF4"
    assert rows["GateAttributeBonus_Lookup"]["confidence"] == "confirmed"
    assert rows["GateAttributeBonus_Table"]["address"] == "0x020A15AC"
    assert rows["GateAttributeBonus_Table"]["confidence"] == "confirmed"


def test_runtime_document_and_candidate_file_match_promoted_evidence() -> None:
    document = Path("docs/runtime-gpower-tracing.md").read_text(encoding="utf-8")
    for required in (
        "0x0223CFE8",
        "0x0223D0F0",
        "0x0223D288",
        "0x0223D28C",
        "0x0223D290",
        "0x0223DDAC",
        "0x02065BF4",
        "0x020A15AC",
        "190 + 100 = 290",
        "230 + 180 = 410",
        "20-byte",
        "level-growth interpretation remains probable",
        "not committed",
    ):
        assert required in document

    candidate = Path("analysis/candidates/gpower.yaml").read_text(encoding="utf-8")
    for required in (
        "runtime_confirmation:",
        "formula_confidence: confirmed",
        "constructor_address: 0x0223CFE8",
        "add_gate_bonus_address: 0x0223D288",
        "store_target_address: 0x0223D28C",
        "watchpoint_post_store_pc: 0x0223D290",
        "display_tween_address: 0x0223DDAC",
        "target_total: base_snapshot_g + gate_attribute_bonus_g",
        "helper_confidence: confirmed",
        "table_address: 0x020A15AC",
        "source_u16_06_semantic_confidence: probable",
    ):
        assert required in candidate
