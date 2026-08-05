from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.authoring import load_authoring_document

AUTHORING = Path("config/gates/milestone-6c-system2-v1.json")


def test_milestone_6c_authoring_is_new_configuration_and_exact_scope() -> None:
    payload = json.loads(AUTHORING.read_text(encoding="utf-8"))
    assert payload["format_version"] == 1
    assert len(payload["records"]) == 103
    assert [item["card_id"] for item in payload["records"]] == list(range(1, 104))
    records = load_authoring_document(AUTHORING)
    assert [record.card_id for record in records if record.archetype != 0] == [19]
    text = AUTHORING.read_text(encoding="utf-8")
    for forbidden in ("raw_bytes", "ram_dump", "save_state", "arena_id"):
        assert forbidden not in text


RUNTIME_CONTRACT = Path("analysis/gates/milestone-6c-runtime-contract.json")


def test_runtime_contract_records_task_9_live_calculation_boundary() -> None:
    payload = json.loads(RUNTIME_CONTRACT.read_text(encoding="utf-8"))
    boundary = payload["task_9_boundary"]
    assert boundary["prototype_gate_id"] == 19
    assert boundary["live_system2_behavior"] == ("juggernoid_hybrid_gate_calculation")
    assert boundary["battle_type_selection"] == ("legacy_fixed_metadata_until_task_10")
    assert boundary["mutable_modifier_scaled"] is False
    assert boundary["tie_activates"] is False
    assert boundary["complete_legacy_fallback"] is True
    assert boundary["descriptor_limit"] == 26
    assert "session +0x28D" in boundary["descriptor_limit_rationale"]
    assert boundary["success_flag_register"] == "r3"
    assert boundary["legacy_fallback_flag"] == 0
    assert boundary["system2_success_flag"] == 1
    assert boundary["context_sources"] == {
        "combatant_participant": "combatant +0x19 high nibble",
        "descriptor_indices": "session +0x28D/+0x28E",
        "descriptor_participant": "descriptor +0x0F low nibble",
        "gate_owner": "battle object +0x06",
        "match_score": "participant +0xEE",
        "team_flag": "0x020D433C +0x98",
        "teammate": "participant +0xF2 with reciprocal-pair validation",
    }
    assert payload["symbols"]["g2_calculate_gate_bonus"].startswith(
        "Calculates the approved Gate 19"
    )
    assert payload["symbols"]["g2_context_store_hook"].startswith(
        "Clamps the successful System 2.0"
    )


def test_runtime_contract_records_task_10_weighted_selector_boundary() -> None:
    payload = json.loads(RUNTIME_CONTRACT.read_text(encoding="utf-8"))
    boundary = payload["task_10_boundary"]
    assert boundary == {
        "battle_history_updated": False,
        "explicit_constructor_precedence": "unchanged",
        "invalid_cache_rng_calls": 0,
        "live_system2_behavior": "weighted_juggernoid_normal_fallback",
        "phase_local_fallback": "legacy_fixed_metadata",
        "scripted_override_precedence": "unchanged",
        "weight_count": 6,
        "weight_pointer": "cache +0x0E",
        "weighted_helper": "0x02021A30",
    }
    assert payload["symbols"]["g2_select_battle_type"].startswith("Uses the approved Gate 19")


BUILD_CONTRACT = Path("analysis/gates/milestone-6c-build-contract.json")
HOOK_PATCHES = Path("patches/gate-system2-milestone-6c-hooks.json")


