from __future__ import annotations

import struct

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.arm32 import (
    ArmProgram,
    Condition,
    DataOpcode,
    Register,
    align,
    branch_to,
    decode_branch_target,
    encode_branch,
    encode_bx,
    encode_data_processing_immediate,
    encode_data_processing_register,
    encode_halfword_transfer,
    encode_literal_load,
    encode_load_store,
    encode_mul,
    encode_pop,
    encode_push,
    label,
    literal,
    load_literal,
    word,
)

MODULE_BASE = 0x0228BC20
MODULE_SIZE = 0x8000


def test_encode_branch_to_module() -> None:
    instruction = encode_branch(
        source_address=0x0223D258,
        target_address=0x0228BC20,
        link=False,
        condition=Condition.AL,
    )
    assert decode_branch_target(0x0223D258, instruction) == 0x0228BC20


def test_exact_forward_backward_and_link_branch_words() -> None:
    assert encode_branch(0x1000, 0x1010) == 0xEA000002
    assert encode_branch(0x1000, 0x1010, link=True) == 0xEB000002
    assert encode_branch(0x1010, 0x1000) == 0xEAFFFFFA
    assert decode_branch_target(0x1010, 0xEAFFFFFA) == 0x1000


def test_branch_condition_and_bx_encodings() -> None:
    assert encode_branch(0x1000, 0x1010, condition=Condition.EQ) == 0x0A000002
    assert encode_bx(Register.LR) == 0xE12FFF1E


def test_branch_rejects_thumb_unaligned_and_out_of_range_targets() -> None:
    with pytest.raises(WorkspaceError, match="ARM aligned"):
        encode_branch(0x1001, 0x1010)
    with pytest.raises(WorkspaceError, match="ARM aligned"):
        encode_branch(0x1000, 0x1011)
    with pytest.raises(WorkspaceError, match="out of range"):
        encode_branch(0x00000000, 0x08000000)


def test_data_processing_exact_words() -> None:
    assert (
        encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1) == 0xE3A00001
    )
    assert (
        encode_data_processing_immediate(
            DataOpcode.ADD, rd=Register.R1, rn=Register.R2, immediate=4
        )
        == 0xE2821004
    )
    assert (
        encode_data_processing_immediate(
            DataOpcode.CMP,
            rn=Register.R3,
            immediate=6,
            set_flags=True,
        )
        == 0xE3530006
    )
    assert (
        encode_data_processing_register(
            DataOpcode.MOV,
            rd=Register.R4,
            rm=Register.R5,
            condition=Condition.NE,
        )
        == 0x11A04005
    )


def test_data_processing_rejects_unencodable_immediate() -> None:
    with pytest.raises(WorkspaceError, match="rotated immediate"):
        encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0x12345678)


def test_multiply_and_memory_transfer_exact_words() -> None:
    assert encode_mul(Register.R0, Register.R1, Register.R2) == 0xE0000291
    assert encode_load_store(Register.R0, Register.R1, offset=4, load=True) == 0xE5910004
    assert (
        encode_load_store(
            Register.R2,
            Register.R3,
            offset=-1,
            load=False,
            byte=True,
        )
        == 0xE5432001
    )
    assert encode_halfword_transfer(Register.R0, Register.R1, offset=2, load=True) == 0xE1D100B2
    assert encode_halfword_transfer(Register.R2, Register.R3, offset=4, load=False) == 0xE1C320B4


def test_stack_register_list_encodings() -> None:
    assert (
        encode_push((Register.R4, Register.R5, Register.R6, Register.R7, Register.LR)) == 0xE92D40F0
    )
    assert (
        encode_pop((Register.R4, Register.R5, Register.R6, Register.R7, Register.PC)) == 0xE8BD80F0
    )
    with pytest.raises(WorkspaceError, match="duplicate"):
        encode_push((Register.R4, Register.R4))
    with pytest.raises(WorkspaceError, match="nonempty"):
        encode_pop(())


def test_literal_load_encodes_positive_and_negative_pc_offsets() -> None:
    assert encode_literal_load(0x1000, 0x1010, Register.R0) == 0xE59F0008
    assert encode_literal_load(0x1010, 0x1000, Register.R1) == 0xE51F1018
    with pytest.raises(WorkspaceError, match="literal range"):
        encode_literal_load(0x1000, 0x3000, Register.R0)


