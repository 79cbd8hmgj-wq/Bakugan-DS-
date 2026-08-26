from nds_disassembly_toolkit.arm32 import (
    ArmProgram as ToolkitArmProgram,
    ArmRelocation as ToolkitArmRelocation,
    BuiltArmProgram as ToolkitBuiltArmProgram,
    Condition as ToolkitCondition,
    DataOpcode as ToolkitDataOpcode,
    Register as ToolkitRegister,
    ShiftType as ToolkitShiftType,
    encode_branch as toolkit_encode_branch,
    encode_data_processing_immediate as toolkit_encode_data_processing_immediate,
    encode_load_store as toolkit_encode_load_store,
)

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
    assert Condition is ToolkitCondition
    assert Register is ToolkitRegister
    assert ShiftType is ToolkitShiftType
    assert DataOpcode is ToolkitDataOpcode
    assert ArmRelocation is ToolkitArmRelocation
    assert BuiltArmProgram is ToolkitBuiltArmProgram
    assert encode_branch is toolkit_encode_branch
    assert encode_data_processing_immediate is toolkit_encode_data_processing_immediate
    assert encode_load_store is toolkit_encode_load_store


def test_bakugan_arm_program_keeps_fixed_module_policy() -> None:
    assert ArmProgram is not ToolkitArmProgram
    assert issubclass(ArmProgram, ToolkitArmProgram)
    assert ARM_MODULE_SIZE == 0x8000
