from __future__ import annotations

import pytest

from bakugan_ds.gates.conditions import GateConditionContext, evaluate_gate_condition
from bakugan_ds.gates.effects import GateEffectContext, apply_gate_effect, matches_gate_target
from bakugan_ds.gates.record import GateConditionId, GateEffectId, GateTargetMode
from bakugan_ds.gates.runtime_module import MODULE_BASE, build_milestone_6c_module
from tests.support.arm32_interpreter import ArmCpu, SparseMemory

_U32 = 0xFFFFFFFF


def _signed(value: int) -> int:
    value &= _U32
    return value if value < 0x80000000 else value - (1 << 32)


def _execute_helper(name: str, registers: tuple[int, int, int, int]) -> tuple[int, int]:
    module = build_milestone_6c_module()
    memory = SparseMemory()
    memory.map(MODULE_BASE, module.image)
    cpu = ArmCpu(memory)
    for index, value in enumerate(registers):
        cpu.registers[index] = value & _U32
    stop = 0x0BADF00C
    cpu.registers[14] = stop
    cpu.run(module.symbols[name].address, stop_addresses={stop})
    return cpu.registers[0], cpu.registers[1]


@pytest.mark.parametrize(
    ("condition", "owner", "opponent", "landing"),
    [
        (GateConditionId.NONE, 0, 0, None),
        (GateConditionId.OWNER_BEHIND, 0, 1, None),
        (GateConditionId.OWNER_BEHIND, 1, 1, None),
        (GateConditionId.OWNER_AHEAD, 2, 1, None),
        (GateConditionId.SCORE_TIED, 2, 2, None),
        (GateConditionId.OWNER_SCORE_ZERO, 0, 2, None),
        (GateConditionId.OWNER_AT_MATCH_POINT, 2, 0, None),
        (GateConditionId.OWNER_AT_MATCH_POINT, 3, 0, None),
        (GateConditionId.OPPONENT_AT_MATCH_POINT, 0, 2, None),
        (GateConditionId.LANDING_GATE_CARD_WON, 0, 0, 1),
        (GateConditionId.LANDING_GATE_CARD_WON, 0, 0, 2),
    ],
)
def test_emitted_condition_helper_matches_host(
    condition: GateConditionId,
    owner: int,
    opponent: int,
    landing: int | None,
) -> None:
    expected = evaluate_gate_condition(
        condition,
        GateConditionContext(owner, opponent, landing),
    )
    result, valid = _execute_helper(
        "g2_evaluate_condition",
        (int(condition), owner, opponent, 0xFFFFFFFF if landing is None else landing),
    )
    if condition is GateConditionId.LANDING_GATE_CARD_WON and landing is None:
        assert (result, valid) == (0, 0)
    else:
        assert (result, valid) == (int(expected), 1)


def test_emitted_condition_helper_rejects_unknown_id() -> None:
    assert _execute_helper("g2_evaluate_condition", (99, 0, 0, 0)) == (0, 0)


@pytest.mark.parametrize(
    ("target", "current", "owner"),
    [
        (GateTargetMode.CURRENT_COMBATANT, 0, 1),
        (GateTargetMode.GATE_OWNER, 1, 1),
        (GateTargetMode.GATE_OWNER, 0, 1),
        (GateTargetMode.GATE_NON_OWNER, 0, 1),
        (GateTargetMode.GATE_NON_OWNER, 1, 1),
    ],
)
def test_emitted_target_helper_matches_host(
    target: GateTargetMode,
    current: int,
    owner: int,
) -> None:
    expected = matches_gate_target(target, GateEffectContext(current, owner))
    assert _execute_helper("g2_matches_target", (int(target), current, owner, 0)) == (
        int(expected),
        1,
    )


def test_emitted_target_helper_rejects_unknown_id() -> None:
    assert _execute_helper("g2_matches_target", (99, 0, 1, 0)) == (0, 0)


@pytest.mark.parametrize(
    ("effect", "value", "current"),
    [
        (GateEffectId.NONE, 40, 100),
        (GateEffectId.ADD_SIGNED_G, 40, 100),
        (GateEffectId.ADD_SIGNED_G, -40, 100),
        (GateEffectId.SUBTRACT_MAGNITUDE_G, 40, 100),
        (GateEffectId.SUBTRACT_MAGNITUDE_G, -40, 100),
        (GateEffectId.ADD_SIGNED_G, 0x7FFF, -0x8000),
    ],
)
def test_emitted_effect_helper_matches_host(
    effect: GateEffectId,
    value: int,
    current: int,
) -> None:
    expected = apply_gate_effect(effect, value, current)
    result, valid = _execute_helper(
        "g2_apply_effect",
        (int(effect), value, current, 0),
    )
    assert (_signed(result), valid) == (expected, 1)


def test_emitted_effect_helper_rejects_unknown_id_and_overflow() -> None:
    assert _execute_helper("g2_apply_effect", (99, 1, 100, 0)) == (0, 0)
    assert _execute_helper(
        "g2_apply_effect",
        (int(GateEffectId.ADD_SIGNED_G), 1, 0x7FFFFFFF, 0),
    ) == (0, 0)
    assert _execute_helper(
        "g2_apply_effect",
        (int(GateEffectId.SUBTRACT_MAGNITUDE_G), 0x80000000, 0, 0),
    ) == (0, 0)
