import csv
import json
from pathlib import Path


def test_target_total_watchpoints_record_exact_runtime_operands() -> None:
    payload = json.loads(
        Path("analysis/runtime-observations/gpower_tutorial.json").read_text(encoding="utf-8")
    )
    capture = payload["target_total_watchpoint_capture"]

    assert capture["add_instruction"] == "0x0223D288"
    assert capture["store_instruction"] == "0x0223D28C"
    assert capture["post_store_pc"] == "0x0223D290"

    hits = {hit["side"]: hit for hit in capture["hits"]}
    assert hits["opponent"]["registers"] == {
        "r0_result": 410,
        "r1_bonus": 180,
        "r2_base": 230,
        "r5_record": "0x022E58E0",
        "r6_container": "0x022E58E0",
    }
    assert hits["player"]["registers"] == {
        "r0_result": 290,
        "r1_bonus": 100,
        "r2_base": 190,
        "r5_record": "0x022E58F4",
        "r6_container": "0x022E58E0",
    }


def test_runtime_symbols_separate_confirmed_math_from_probable_lookup_semantics() -> None:
    with Path("analysis/symbols/runtime_gpower.csv").open(newline="", encoding="utf-8") as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)}

    assert rows["BattleGPower_AddGateBonus"]["address"] == "0x0223D288"
    assert rows["BattleGPower_AddGateBonus"]["confidence"] == "confirmed"
    assert rows["BattleGPower_StoreTarget"]["address"] == "0x0223D28C"
    assert rows["BattleGPower_StoreTarget"]["confidence"] == "confirmed"
    assert rows["GateAttributeBonus_Lookup"]["confidence"] == "probable"


def test_runtime_document_states_the_remaining_semantic_boundary() -> None:
    text = Path("docs/runtime-gpower-tracing.md").read_text(encoding="utf-8")
    assert "0x0223D290" in text
    assert "r2 = 230" in text
    assert "r1 = 180" in text
    assert "r2 = 190" in text
    assert "r1 = 100" in text
    assert "helper's exact card/attribute semantics remain probable" in text
