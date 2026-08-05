# Milestone 6C Comeback Gate Verification

## Scope

This document records deterministic build and runtime acceptance for the approved Gate Card System 2.0 Juggernoid prototype on profile `b6re_rev0`.

Only Gate ID `19` enables System 2.0 behavior. Every unrelated Gate remains a canonical legacy passthrough.

## Exact local inputs

```text
Reference ROM SHA-256:
7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b

Reference ROM size:
134217728 bytes

Reference decoded overlay 7 SHA-256:
82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1

Reference runtime-decoded ARM9 SHA-256:
7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e
```

These user-owned inputs remain local and are not committed.

## Install contract

```text
Generated G2DT trailer size:        4152 bytes
Generated G2DT trailer SHA-256:     c67d3bad47ad318ea782a938fc3412a6244509e96b0d2fb75e3bf8424c9fe72b
Installed carrier size:             6992 bytes
Installed carrier SHA-256:          6961673e91f0ced7afa299d371ba54d73b3e64ab75c79e14224e59c56003b634
Generated module size:              32768 bytes
Generated module SHA-256:           cb0d3734ba0dfba383313890c787f7307eacfa2da0f14d45396f06e090adc178
Expanded overlay 7 size:            501728 bytes
Expanded overlay 7 SHA-256:         78d8e5963673c77a14fb36548b269fb8ab9abca9968b40167494531196b11b96
Patched stored ARM9 size:            448192 bytes
Patched stored ARM9 SHA-256:         95494b52cb94c85f7209ddf00fd37b6289fdecd6ad855f7344132b3f840236f8
Patched ARM9 BLZ passthrough:        32768 bytes
Patched ARM9 in-place decode:        byte-identical to host decode
```

The runtime loader sequentially reads all 103 ordered records, recomputes reflected IEEE CRC32 over the complete 4,120-byte payload, compares it with the approved header CRC, validates the exact selected record, and clears the complete 64-byte cache on any failure. A regression control mutates an unrelated record while Gate 19 is selected; the exact emitted loader rejects the trailer and leaves all cache bytes zero.

Seven guarded changes are installed:

- Six overlay-7 branch hooks: cache load, Gate bonus, context store, battle-type selector, expanded-data lookup, and cache clear.
- One decoded ARM9 arena-low literal replacement at offset `0x6264`, changing the boundary from `0x0228BC20` to `0x02293C60`.

Overlay 7 declares:

```text
RAM size:     0x7A7E0
BSS size:     0x40
Flags:        0
Module:       0x0228BC20–0x02293C20
Cache:        0x02293C20–0x02293C60
Arena low:    0x02293C60
Arena high:   0x023E0000
```

## Deterministic rebuild proof

Two rebuilds from an unchanged installed workspace are byte-identical.

```text
Rebuilt ROM SHA-256:
d353b38f83d7c6790fefbcb50fb2583fa92f9a53d9601038f8743b3b730f1a41

Build report SHA-256:
b12900aadfc38a4499b455247fe42415ab8a84cbba2e48f6bd0ad67d821cc97f

ROM size:
134217728 bytes
```

The build report contains exactly three modified components:

| Kind | Identifier | Encoding |
|---|---|---|
| `arm9` | `arm9` | `raw` |
| `nitrofs_raw` | `font/mes_CardName.mes` | `raw-override` |
| `overlay` | `7` | `uncompressed-overlay` |

The exact rebuilt-ROM integration test confirms:

- 11,005 FAT entries remain present.
- 10,996 named FNT files retain identical ID/path mappings.
- All nine ARM9 overlay entries remain present.
- Only FAT file IDs `7` and `2762` change.
- Every other FAT payload is byte-identical to the reference ROM.
- Carrier file ID `2762` contains the original 2,840-byte stream followed by the exact 4,152-byte trailer.
- Gate ID `19` exactly matches the approved Juggernoid prototype.
- Unrelated Gates are canonical passthrough records.
- The expanded overlay contains the zero-backed original BSS and exact generated module.
- All six hook replacements match their generated branch bytes.
- The stored ARM9 remains exactly 448,192 bytes after deterministic runtime-safe BLZ re-encoding.

## Controlled runtime acceptance

The acceptance matrix separates three evidence methods:

1. Exact-profile extraction, installation, rebuilding, and binary inspection.
2. Execution of the exact generated ARM32 module in the repository interpreter.
3. A clean DeSmuME run of the same CRC-enabled rebuilt ROM.

The exact emitted-module controls prove the complete approved arithmetic and selector matrix. They are not represented as naturally occurring emulator matches.

The live rebuilt-ROM run confirms:

- title and menu entry;
- Battle Arena setup and live-play entry;
- Aquos selection and throw;
- normal Battle Arena exit without saving;
- completion of the built-in Battle tutorial through its supported skip path;
- return to the responsive Tutorial menu;
- generated module bytes present at `0x0228BC20`;
- all 64 cache bytes zero after completion.

Raw ROMs, screenshots, saves, states, selected memory, and debugger output remain local and uncommitted.

## Final verification

Fresh verification on the CRC-remediated source produced:

```text
Host repository suite:       541 passed, 39 expected environment-gated skips
Exact Milestone 6C controls: 8 passed
Python compilation:          passed
Whitespace validation:       passed
Prohibited committed files:  none
Tracked files over 5 MiB:    none
```

The previous synchronized source was checked remotely with Ruff and strict mypy before the final CRC correction. The final head's standard GitHub Actions run was awaiting platform approval rather than reporting a test failure; no Ruff or mypy result is claimed for that blocked run.

A repository-wide run with every historical reference-file integration variable enabled exceeded the ten-minute execution cap without reporting a failure. It is not counted as completed verification.

## Acceptance boundary

Milestone 6C includes the exact build, complete-payload CRC validation, emitted runtime behavior, live boot/battle compatibility, tutorial completion, normal return, cache-clear proof, and persistent-state scope controls.

Arena ID, full-roster conversion, reusable archetypes, power budgets, additional effects, fatigue, Ability interaction, AI evaluation, presentation, and save-format changes remain outside this milestone.
