from pathlib import Path

from nds_disassembly_toolkit.workspace.extract import (
    ExtractionOptions,
    extract_workspace as _toolkit_extract_workspace,
)
from nds_disassembly_toolkit.workspace.manifest import WorkspaceManifest

from bakugan_ds.profile import RomProfile


def extract_workspace(
    rom_path: Path,
    profile: RomProfile,
    options: ExtractionOptions,
) -> WorkspaceManifest:
    return _toolkit_extract_workspace(
        rom_path,
        options,
        profile=profile,
        require_supported=True,
    )


__all__ = ["ExtractionOptions", "extract_workspace"]