def test_program_build_resolves_labels_literals_and_zero_padding() -> None:
    program = ArmProgram(
        (
            label("entry"),
            load_literal(Register.R0, "cache_address"),
            branch_to("done"),
            align(16),
            literal("cache_address", 0x02293C20),
            label("done"),
            word(encode_bx(Register.LR)),
        )
    )

    built = program.build(MODULE_BASE, MODULE_SIZE)

    assert len(built.image) == MODULE_SIZE
    assert built.symbols == {
        "entry": MODULE_BASE,
        "cache_address": MODULE_BASE + 0x10,
        "done": MODULE_BASE + 0x14,
    }
    assert struct.unpack_from("<I", built.image, 0)[0] == 0xE59F0008
    assert (
        decode_branch_target(MODULE_BASE + 4, struct.unpack_from("<I", built.image, 4)[0])
        == MODULE_BASE + 0x14
    )
    assert struct.unpack_from("<I", built.image, 0x10)[0] == 0x02293C20
    assert struct.unpack_from("<I", built.image, 0x14)[0] == 0xE12FFF1E
    assert built.image[0x18:] == b"\0" * (MODULE_SIZE - 0x18)
    assert [relocation.kind for relocation in built.relocations] == [
        "literal_load",
        "branch",
    ]


def test_program_build_rejects_duplicate_and_unresolved_symbols() -> None:
    duplicate = ArmProgram((label("same"), word(0), label("same")))
    with pytest.raises(WorkspaceError, match="duplicate symbol"):
        duplicate.build(MODULE_BASE, MODULE_SIZE)

    unresolved = ArmProgram((branch_to("missing"),))
    with pytest.raises(WorkspaceError, match="unresolved symbol"):
        unresolved.build(MODULE_BASE, MODULE_SIZE)


def test_program_build_rejects_literal_overflow_and_image_overflow() -> None:
    far_literal_items = [load_literal(Register.R0, "far")]
    far_literal_items.extend(word(0) for _ in range(1025))
    far_literal_items.append(literal("far", 1))
    with pytest.raises(WorkspaceError, match="literal range"):
        ArmProgram(tuple(far_literal_items)).build(MODULE_BASE, MODULE_SIZE)

    too_large = ArmProgram(tuple(word(0) for _ in range(MODULE_SIZE // 4 + 1)))
    with pytest.raises(WorkspaceError, match="image exceeds"):
        too_large.build(MODULE_BASE, MODULE_SIZE)


def test_program_requires_exact_module_size_and_zero_alignment_padding() -> None:
    with pytest.raises(WorkspaceError, match="0x8000"):
        ArmProgram((word(0),)).build(MODULE_BASE, 0x100)

    program = ArmProgram((word(0x11223344), align(16), word(0x55667788)))
    built = program.build(MODULE_BASE, MODULE_SIZE)
    assert built.image[4:16] == b"\0" * 12
    assert built.image[:4] == b"\x44\x33\x22\x11"


def test_shifted_register_data_processing_encodes_exact_arm_words() -> None:
    from bakugan_ds.gates.arm32 import (
        Condition,
        DataOpcode,
        Register,
        ShiftType,
        encode_data_processing_shifted_register,
    )

    assert (
        encode_data_processing_shifted_register(
            DataOpcode.MOV,
            rd=Register.R0,
            rm=Register.R0,
            shift_type=ShiftType.LSR,
            shift_amount=8,
        )
        == 0xE1A00420
    )
    assert (
        encode_data_processing_shifted_register(
            DataOpcode.MOV,
            rd=Register.R0,
            rm=Register.R0,
            shift_type=ShiftType.LSR,
            shift_amount=1,
            condition=Condition.HI,
        )
        == 0x81A000A0
    )
    assert (
        encode_data_processing_shifted_register(
            DataOpcode.ADD,
            rd=Register.R1,
            rn=Register.R1,
            rm=Register.R0,
            shift_type=ShiftType.LSL,
            shift_amount=2,
        )
        == 0xE0811100
    )
