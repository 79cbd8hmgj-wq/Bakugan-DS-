# Bakugan DS Modding Framework Design

## Status

Approved project direction: build a practical, reproducible modding and reverse-engineering framework for **Bakugan: Battle Brawlers (Nintendo DS, USA revision 0)**. The framework will prioritize gameplay data discovery and controlled binary patches over a full matching source decompilation.

## Reference ROM

The initial supported ROM is identified by all of the following values:

- Internal title: `BAKUGAN W`
- Game code: `B6RE`
- Maker code: `52`
- Revision: `0`
- ROM size: `134217728` bytes
- SHA-256: `7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b`

The repository must not contain the ROM, extracted copyrighted assets, or rebuilt ROM images. Users provide their own legally obtained ROM locally.

## Goals

1. Provide deterministic commands to inspect, extract, modify, and rebuild the supported ROM.
2. Preserve a clean original workspace and make every modification reproducible from source-controlled patches and configuration.
3. Produce a documented map of ARM9, ARM7, NitroFS, overlay tables, load addresses, compression state, and discovered gameplay structures.
4. Support two patch classes:
   - structured data replacement when the game stores editable tables or resources;
   - bounded ARM binary patches when gameplay logic is compiled into ARM9 or an overlay.
5. Locate and document the battle-engine paths responsible for G-Power scaling, evolution contribution, Gate Card bonuses, attributes, and battle-type selection.
6. Expose confirmed balance data through readable configuration only after its format and behavior are verified.
7. Keep the architecture suitable for later functional decompilation of selected battle-engine functions without requiring a full matching decompilation.

## Non-goals

The first project phase will not:

- attempt to reproduce the complete original source tree;
- require byte-matching C compilation;
- redesign AI, story content, graphics, or user interface;
- invent new battle mechanics before existing calculations are understood;
- publish copyrighted game data;
- support other regions or revisions without a separate verified ROM profile;
- treat guessed offsets or inferred structures as confirmed facts.

## Verified ROM Layout Baseline

The framework will encode and test the following verified header facts:

- ARM9 ROM offset: `0x00004000`
- ARM9 RAM address: `0x02000000`
- ARM9 size: `448192` bytes
- ARM7 ROM offset: `0x000D8A00`
- ARM7 RAM address: `0x02380000`
- ARM7 size: `160048` bytes
- File Name Table offset: `0x000FFD00`
- File Name Table size: `212348` bytes
- File Allocation Table offset: `0x00133A00`
- File Allocation Table size: `88040` bytes
- NitroFS file count: `11005`
- Directory count: `95`
- ARM9 overlay count: `9`
- ARM7 overlay count: `0`

All nine ARM9 overlays load at `0x0221A1C0`. Overlay 7 is the largest, with a declared decompressed RAM size of `467360` bytes, BSS size of `1600` bytes, and compressed payload size of `255740` bytes. It is the first high-priority executable region for battle-engine analysis, but its exact responsibilities remain hypotheses until call paths and runtime behavior are confirmed.

## Architecture

### 1. ROM profile and validation

A machine-readable ROM profile will hold immutable identity and layout expectations for the supported revision. Every command that reads or writes a ROM must validate the SHA-256 and header fields before proceeding. A mismatch must stop execution unless the command is explicitly inspection-only.

The profile will contain:

- ROM identity fields;
- executable offsets, RAM addresses, and sizes;
- FNT, FAT, and overlay-table locations;
- known compression state;
- expected file and directory counts;
- named analysis targets as they are confirmed.

### 2. Nintendo DS container reader

A focused Python package will parse:

- the NDS header;
- File Name Table directory records and path names;
- File Allocation Table file ranges;
- ARM9 overlay table entries;
- ARM9 and ARM7 executable regions.

The reader will expose typed records rather than passing raw dictionaries throughout the codebase. Parsing must reject out-of-range offsets, overlapping invalid ranges, malformed directory records, and file entries that extend beyond the ROM.

### 3. Compression layer

The project will implement or vendor audited support for the compression formats actually encountered in the ROM. Initial scope is:

- Nintendo LZ10 for NitroFS resources;
- BLZ-style backward compression used by compressed ARM overlays.

Compression and decompression must be tested independently. A decompressed file that is recompressed without modification must either reproduce the original bytes or be marked as semantically equivalent but non-identical. The rebuild system must never silently substitute a non-identical executable compression result where exact layout is required.

### 4. Workspace model

Extraction will create a local workspace outside source control:

```text
work/
├── original/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── overlays/
│   └── nitrofs/
├── modified/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── overlays/
│   └── nitrofs/
├── manifests/
│   ├── rom.json
│   ├── files.json
│   └── overlays.json
└── output/
    └── Bakugan-DS-modded.nds
```

`original/` is immutable after extraction. Modding commands operate on `modified/`. Manifests record file IDs, paths, offsets, sizes, compression state, hashes, overlay IDs, load addresses, and rebuild decisions.

### 5. Deterministic rebuild pipeline

The rebuild command will:

