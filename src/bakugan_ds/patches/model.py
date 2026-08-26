from pathlib import Path

from nds_disassembly_toolkit.patches.model import (
    BinaryPatch,
    PatchSet,
    load_patch_set as _toolkit_load_patch_set,
)

from bakugan_ds.errors import WorkspaceError


def load_patch_set(path: Path) -> PatchSet:
    patch_set = _toolkit_load_patch_set(path)
    if patch_set.profile_id is None:
        raise WorkspaceError("Bakugan patch set is missing profile_id")
    return patch_set


__all__ = ["BinaryPatch", "PatchSet", "load_patch_set"]
