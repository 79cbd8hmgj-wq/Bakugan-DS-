from __future__ import annotations

from pathlib import Path

from bakugan_ds.gates.authoring import load_gate_roster_authoring_document
from bakugan_ds.gates.roster_analysis import (
    REFERENCE_ATTRIBUTES,
    REFERENCE_CORE_G,
    REFERENCE_LANDING_CASES,
    REFERENCE_SCORE_CASES,
    REFERENCE_TARGET_CASES,
)
from bakugan_ds.gates.runtime_module_6d import build_milestone_6d_module
from bakugan_ds.gates.selector import select_system2_battle_type
from bakugan_ds.gates.system2 import GateCalculationContext, calculate_gate_bonus
from tests.unit import test_gate_milestone_6d_runtime_module as runtime_harness

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
SEEDS = (0, 1, 0x12345678, 0xFFFFFFFFFFFFFFFF)


def _cases():
    for core_g in REFERENCE_CORE_G:
        for attribute_id in REFERENCE_ATTRIBUTES:
            for _target_name, current, owner in REFERENCE_TARGET_CASES:
                for _score_name, owner_score, opposing_score in REFERENCE_SCORE_CASES:
                    for _landing_name, landing_result in REFERENCE_LANDING_CASES:
                        yield (
                            core_g,
                            attribute_id,
                            current,
                            owner,
                            owner_score,
                            opposing_score,
                            landing_result,
                        )


def test_all_103_records_match_exact_emitted_arm_over_complete_matrix(monkeypatch) -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    module = build_milestone_6d_module()
    monkeypatch.setattr(runtime_harness, "build_milestone_6d_module", lambda: module)

    checked = 0
    for record in records:
        for (
            core_g,
            attribute_id,
            current,
            owner,
            owner_score,
            opposing_score,
            landing_result,
        ) in _cases():
            host = calculate_gate_bonus(
                record,
                GateCalculationContext(
                    compressed_core_g=core_g,
                    attribute_id=attribute_id,
                    current_participant=current,
                    owner_participant=owner,
                    owner_side_score=owner_score,
                    opposing_side_score=opposing_score,
                    gate_id=record.card_id,
                    landing_result=landing_result,
                ),
            )
            emitted = runtime_harness._execute_emitted_gate_case(
                record,
                compressed_core_g=core_g,
                attribute_id=attribute_id,
                current_participant=current,
                owner_participant=owner,
                owner_score=owner_score,
                opposing_score=opposing_score,
                landing_result=landing_result,
            )
            if host.effective_gate_bonus is None:
                assert emitted[2] == 0
            else:
                assert emitted == (
                    host.effective_gate_bonus,
                    host.target_total_g,
                    1,
                )
            checked += 1

    assert checked == 103 * 1080


def test_all_weight_vectors_match_host_selector_for_controlled_rng() -> None:
    records = load_gate_roster_authoring_document(AUTHORING)
    for record in records:
        for seed in SEEDS:
            selected = select_system2_battle_type(
                record,
                constructor_type=-1,
                scripted_override=None,
                rng_state=seed,
                legacy_type=2,
            )
            assert 0 <= selected.final_type < 6
            assert selected.weighted_result is not None
            assert selected.fallback_reason.value == "none"
