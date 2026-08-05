from __future__ import annotations

import pytest

from bakugan_ds.gates.conditions import GateConditionContext, evaluate_gate_condition
from bakugan_ds.gates.effects import GateEffectContext, apply_gate_effect, matches_gate_target
from bakugan_ds.gates.record import GateConditionId, GateEffectId, GateTargetMode
from bakugan_ds.gates.runtime_module import MODULE_BASE
from bakugan_ds.gates.runtime_module_6d import build_milestone_6d_module
from tests.support.arm32_interpreter import ArmCpu, SparseMemory

_U32 = 0xFFFFFFFF


def _signed(value: int) -> int:
    value &= _U32
    return value if value < 0x80000000 else value - (1 << 32)


def _execute_helper(name: str, registers: tuple[int, int, int, int]) -> tuple[int, int]:
    module = build_milestone_6d_module()
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


def _source_core_for_compressed(value: int) -> int:
    if value <= 400:
        return value
    return (value - 200) * 2


def _signed16(value: int) -> int:
    value &= 0xFFFF
    return value if value < 0x8000 else value - 0x10000


def _execute_emitted_gate_case(
    record: object,
    *,
    compressed_core_g: int = 190,
    attribute_id: int = 0,
    current_participant: int = 0,
    owner_participant: int = 0,
    owner_score: int = 1,
    opposing_score: int = 1,
    landing_result: int | None = None,
) -> tuple[int, int, int]:
    from bakugan_ds.gates.loader import CACHE_ADDRESS, build_cache
    from bakugan_ds.gates.record import GateRecordV1

    assert isinstance(record, GateRecordV1)
    module = build_milestone_6d_module()
    memory = SparseMemory()
    memory.map(MODULE_BASE, module.image)
    memory.map(CACHE_ADDRESS, build_cache(record, arena_entry=0))

    global_config = 0x020D433C
    session = 0x0229FC80
    battle = 0x022E58E0
    participants = (0x022E24E0, 0x022E2640)
    memory.write32(global_config, session)
    memory.write8(global_config + 0x98, 0)
    memory.write16(battle + 0x04, record.card_id)
    memory.write8(battle + 0x06, owner_participant)
    if landing_result is not None:
        throw_controller = 0x022F1000
        memory.write32(session + 0x298, throw_controller)
        memory.write8(throw_controller + 0x1D2, landing_result)

    scores = [opposing_score, opposing_score]
    scores[owner_participant] = owner_score
    for index, participant in enumerate(participants):
        memory.write32(session + 0x0C + index * 4, participant)
        memory.write8(participant + 0xEE, scores[index])
        memory.write8(participant + 0xF2, index)

        descriptor = session + 0x7C + index * 20
        memory.write8(descriptor + 0x0E, 0)
        memory.write8(descriptor + 0x0F, index)
        memory.write8(session + 0x28D + index, index)

        source = participant + 0x0C
        memory.write16(source + 0x04, _source_core_for_compressed(compressed_core_g))
        memory.write16(source + 0x06, 0)
        memory.write8(source + 0x09, attribute_id)

        record_base = battle + index * 20
        memory.write8(record_base + 0x19, (index << 4) | attribute_id)
        memory.write16(record_base + 0x0C, compressed_core_g)
        memory.write16(record_base + 0x10, compressed_core_g)

    cpu = ArmCpu(memory)
    cpu.registers[4] = current_participant
    cpu.registers[5] = battle + current_participant * 20
    cpu.registers[6] = battle
    cpu.registers[13] = 0x027FF000

    def legacy_gate_lookup(machine: ArmCpu) -> None:
        machine.registers[0] = 10
        machine.registers[15] = machine.registers[14]

    cpu.external_calls[0x02065BF4] = legacy_gate_lookup
    cpu.run(
        module.symbols["g2_gate_bonus_hook"].address,
        stop_addresses={0x0223D278},
    )
    record_base = battle + current_participant * 20
    raw_bonus = memory.read16(record_base + 0x12)
    fallback_flag = cpu.registers[3]

    cpu.registers[1] = raw_bonus
    cpu.registers[2] = memory.read16(record_base + 0x0C)
    cpu.registers[5] = record_base
    cpu.run(
        module.symbols["g2_context_store_hook"].address,
        stop_addresses={0x0223D290},
    )
    return _signed16(raw_bonus), memory.read16(record_base + 0x0E), fallback_flag


