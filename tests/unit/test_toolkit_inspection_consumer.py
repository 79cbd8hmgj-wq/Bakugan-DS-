from inspect import Parameter, signature

import nds_disassembly_toolkit.inspection as toolkit_inspection

import bakugan_ds.inspection as bakugan_inspection


def test_inspection_models_are_toolkit_owned() -> None:
    assert bakugan_inspection.LayoutMismatch is toolkit_inspection.LayoutMismatch
    assert bakugan_inspection.RomInspection is toolkit_inspection.RomInspection


def test_bakugan_inspect_rom_preserves_profile_required_contract() -> None:
    parameters = signature(bakugan_inspection.inspect_rom).parameters

    assert parameters["profile"].default is Parameter.empty
    assert parameters["require_supported"].default is Parameter.empty
