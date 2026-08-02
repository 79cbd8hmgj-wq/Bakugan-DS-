from __future__ import annotations

import csv
import json
from pathlib import Path

EVIDENCE = Path("analysis/gates/card-id-evidence.json")
SYMBOLS = Path("analysis/symbols/gate_cards.csv")
LIFECYCLE = Path("analysis/gates/activation-lifecycle.json")
LIFECYCLE_DOC = Path("docs/gate-card-runtime-lifecycle.md")
SELECTOR = Path("analysis/gates/battle-type-selector.json")
BATTLE_TYPE_SYMBOLS = Path("analysis/symbols/battle_types.csv")
CONTEXT = Path("analysis/gates/battle-context.json")
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


def test_hook_feasibility_has_all_purposes_and_reversible_instrumentation() -> None:
    from bakugan_ds.gates.hooks import HookPurpose, normalize_hook_capture, validate_hook_sites

    payload = json.loads(Path("analysis/gates/hook-feasibility.json").read_text())
    sites = normalize_hook_capture(payload)
    validate_hook_sites(sites)
    assert {site.purpose for site in sites} == set(HookPurpose)
    assert all(site.core_g_compatible for site in sites)
    assert payload["instrumentation"]["gameplay_result_changed"] is False
    assert payload["instrumentation"]["register_or_memory_mutation_by_instrumentation"] is False
    assert payload["instrumentation"]["returned_to_surrounding_story"] is True
    assert payload["instrumentation"]["post_exit_input_responsive"] is True
    assert payload["instrumentation"]["raw_debugger_log_committed"] is False
    assert payload["code_layout"]["module_start"] == "0x0228BC20"
    assert payload["code_layout"]["module_end"] == "0x02293C20"


def test_all_gate_json_artifacts_are_normalized_and_safe() -> None:
    for path in sorted(Path("analysis/gates").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert path.read_text(encoding="utf-8").endswith("\n")
        assert FORBIDDEN_KEYS.isdisjoint(walk_keys(payload)), path


def test_milestone_6a_success_criteria_are_documented() -> None:
    legacy = json.loads(Path("analysis/gates/legacy-table-metadata.json").read_text())
    assert legacy["confidence"] == "confirmed"
    assert legacy["record_count"] == 213
    assert legacy["record_stride"] == 6
    assert legacy["element_width"] == 1
    assert legacy["signed"] is False
    assert legacy["attribute_order"] == [
        "pyrus",
        "aquos",
        "subterra",
        "haos",
        "darkus",
        "ventus",
    ]

    lifecycle = json.loads(Path("analysis/gates/activation-lifecycle.json").read_text())
    assert any(item["to_state"] == "battle_started" for item in lifecycle["transitions"])
    assert lifecycle["ai_path"]["shared"] is True

    selector = json.loads(Path("analysis/gates/battle-type-selector.json").read_text())
    assert selector["selection_mode"] == "fixed_metadata"
    assert selector["forced_paths"]

    context = json.loads(Path("analysis/gates/battle-context.json").read_text())
    confirmed = {
        item["name"]
        for item in context["fields"]
        if item["confidence"] == "confirmed" and item["safe_for_hook"]
    }
    assert "gate_card_id" in confirmed
    assert "compressed_core_g" in confirmed
    assert "battle_type_id" in confirmed

    hooks = json.loads(Path("analysis/gates/hook-feasibility.json").read_text())
    assert {item["purpose"] for item in hooks["sites"]} == {
        "gate_bonus",
        "battle_type_selector",
        "context_access",
        "expanded_data_lookup",
    }
    assert hooks["instrumentation"]["gameplay_result_changed"] is False


def test_gate_documentation_defines_legacy_and_6b_contracts() -> None:
    legacy = Path("docs/gate-card-legacy-system.md").read_text(encoding="utf-8")
    roadmap = Path("docs/gate-card-system-2-roadmap.md").read_text(encoding="utf-8")

    for required in (
        "0x020A15AC",
        "213",
        "Pyrus",
        "bakugan-ds gate export-legacy",
        "Copyright and evidence boundary",
    ):
        assert required in legacy

    for required in (
        "No System 2.0 gameplay effect is implemented",
        "4,152-byte `G2DT` trailer",
        "0x0228BC20–0x02293C20",
        "fixed-point percentage of compressed core G",
        "Every other Gate retains original",
        "Milestone 6G",
    ):
        assert required in roadmap
