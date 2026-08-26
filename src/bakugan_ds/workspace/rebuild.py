from pathlib import Path

from nds_disassembly_toolkit.workspace.rebuild import (
    BuildChange,
    BuildReport,
    RebuildOptions,
    rebuild_rom as _toolkit_rebuild_rom,
)

from bakugan_ds.profile import RomProfile


def rebuild_rom(
    source_rom: Path,
    profile: RomProfile,
    workspace: Path,
    options: RebuildOptions,
) -> BuildReport:
    return _toolkit_rebuild_rom(
        source_rom,
        workspace,
        options,
        profile=profile,
        require_supported=True,
    )


__all__ = ["BuildChange", "BuildReport", "RebuildOptions", "rebuild_rom"]
