from pathlib import Path

from nds_disassembly_toolkit.workspace.validate import (
    ValidatedWorkspace,
    WorkspaceChange,
    validate_workspace as _toolkit_validate_workspace,
)

from bakugan_ds.profile import RomProfile


def validate_workspace(
    source_rom: Path,
    profile: RomProfile,
    workspace: Path,
) -> ValidatedWorkspace:
    return _toolkit_validate_workspace(
        source_rom,
        workspace,
        profile=profile,
        require_supported=True,
    )


__all__ = ["ValidatedWorkspace", "WorkspaceChange", "validate_workspace"]
