from __future__ import annotations

import json
from pathlib import Path

from bakugan_ds.gates.authoring import load_milestone_6d_authoring_document
from bakugan_ds.gates.loader import CACHE_ADDRESS, SYSTEM2_MODULE_SIZE
from bakugan_ds.gates.record import (
    GateArchetype,
    GateConditionId,
    GateEffectId,
    GateTargetMode,
    GateTimingPhase,
)
from bakugan_ds.gates.runtime_module import MODULE_BASE, MODULE_END
from bakugan_ds.gates.runtime_module_6d import build_milestone_6d_module

ENTRY_CONTRACT = Path("analysis/gates/milestone-6e-entry-contract.json")
AUTHORING = Path("config/gates/milestone-6d-system2-v1.json")


def _load() -> dict[str, object]:
    text = ENTRY_CONTRACT.read_text(encoding="utf-8")
    assert text.endswith("\n")
    payload = json.loads(text)
    assert isinstance(payload, dict)
    return payload


def _enum_map(enum_type: type[object]) -> dict[str, int]:
    return {member.name.lower(): int(member.value) for member in enum_type}  # type: ignore[attr-defined]


def test_entry_contract_freezes_milestone_6d_runtime_and_semantics() -> None:
    payload = _load()
    records = load_milestone_6d_authoring_document(AUTHORING)
    module = build_milestone_6d_module()

    assert payload["format_version"] == 1
    assert payload["profile_id"] == "b6re_rev0"
    assert payload["merged_milestone_6d_commit"] == (
        "8541867e7443f47bd24ea006e6a7be3f0fa1d54d"
    )
    assert payload["source_authoring_path"] == str(AUTHORING)
    assert payload["record_count"] == len(records) == 103
    assert payload["source_live_card_ids"] == [19]
    assert payload["source_legacy_passthrough_count"] == 102

    geometry = payload["runtime_geometry"]
    assert geometry == {
        "arena_start": "0x02293C60",
        "cache_end": f"0x{CACHE_ADDRESS + 64:08X}",
        "cache_size": 64,
        "cache_start": f"0x{CACHE_ADDRESS:08X}",
        "module_end": f"0x{MODULE_END:08X}",
        "module_size": SYSTEM2_MODULE_SIZE,
        "module_start": f"0x{MODULE_BASE:08X}",
    }
    assert payload["module_sha256"] == module.sha256
    assert payload["module_symbol_count"] == len(module.symbols) == 16
    assert payload["hook_count"] == len(module.hook_replacements) == 6

    semantics = payload["semantic_ids"]
    assert semantics["archetypes"] == _enum_map(GateArchetype)
    assert semantics["conditions"] == _enum_map(GateConditionId)
    assert semantics["effects"] == _enum_map(GateEffectId)
    assert semantics["targets"] == _enum_map(GateTargetMode)
    assert semantics["timing_phases"] == _enum_map(GateTimingPhase)


def test_entry_contract_freezes_juggernoid_and_scope_boundaries() -> None:
    payload = _load()
    records = load_milestone_6d_authoring_document(AUTHORING)
    juggernoid = records[18]

    assert juggernoid.card_id == 19
    assert payload["juggernoid_fixture"] == {
        "archetype": int(GateArchetype.COMEBACK),
        "attribute_modifiers": [0, 30, 0, 0, 0, 0],
        "battle_weights": [50, 30, 30, 30, 30, 30],
        "card_id": 19,
        "condition_id": int(GateConditionId.OWNER_BEHIND),
        "drawback_id": int(GateEffectId.NONE),
        "drawback_value": 0,
        "effect_id": int(GateEffectId.ADD_SIGNED_G),
        "effect_value": 40,
        "flat_bonus_g": 60,
        "percent_q8_8": 20,
        "preferred_type": 0,
        "target_mode": int(GateTargetMode.GATE_OWNER),
        "timing_phase": int(GateTimingPhase.PRE_GATE_CALCULATION),
    }

    assert juggernoid.archetype == payload["juggernoid_fixture"]["archetype"]
    assert list(juggernoid.attribute_modifiers) == payload["juggernoid_fixture"][
        "attribute_modifiers"
    ]
    assert list(juggernoid.battle_weights) == payload["juggernoid_fixture"][
        "battle_weights"
    ]

    assert payload["archetype_budget_bands"] == {
        "attribute": [90, 110],
        "chaos": [90, 120],
        "comeback": [85, 115],
        "control": [85, 110],
        "power": [90, 110],
        "risk": [85, 120],
        "skill": [90, 110],
    }
    assert payload["protected_core_g_ranges"] == [
        {"end_offset": "0x00023C1C", "start_offset": "0x00023C18"},
        {"end_offset": "0x00023CF8", "start_offset": "0x00023CB0"},
        {"end_offset": "0x00023D7C", "start_offset": "0x00023D78"},
    ]
    assert payload["deferred_semantics"] == [
        "ability_manipulation",
        "activation_limits",
        "ai_evaluation",
        "arena_id",
        "battle_history_penalties",
        "fatigue",
        "presentation",
        "save_changes",
        "secondary_live_effects",
    ]
