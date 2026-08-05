from __future__ import annotations

import hashlib
import struct

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.arm32 import (
    Condition,
    DataOpcode,
    Register,
    ShiftType,
    encode_bx,
    encode_data_processing_immediate,
    encode_data_processing_register,
    encode_halfword_transfer,
    encode_load_store,
    encode_mul,
    encode_pop,
    encode_push,
)
from bakugan_ds.gates.history import WEIGHTED_SELECTOR_ADDRESS
from bakugan_ds.gates.loader import CACHE_ADDRESS, SYSTEM2_MODULE_SIZE
from bakugan_ds.gates.record import (
    GATE_RECORD_BATTLE_WEIGHTS_OFFSET,
    GateConditionId,
    GateEffectId,
    GateTargetMode,
)
from bakugan_ds.gates.runtime_module import (
    MODULE_BASE,
    RuntimeModule,
    RuntimeSymbol,
    _add_register,
    _branch,
    _build_clear_cache,
    _build_crc32_update,
    _build_load_selected_record,
    _build_validate_cache,
    _build_validate_selected_record,
    _compare_immediate,
    _compare_register,
    _emit_participant_pointer,
    _hook_replacements,
    _mov_register,
    _RoutineAssembler,
    _RoutineDefinition,
    _RoutineImage,
    _shift_register,
    _static_routine,
    _with_condition,
)
from bakugan_ds.gates.system2 import (
    CORE_G_COMPRESSION_BASE,
    CORE_G_COMPRESSION_THRESHOLD,
)

_MILESTONE_6D_OFFSETS = {
    "g2_clear_cache": 0x000,
    "g2_validate_cache": 0x040,
    "g2_crc32_update": 0x0A0,
    "g2_load_selected_record": 0x100,
    "g2_validate_selected_record": 0x500,
    "g2_legacy_gate_bonus": 0x700,
    "g2_calculate_gate_bonus": 0x740,
    "g2_gate_bonus_hook": 0xB40,
    "g2_context_store_hook": 0xB80,
    "g2_select_battle_type": 0xC00,
    "g2_selector_hook": 0xC80,
    "g2_loader_trampoline": 0xCC0,
    "g2_clear_hook": 0xD00,
    "g2_evaluate_condition": 0xE00,
    "g2_matches_target": 0xF00,
    "g2_apply_effect": 0xF80,
}


def _address_6d(name: str) -> int:
    return MODULE_BASE + _MILESTONE_6D_OFFSETS[name]


