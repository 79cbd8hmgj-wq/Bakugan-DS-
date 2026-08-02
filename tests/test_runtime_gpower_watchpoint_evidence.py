import csv
import json
from pathlib import Path


def test_target_total_watchpoints_record_exact_runtime_operands() -> None:
    payload = json.loads(
        Path("analysis/runtime-observations/gpower_tutorial.json").read_text(
            encoding="utf-8"
        )
    )
    capture = payload["target_total_watchpoint_capture"]

    assert capture["add_instruction"] == "0x0223D288"
    assert capture["store_instruction"] == "0x0223D28C"
    assert capture["post_store_pc"] == "0x0223D290"

    hits = {hit["side"]: hit for hit in capture["hits"]}
    assert hits["opponent"]["stop_packet"] == "T06watch:ee85e220;"
    assert hits["opponent"]["registers"] == {
        "r0_result": 410,
        "r1_bonus": 180,
        "r2_base": 230,
        "r5_entry_base": "0x022E58E0",
        "r6_container_base": "0x022E58E0",
    }
    assert hits["player"]["stop_packet"] == "T06watch:2095e220;"
    assert hits["player"]["registers"] == {
        "r0_result": 290,
        "r1_bonus": 100,
        "r2_base": 190,
        "r5_entry_base": "0x022E58F4",
        "r6_container_base": "0x022E58E0",
    }


def test_runtime_symbols_separate_confirmed_math_from_unresolved_later_modifier() -> None:
    with Path("analysis/symbols/runtime_gpower.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)}

    assert rows["BattleGPower_AddGateBonus"]["confidence"] == "confirmed"
    assert rows["BattleGPower_StoreTarget"]["confidence"] == "confirmed"
    assert rows["GateAttributeBonus_Lookup"]["confidence"] == "confirmed"
    assert rows["GateAttributeBonus_Table"]["confidence"] == "confirmed"
    assert rows["BattleGPower_AdjustState"]["confidence"] == "probable"


def test_runtime_document_states_only_the_remaining_semantic_boundaries() -> None:
    text = Path("docs/runtime-gpower-tracing.md").read_text(encoding="utf-8")
    for required in (
        "r2 = 230",
        "r1 = 180",
        "r2 = 190",
        "r1 = 100",
        "helper **`0x02065BF4`**",
        "table at\n**`0x020A15AC`**",
        "level-growth interpretation remains probable",
        "Evolution is likewise\nexpected",
        "field\n`+0x0A`",
    ):
        assert required in text
