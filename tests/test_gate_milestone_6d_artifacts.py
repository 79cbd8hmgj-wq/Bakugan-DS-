from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bakugan_ds.gates.authoring import (
    build_milestone_6d_balance_report,
    load_milestone_6d_authoring_document,
)
from bakugan_ds.gates.runtime_module_6d import build_milestone_6d_module

BALANCE_CONTRACT = Path("analysis/gates/milestone-6d-balance-contract.json")
RUNTIME_CONTRACT = Path("analysis/gates/milestone-6d-runtime-contract.json")
AUTHORING = Path("config/gates/milestone-6d-system2-v1.json")


def _load(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    payload = json.loads(text)
    assert isinstance(payload, dict)
    return payload


def test_balance_contract_matches_authoring_and_frozen_ids() -> None:
    payload = _load(BALANCE_CONTRACT)
    records = load_milestone_6d_authoring_document(AUTHORING)
    report = build_milestone_6d_balance_report(records)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"

    assert payload["profile_id"] == "b6re_rev0"
    assert payload["record_count"] == 103
    assert payload["live_card_ids"] == [19]
    assert payload["legacy_passthrough_count"] == 102
    assert payload["balance_report_sha256"] == hashlib.sha256(encoded.encode()).hexdigest()
    assert payload["archetypes"] == {
        "attribute": 6,
        "chaos": 7,
        "comeback": 1,
        "control": 4,
        "legacy": 0,
        "power": 2,
        "risk": 5,
        "skill": 3,
    }
    assert payload["conditions"]["landing_gate_card_won"] == 7
    assert payload["effects"] == {
        "add_signed_g": 1,
        "none": 0,
        "subtract_magnitude_g": 2,
    }
    assert payload["targets"] == {
        "current_combatant": 0,
        "gate_non_owner": 2,
        "gate_owner": 1,
    }
    assert payload["juggernoid"]["net_budget"] == 91
    assert payload["juggernoid"]["battle_weights"] == [50, 30, 30, 30, 30, 30]
    assert payload["scope"]["full_roster_conversion"] == "Milestone 6E"
    assert payload["scope"]["arena_id"] == "deferred"


def test_runtime_contract_matches_exact_generated_module_and_build() -> None:
    payload = _load(RUNTIME_CONTRACT)
    module = build_milestone_6d_module()

    assert payload["module_sha256"] == module.sha256
    assert payload["module"] == {
        "base": "0x0228BC20",
        "cache_end": "0x02293C60",
        "cache_start": "0x02293C20",
        "end": "0x02293C20",
        "size": 32768,
    }
    assert payload["symbol_count"] == len(module.symbols) == 16
    assert payload["hook_count"] == len(module.hook_replacements) == 6
    assert set(payload["symbols"]) == set(module.symbols)
    for name, symbol in module.symbols.items():
        recorded = payload["symbols"][name]
        assert recorded["address"] == f"0x{symbol.address:08X}"
        assert recorded["size"] == symbol.size
        assert recorded["purpose"] == symbol.purpose

    build = payload["build"]
    assert build["trailer_sha256"] == (
        "c67d3bad47ad318ea782a938fc3412a6244509e96b0d2fb75e3bf8424c9fe72b"
    )
    assert build["rebuilt_rom_sha256"] == (
        "519edbd5f4e17db3513cff0451109036ad411b44f1f2fd8f8e635fb68d0ffc7c"
    )
    assert build["expanded_overlay_sha256"] == (
        "748574da0d20ceb99b4ea48f848cab62b1139e5c4398f9d95a29adbc6dce5121"
    )
    assert build["rom_size"] == 134_217_728
    assert build["guarded_change_count"] == 7
    assert build["deterministic_double_build"] is True
    assert payload["live_system2_gate_ids"] == [19]
    assert payload["helper_contract"]["unknown_ids"] == (
        "complete legacy calculation fallback"
    )
    assert "ability state" in payload["forbidden_writes"]
    assert "battle history" in payload["forbidden_writes"]

BALANCE_DOC = Path("docs/gate-card-system-2-balance-framework.md")
ROADMAP = Path("docs/gate-card-system-2-roadmap.md")
README = Path("README.md")
VERIFICATION = Path(
    "docs/superpowers/plans/2026-08-05-milestone-6d-verification.md"
)


def test_balance_framework_document_freezes_scope_and_geometry() -> None:
    text = BALANCE_DOC.read_text(encoding="utf-8")
    assert "Only Gate ID 19, Juggernoid, is live" in text
    assert "full roster is Milestone 6E" not in text  # exact wording is not required
    assert "Full-roster conversion remains Milestone 6E" in text
    for archetype in (
        "Comeback",
        "Power",
        "Skill",
        "Control",
        "Risk",
        "Attribute",
        "Chaos",
    ):
        assert archetype in text
    assert "0x0228BC20–0x02293C20" in text
    assert "0x02293C20–0x02293C60" in text
    assert "0x8000" in text
    assert "maximum probability at most `40%`" in text
    assert "Ability manipulation" in text
    assert "arena-dependent" in text
    assert "bakugan-ds gate validate-milestone-6d" in text
    assert "bakugan-ds gate report-milestone-6d" in text
    assert "bakugan-ds gate install-milestone-6d" in text


def test_roadmap_marks_6d_complete_and_defines_6e_entry_gate() -> None:
    text = ROADMAP.read_text(encoding="utf-8")
    assert "Milestone 6D — core balance framework — complete" in text
    assert "Only Gate ID `19`, Juggernoid, is live" in text
    assert "Entry requires merged Milestone 6D verification" in text
    assert "assign exactly one of the seven archetypes" in text
    assert "Milestone 6E must not silently add Ability effects" in text


def test_readme_and_verification_distinguish_live_and_emitted_proof() -> None:
    readme = README.read_text(encoding="utf-8")
    verification = VERIFICATION.read_text(encoding="utf-8")
    assert "Milestone 6D generalizes that prototype" in readme
    assert "Juggernoid as the only live System 2.0 Gate" in readme
    assert "31 naturally occurring emulator battles" in verification
    assert "controlled executions of the exact emitted module" in verification
    assert "remaining 102 records are canonical legacy passthroughs" in verification


def test_documentation_contains_no_prohibited_completion_claims() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in (BALANCE_DOC, ROADMAP, README)
    )
    prohibited = (
        "all 103 Gates are live",
        "full roster is converted",
        "Ability Card manipulation is implemented",
        "fatigue is implemented",
        "arena ID is confirmed for Milestone 6D",
    )
    assert all(claim not in combined for claim in prohibited)