def _build_evaluate_condition_6d() -> _RoutineImage:
    """Return r0=result and r1=valid for a deterministic condition."""
    asm = _RoutineAssembler(_address_6d("g2_evaluate_condition"))
    asm.emit(_mov_register(Register.R12, Register.R0))
    asm.emit(_mov_register(Register.R0, Register.R1))

    for condition, label in (
        (GateConditionId.NONE, "condition_none"),
        (GateConditionId.OWNER_BEHIND, "condition_owner_behind"),
        (GateConditionId.OWNER_AHEAD, "condition_owner_ahead"),
        (GateConditionId.SCORE_TIED, "condition_score_tied"),
        (GateConditionId.OWNER_SCORE_ZERO, "condition_owner_zero"),
        (GateConditionId.OWNER_AT_MATCH_POINT, "condition_owner_match_point"),
        (GateConditionId.OPPONENT_AT_MATCH_POINT, "condition_opponent_match_point"),
        (GateConditionId.LANDING_GATE_CARD_WON, "condition_landing_won"),
    ):
        asm.emit(_compare_immediate(Register.R12, int(condition)))
        asm.branch(label, condition=Condition.EQ)
    asm.branch("invalid")

    asm.label("condition_none")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1))
    asm.branch("valid")

    asm.label("condition_owner_behind")
    asm.emit(_compare_register(Register.R0, Register.R2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.LO,
        )
    )
    asm.branch("valid")

    asm.label("condition_owner_ahead")
    asm.emit(_compare_register(Register.R0, Register.R2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.HI,
        )
    )
    asm.branch("valid")

    asm.label("condition_score_tied")
    asm.emit(_compare_register(Register.R0, Register.R2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("condition_owner_zero")
    asm.emit(_compare_immediate(Register.R0, 0))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("condition_owner_match_point")
    asm.emit(_compare_immediate(Register.R0, 2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("condition_opponent_match_point")
    asm.emit(_compare_immediate(Register.R2, 2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("condition_landing_won")
    asm.load_constant(Register.R1, "landing_unavailable", 0xFFFFFFFF)
    asm.emit(_compare_register(Register.R3, Register.R1))
    asm.branch("invalid", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R3, 1))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")

    asm.label("invalid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=0))
    asm.emit(encode_bx(Register.LR))
    asm.label("valid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=1))
    asm.emit(encode_bx(Register.LR))
    return asm.finish()


def _build_matches_target_6d() -> _RoutineImage:
    """Return r0=result and r1=valid for a current-combatant target predicate."""
    asm = _RoutineAssembler(_address_6d("g2_matches_target"))
    asm.emit(_mov_register(Register.R12, Register.R0))
    asm.emit(_mov_register(Register.R0, Register.R1))
    asm.emit(_compare_immediate(Register.R12, int(GateTargetMode.CURRENT_COMBATANT)))
    asm.branch("always", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R12, int(GateTargetMode.GATE_OWNER)))
    asm.branch("owner", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R12, int(GateTargetMode.GATE_NON_OWNER)))
    asm.branch("non_owner", condition=Condition.EQ)
    asm.branch("invalid")

    asm.label("always")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1))
    asm.branch("valid")
    asm.label("owner")
    asm.emit(_compare_register(Register.R0, Register.R2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.EQ,
        )
    )
    asm.branch("valid")
    asm.label("non_owner")
    asm.emit(_compare_register(Register.R0, Register.R2))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=1,
            condition=Condition.NE,
        )
    )
    asm.branch("valid")
    asm.label("invalid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=0))
    asm.emit(encode_bx(Register.LR))
    asm.label("valid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=1))
    asm.emit(encode_bx(Register.LR))
    return asm.finish()


def _build_apply_effect_6d() -> _RoutineImage:
    """Return r0=new signed value and r1=valid for one deterministic G effect."""
    asm = _RoutineAssembler(_address_6d("g2_apply_effect"))
    asm.emit(_mov_register(Register.R12, Register.R0))
    asm.emit(_compare_immediate(Register.R12, int(GateEffectId.NONE)))
    asm.branch("none", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R12, int(GateEffectId.ADD_SIGNED_G)))
    asm.branch("add", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R12, int(GateEffectId.SUBTRACT_MAGNITUDE_G)))
    asm.branch("subtract_magnitude", condition=Condition.EQ)
    asm.branch("invalid")

    asm.label("none")
    asm.emit(_mov_register(Register.R0, Register.R2))
    asm.branch("valid")

    asm.label("add")
    asm.emit(
        encode_data_processing_register(
            DataOpcode.ADD,
            rd=Register.R0,
            rn=Register.R2,
            rm=Register.R1,
            set_flags=True,
        )
    )
    asm.branch("invalid", condition=Condition.VS)
    asm.branch("valid")

    asm.label("subtract_magnitude")
    asm.load_constant(Register.R0, "i32_min", 0x80000000)
    asm.emit(_compare_register(Register.R1, Register.R0))
    asm.branch("invalid", condition=Condition.EQ)
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R3, immediate=0))
    asm.emit(_compare_immediate(Register.R1, 0))
    asm.emit(
        encode_data_processing_register(
            DataOpcode.SUB,
            rd=Register.R3,
            rn=Register.R3,
            rm=Register.R1,
            condition=Condition.MI,
        )
    )
    asm.emit(_with_condition(_mov_register(Register.R3, Register.R1), Condition.PL))
    asm.emit(
        encode_data_processing_register(
            DataOpcode.SUB,
            rd=Register.R0,
            rn=Register.R2,
            rm=Register.R3,
            set_flags=True,
        )
    )
    asm.branch("invalid", condition=Condition.VS)
    asm.branch("valid")

    asm.label("invalid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=0))
    asm.emit(encode_bx(Register.LR))
    asm.label("valid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=1))
    asm.emit(encode_bx(Register.LR))
    return asm.finish()


def _build_calculate_gate_bonus_6d() -> _RoutineImage:
    asm = _RoutineAssembler(_address_6d("g2_calculate_gate_bonus"))
    saved = (*tuple(Register(value) for value in range(4, 13)), Register.LR)
    asm.emit(encode_push(saved))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.SUB,
            rd=Register.SP,
            rn=Register.SP,
            immediate=32,
        )
    )
    asm.emit(encode_load_store(Register.R4, Register.SP, offset=0, load=False))

    asm.emit(encode_halfword_transfer(Register.R11, Register.R6, offset=4, load=True))
    asm.emit(_compare_immediate(Register.R11, 0))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R11, 104))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_mov_register(Register.R0, Register.R11))
    asm.branch(_address_6d("g2_validate_cache"), link=True)
    asm.emit(_compare_immediate(Register.R0, 1))
    asm.branch("fallback", condition=Condition.NE)

    asm.load_constant(Register.R7, "cache", CACHE_ADDRESS)
    asm.emit(encode_load_store(Register.R0, Register.R7, offset=1, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R0, 0))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R0, 8))
    asm.branch("fallback", condition=Condition.HS)
    for offset, upper_bound in ((21, 8), (22, 3), (23, 3), (30, 3)):
        asm.emit(encode_load_store(Register.R0, Register.R7, offset=offset, load=True, byte=True))
        asm.emit(_compare_immediate(Register.R0, upper_bound))
        asm.branch("fallback", condition=Condition.HS)
    for offset in (28, 29, 31, 34, 35):
        asm.emit(encode_load_store(Register.R0, Register.R7, offset=offset, load=True, byte=True))
        asm.emit(_compare_immediate(Register.R0, 0))
        asm.branch("fallback", condition=Condition.NE)
    for offset in (36, 38):
        asm.emit(encode_halfword_transfer(Register.R0, Register.R7, offset=offset, load=True))
        asm.emit(_compare_immediate(Register.R0, 0))
        asm.branch("fallback", condition=Condition.NE)

    asm.emit(encode_load_store(Register.R4, Register.R6, offset=6, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R4, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(encode_load_store(Register.R4, Register.SP, offset=20, load=False))

    asm.emit(encode_load_store(Register.R0, Register.R5, offset=0x19, load=True, byte=True))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.AND,
            rd=Register.R9,
            rn=Register.R0,
            immediate=0x0F,
        )
    )
    asm.emit(_compare_immediate(Register.R9, 6))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(encode_load_store(Register.R9, Register.SP, offset=8, load=False))
    asm.emit(_shift_register(Register.R8, Register.R0, ShiftType.LSR, 4))
    asm.emit(_compare_immediate(Register.R8, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(encode_load_store(Register.R8, Register.SP, offset=16, load=False))

    asm.load_constant(Register.R9, "global_config", 0x020D433C)
    asm.emit(encode_load_store(Register.R10, Register.R9, load=True))
    asm.emit(_compare_immediate(Register.R10, 0))
    asm.branch("fallback", condition=Condition.EQ)

    asm.emit(encode_load_store(Register.R11, Register.SP, offset=0, load=True))
    asm.emit(_compare_immediate(Register.R11, 2))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_compare_immediate(Register.R11, 0))
    asm.emit(
        encode_load_store(
            Register.R0,
            Register.R10,
            offset=0x28D,
            load=True,
            byte=True,
            condition=Condition.EQ,
        )
    )
    asm.emit(
        encode_load_store(
            Register.R0,
            Register.R10,
            offset=0x28E,
            load=True,
            byte=True,
            condition=Condition.NE,
        )
    )
    asm.emit(_compare_immediate(Register.R0, 26))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_shift_register(Register.R1, Register.R0, ShiftType.LSL, 2))
    asm.emit(_add_register(Register.R1, Register.R1, Register.R0))
    asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.LSL, 2))
    asm.emit(_add_register(Register.R12, Register.R10, Register.R1))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R12,
            rn=Register.R12,
            immediate=0x7C,
        )
    )
    asm.emit(encode_load_store(Register.R1, Register.R12, offset=0x0F, load=True, byte=True))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.AND,
            rd=Register.R1,
            rn=Register.R1,
            immediate=0x0F,
        )
    )
    asm.emit(_compare_register(Register.R1, Register.R8))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R0, Register.R12, offset=0x0E, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R0, 3))
    asm.branch("fallback", condition=Condition.HS)

    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R8,
        destination=Register.R1,
        scratch=Register.R2,
        failure_label="fallback",
    )
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R2, immediate=12))
    asm.emit(encode_mul(Register.R0, Register.R0, Register.R2))
    asm.emit(_add_register(Register.R12, Register.R1, Register.R0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R12,
            rn=Register.R12,
            immediate=12,
        )
    )
    asm.emit(encode_halfword_transfer(Register.R0, Register.R12, offset=4, load=True))
    asm.emit(_compare_immediate(Register.R0, CORE_G_COMPRESSION_THRESHOLD))
    asm.emit(
        _shift_register(
            Register.R0,
            Register.R0,
            ShiftType.LSR,
            1,
            condition=Condition.HI,
        )
    )
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R0,
            rn=Register.R0,
            immediate=CORE_G_COMPRESSION_BASE,
            condition=Condition.HI,
        )
    )
    asm.emit(encode_load_store(Register.R0, Register.SP, offset=4, load=False))

    asm.emit(encode_halfword_transfer(Register.R1, Register.R7, offset=4, load=True))
    asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.LSL, 16))
    asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.ASR, 16))
    asm.emit(encode_halfword_transfer(Register.R2, Register.R7, offset=6, load=True))
    asm.emit(_shift_register(Register.R2, Register.R2, ShiftType.LSL, 16))
    asm.emit(_shift_register(Register.R2, Register.R2, ShiftType.ASR, 16))
    asm.emit(encode_mul(Register.R3, Register.R0, Register.R2))
    asm.emit(_compare_immediate(Register.R3, 0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R3,
            rn=Register.R3,
            immediate=255,
            condition=Condition.MI,
        )
    )
    asm.emit(_shift_register(Register.R3, Register.R3, ShiftType.ASR, 8))
    asm.emit(encode_load_store(Register.R0, Register.SP, offset=8, load=True))
    asm.emit(_add_register(Register.R12, Register.R7, Register.R0))
    asm.emit(encode_load_store(Register.R0, Register.R12, offset=8, load=True, byte=True))
    asm.emit(_shift_register(Register.R0, Register.R0, ShiftType.LSL, 24))
    asm.emit(_shift_register(Register.R0, Register.R0, ShiftType.ASR, 24))
    asm.emit(_add_register(Register.R3, Register.R3, Register.R1))
    asm.emit(_add_register(Register.R3, Register.R3, Register.R0))
    asm.emit(encode_load_store(Register.R3, Register.SP, offset=12, load=False))

    asm.emit(encode_load_store(Register.R0, Register.R6, offset=0x19, load=True, byte=True))
    asm.emit(_shift_register(Register.R0, Register.R0, ShiftType.LSR, 4))
    asm.emit(_compare_immediate(Register.R0, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(encode_load_store(Register.R1, Register.R6, offset=0x2D, load=True, byte=True))
    asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.LSR, 4))
    asm.emit(_compare_immediate(Register.R1, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_compare_register(Register.R0, Register.R1))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(_compare_register(Register.R4, Register.R0))
    asm.emit(_with_condition(_mov_register(Register.R12, Register.R1), Condition.EQ))
    asm.branch("owner_resolved", condition=Condition.EQ)
    asm.emit(_compare_register(Register.R4, Register.R1))
    asm.emit(_with_condition(_mov_register(Register.R12, Register.R0), Condition.EQ))
    asm.branch("fallback", condition=Condition.NE)
    asm.label("owner_resolved")
    asm.emit(encode_load_store(Register.R12, Register.SP, offset=24, load=False))

    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R4,
        destination=Register.R1,
        scratch=Register.R11,
        failure_label="fallback",
    )
    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R12,
        destination=Register.R0,
        scratch=Register.R11,
        failure_label="fallback",
    )
    asm.emit(encode_load_store(Register.R2, Register.R1, offset=0xEE, load=True, byte=True))
    asm.emit(encode_load_store(Register.R3, Register.R0, offset=0xEE, load=True, byte=True))
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0x98, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R6, 0))
    asm.branch("scores_ready", condition=Condition.EQ)

    asm.emit(encode_load_store(Register.R11, Register.R1, offset=0xF2, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R11, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_compare_register(Register.R11, Register.R4))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(_compare_register(Register.R11, Register.R12))
    asm.branch("fallback", condition=Condition.EQ)
    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R11,
        destination=Register.R9,
        scratch=Register.R6,
        failure_label="fallback",
    )
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0xF2, load=True, byte=True))
    asm.emit(_compare_register(Register.R6, Register.R4))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0xEE, load=True, byte=True))
    asm.emit(_add_register(Register.R2, Register.R2, Register.R6))

    asm.emit(encode_load_store(Register.R11, Register.R0, offset=0xF2, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R11, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_compare_register(Register.R11, Register.R12))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(_compare_register(Register.R11, Register.R4))
    asm.branch("fallback", condition=Condition.EQ)
    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R11,
        destination=Register.R9,
        scratch=Register.R6,
        failure_label="fallback",
    )
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0xF2, load=True, byte=True))
    asm.emit(_compare_register(Register.R6, Register.R12))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0xEE, load=True, byte=True))
    asm.emit(_add_register(Register.R3, Register.R3, Register.R6))

    asm.label("scores_ready")
    asm.emit(encode_load_store(Register.R0, Register.R7, offset=21, load=True, byte=True))
    asm.emit(_mov_register(Register.R1, Register.R2))
    asm.emit(_mov_register(Register.R2, Register.R3))
    asm.load_constant(Register.R3, "landing_unavailable", 0xFFFFFFFF)
    asm.emit(_compare_immediate(Register.R0, int(GateConditionId.LANDING_GATE_CARD_WON)))
    asm.branch("condition_ready", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R3, Register.R10, offset=0x298, load=True))
    asm.emit(_compare_immediate(Register.R3, 0))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(encode_load_store(Register.R3, Register.R3, offset=0x1D2, load=True, byte=True))
    asm.label("condition_ready")
    asm.branch(_address_6d("g2_evaluate_condition"), link=True)
    asm.emit(_compare_immediate(Register.R1, 1))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(_mov_register(Register.R11, Register.R0))

    asm.emit(encode_load_store(Register.R0, Register.R7, offset=30, load=True, byte=True))
    asm.emit(encode_load_store(Register.R1, Register.SP, offset=16, load=True))
    asm.emit(encode_load_store(Register.R2, Register.SP, offset=20, load=True))
    asm.branch(_address_6d("g2_matches_target"), link=True)
    asm.emit(_compare_immediate(Register.R1, 1))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(_compare_immediate(Register.R11, 0))
    asm.branch("effects_complete", condition=Condition.EQ)
    asm.emit(_compare_immediate(Register.R0, 0))
    asm.branch("effects_complete", condition=Condition.EQ)

    for effect_offset, value_offset in ((22, 24), (23, 26)):
        asm.emit(
            encode_load_store(
                Register.R0,
                Register.R7,
                offset=effect_offset,
                load=True,
                byte=True,
            )
        )
        asm.emit(encode_halfword_transfer(Register.R1, Register.R7, offset=value_offset, load=True))
        asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.LSL, 16))
        asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.ASR, 16))
        asm.emit(encode_load_store(Register.R2, Register.SP, offset=12, load=True))
        asm.branch(_address_6d("g2_apply_effect"), link=True)
        asm.emit(_compare_immediate(Register.R1, 1))
        asm.branch("fallback", condition=Condition.NE)
        asm.emit(encode_load_store(Register.R0, Register.SP, offset=12, load=False))

    asm.label("effects_complete")
    asm.emit(encode_load_store(Register.R7, Register.SP, offset=12, load=True))
    asm.load_constant(Register.R0, "i16_max", 0x7FFF)
    asm.emit(_compare_register(Register.R7, Register.R0))
    asm.emit(_with_condition(_mov_register(Register.R7, Register.R0), Condition.GT))
    asm.load_constant(Register.R0, "i16_min", 0xFFFF8000)
    asm.emit(_compare_register(Register.R7, Register.R0))
    asm.emit(_with_condition(_mov_register(Register.R7, Register.R0), Condition.LT))
    asm.emit(encode_halfword_transfer(Register.R7, Register.R5, offset=0x12, load=False))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.SP,
            rn=Register.SP,
            immediate=32,
        )
    )
    asm.emit(encode_pop(saved))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R3, immediate=1))
    asm.branch(0x0223D278)

    asm.label("fallback")
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.SP,
            rn=Register.SP,
            immediate=32,
        )
    )
    asm.emit(encode_pop(saved))
    asm.branch(_address_6d("g2_legacy_gate_bonus"))
    return asm.finish()



