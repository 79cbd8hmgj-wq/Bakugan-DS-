import nds_disassembly_toolkit.disassembly as toolkit_disassembly

import bakugan_ds.disassembly as bakugan_disassembly


def test_disassembly_api_is_toolkit_owned() -> None:
    names = (
        "ModuleParams",
        "find_module_params",
        "overlay_layout_report",
        "render_labelled_bytes",
        "build_objdump_command",
        "disassemble_binary",
        "unified_disassembly_diff",
    )

    for name in names:
        assert getattr(bakugan_disassembly, name) is getattr(toolkit_disassembly, name)


def test_disassembly_constants_match_toolkit() -> None:
    assert bakugan_disassembly.MODULE_PARAMS_MAGIC == toolkit_disassembly.MODULE_PARAMS_MAGIC
    assert bakugan_disassembly.MODULE_PARAMS_SIZE == toolkit_disassembly.MODULE_PARAMS_SIZE
    assert (
        bakugan_disassembly.MODULE_PARAMS_MAGIC_OFFSET
        == toolkit_disassembly.MODULE_PARAMS_MAGIC_OFFSET
    )
