from nds_disassembly_toolkit.arm32 import (
    ArmItem,
    ArmProgram as ToolkitArmProgram,
    ArmRelocation,
    BuiltArmProgram,
    Condition,
    DataOpcode,
    Register,
    ShiftType,
    align,
    branch_to,
    decode_branch_target,
    encode_branch,
    encode_bx,
    encode_data_processing_immediate,
    encode_data_processing_register,
    encode_data_processing_shifted_register,
    encode_halfword_transfer,
    encode_literal_load,
    encode_load_store,
    encode_mul,
    encode_pop,
    encode_push,
    encode_rotated_immediate,
    label,
    literal,
    load_literal,
    word,
)

from bakugan_ds.errors import WorkspaceError

ARM_MODULE_SIZE = 0x8000


class ArmProgram(ToolkitArmProgram):
    def build(self, base_address: int, final_size: int) -> BuiltArmProgram:
        if final_size != ARM_MODULE_SIZE:
            raise WorkspaceError("ARM module final size must be exactly 0x8000")
        return super().build(base_address, final_size)


__all__ = [
    "ARM_MODULE_SIZE",
    "ArmItem",
    "ArmProgram",
    "ArmRelocation",
    "BuiltArmProgram",
    "Condition",
    "DataOpcode",
    "Register",
    "ShiftType",
    "align",
    "branch_to",
    "decode_branch_target",
    "encode_branch",
    "encode_bx",
    "encode_data_processing_immediate",
    "encode_data_processing_register",
    "encode_data_processing_shifted_register",
    "encode_halfword_transfer",
    "encode_literal_load",
    "encode_load_store",
    "encode_mul",
    "encode_pop",
    "encode_push",
    "encode_rotated_immediate",
    "label",
    "literal",
    "load_literal",
    "word",
]