def _build_context_store_hook_6d() -> _RoutineImage:
    asm = _RoutineAssembler(_address_6d("g2_context_store_hook"))
    asm.emit(_compare_immediate(Register.R3, 1))
    asm.branch("legacy", condition=Condition.NE)
    asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.LSL, 16))
    asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.ASR, 16))
    asm.emit(_add_register(Register.R0, Register.R2, Register.R1))
    asm.emit(_compare_immediate(Register.R0, 0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.MOV,
            rd=Register.R0,
            immediate=0,
            condition=Condition.LT,
        )
    )
    asm.load_constant(Register.R12, "u16_max", 0xFFFF)
    asm.emit(_compare_register(Register.R0, Register.R12))
    asm.emit(_with_condition(_mov_register(Register.R0, Register.R12), Condition.HI))
    asm.emit(encode_halfword_transfer(Register.R0, Register.R5, offset=0x0E, load=False))
    asm.branch(0x0223D290)
    asm.label("legacy")
    asm.emit(_add_register(Register.R0, Register.R2, Register.R1))
    asm.emit(encode_halfword_transfer(Register.R0, Register.R5, offset=0x0E, load=False))
    asm.branch(0x0223D290)
    return asm.finish()


def _build_select_battle_type_6d() -> _RoutineImage:
    asm = _RoutineAssembler(_address_6d("g2_select_battle_type"))
    asm.emit(encode_push((Register.R4, Register.LR)))
    asm.emit(_mov_register(Register.R4, Register.R0))
    asm.emit(encode_halfword_transfer(Register.R0, Register.R4, offset=4, load=True))
    asm.branch(_address_6d("g2_validate_cache"), link=True)
    asm.emit(_compare_immediate(Register.R0, 1))
    asm.branch("legacy", condition=Condition.NE)
    asm.load_constant(Register.R1, "cache", CACHE_ADDRESS)
    asm.emit(encode_load_store(Register.R2, Register.R1, offset=1, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R2, 0))
    asm.branch("legacy", condition=Condition.EQ)
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=6))
    asm.load_constant(
        Register.R1,
        "battle_weights",
        CACHE_ADDRESS + GATE_RECORD_BATTLE_WEIGHTS_OFFSET,
    )
    asm.branch(WEIGHTED_SELECTOR_ADDRESS, link=True)
    asm.emit(_compare_immediate(Register.R0, 5))
    asm.branch("done", condition=Condition.LS)
    asm.label("legacy")
    asm.emit(_mov_register(Register.R0, Register.R4))
    asm.branch(0x022433AC, link=True)
    asm.label("done")
    asm.emit(encode_pop((Register.R4, Register.PC)))
    return asm.finish()


