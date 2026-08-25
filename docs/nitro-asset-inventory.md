# Nitro Asset Inventory

The asset inventory is a read-only companion to the ROM inspection and disassembly workflows. It identifies standard Nintendo Nitro asset formats after applying the repository's existing strict LZ10 decoder.

## Command

```bash
bakugan-ds assets inventory \
  "Bakugan - Battle Brawlers (USA) (En,Fr).nds" \
  --output build/assets.json
```

Use `--include-unknown` when the detailed JSON should also contain files whose format is not recognized by this scanner. Unknown files are always counted even when they are omitted from the detailed list.

`--allow-unsupported` has the same read-only meaning as the inspection command: it permits structural analysis of a ROM that does not match the selected exact profile. It does not make that ROM safe for patching.

## Evidence levels

### Signature evidence

The scanner decompresses LZ10-wrapped files before checking their first four decoded bytes. These formats are only identified when the decoded signature matches:

| Signature | Format |
| --- | --- |
| `BMD0` | NSBMD model |
| `BTX0` | NSBTX texture archive |
| `SDAT` | Nintendo DS sound archive |
| `NARC` | Nitro archive |
| `RGCN` | NCGR character/tile graphics |
| `RLCN` | NCLR palette |
| `RCSN` | NSCR screen map |
| `BCA0` | NSBCA animation |
| `BMA0` | NSBMA material animation |
| `BTP0` | NSBTP texture-pattern animation |
| `BTA0` | NSBTA texture-coordinate animation |
| `BVA0` | NSBVA visibility animation |

A signed file-name family such as `.nsbmd` that does not decode to the expected signature is reported as a signed mismatch rather than silently trusted.

### Extension evidence

Bakugan also contains raw Nintendo tile and palette payloads using:

- `.ntft` -> NTFT tile data;
- `.ntfp` -> NTFP palette data.

These raw payloads do not provide the same self-identifying four-byte signature. The inventory therefore labels them as `extension` evidence instead of promoting the name to signature-confirmed evidence.

### Unknown

Other files remain `unknown`. The command does not infer the meaning of Bakugan-specific `.bin`, `.mes`, `.cam`, `.ahx`, `.adx`, or other payloads merely from their names.

## Localized suffixes

The ROM contains localized suffix variants such as `.nsbmd_d`, `.nsbmd_f`, `.nsbtx_g`, and similar forms. The inventory keeps the literal suffix in each record while normalizing the expected family to NSBMD/NSBTX for signature comparison.

This matters for the exact reference count: counting only files whose literal suffix is `.nsbmd` or `.nsbtx` undercounts the actual signed model and texture assets.

## Exact B6RE reference

For the supported USA revision-0 B6RE ROM, the current exact-binary fixture is:

```text
FAT entries:               11,005
Named NitroFS files:       10,996
Recognized assets:          2,575
Unknown files:              8,421

NSBMD / BMD0:                 678
NSBTX / BTX0:                 587
NTFT:                         327
NTFP:                         982
SDAT:                           1

Recognized LZ10 files:      2,574
Recognized raw files:           1
Signed mismatches:              0
```

These numbers are regression evidence for the exact supported ROM, not generic Nintendo DS assumptions.

## Relationship to Tinke

Tinke was useful reference material for identifying the Nintendo Nitro formats relevant to Bakugan, especially BMD0/BTX0 and the NTFT/NTFP file families. The implementation in this repository is clean-room Python and does not vendor Tinke source.

The current inventory intentionally stops at classification. Parsing model geometry, texture metadata, palettes, or sound-bank internals should be added as separate evidence-backed format readers only when the project needs them.
