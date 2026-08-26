from pathlib import Path

from nds_disassembly_toolkit.patches.apply import (
    AppliedPatch,
    PatchApplicationReport,
    apply_patch_set as _toolkit_apply_patch_set,
)
from nds_disassembly_toolkit.workspace.manifest import load_workspace_manifest
from nds_disassembly_toolkit.workspace.model import WorkspaceLayout

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.patches.model import load_patch_set


def apply_patch_set(workspace: Path, patch_path: Path) -> PatchApplicationReport:
    layout = WorkspaceLayout.from_root(workspace)
    manifest = load_workspace_manifest(layout.manifests / "workspace.json")
    if manifest.profile_id is None:
        raise WorkspaceError("Bakugan workspace manifest is missing profile_id")

    patch_set = load_patch_set(patch_path)
    if patch_set.profile_id != manifest.profile_id:
        raise WorkspaceError(
            f"patch profile mismatch: expected {manifest.profile_id}, got {patch_set.profile_id}"
        )

    return _toolkit_apply_patch_set(workspace, patch_path)


__all__ = ["AppliedPatch", "PatchApplicationReport", "apply_patch_set"]