def _build_loader_trampoline_6d() -> _RoutineImage:
    asm = _RoutineAssembler(_address_6d("g2_loader_trampoline"))
    asm.emit(0xE92D4008)
    extra = (
        Register.R0,
        Register.R1,
        Register.R2,
        *tuple(Register(value) for value in range(4, 13)),
    )
    asm.emit(encode_push(extra))
    asm.emit(encode_load_store(Register.R1, Register.R0, offset=0x38, load=True))
    asm.emit(encode_halfword_transfer(Register.R4, Register.R1, offset=4, load=True))
    asm.emit(_mov_register(Register.R0, Register.R4))
    asm.branch(_address_6d("g2_validate_cache"), link=True)
    asm.emit(_compare_immediate(Register.R0, 1))
    asm.branch("restore", condition=Condition.EQ)
    asm.emit(_mov_register(Register.R0, Register.R4))
    asm.branch(_address_6d("g2_load_selected_record") + 8, link=True)
    asm.label("restore")
    asm.emit(encode_pop(extra))
    asm.branch(0x022433B0)
    return asm.finish()


def _build_clear_hook_6d() -> _RoutineImage:
    asm = _RoutineAssembler(_address_6d("g2_clear_hook"))
    saved = (
        Register.R1,
        Register.R2,
        Register.R3,
        Register.R4,
        Register.R12,
        Register.LR,
    )
    asm.emit(encode_push(saved))
    asm.branch(_address_6d("g2_clear_cache"), link=True)
    asm.load_constant(Register.R12, "legacy_load_address", 0x02241B0C)
    asm.emit(encode_load_store(Register.R0, Register.R12, offset=0, load=True))
    asm.emit(
        encode_pop(
            (
                Register.R1,
                Register.R2,
                Register.R3,
                Register.R4,
                Register.R12,
                Register.PC,
            )
        )
    )
    return asm.finish()


