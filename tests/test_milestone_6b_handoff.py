from __future__ import annotations

import json
from pathlib import Path

REQUIREMENTS = Path("analysis/gates/milestone-6b-requirements.json")
READINESS = Path("analysis/gates/milestone-6c-readiness.json")
RUNTIME_CONTEXT = Path("docs/gate-card-system-2-runtime-context.md")
VERIFICATION = Path(
    "docs/superpowers/plans/2026-08-02-milestone-6b-verification.md"
)
README = Path("README.md")


def test_milestone_6c_readiness_is_generated_and_fail_closed() -> None:
    requirements = json.loads(REQUIREMENTS.read_text(encoding="utf-8"))
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))

    assert len(requirements["requirements"]) == 51
    assert readiness["ready_for_milestone_6c"] is True
    assert readiness["deferred"] == ["arena_id"]
    assert readiness["failures"] == []
    assert len(readiness["confirmed"]) == 50
    assert "arena_id" not in readiness["confirmed"]


def test_runtime_context_enumerates_every_requirement_and_timing_phase() -> None:
    requirements = json.loads(REQUIREMENTS.read_text(encoding="utf-8"))
    text = RUNTIME_CONTEXT.read_text(encoding="utf-8")

    for item in requirements["requirements"]:
        assert f"| `{item['name']}` |" in text
    for phase in (
        "pre_gate",
        "post_gate",
        "pre_battle_type",
        "post_battle_type",
        "battle_start",
        "ability_activation",
        "ability_resolution",
        "battle_result",
        "gate_capture",
        "gate_removal",
        "round_reset",
        "match_reset",
    ):
        assert f"`{phase}`" in text
    assert "`arena_id` is the only deferred field" in text
    assert "0x02293C20" in text
    assert "0x02293C60" in text


def test_verification_records_required_scenarios_and_rebuild_proof() -> None:
    text = VERIFICATION.read_text(encoding="utf-8")

    for scenario in (
        "Normal player battle",
        "AI path",
        "Tutorial/scripted path",
        "Ability used",
        "Ability unused",
        "Score/capture update",
        "Repeated round/Gate transition",
        "Landing outcomes",
        "Difficulty controls",
        "Valid trailer",
        "Malformed trailer",
        "Cache lifecycle",
    ):
        assert f"| {scenario} |" in text
    assert text.count(
        "7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b"
    ) >= 3
    assert "f95eda0d5a7b3d81e3c9bde6e26797b27f725059289c1454a74b24937283c991" in text
    assert "Reported changes:       0" in text


def test_readme_states_milestone_6b_has_no_live_effect() -> None:
    text = README.read_text(encoding="utf-8")

    assert "complete runtime-context contract" in text
    assert "Milestone 6B implements no live System 2.0 gameplay effect" in text
    assert "first experimental Gate remains a separately reviewed Milestone 6C" in text
