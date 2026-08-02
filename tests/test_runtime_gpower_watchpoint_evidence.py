import csv
import json
from pathlib import Path


def load_observation() -> dict[str, object]:
    return json.loads(
        Path("analysis/runtime-observations/gpower_tutorial.json").read_text(
            encoding="utf-8"
        )
    )


def test_target_total_watchpoints_record_exact_runtime_operands() -> None:
    payload = load_observation()
    capture = payload["target_total_watchpoint_capture"]
    assert capture["add_instruction"] == "0x0223D288"
    assert capture["store_instruction"] == "0x0223D28C"
    assert capture["post_store_pc"] == "0x0223D290"
    hits = {hit["side"]: hit for hit in capture["hits"]}
    assert hits["opponent"]["registers"]["r0_result"] == 410
    assert hits["opponent"]["registers"]["r1_bonus"] == 180
    assert hits["opponent"]["registers"]["r2_base"] == 230
    assert hits["player"]["registers"]["r0_result"] == 290
    assert hits["player"]["registers"]["r1_bonus"] == 100
    assert hits["player"]["registers"]["r2_base"] == 190


def test_runtime_symbols_separate_confirmed_math_from_unresolved_paths() -> None:
    with Path("analysis/symbols/runtime_gpower.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)}
    assert rows["BattleGPower_AddGateBonus"]["confidence"] == "confirmed"
    assert rows["ParticipantGPower_AdjustModifier"]["confidence"] == "confirmed"
    assert rows["BattleGPower_AdjustState"]["confidence"] == "probable"


def test_validation_summary_does_not_overstate_progression_or_evolution() -> None:
    text = Path("docs/gpower-runtime-validation.md").read_text(encoding="utf-8")
    assert "general mutable-modifier routine" in text
    assert "Probable:" in text
    assert "Candidate:" in text
    assert "evolution selecting" in text