def _milestone_6d_routine_definitions() -> tuple[_RoutineDefinition, ...]:
    legacy = _address_6d("g2_legacy_gate_bonus")
    return (
        _RoutineDefinition(
            "g2_clear_cache",
            _MILESTONE_6D_OFFSETS["g2_clear_cache"],
            _build_clear_cache(),
            "Clear exactly sixteen cache words and return.",
        ),
        _RoutineDefinition(
            "g2_validate_cache",
            _MILESTONE_6D_OFFSETS["g2_validate_cache"],
            _build_validate_cache(),
            "Validate cache flag, version, metadata ID, and record ID.",
        ),
        _RoutineDefinition(
            "g2_crc32_update",
            _MILESTONE_6D_OFFSETS["g2_crc32_update"],
            _build_crc32_update(),
            "Update a reflected IEEE CRC32 over a bounded byte buffer.",
        ),
        _RoutineDefinition(
            "g2_load_selected_record",
            _MILESTONE_6D_OFFSETS["g2_load_selected_record"],
            _build_load_selected_record(),
            (
                "Read all 103 ordered records, recompute payload CRC32, and stage "
                "the selected record through confirmed NitroFS calls."
            ),
        ),
        _RoutineDefinition(
            "g2_validate_selected_record",
            _MILESTONE_6D_OFFSETS["g2_validate_selected_record"],
            _build_validate_selected_record(),
            "Validate canonical passthrough bytes or the exact approved Gate 19 record.",
        ),
        _RoutineDefinition(
            "g2_legacy_gate_bonus",
            _MILESTONE_6D_OFFSETS["g2_legacy_gate_bonus"],
            _static_routine(
                legacy,
                (
                    0xE5D51019,
                    0xE1D600B4,
                    0xE1A01E01,
                    0xE1A01E21,
                    _branch(legacy + 16, 0x02065BF4, link=True),
                    0xE3A0100A,
                    0xE0010190,
                    0xE1C511B2,
                    0xE3A03000,
                    _branch(legacy + 36, 0x0223D278),
                ),
                (4, 9),
            ),
            "Relocated exact original Gate lookup, scale, and store block.",
        ),
        _RoutineDefinition(
            "g2_calculate_gate_bonus",
            _MILESTONE_6D_OFFSETS["g2_calculate_gate_bonus"],
            _build_calculate_gate_bonus_6d(),
            "Evaluate the selected version-1 Gate record through generic deterministic dispatch.",
        ),
        _RoutineDefinition(
            "g2_gate_bonus_hook",
            _MILESTONE_6D_OFFSETS["g2_gate_bonus_hook"],
            _static_routine(
                _address_6d("g2_gate_bonus_hook"),
                (
                    _branch(
                        _address_6d("g2_gate_bonus_hook"),
                        _address_6d("g2_calculate_gate_bonus"),
                    ),
                ),
                (0,),
            ),
            "Stable Gate hook entry routed through the Milestone 6D dispatcher.",
        ),
        _RoutineDefinition(
            "g2_context_store_hook",
            _MILESTONE_6D_OFFSETS["g2_context_store_hook"],
            _build_context_store_hook_6d(),
            "Clamp signed System 2.0 totals and replay the exact legacy add/store path.",
        ),
        _RoutineDefinition(
            "g2_select_battle_type",
            _MILESTONE_6D_OFFSETS["g2_select_battle_type"],
            _build_select_battle_type_6d(),
            "Use bounded cached weights for nonlegacy records and legacy metadata otherwise.",
        ),
        _RoutineDefinition(
            "g2_selector_hook",
            _MILESTONE_6D_OFFSETS["g2_selector_hook"],
            _static_routine(
                _address_6d("g2_selector_hook"),
                (
                    _branch(
                        _address_6d("g2_selector_hook"),
                        _address_6d("g2_select_battle_type"),
                    ),
                ),
                (0,),
            ),
            "Stable selector entry routed through bounded Milestone 6D weights.",
        ),
        _RoutineDefinition(
            "g2_loader_trampoline",
            _MILESTONE_6D_OFFSETS["g2_loader_trampoline"],
            _build_loader_trampoline_6d(),
            "Validate selected cache identity, reload on mismatch, then continue selector.",
        ),
        _RoutineDefinition(
            "g2_clear_hook",
            _MILESTONE_6D_OFFSETS["g2_clear_hook"],
            _build_clear_hook_6d(),
            "Clear cache, replay displaced result-path load, and return.",
        ),
        _RoutineDefinition(
            "g2_evaluate_condition",
            _MILESTONE_6D_OFFSETS["g2_evaluate_condition"],
            _build_evaluate_condition_6d(),
            "Evaluate one deterministic Gate condition and return result plus validity.",
        ),
        _RoutineDefinition(
            "g2_matches_target",
            _MILESTONE_6D_OFFSETS["g2_matches_target"],
            _build_matches_target_6d(),
            "Evaluate the current-combatant Gate target predicate.",
        ),
        _RoutineDefinition(
            "g2_apply_effect",
            _MILESTONE_6D_OFFSETS["g2_apply_effect"],
            _build_apply_effect_6d(),
            "Apply one checked signed Gate G effect and return validity.",
        ),
    )


