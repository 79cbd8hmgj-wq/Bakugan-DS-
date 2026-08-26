from pathlib import Path

from nds_disassembly_toolkit.source_apply import (
    AppliedSourceHook,
    SourcePatchReport,
    apply_source_patch as _toolkit_apply_source_patch,
    build_patched_runtime,
    encode_target_storage,
)

from bakugan_ds.profile import RomProfile
from bakugan_ds.source_compile import SourceToolchain
from bakugan_ds.source_patch import load_source_patch_manifest


def apply_source_patch(
    workspace: Path,
    manifest_path: Path,
    profile: RomProfile,
    *,
    toolchain: SourceToolchain | None = None,
) -> SourcePatchReport:
    # Enforce Bakugan's profile-bound/B6RE manifest policy before delegating
    # compilation, target revalidation, mutation, rollback, and reporting.
    load_source_patch_manifest(manifest_path)
    return _toolkit_apply_source_patch(
        workspace,
        manifest_path,
        profile,
        toolchain=toolchain,
    )


__all__ = [
    "AppliedSourceHook",
    "SourcePatchReport",
    "apply_source_patch",
    "build_patched_runtime",
    "encode_target_storage",
]
