# Overlay Analysis Handoff

## Overlay 7

Overlay 7 is the first candidate for battle-engine analysis. Its role is not
yet confirmed; the values below describe only its verified executable layout.

- Raw BLZ payload: `original/raw/overlays/overlay_007.bin`
- Decoded executable: `original/decoded/overlays/overlay_007.bin`
- Editable copy: `modified/overlays/overlay_007.bin`
- FAT file ID: `7`
- Load address: `0x02219440`
- Decoded executable size: `467360` bytes
- Executable end / BSS start: `0x0228B5E0`
- BSS size: `1600` bytes
- BSS end: `0x0228BC20`
- Raw SHA-256: `0078608585052efc0b90ab084af3856e0162871de2cc43e70218657a9e2b0e97`
- Decoded SHA-256: `82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1`

Import the decoded executable as little-endian ARM code with base address
`0x02219440`. Create an uninitialized BSS block at `0x0228B5E0` with length
`1600` bytes. Runtime addresses convert to component-relative offsets by
subtracting `0x02219440`.

## Overlapping overlay address spaces

All nine ARM9 overlays declare the same load address. They do not coexist as a
single static memory image. Use a separate program, separate overlay memory
space, or another overlay-aware mapping for each overlay. A runtime address is
not unique without the overlay ID.

## Confidence boundary

The load address, sizes, hashes, initializer ranges, and FAT mappings are
confirmed from the exact ROM and automated tests. Any function names, battle
responsibilities, tables, or call-path interpretations remain candidate or
probable until runtime evidence or a controlled patch confirms them.
