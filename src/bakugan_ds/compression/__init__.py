from nds_disassembly_toolkit.compression import (
    BlzFooter,
    compress_blz,
    compress_lz10,
    decompress_blz,
    decompress_blz_in_place,
    decompress_lz10,
    is_blz,
    is_lz10,
    lz10_declared_size,
    parse_blz_footer,
)

__all__ = [
    "BlzFooter",
    "compress_blz",
    "compress_lz10",
    "decompress_blz",
    "decompress_blz_in_place",
    "decompress_lz10",
    "is_blz",
    "is_lz10",
    "lz10_declared_size",
    "parse_blz_footer",
]
