from bakugan_ds import errors as bakugan_errors
from bakugan_ds.compression import blz as bakugan_blz
from bakugan_ds.compression import lz10 as bakugan_lz10
from bakugan_ds.nds import fat as bakugan_fat
from bakugan_ds.nds import fnt as bakugan_fnt
from bakugan_ds.nds import header as bakugan_header
from bakugan_ds.nds import overlays as bakugan_overlays
from nds_disassembly_toolkit import errors as toolkit_errors
from nds_disassembly_toolkit.compression import blz as toolkit_blz
from nds_disassembly_toolkit.compression import lz10 as toolkit_lz10
from nds_disassembly_toolkit.nds import fat as toolkit_fat
from nds_disassembly_toolkit.nds import fnt as toolkit_fnt
from nds_disassembly_toolkit.nds import header as toolkit_header
from nds_disassembly_toolkit.nds import overlays as toolkit_overlays


def test_generic_error_hierarchy_is_owned_by_toolkit() -> None:
    assert bakugan_errors.BakuganDSError is toolkit_errors.NdsToolkitError
    assert bakugan_errors.ProfileError is toolkit_errors.ProfileError
    assert bakugan_errors.UnsupportedRomError is toolkit_errors.UnsupportedRomError
    assert bakugan_errors.RomFormatError is toolkit_errors.RomFormatError
    assert bakugan_errors.BoundsError is toolkit_errors.BoundsError
    assert bakugan_errors.WorkspaceError is toolkit_errors.WorkspaceError


def test_nds_parser_compatibility_modules_reexport_toolkit() -> None:
    assert bakugan_header.NdsHeader is toolkit_header.NdsHeader
    assert bakugan_header.SectionRange is toolkit_header.SectionRange
    assert bakugan_fat.FatEntry is toolkit_fat.FatEntry
    assert bakugan_fat.parse_fat is toolkit_fat.parse_fat
    assert bakugan_fnt.FntTree is toolkit_fnt.FntTree
    assert bakugan_fnt.parse_fnt is toolkit_fnt.parse_fnt
    assert bakugan_overlays.OverlayEntry is toolkit_overlays.OverlayEntry
    assert bakugan_overlays.parse_overlay_table is toolkit_overlays.parse_overlay_table


def test_compression_compatibility_modules_reexport_toolkit() -> None:
    assert bakugan_lz10.compress_lz10 is toolkit_lz10.compress_lz10
    assert bakugan_lz10.decompress_lz10 is toolkit_lz10.decompress_lz10
    assert bakugan_blz.compress_blz is toolkit_blz.compress_blz
    assert bakugan_blz.decompress_blz is toolkit_blz.decompress_blz
    assert bakugan_blz.decompress_blz_in_place is toolkit_blz.decompress_blz_in_place