def test_milestone_6d_module_preserves_milestone_6c_juggernoid_vectors() -> None:
    from bakugan_ds.gates.authoring import approved_juggernoid_record

    record = approved_juggernoid_record()
    assert _execute_emitted_gate_case(
        record,
        attribute_id=1,
        owner_score=0,
        opposing_score=1,
    ) == (144, 334, 1)
    assert _execute_emitted_gate_case(
        record,
        attribute_id=0,
        owner_score=1,
        opposing_score=1,
    ) == (74, 264, 1)


def test_emitted_generic_control_reward_and_drawback_match_host() -> None:
    from dataclasses import replace

    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.record import GateArchetype
    from bakugan_ds.gates.system2 import GateCalculationContext, calculate_gate_bonus

    record = replace(
        approved_juggernoid_record(),
        card_id=20,
        archetype=GateArchetype.CONTROL,
        flat_bonus_g=50,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        condition_id=GateConditionId.OWNER_AHEAD,
        effect_id=GateEffectId.ADD_SIGNED_G,
        effect_value=50,
        drawback_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
        drawback_value=25,
        target_mode=GateTargetMode.GATE_OWNER,
    )
    host = calculate_gate_bonus(
        record,
        GateCalculationContext(190, 0, 0, 0, 2, 1, 20),
    )
    emitted = _execute_emitted_gate_case(
        record,
        owner_score=2,
        opposing_score=1,
    )
    assert emitted == (host.effective_gate_bonus, host.target_total_g, 1)


def test_emitted_generic_non_owner_negative_components_match_host() -> None:
    from dataclasses import replace

    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.record import GateArchetype
    from bakugan_ds.gates.system2 import GateCalculationContext, calculate_gate_bonus

    record = replace(
        approved_juggernoid_record(),
        card_id=21,
        archetype=GateArchetype.CONTROL,
        flat_bonus_g=20,
        percent_q8_8=-16,
        attribute_modifiers=(-20, 0, 0, 0, 0, 0),
        condition_id=GateConditionId.NONE,
        effect_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
        effect_value=30,
        target_mode=GateTargetMode.GATE_NON_OWNER,
    )
    host = calculate_gate_bonus(
        record,
        GateCalculationContext(190, 0, 1, 0, 1, 1, 21),
    )
    emitted = _execute_emitted_gate_case(
        record,
        current_participant=1,
        owner_participant=0,
    )
    assert host.effective_gate_bonus == -41
    assert emitted == (host.effective_gate_bonus, host.target_total_g, 1)


def test_emitted_landing_condition_uses_confirmed_throw_result() -> None:
    from dataclasses import replace

    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.record import GateArchetype

    record = replace(
        approved_juggernoid_record(),
        card_id=22,
        archetype=GateArchetype.CONTROL,
        flat_bonus_g=60,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        condition_id=GateConditionId.LANDING_GATE_CARD_WON,
        target_mode=GateTargetMode.CURRENT_COMBATANT,
    )
    assert _execute_emitted_gate_case(record, landing_result=1) == (100, 290, 1)
    assert _execute_emitted_gate_case(record, landing_result=2) == (60, 250, 1)
    assert _execute_emitted_gate_case(record) == (100, 290, 0)


def test_milestone_6d_context_store_clamps_negative_total_to_zero() -> None:
    module = build_milestone_6d_module()
    memory = SparseMemory()
    memory.map(MODULE_BASE, module.image)
    record = 0x022E58E0
    cpu = ArmCpu(memory)
    cpu.registers[1] = (-250) & 0xFFFF
    cpu.registers[2] = 190
    cpu.registers[3] = 1
    cpu.registers[5] = record
    cpu.run(
        module.symbols["g2_context_store_hook"].address,
        stop_addresses={0x0223D290},
    )
    assert memory.read16(record + 0x0E) == 0


def test_milestone_6d_module_keeps_fixed_geometry_and_generic_symbols() -> None:
    from bakugan_ds.gates.loader import SYSTEM2_MODULE_SIZE

    module = build_milestone_6d_module()
    assert len(module.image) == SYSTEM2_MODULE_SIZE
    assert {
        "g2_evaluate_condition",
        "g2_matches_target",
        "g2_apply_effect",
    } <= module.symbols.keys()