1. validate the original ROM profile;
2. validate the extracted workspace manifests;
3. apply declared patches to a fresh copy of original data;
4. recompress files or overlays only where required;
5. reconstruct FAT ranges and update affected header fields;
6. preserve alignment rules;
7. recalculate required Nintendo DS header checksums;
8. emit a rebuilt ROM and a build report containing input hash, patch set, changed regions, and output hash.

The first successful rebuild milestone is a no-op round trip that boots and behaves like the reference ROM. Byte identity is preferred but is not required for filesystem repacking if the output is functionally identical and the report explains every layout difference.

### 6. Patch model

Patches will be declarative and fail closed. Each patch will state:

- target ROM profile;
- target component and file or overlay ID;
- expected original bytes or expected original hash;
- replacement bytes or a named transformation;
- human-readable rationale;
- validation rules.

A patch must refuse to apply when expected bytes do not match. Raw offsets without an expected-byte guard are prohibited.

Patch categories:

- `file_replace`: replace a complete NitroFS file;
- `binary_replace`: replace a bounded byte sequence in ARM9, ARM7, or an overlay;
- `table_edit`: edit confirmed fixed-width records through a documented schema;
- `hook`: insert a bounded ARM/Thumb routine and redirect a confirmed call site or branch.

The initial framework will implement `file_replace` and guarded `binary_replace`. `table_edit` and `hook` will be added only after a real target requires them.

### 7. Reverse-engineering metadata

The repository will store analysis products rather than disassembler project binaries:

```text
analysis/
├── memory-map.yaml
├── overlays.yaml
├── symbols/
│   ├── arm9.sym
│   └── overlay_0007.sym
├── functions/
│   └── overlay_0007.md
└── scripts/
    └── export_disassembler_imports.py
```

Every named symbol will carry a confidence level:

- `confirmed`: behavior demonstrated by runtime observation or a controlled patch;
- `probable`: strong static evidence but not yet demonstrated;
- `candidate`: useful lead requiring validation.

Addresses must be expressed as both runtime addresses and component-relative offsets. Overlay symbols must state the overlay ID and load address so that overlapping overlay address spaces are not confused.

### 8. Runtime investigation workflow

Static analysis alone is insufficient for the first balance targets. The documented workflow will support emulator-assisted discovery:

1. record a visible G-Power value in a controlled battle state;
2. search RAM for matching 16-bit and 32-bit values;
3. alter one input at a time, such as level, evolution state, Gate Card, or attribute;
4. narrow candidate addresses;
5. place a write breakpoint on the live result;
6. identify the executing ARM9 or overlay code;
7. map the runtime instruction address back to the extracted binary;
8. trace callers and inputs;
9. verify the function with a reversible controlled patch;
10. document the function, data structure, and confidence evidence.

The repository will not encode emulator-specific instructions until the selected emulator and its debugger capabilities are known.

## Balance Research Targets

These are design targets supplied for the mod and are not claims about the original implementation.

### G-Power scaling

Desired outcome:

- late-game strength must not reduce to highest base G-Power plus strongest evolution;
- weaker Bakugan should remain viable through growth curves rather than inflated starting values.

Candidate implementation patterns to test are:

- linear growth;
- multiplication after base and level growth;
- per-level table plus evolution bonus.

Initial tuning concepts, to be used only after the implementation is confirmed:

- retain full early-level growth;
- reduce later-level contribution by approximately 30–50 percent;
- reduce an evolution multiplier by approximately 10–20 percent if one exists;
- replace part of multiplicative evolution scaling with a modest flat bonus;
- improve weaker Bakugan through growth rather than base-stat inflation.

### Attribute identity

Desired outcome: Pyrus, Aquos, Ventus, Subterra, Haos, and Darkus should affect decisions rather than function only as presentation categories.

The lowest-risk route is to identify existing attribute modifiers and tune them. A code hook that adds new passive rules is a later option only if no suitable table or existing mechanic is available. Exact attribute effects will be designed after card categories, battle outcomes, and existing modifiers are documented.

### Gate Card tuning

Desired outcomes:

- Gate bonuses should not become disproportionately strong or irrelevant as base G-Power changes;
- universally optimal Gate Cards should be less dominant;
- battle-type selection should not repeatedly produce one exploitable optimal minigame.

Investigation must distinguish:

- stored Gate Card values;
- attribute-specific Gate modifiers;
- stage or progression scaling;
- random battle-type selection tables;
- deterministic selection rules caused by card or field state.

An anti-repeat rule is out of scope until the existing probability and state model is confirmed.

## Data Flow

```text
User-owned ROM
    -> profile validation
    -> header/FNT/FAT/overlay parsing
    -> immutable original workspace
    -> patch manifest selection
    -> guarded transformations on fresh modified data
    -> compression and layout rebuild
    -> checksum update
    -> structural verification
    -> output ROM and build report
```

Reverse-engineering discoveries flow separately:

```text
Runtime observation + static analysis
    -> candidate symbol
    -> controlled verification patch
    -> confirmed symbol and structure documentation
    -> schema or guarded patch definition
    -> balance configuration
```

## Error Handling

All command-line failures will use concise messages and nonzero exit codes. The tools must distinguish at least:

