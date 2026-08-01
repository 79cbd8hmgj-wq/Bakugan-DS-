# Extracted Workspace Format

Milestone 2 converts the exact supported ROM into a deterministic local
workspace. The workspace is intentionally excluded from Git because it contains
copyrighted game data derived from the user's ROM.

## Directory roles

```text
workspace/
├── original/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── raw/
│   │   ├── overlays/overlay_000.bin ... overlay_008.bin
│   │   └── nitrofs/<original FNT path>
│   └── decoded/
│       ├── overlays/overlay_000.bin ... overlay_008.bin
│       └── nitrofs/<original FNT path>
├── modified/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── overlays/overlay_000.bin ... overlay_008.bin
│   └── nitrofs/<original FNT path>
└── manifests/
    ├── workspace.json
    ├── files.json
    └── overlays.json
```

`original/raw` preserves the exact bytes stored in the ROM. `original/decoded`
contains decompressed reference data. `modified` begins as a byte-identical copy
of the decoded reference data and is the only tree intended for editing.

The extractor removes write permission from `original` after a successful
transaction. These permission bits protect against accidental edits but are not
a security boundary.

## Compression representation

NitroFS files beginning with a valid LZ10 header are stored compressed under
`original/raw/nitrofs` and decompressed under both `original/decoded/nitrofs`
and `modified/nitrofs`. Other NitroFS files are copied unchanged.

Overlay FAT payloads remain compressed under `original/raw/overlays`. BLZ is
decoded backward into the overlay's declared RAM size for the decoded and
modified trees.

## Manifests

The manifests use format version `1` and are sorted by numeric file or overlay
ID. Each record includes raw and decoded sizes, SHA-256 hashes, compression
classification, and the original identity fields needed by later rebuild and
patch stages.

Two extractions from the same ROM and tool version must produce byte-identical
manifest files. Workspace paths and timestamps are deliberately omitted.

## Transaction rules

Extraction builds a complete staging directory beside the requested target.
The target name is installed only after all decoding and manifest validation
succeeds. Existing workspaces are refused unless `--force` is supplied. A
forced replacement preserves the old workspace until the new staging tree is
complete.
