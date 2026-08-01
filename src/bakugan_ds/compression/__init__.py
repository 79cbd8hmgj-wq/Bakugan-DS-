from bakugan_ds.compression.blz import BlzFooter, decompress_blz, is_blz, parse_blz_footer
from bakugan_ds.compression.lz10 import compress_lz10, decompress_lz10, is_lz10, lz10_declared_size

__all__ = [
    "BlzFooter",
    "compress_lz10",
    "decompress_blz",
    "decompress_lz10",
    "is_blz",
    "is_lz10",
    "lz10_declared_size",
    "parse_blz_footer",
]