def test_milestone_6c_build_contract_has_exact_install_scope() -> None:
    contract = json.loads(BUILD_CONTRACT.read_text(encoding="utf-8"))
    patches = json.loads(HOOK_PATCHES.read_text(encoding="utf-8"))

    assert contract["profile_id"] == "b6re_rev0"
    assert contract["prerequisite_overlay_sha256"] == (
        "7e310ef95fcc3304870b98d11046ed453b1dc2d270f42a438af161b603437f2e"
    )
    assert contract["raw_carrier"] == {
        "file_id": 2762,
        "original_size": 2840,
        "replacement_size": 6992,
    }
    assert contract["overlay"] == {
        "overlay_id": 7,
        "original_ram_size": 467360,
        "original_bss_size": 1600,
        "replacement_ram_size": 501728,
        "replacement_bss_size": 64,
    }
    assert contract["arm9"] == {
        "decoded_patch_address": "0x02006264",
        "decoded_patch_offset": "0x00006264",
        "expected": "20bc2802",
        "replacement": "603c2902",
        "stored_size_preserved": True,
    }
    assert contract["blz_reencode"] == {
        "decoded_size": 786712,
        "stored_size": 448192,
        "passthrough_length": 32768,
        "header_length": 193,
        "stored_sha256": ("95494b52cb94c85f7209ddf00fd37b6289fdecd6ad855f7344132b3f840236f8"),
        "in_place_decode_matches": True,
    }
    assert contract["guarded_change_count"] == 7
    assert len(patches["patches"]) == 7
    assert {item["id"] for item in patches["patches"]} == {
        "gate-system2-gate-bonus-hook",
        "gate-system2-context-access-hook",
        "gate-system2-battle-type-selector-hook",
        "gate-system2-expanded-data-lookup-hook",
        "gate-system2-cache-load-hook",
        "gate-system2-cache-clear-hook",
        "gate-system2-arena-low",
    }
    text = BUILD_CONTRACT.read_text(encoding="utf-8")
    for forbidden in ("module_binary", "rom_bytes", "ram_dump", "save_state"):
        assert forbidden not in text


PROTOTYPE_DOC = Path("docs/gate-card-system-2-prototype.md")
ROADMAP_DOC = Path("docs/gate-card-system-2-roadmap.md")
RUNTIME_CONTEXT_DOC = Path("docs/gate-card-system-2-runtime-context.md")
VERIFICATION_DOC = Path("docs/superpowers/plans/2026-08-03-milestone-6c-verification.md")
README = Path("README.md")


def test_milestone_6c_prototype_document_records_exact_live_contract() -> None:
    text = PROTOTYPE_DOC.read_text(encoding="utf-8")
    for required in (
        "Gate ID `19`, Juggernoid",
        "flat_bonus_g:         60",
        "percent_q8_8:         20",
        "attribute_modifiers:  [0, 30, 0, 0, 0, 0]",
        "battle_weights:       [50, 30, 30, 30, 30, 30]",
        "Gate-owner side is behind",
        "0x0228BC20–0x02293C20",  # noqa: RUF001
        "0x02293C20–0x02293C60",  # noqa: RUF001
        "Record-level fallback",
        "Calculation-level fallback",
        "Selector-phase fallback",
        "bakugan-ds gate install-milestone-6c",
        "Milestone 6C does not implement",
    ):
        assert required in text
    for exclusion in (
        "arena-ID conditions",
        "Ability Card interaction",
        "AI evaluation",
        "save-format changes",
        "complete Gate roster conversion",
    ):
        assert exclusion in text


def test_milestone_6c_docs_mark_only_the_prototype_complete() -> None:
    roadmap = ROADMAP_DOC.read_text(encoding="utf-8")
    context = RUNTIME_CONTEXT_DOC.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    verification = VERIFICATION_DOC.read_text(encoding="utf-8")

    assert "Milestone 6C — engine and first prototype — complete" in roadmap
    assert "Only Gate ID `19`, Juggernoid, is active" in roadmap
    assert "## Milestone 6D — core balance framework" in roadmap
    assert "Milestone 6C uses only the confirmed fields" in context
    assert "Arena ID, Ability state, fatigue, history, AI, presentation, and saves" in context
    assert "Milestone 6C now implements" in readme
    assert "gate install-milestone-6c" in readme
    assert "## Controlled runtime acceptance" in verification
    assert "does not claim that every arithmetic vector occurred naturally" in verification
