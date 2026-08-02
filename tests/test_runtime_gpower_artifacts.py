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
    cases = {record["side"]: record for record in payload["controlled_records"]}
    assert cases["player"]["equation"] == "190 + 100 = 290"
    assert cases["opponent"]["equation"] == "230 + 180 = 410"
    assert payload["formula"]["initial_base_snapshot"] == (
        "source_core_g + source_mutable_modifier"
    )
    assert payload["formula"]["target_total"] == (
        "base_snapshot_g + gate_attribute_bonus_g"
    )


def test_gate_lookup_and_watchpoint_evidence_are_exact() -> None:
    payload = load_observation()
    source = payload["gate_bonus_source"]
    assert source["helper_address"] == "0x02065BF4"
    assert source["table_address"] == "0x020A15AC"
    assert source["row_width"] == 6
    assert source["value_scale"] == 10
    gate_hit = payload["gate_bonus_watchpoint_capture"]["final_hit"]
    assert gate_hit == {
        "writer_instruction": "0x0223D274",
        "post_store_pc": "0x0223D278",
        "source_register": "r1",
        "source_value": 100,
    }


def test_mutable_modifier_is_general_and_semantics_remain_bounded() -> None:
    payload = load_observation()
    modifier = payload["mutable_modifier"]
    assert modifier["function_address"] == "0x0226A380"
    assert modifier["maximum_combined_g"] == 990
    boundaries = payload["confidence_boundaries"]
    assert boundaries["source_mutable_modifier"]["confidence"] == "confirmed_function"
    assert boundaries["progression_callsites"]["confidence"] == "probable"
    assert boundaries["evolution_representation"]["confidence"] == "candidate"
    assert "not exclusively" in boundaries["source_mutable_modifier"]["interpretation"]


def test_runtime_symbols_include_confirmed_pipeline_and_modifier() -> None:
    with Path("analysis/symbols/runtime_gpower.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)}
    assert rows["BattleGPowerRecord_Init"]["address"] == "0x0223CFE8"
    assert rows["BattleGPower_AddGateBonus"]["address"] == "0x0223D288"
    assert rows["ParticipantGPower_InitializeRecords"]["address"] == "0x022696B4"
    assert rows["ParticipantGPower_AdjustModifier"]["address"] == "0x0226A380"
    assert rows["ParticipantGPower_AdjustModifier"]["confidence"] == "confirmed"
    assert rows["GateAttributeBonus_Lookup"]["address"] == "0x02065BF4"


def test_document_and_candidate_file_preserve_confidence_boundaries() -> None:
    document = Path("docs/runtime-gpower-tracing.md").read_text(encoding="utf-8")
    for required in (
        "general mutable G modifier",
        "0x0226A380",
        "Probable progression callsites",
        "Candidate evolution model",
        "Evolution is not yet runtime-confirmed",
        "0x02007EB8",
    ):
        assert required in document
    candidate = Path("analysis/candidates/gpower.yaml").read_text(encoding="utf-8")
    assert "source_mutable_modifier: confirmed_general_additive_channel" in candidate
    assert "progression_callsites: probable" in candidate
    assert "evolution_representation: candidate" in candidate
