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

The repository provides exact-ROM inspection, deterministic extraction and
rebuilding, guarded patches, normalized runtime-analysis evidence for the
battle G-Power pipeline, and the reverse-engineering foundation for Gate Card
System 2.0.

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

Gate runtime integration tests also require a runtime-decompressed ARM9 image:

```bash
BAKUGAN_DS_ROM="/absolute/path/to/game.nds" \
BAKUGAN_DS_RUNTIME_ARM9="/absolute/path/to/runtime-arm9.bin" \
python -m pytest -m integration -v
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

## First gameplay balance patch

The [core G-Power compression patch](docs/core-g-compression.md) preserves core
G through 400 and halves only the excess above 400. It modifies the battle
constructor before mutable modifiers and Gate Card bonuses are added.

```bash
bakugan-ds patch work/bakugan patches/core-g-compression-400.json
bakugan-ds rebuild "/path/to/game.nds" work/bakugan output/Bakugan-Core-G-400.nds
```

## Gate Card System 2.0 foundation

Milestone 6A maps the original Gate table, card IDs, attribute order, activation
lifecycle, fixed battle-type selector, hook-safe context, expansion storage,
and guarded hook boundaries. It does **not** implement a System 2.0 gameplay
effect or rebalance any Gate Card.

Inspect the confirmed legacy table metadata without dumping the table:

```bash
bakugan-ds gate inspect work/bakugan \
  --runtime-arm9 work/runtime/arm9.bin \
  --metadata analysis/gates/legacy-table-metadata.json
```

Export the complete legacy table only to an ignored local report:

```bash
bakugan-ds gate export-legacy work/bakugan \
  work/reports/gates/legacy-table.json \
  --runtime-arm9 work/runtime/arm9.bin \
  --metadata analysis/gates/legacy-table-metadata.json
```

Write the confirmed hook-safe context and explicit exclusions:

```bash
bakugan-ds gate report-context work/bakugan \
  work/reports/gates/battle-context.json \
  --evidence analysis/gates/battle-context.json
```

See [the legacy Gate system documentation](docs/gate-card-legacy-system.md) and
[the System 2.0 roadmap](docs/gate-card-system-2-roadmap.md). The first
experimental System 2.0 Gate is deferred to a separately reviewed Milestone 6B.

## Build the runtime debugger

Milestone 4B requires a Linux x86_64 DeSmuME CLI with ARM9 GDB-stub support.
The manual, ROM-free GitHub Actions workflow and artifact handoff are documented
in [docs/desmume-debug-bundle.md](docs/desmume-debug-bundle.md).
