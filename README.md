# Bakugan DS

Reproducible inspection and modding tools for the USA revision 0 release of
**Bakugan: Battle Brawlers** on Nintendo DS.

## Legal boundary

This repository contains code, documentation, hashes, schemas, and minimal
synthetic test fixtures. It does not contain ROM images, extracted game assets,
or rebuilt game images. Users must provide their own legally obtained ROM.

## Supported ROM

- Internal title: `BAKUGAN W`
- Game code: `B6RE`
- Revision: `0`
- SHA-256: `7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b`

## Development setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
```

## Current scope

The framework validates, extracts, rebuilds, and guarded-patches the supported
ROM. Static and runtime analysis have confirmed the initial battle G-Power
record, Gate/attribute lookup, target-total arithmetic, and display animation.
Milestone 5 adds the first playable balance patch.

## Inspect a ROM

```bash
bakugan-ds inspect "/path/to/Bakugan - Battle Brawlers.nds"
```

Write a deterministic JSON report:

```bash
bakugan-ds inspect "/path/to/game.nds" --output reports/rom.json
```

Inspection rejects any ROM that does not exactly match the supported profile.
`--allow-unsupported` permits read-only structural inspection and clearly marks
the report as unsupported; it must never be used by future write commands.

## Reference-ROM integration test

The unit suite uses only synthetic fixtures. To test against the supported ROM
without copying it into the repository:

```bash
BAKUGAN_DS_ROM="/absolute/path/to/game.nds" python -m pytest -m integration -v
```

The ROM path and generated reports are ignored by Git.

## Extract an editable workspace

```bash
bakugan-ds extract "/path/to/game.nds" work/bakugan
```

Use `--force` to replace an existing workspace only after a complete new staging
workspace has been created successfully.

The extractor creates approximately 300 MB of local files for the supported
ROM. Exact compressed payloads remain under `original/raw`; decoded reference
files remain under read-only `original/decoded`; editable copies are written to
`modified`.

```text
workspace/
├── original/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── raw/{overlays,nitrofs}/
│   └── decoded/{overlays,nitrofs}/
├── modified/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── overlays/
│   └── nitrofs/
└── manifests/{workspace,files,overlays}.json
```

The `original` tree is made read-only after extraction. This permission is an
accidental-edit safeguard, not a security boundary.

## Rebuild a ROM

```bash
bakugan-ds rebuild "/path/to/game.nds" work/bakugan output/Bakugan-modded.nds
```

A workspace with no edits produces a byte-identical copy of the supported ROM.
Changed NitroFS resources originally stored as LZ10 are recompressed
deterministically. A changed overlay is stored uncompressed at its declared RAM
size, and its overlay-table compression flag and compressed-size field are
cleared. Use `--force` to replace an existing output and its `.build.json`
report.

## Apply guarded patches

```bash
bakugan-ds patch work/bakugan patches/example.json
```

Patch files describe fixed-length binary replacements against `arm9`, `arm7`,
`overlay:<id>`, or `nitrofs:<path>`. Every replacement includes the exact bytes
expected at the target offset. If any guard is stale, out of bounds, or targets
the wrong ROM profile, no patch target is written.

## First gameplay patch

`patches/gpower-progression-50.json` keeps each Bakugan form's level-1 base G
unchanged while reducing its additive level/progression contribution to 50%.
Apply it to a clean workspace before rebuilding:

```bash
bakugan-ds patch work/bakugan patches/gpower-progression-50.json
bakugan-ds rebuild "/path/to/game.nds" work/bakugan output/Bakugan-G50.nds
```

The exact instructions, expected roster effects, validation results, and current
limitations are documented in
[docs/gpower-rebalance.md](docs/gpower-rebalance.md).

## Build the runtime debugger

Milestone 4B requires a Linux x86_64 DeSmuME CLI with ARM9 GDB-stub support.
The manual, ROM-free GitHub Actions workflow and artifact handoff are documented
in [docs/desmume-debug-bundle.md](docs/desmume-debug-bundle.md).