def build_milestone_6d_module() -> RuntimeModule:
    image = bytearray(SYSTEM2_MODULE_SIZE)
    symbols: dict[str, RuntimeSymbol] = {}
    for definition in _milestone_6d_routine_definitions():
        address = MODULE_BASE + definition.offset
        data = struct.pack(f"<{len(definition.image.words)}I", *definition.image.words)
        end = definition.offset + len(data)
        if end > SYSTEM2_MODULE_SIZE:
            raise WorkspaceError(f"runtime routine {definition.name} exceeds module")
        if any(image[definition.offset:end]):
            raise WorkspaceError(f"runtime routine {definition.name} overlaps another")
        image[definition.offset:end] = data
        symbol = RuntimeSymbol(
            name=definition.name,
            address=address,
            size=len(data),
            code_size=definition.image.instruction_word_count * 4,
            branch_targets=definition.image.branch_targets,
            purpose=definition.purpose,
        )
        symbol.validate()
        symbols[definition.name] = symbol
    ordered_symbols = dict(sorted(symbols.items(), key=lambda item: item[1].address))
    module = RuntimeModule(
        image=bytes(image),
        symbols=ordered_symbols,
        hook_replacements=_hook_replacements(ordered_symbols),
        sha256=hashlib.sha256(image).hexdigest(),
    )
    module.validate()
    return module
