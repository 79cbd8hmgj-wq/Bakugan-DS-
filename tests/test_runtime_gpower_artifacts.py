import csv
import json
from pathlib import Path


def test_runtime_observation_records_controlled_formula() -> None:
    payload = json.loads(
        Path("analysis/runtime-observations/gpower_tutorial.json").read_text(encoding="utf-8")
    )

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

    assert payload["gate_bonus_source"]["helper_confidence"] == "probable"
    boundaries = payload["confidence_boundaries"]
    assert boundaries["source_u16_04"]["confidence"] == "probable"
    assert boundaries["source_u16_06"]["confidence"] == "probable"


def test_runtime_symbols_include_confirmed_constructor_math_and_tween() -> None:
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
    assert rows["GateAttributeBonus_Lookup"]["confidence"] == "probable"


def test_runtime_document_preserves_evidence_boundaries() -> None:
    text = Path("docs/runtime-gpower-tracing.md").read_text(encoding="utf-8")
    for required in (
        "0x0223CFE8",
        "0x0223D0F0",
        "0x0223D288",
        "0x0223D28C",
        "0x0223D290",
        "0x0223DDAC",
        "190 + 100 = 290",
        "230 + 180 = 410",
        "20-byte",
        "Probable, not confirmed",
        "not committed",
    ):
        assert required in text


def test_static_candidate_file_is_promoted_by_runtime_evidence() -> None:
    text = Path("analysis/candidates/gpower.yaml").read_text(encoding="utf-8")
    for required in (
        "runtime_confirmation:",
        "formula_confidence: confirmed",
        "constructor_address: 0x0223CFE8",
        "add_gate_bonus_address: 0x0223D288",
        "store_target_address: 0x0223D28C",
        "watchpoint_post_store_pc: 0x0223D290",
        "display_tween_address: 0x0223DDAC",
        "target_total: base_snapshot_g + gate_attribute_bonus_g",
        "helper_confidence: probable",
    ):
        assert required in text
