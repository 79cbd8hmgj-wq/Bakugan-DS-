from bakugan_ds import __version__
from bakugan_ds.errors import BakuganDSError, BoundsError, RomFormatError


def test_package_exports_version() -> None:
    assert __version__ == "0.1.0"


def test_domain_errors_share_common_base() -> None:
    assert issubclass(BoundsError, RomFormatError)
    assert issubclass(RomFormatError, BakuganDSError)
