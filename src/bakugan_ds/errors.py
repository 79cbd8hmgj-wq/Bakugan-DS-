from nds_disassembly_toolkit.errors import (
    BoundsError,
    NdsToolkitError,
    ProfileError,
    RomFormatError,
    UnsupportedRomError,
    WorkspaceError,
)

BakuganDSError = NdsToolkitError

__all__ = [
    "BakuganDSError",
    "BoundsError",
    "ProfileError",
    "RomFormatError",
    "UnsupportedRomError",
    "WorkspaceError",
]
