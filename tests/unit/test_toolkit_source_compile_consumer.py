from nds_disassembly_toolkit import source_compile as toolkit_compile

from bakugan_ds import source_compile as bakugan_compile


def test_source_compiler_is_owned_by_toolkit() -> None:
    assert bakugan_compile.CompiledSource is toolkit_compile.CompiledSource
    assert bakugan_compile.SourcePatchLike is toolkit_compile.SourcePatchLike
    assert bakugan_compile.SourceToolchain is toolkit_compile.SourceToolchain
    assert bakugan_compile.build_compile_command is toolkit_compile.build_compile_command
    assert bakugan_compile.build_link_command is toolkit_compile.build_link_command
    assert bakugan_compile.build_linker_script is toolkit_compile.build_linker_script
    assert bakugan_compile.compile_source_patch is toolkit_compile.compile_source_patch
    assert bakugan_compile.parse_nm_symbols is toolkit_compile.parse_nm_symbols
    assert bakugan_compile.run_command is toolkit_compile.run_command
