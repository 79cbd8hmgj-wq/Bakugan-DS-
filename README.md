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

Milestone 1 validates the supported ROM and parses its NDS header, FAT, FNT,
and overlay tables. Extraction, rebuilding, and gameplay patches follow in
later milestones.

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
