from pathlib import Path

from nds_disassembly_toolkit.source_patch import (
    SourceHook,
    SourcePatchManifest,
    SourceTarget,
    encode_hook,
    load_source_patch_manifest as _toolkit_load_source_patch_manifest,
    resolve_source_target as _toolkit_resolve_source_target,
)

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.profile import RomProfile

_B6RE_ARM9_REENCODE_PASSTHROUGH = 0x8000


def _validate_bakugan_source_policy(manifest: SourcePatchManifest) -> None:
    if manifest.profile_id is None:
        raise WorkspaceError("profile_id must be nonempty")
    if (
        manifest.profile_id == "b6re_rev0"
        and manifest.target == "arm9"
        and manifest.blz_passthrough_length != _B6RE_ARM9_REENCODE_PASSTHROUGH
    ):
        raise WorkspaceError(
            "B6RE ARM9 source patch manifest must declare "
            "blz_passthrough_length=32768"
        )


def load_source_patch_manifest(path: Path) -> SourcePatchManifest:
    manifest = _toolkit_load_source_patch_manifest(path)
    _validate_bakugan_source_policy(manifest)
    return manifest


def resolve_source_target(
    workspace: Path,
    manifest: SourcePatchManifest,
    profile: RomProfile,
) -> SourceTarget:
    _validate_bakugan_source_policy(manifest)
    return _toolkit_resolve_source_target(workspace, manifest, profile)


__all__ = [
    "SourceHook",
    "SourcePatchManifest",
    "SourceTarget",
    "encode_hook",
    "load_source_patch_manifest",
    "resolve_source_target",
]
