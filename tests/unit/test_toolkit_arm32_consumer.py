import nds_disassembly_toolkit.arm32 as toolkit_arm32

from bakugan_ds.gates.arm32 import (
    ARM_MODULE_SIZE,
    ArmProgram,
    ArmRelocation,
    BuiltArmProgram,
    Condition,
    DataOpcode,
    Register,
    ShiftType,
    encode_branch,
    encode_data_processing_immediate,
    encode_load_store,
)


def test_generic_arm32_types_and_encoders_are_toolkit_owned() -> None:
    assert Condition is toolkit_arm32.Condition
    assert Register is toolkit_arm32.Register
    assert ShiftType is toolkit_arm32.ShiftType
    assert DataOpcode is toolkit_arm32.DataOpcode
    assert ArmRelocation is toolkit_arm32.ArmRelocation
    assert BuiltArmProgram is toolkit_arm32.BuiltArmProgram
    assert encode_branch is toolkit_arm32.encode_branch
    assert encode_data_processing_immediate is toolkit_arm32.encode_data_processing_immediate
    assert encode_load_store is toolkit_arm32.encode_load_store


def test_bakugan_arm_program_keeps_fixed_module_policy() -> None:
    assert ArmProgram is not toolkit_arm32.ArmProgram
    assert issubclass(ArmProgram, toolkit_arm32.ArmProgram)
    assert ARM_MODULE_SIZE == 0x8000
