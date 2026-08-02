from __future__ import annotations

import csv
import json
from pathlib import Path

EVIDENCE = Path("analysis/gates/card-id-evidence.json")
SYMBOLS = Path("analysis/symbols/gate_cards.csv")
FORBIDDEN_KEYS = {"raw_bytes", "ram_dump", "save_state", "screenshot", "complete_gate_table"}


def walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_selected_gate_identity_artifacts_preserve_copyright_boundary() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["complete_name_table_committed"] is False
    assert payload["guide_order_used_for_ids"] is False
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))

    attributes = payload["attributes"]
    assert [(item["attribute_id"], item["name"]) for item in attributes] == [
        (0, "pyrus"),
        (1, "aquos"),
        (2, "subterra"),
        (3, "haos"),
        (4, "darkus"),
        (5, "ventus"),
    ]
    assert all(item["confidence"] == "confirmed" for item in attributes)

    mappings = payload["mappings"]
    assert [(item["card_id"], item["label"]) for item in mappings] == [
        (19, "Juggernoid"),
        (20, "Robotallion"),
        (22, "Serpenoid"),
    ]
    assert len(payload["selected_rows"]) == 3


def test_gate_symbol_csv_matches_selected_mappings() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    with SYMBOLS.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [(int(row["card_id"]), row["label"]) for row in rows] == [
        (item["card_id"], item["label"]) for item in payload["mappings"]
    ]
    assert all(row["confidence"] == "confirmed" for row in rows)


LIFECYCLE = Path("analysis/gates/activation-lifecycle.json")
LIFECYCLE_DOC = Path("docs/gate-card-runtime-lifecycle.md")


def test_gate_lifecycle_artifact_has_battle_path_and_evidence() -> None:
    payload = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    transitions = payload["transitions"]
    assert transitions
    assert any(item["to_state"] == "battle_started" for item in transitions)
    assert all(item["evidence"].strip() for item in transitions)
    assert all(item["owner_source"].strip() for item in transitions)
    assert all(item["card_id_source"].strip() for item in transitions)
    assert payload["ai_path"]["shared"] is True
    assert payload["reuse_supported"] is False
    assert payload["complete_runtime_capture_committed"] is False
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))

    document = LIFECYCLE_DOC.read_text(encoding="utf-8")
    assert "0x0223EA60" in document
    assert "Resolved to reset" in document
    assert "Reused" in document


SELECTOR = Path("analysis/gates/battle-type-selector.json")
BATTLE_TYPE_SYMBOLS = Path("analysis/symbols/battle_types.csv")


def test_battle_type_selector_is_fixed_and_complete() -> None:
    payload = json.loads(SELECTOR.read_text(encoding="utf-8"))
    assert payload["selection_mode"] == "fixed_metadata"
    assert payload["uses_rng_in_normal_path"] is False
    assert payload["rng_calls"] == []
    assert payload["random_range"] is None
    assert [(item["type_id"], item["label"]) for item in payload["types"]] == [
        (0, "Scratch"),
        (1, "Timing"),
        (2, "Pop"),
        (3, "Spin"),
        (4, "Trace"),
        (5, "Bound"),
    ]
    assert len(payload["comparison_cases"]) == 6
    assert {item["selected_type_id"] for item in payload["comparison_cases"]} == set(range(6))
    assert payload["complete_card_metadata_committed"] is False
    assert payload["type_label_source"]["complete_reference_table_committed"] is False
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))


def test_battle_type_symbol_csv_has_required_columns() -> None:
    with BATTLE_TYPE_SYMBOLS.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == [
            "component",
            "runtime_address",
            "component_offset",
            "name",
            "confidence",
            "evidence",
        ]
    assert {row["name"] for row in rows} >= {
        "GetCardMetadataByte",
        "SelectGateBattleType",
        "StoreSelectedBattleType",
        "ApplyBattleTypeOverride",
        "DispatchBattleType",
    }
    assert all(row["confidence"] == "confirmed" for row in rows)


CONTEXT = Path("analysis/gates/battle-context.json")


def test_battle_context_has_confirmed_hook_safe_core() -> None:
    from bakugan_ds.gates.context import confirmed_hook_context, load_context_fields

    fields = load_context_fields(CONTEXT)
    included = {item.name for item in confirmed_hook_context(fields)}
    assert {
        "gate_card_id",
        "attribute_id",
        "compressed_core_g",
        "mutable_modifier_g",
        "base_snapshot_g",
        "gate_bonus_g",
        "target_total_g",
        "combatant_record_pointer",
        "battle_type_id",
        "battle_state",
    } <= included
    assert "animated_current_g" not in included
    assert "gate_owner" not in included

    payload = json.loads(CONTEXT.read_text(encoding="utf-8"))
    unresolved = {item["name"] for item in payload["unresolved_fields"]}
    assert {
        "match_score_or_captured_gate_count",
        "ability_cards_used",
        "gate_activation_count",
        "previous_battle_types",
        "landing_or_shot_condition",
        "arena_id",
        "difficulty",
        "human_ai_identity",
    } <= unresolved
    assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload))


def test_storage_strategy_selects_viable_primary_and_fallback() -> None:
    from bakugan_ds.gates.storage import SYSTEM2_STORAGE_DECISION, validate_storage_decision

    validate_storage_decision(SYSTEM2_STORAGE_DECISION)
    assert SYSTEM2_STORAGE_DECISION.primary == "hybrid"
    assert SYSTEM2_STORAGE_DECISION.fallback == "nitrofs"
    candidates = {item.name: item for item in SYSTEM2_STORAGE_DECISION.candidates}
    assert set(candidates) == {
        "nitrofs",
        "expanded_executable_overlay",
        "dedicated_overlay",
        "hybrid",
    }
    assert candidates["hybrid"].viable is True
    assert candidates["nitrofs"].viable is True
    assert candidates["expanded_executable_overlay"].viable is False
    assert candidates["dedicated_overlay"].viable is False

    document = Path("analysis/gates/expansion-strategy.md").read_text(encoding="utf-8")
    for required in (
        "4,152 bytes total",
        "0x0228BC20",
        "0x02293C60",
        "0x8000",
        "0x7A7E0",
        "0x023E0000",
        "72-byte stack buffer",
        "Missing or malformed",
        "Dedicated overlay",
        "Expanded executable or overlay",
    ):
        assert required in document