- unsupported ROM;
- corrupted or truncated ROM;
- malformed FNT or FAT;
- unsupported compression;
- decompression failure;
- workspace manifest mismatch;
- stale patch expected-byte mismatch;
- output range or alignment failure;
- checksum verification failure.

No command may leave a partially rebuilt ROM at the final output path. Builds write to a temporary path and move into place only after validation succeeds.

## Testing Strategy

### Unit tests

- header parsing against the verified `B6RE` values;
- FNT traversal and directory count;
- FAT parsing and file count;
- overlay table parsing and overlay 7 metadata;
- bounds and malformed-input rejection;
- LZ10 round trips using synthetic fixtures;
- overlay decompression using a small repository-safe synthetic fixture;
- guarded patch success and expected-byte mismatch failure;
- checksum calculation using constructed headers.

### Integration tests

Integration tests will use a locally supplied ROM path through an environment variable and will be skipped when no ROM is present. They will verify:

- exact SHA-256 detection;
- extraction of all `11005` files;
- stable manifests across repeated extraction;
- no-op rebuild structural validity;
- successful reparse of the rebuilt ROM;
- unchanged extracted payload hashes after a no-op round trip, except where explicitly documented repacking behavior applies.

No copyrighted fixture larger than minimal synthetic test data may be committed.

### Emulator smoke tests

For milestone releases, a rebuilt ROM must:

- reach the title screen;
- load or start a save;
- enter a battle;
- complete a battle without an overlay load failure;
- return to the surrounding game state.

These checks are manual until a reliable emulator automation path is established.

## Repository Structure

```text
Bakugan-DS-/
├── README.md
├── pyproject.toml
├── config/
│   └── b6re_rev0.json
├── src/
│   └── bakugan_ds/
│       ├── cli.py
│       ├── errors.py
│       ├── profile.py
│       ├── nds/
│       │   ├── header.py
│       │   ├── fnt.py
│       │   ├── fat.py
│       │   ├── overlays.py
│       │   └── checksums.py
│       ├── compression/
│       │   ├── lz10.py
│       │   └── blz.py
│       ├── workspace/
│       │   ├── extract.py
│       │   ├── manifest.py
│       │   └── rebuild.py
│       └── patches/
│           ├── model.py
│           └── apply.py
├── patches/
├── analysis/
│   ├── memory-map.yaml
│   ├── overlays.yaml
│   ├── symbols/
│   ├── functions/
│   └── scripts/
├── docs/
│   ├── rom-map.md
│   ├── reverse-engineering-workflow.md
│   └── superpowers/
│       ├── specs/
│       └── plans/
└── tests/
    ├── fixtures/
    ├── unit/
    └── integration/
```

## Milestones

### Milestone 1: Foundation

- initialize the Python project and CLI;
- validate the reference ROM;
- parse header, FNT, FAT, and overlay table;
- emit inspection reports;
- establish unit and local-ROM integration tests.

### Milestone 2: Reproducible workspace

- extract executables, overlays, and NitroFS;
- create immutable original and mutable modified trees;
- generate stable manifests;
- implement compression support required by extraction.

### Milestone 3: Rebuild and guarded patches

- rebuild a no-op ROM;
- update FAT, alignment, and checksums;
- validate the output structurally;
- add guarded file and binary replacement patches;
- produce a machine-readable build report.

### Milestone 4: Battle-engine discovery

- generate disassembler import metadata for ARM9 and all overlays;
- document overlay 7 candidates;
- select an emulator/debugger workflow;
- locate and verify the live G-Power calculation;
- identify base, level, evolution, Gate, and attribute contributions where present.

### Milestone 5: First balance patch

- expose the confirmed G-Power data or function through a documented schema or guarded hook;
- implement one conservative balance model;
- validate early-, middle-, and late-game calculations;
- produce a distributable patch set without game assets or ROM data.

Gate Card and attribute changes begin only after the first G-Power patch proves the full analysis-to-build-to-emulator workflow.

## Success Criteria

The design is successful when a contributor can:

1. clone the repository;
2. point the CLI at the exact supported ROM;
3. inspect and extract it without proprietary tools;
4. rebuild a structurally valid ROM from a clean workspace;
5. apply a guarded source-controlled patch;
6. reproduce the same changed regions and output hash on the same tool version;
7. trace a documented runtime battle value to a confirmed executable function;
8. change that behavior through a reviewable patch rather than an undocumented hex edit.

## Key Risks and Controls

- **Incorrect executable assumptions:** require runtime verification and confidence labels.
- **Overlay address confusion:** always pair runtime address with overlay ID and relative offset.
- **Compression corruption:** test codecs independently and retain original compressed bytes for unchanged components.
- **Filesystem layout drift:** generate rebuild reports and reparse every output ROM.
- **Revision-specific patches:** hard-gate all writes on the exact ROM profile and expected bytes.
- **Project scope expansion:** complete the G-Power workflow before adding Gate, attributes, AI, or content changes.
- **Copyright contamination:** commit only code, documentation, schemas, symbols, hashes, and minimal synthetic fixtures.
