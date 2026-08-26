from pathlib import Path

from nds_disassembly_toolkit.inspection import (
    LayoutMismatch,
    RomInspection,
    inspect_rom as _toolkit_inspect_rom,
)

from bakugan_ds.profile import RomProfile


def inspect_rom(path: Path, profile: RomProfile, require_supported: bool) -> RomInspection:
    return _toolkit_inspect_rom(
        path,
        profile,
        require_supported=require_supported,
    )


__all__ = ["LayoutMismatch", "RomInspection", "inspect_rom"]
