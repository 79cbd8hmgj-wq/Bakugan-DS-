# Milestone 4 Static Battle Analysis Plan

**Goal:** Produce reproducible static-analysis tools and evidence that narrow the
G-Power investigation to concrete code and data candidates, then define the
runtime experiment required to confirm the calculation.

## Scope split

### 4A — Static reconnaissance

- Import locally extracted Bakugan, Gate Card, and Ability Card reference tables.
- Extract battle-related ASCII strings from ARM9 and decoded overlay 7.
- Locate exact little-endian pointer references to those strings.
- Associate GP-effect references with nearby ARM function prologues.
- Search for exact scaled Gate Card bonus rows and cluster nearby matches.
- Generate deterministic JSON reports with component hashes.
- Provide Ghidra layout and symbol-import artifacts.
- Record confidence and evidence without claiming the central formula is found.

### 4B — Runtime confirmation

- Search emulator RAM for the live G-Power value.
- Break on writes and capture the responsible instruction and call chain.
- Isolate base, level, evolution, Gate, and attribute inputs.
- Promote candidates only after controlled runtime evidence.

Runtime confirmation is intentionally not fabricated in 4A; it requires a
debugger-capable emulator session.

## Tests

- ASCII extraction and pointer xrefs.
- ARM prologue and nearest-function detection.
- Reference CSV normalization and validation.
- Scaled numeric-row matching and proximity clustering.
- GP evidence aggregation into one symbol per function.
- Exact-ROM optional integration assertions for hashes, addresses, match counts,
  and the ARM9 gate-data cluster.
- Text checks for the committed Ghidra layout and symbol artifacts.
