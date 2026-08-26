from nds_disassembly_toolkit import source_apply as toolkit_apply
from nds_disassembly_toolkit import source_patch as toolkit_patch

from bakugan_ds import source_apply as bakugan_apply
from bakugan_ds import source_patch as bakugan_patch


def test_source_patch_models_and_hook_encoder_are_owned_by_toolkit() -> None:
    assert bakugan_patch.SourceHook is toolkit_patch.SourceHook
    assert bakugan_patch.SourcePatchManifest is toolkit_patch.SourcePatchManifest
    assert bakugan_patch.SourceTarget is toolkit_patch.SourceTarget
    assert bakugan_patch.encode_hook is toolkit_patch.encode_hook


def test_source_patch_runtime_helpers_are_owned_by_toolkit() -> None:
    assert bakugan_apply.AppliedSourceHook is toolkit_apply.AppliedSourceHook
    assert bakugan_apply.SourcePatchReport is toolkit_apply.SourcePatchReport
    assert bakugan_apply.build_patched_runtime is toolkit_apply.build_patched_runtime
    assert bakugan_apply.encode_target_storage is toolkit_apply.encode_target_storage
