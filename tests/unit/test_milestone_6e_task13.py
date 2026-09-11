"""Structural tests for the Task 13 runtime scaffold.

These tests never touch a ROM or emulator - they only prove the scenario
objects are well-formed against the real nds-disassembly-toolkit
orchestration API, and that the sample-matrix selection is reproducible
from the approved roster metadata rather than an independently
hand-maintained list that could silently drift.

The `runtime` extra (nds-disassembly-toolkit) is optional, so this whole
module is skipped when it is not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

nds_disassembly_toolkit = pytest.importorskip("nds_disassembly_toolkit")

from bakugan_ds.gates import roster_metadata as rm  # noqa: E402
from bakugan_ds.runtime import milestone_6e_task13 as task13  # noqa: E402

_ROSTER_METADATA_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "gates" / "milestone-6e-roster-metadata.json"
)


def _roster() -> tuple[rm.GateRosterMetadataEntry, ...]:
    return rm.load_gate_roster_metadata(_ROSTER_METADATA_PATH)


def test_confirmed_breakpoints_are_distinct_and_within_overlay_or_arm9_range() -> None:
    breakpoints = {
        "TIMING_PRE_GATE": task13.TIMING_PRE_GATE,
        "TIMING_POST_GATE": task13.TIMING_POST_GATE,
        "TIMING_PRE_BATTLE_TYPE": task13.TIMING_PRE_BATTLE_TYPE,
        "TIMING_POST_BATTLE_TYPE": task13.TIMING_POST_BATTLE_TYPE,
        "TIMING_BATTLE_START": task13.TIMING_BATTLE_START,
        "TIMING_BATTLE_RESULT": task13.TIMING_BATTLE_RESULT,
        "TIMING_GATE_CAPTURE": task13.TIMING_GATE_CAPTURE,
        "TIMING_GATE_REMOVAL": task13.TIMING_GATE_REMOVAL,
        "TIMING_ROUND_RESET": task13.TIMING_ROUND_RESET,
        "TIMING_MATCH_RESET": task13.TIMING_MATCH_RESET,
    }
    assert len(set(breakpoints.values())) == len(breakpoints)
    for name, address in breakpoints.items():
        assert 0x02200000 <= address <= 0x0227FFFF, f"{name} outside overlay_0007's mapped range"
    assert 0x02000000 <= task13.LOOKUP_GATE_ATTRIBUTE_BONUS <= 0x023FFFFF


def test_gate_system2_cache_region_matches_runtime_contract() -> None:
    import json

    contract = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "analysis"
            / "gates"
            / "milestone-6e-runtime-contract.json"
        ).read_text(encoding="utf-8")
    )
    start, end = (int(value, 16) for value in contract["cache_range"])
    assert start == task13.GATE_SYSTEM2_CACHE_START
    assert end - start == task13.GATE_SYSTEM2_CACHE_LENGTH
    assert int(contract["module_base"], 16) == task13.MODULE_BASE
    assert contract["module_size"] == task13.MODULE_SIZE


def test_sample_matrix_card_ids_exist_in_the_approved_roster() -> None:
    by_id = {entry.card_id: entry for entry in _roster()}
    for case in task13.SAMPLE_MATRIX:
        assert case.card_id in by_id, f"card {case.card_id} is not in the approved roster"


def test_sample_matrix_covers_juggernoid() -> None:
    assert any(case.card_id == 19 for case in task13.SAMPLE_MATRIX)


def test_sample_matrix_covers_every_archetype() -> None:
    by_id = {entry.card_id: entry for entry in _roster()}
    covered = {by_id[case.card_id].archetype.name for case in task13.SAMPLE_MATRIX}
    all_archetypes = {entry.archetype.name for entry in _roster()}
    assert covered == all_archetypes


def test_sample_matrix_covers_a_landing_conditioned_gate() -> None:
    by_id = {entry.card_id: entry for entry in _roster()}
    assert any(
        "landing" in by_id[case.card_id].rule_summary.lower() for case in task13.SAMPLE_MATRIX
    )


def test_sample_matrix_covers_an_owner_and_a_non_owner_control_gate() -> None:
    by_id = {entry.card_id: entry for entry in _roster()}
    control_cases = [
        by_id[case.card_id]
        for case in task13.SAMPLE_MATRIX
        if by_id[case.card_id].archetype.name == "CONTROL"
    ]
    assert any("gate owner" in entry.rule_summary.lower() for entry in control_cases)
    assert any("non-owner" in entry.rule_summary.lower() for entry in control_cases)


def test_sample_matrix_covers_a_match_point_gate() -> None:
    by_id = {entry.card_id: entry for entry in _roster()}
    assert any(
        "match point" in by_id[case.card_id].rule_summary.lower() for case in task13.SAMPLE_MATRIX
    )


def test_sample_matrix_covers_a_high_risk_drawback_gate() -> None:
    by_id = {entry.card_id: entry for entry in _roster()}
    assert any(
        by_id[case.card_id].archetype.name == "RISK"
        and "drawback" in by_id[case.card_id].rule_summary.lower()
        for case in task13.SAMPLE_MATRIX
    )


def test_sample_matrix_checkpoint_names_are_unique() -> None:
    names = [case.checkpoint_name for case in task13.SAMPLE_MATRIX]
    assert len(names) == len(set(names))


def test_describe_required_checkpoints_has_one_entry_per_case() -> None:
    descriptions = task13.describe_required_checkpoints()
    assert len(descriptions) == len(task13.SAMPLE_MATRIX)
    for case in task13.SAMPLE_MATRIX:
        assert case.checkpoint_name in descriptions
        assert str(case.card_id) in descriptions[case.checkpoint_name]


def test_build_scenario_for_case_is_well_formed() -> None:
    from nds_disassembly_toolkit.analysis.orchestration import EmulatorKind
    from nds_disassembly_toolkit.analysis.orchestration.scenario import CaptureTraceStep
    from nds_disassembly_toolkit.analysis.runtime import RuntimeCpu

    case = task13.SAMPLE_MATRIX[0]
    scenario = task13.build_scenario_for_case(case)

    assert scenario.backend is EmulatorKind.DESMUME
    assert scenario.cpu is RuntimeCpu.ARM9
    assert scenario.checkpoint == case.checkpoint_name
    assert "debugger_arm9" in scenario.required_capabilities
    assert len(scenario.steps) > 0

    step_ids = [step.id for step in scenario.steps]
    assert len(step_ids) == len(set(step_ids))

    trace_steps = [step for step in scenario.steps if isinstance(step, CaptureTraceStep)]
    assert trace_steps, "scenario must exercise at least one confirmed breakpoint"
    break_addresses = {step.break_address for step in trace_steps}
    assert task13.TIMING_PRE_GATE in break_addresses
    assert task13.TIMING_POST_GATE in break_addresses
    for step in trace_steps:
        expected_region = (task13.GATE_SYSTEM2_CACHE_START, task13.GATE_SYSTEM2_CACHE_LENGTH)
        assert step.memory == (expected_region,)


def test_build_scenario_for_case_uses_the_cases_own_checkpoint() -> None:
    for case in task13.SAMPLE_MATRIX:
        scenario = task13.build_scenario_for_case(case)
        assert scenario.checkpoint == case.checkpoint_name
        assert case.checkpoint_name in scenario.name


def test_build_all_scenarios_has_one_entry_per_sample() -> None:
    scenarios = task13.build_all_scenarios()
    assert len(scenarios) == len(task13.SAMPLE_MATRIX)
    for case in task13.SAMPLE_MATRIX:
        assert case.checkpoint_name in scenarios
        assert scenarios[case.checkpoint_name].checkpoint == case.checkpoint_name
