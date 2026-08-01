class BakuganDSError(Exception):
    """Base exception for expected tool failures."""


class ProfileError(BakuganDSError):
    """Raised when a ROM profile is malformed or incomplete."""


class UnsupportedRomError(BakuganDSError):
    """Raised when a ROM does not match the selected supported profile."""


class RomFormatError(BakuganDSError):
    """Raised when Nintendo DS structures are malformed."""


class BoundsError(RomFormatError):
    """Raised when a structure points outside the available ROM bytes."""
