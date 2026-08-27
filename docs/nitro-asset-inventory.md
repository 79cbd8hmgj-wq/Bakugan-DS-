# B6RE Nitro Asset Inventory Addendum

Generic NitroFS asset detection, LZ10 decoding, signature/extension evidence, localized suffix handling, and JSON report structure are documented by the standalone [NDS Disassembly Toolkit asset guide](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit/blob/main/docs/assets.md).

This document records the Bakugan-specific policy and exact B6RE regression evidence.

## Bakugan command

```bash
bakugan-ds assets inventory \
  "Bakugan - Battle Brawlers (USA) (En,Fr).nds" \
  --output build/assets.json
```

Bakugan supplies its B6RE profile automatically. The command is read-only; its unsupported-ROM option follows the same explicit read-only policy as inspection and does not make an unsupported ROM safe for patching or rebuilding.

Use `--include-unknown` when unrecognized files should appear in the detailed report.

## Exact B6RE reference inventory

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

These counts are B6RE regression evidence, not assumptions about other Nintendo DS games.

## Bakugan-specific interpretation boundary

The generic toolkit recognizes standard Nintendo formats but does not infer semantics for Bakugan-specific `.bin`, `.mes`, `.cam`, `.ahx`, `.adx`, or other unknown payload families merely from filenames.

Likewise, the presence of a standard NSBMD/NSBTX/NTFT/NTFP asset establishes its container/format family, not its role in Bakugan gameplay or presentation. Any game-specific interpretation should be backed by Bakugan evidence and remain in this repository.

## Reference-material boundary

Tinke and other external Nintendo DS tools were useful reference material when identifying relevant standard Nitro formats. The implementation consumed by Bakugan is the clean-room Python implementation in `NDS-Disassembly-Toolkit`; no Tinke implementation is vendored into this repository.
