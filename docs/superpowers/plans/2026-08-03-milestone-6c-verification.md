# Milestone 6C Comeback Gate Verification

## Scope

This document records the deterministic build proof for the approved Gate Card System 2.0 Juggernoid prototype on profile `b6re_rev0`. Runtime gameplay acceptance is recorded separately by Task 13.

The build enables only Gate ID `19`. Gate IDs `20`, `22`, and every other unrelated Gate remain canonical legacy passthrough records.

## Local inputs

```text
Reference ROM SHA-256:
7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b

Reference ROM size:
134217728 bytes

Reference decoded overlay 7 SHA-256:
82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1

Reference decoded ARM9 SHA-256:
7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e
```

These user-owned inputs remain local and are not committed.

## Commands

```bash
export BAKUGAN_DS_ROM='/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds'
export BAKUGAN_DS_OVERLAY7='/path/to/overlay_007.bin'
export BAKUGAN_DS_RUNTIME_ARM9='/path/to/runtime-decoded-arm9.bin'

PYTHONPATH=src python -m pytest \
  tests/integration/test_gate_milestone_6c_build.py \
  tests/integration/test_gate_milestone_6c_reference.py -v
```

Without the user-owned inputs, the exact-ROM cases skip rather than weakening their identity guards. Host arithmetic, malformed-data, authoring, module, installer, and artifact tests still run normally.

## Install contract

The installer requires the already-approved core-G compression patch and then generates all Milestone 6C binary products locally.

```text
Generated G2DT trailer size:        4152 bytes
Generated G2DT trailer SHA-256:     c67d3bad47ad318ea782a938fc3412a6244509e96b0d2fb75e3bf8424c9fe72b
Installed carrier size:             6992 bytes
Installed carrier SHA-256:          6961673e91f0ced7afa299d371ba54d73b3e64ab75c79e14224e59c56003b634
Generated module size:              32768 bytes
Generated module SHA-256:           ed4c0f5c1779eed6028d9b5e525fa94581c68664f5e98419747f74ffacb843f2
Expanded overlay 7 size:            501728 bytes
Expanded overlay 7 SHA-256:         5a19d4dd58d7d26c46c90d1890636f29a54209ca6c54a136c20cc5800ae39f8e
Patched stored ARM9 size:            448192 bytes
Patched stored ARM9 SHA-256:         95494b52cb94c85f7209ddf00fd37b6289fdecd6ad855f7344132b3f840236f8
Patched ARM9 BLZ passthrough:        32768 bytes
Patched ARM9 BLZ header length:      193 bytes
Patched ARM9 in-place decode:        byte-identical to host decode
```

Seven guarded changes are installed:

- Six overlay-7 branch hooks: cache load, Gate bonus, context store, battle-type selector, expanded-data lookup, and cache clear.
- One decoded ARM9 arena-low literal replacement at offset `0x6264` from `0x0228BC20` to `0x02293C60`.

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

The original `0x640` overlay BSS is materialized as zero-backed payload bytes before the generated module. The three protected core-G replacement regions remain exact.

## Deterministic rebuild proof

Two rebuilds from the unchanged installed workspace produced byte-identical ROMs and byte-identical reports.

```text
Rebuilt ROM A SHA-256:
78f9ac00bbfd1eed86ee2977016af3395198158bb25c12cef82eb55ac14eeceb

Rebuilt ROM B SHA-256:
78f9ac00bbfd1eed86ee2977016af3395198158bb25c12cef82eb55ac14eeceb

Build report A SHA-256:
858491ec0792d63ebdee1a1df8df107230dcfc9fe8dd30b10bc7aa198e68de63

Build report B SHA-256:
858491ec0792d63ebdee1a1df8df107230dcfc9fe8dd30b10bc7aa198e68de63

ROM size:
134217728 bytes
```

The build report contains exactly three modified components:

| Kind | Identifier | Encoding |
|---|---|---|
| `arm9` | `arm9` | `raw` |
| `nitrofs_raw` | `font/mes_CardName.mes` | `raw-override` |
| `overlay` | `7` | `uncompressed-overlay` |

## Regression matrix

The exact rebuilt-ROM integration test confirms:

- 11,005 FAT entries remain present.
- 10,996 named FNT files retain identical ID/path mappings.
- All nine ARM9 overlay entries remain present.
- Only FAT file IDs `7` and `2762` change.
- Every other FAT payload is byte-identical to the reference ROM.
- Carrier file ID `2762` contains the exact original 2,840-byte LZ10 stream followed by the exact 4,152-byte trailer.
- The trailer parses as one 32-byte header and 103 ordered 40-byte records.
- Gate ID `19` exactly matches the approved Juggernoid prototype.
- Gate IDs `20` and `22` are canonical passthrough records.
- The expanded overlay contains the exact zero-backed original BSS and exact generated module.
- All six hook replacements match their generated branch bytes.
- The decoded ARM9 differs from the reference only at bytes `0x6264–0x6267`; three byte values change because one byte is shared by both little-endian constants.
- The stored ARM9 remains exactly 448,192 bytes after deterministic BLZ re-encoding.

## Legacy samples

The confirmed unrelated Gate samples retain these legacy rows:

| Gate | Attribute raw values | Displayed bonuses | Fixed battle type |
|---|---|---|---|
| Robotallion, ID 20 | `16, 11, 9, 12, 9, 4` | `160, 110, 90, 120, 90, 40` | Scratch, ID `0` |
| Serpenoid, ID 22 | `18, 6, 9, 14, 13, 5` | `180, 60, 90, 140, 130, 50` | Scratch, ID `0` |

Their System 2.0 records never calculate a hybrid bonus or consume weighted RNG.

## Fail-closed controls

Host and runtime-model tests reject or fall back on:

- Invalid trailer magic.
- Invalid header CRC.
- Selected cache card-ID mismatch.
- Nonzero reserved cache metadata.
- Unsupported prototype archetype or enum values.
- Nonzero deferred activation or fatigue values.
- Invalid live participant, attribute, score, and team context.
- Invalid or zero-total battle weights.

Record-level failures return complete legacy Gate behavior. Weighted-selector-only failures use phase-local fixed-metadata fallback.

## Core-G compatibility

The original bounded curve remains:

```text
core <= 400: unchanged
core > 400:  200 + floor(core / 2)
```

Verified controls include `190 → 190`, `400 → 400`, `401 → 400`, `440 → 420`, `650 → 525`, `900 → 650`, and `990 → 695`. System 2.0 percentage scaling reads that compressed core snapshot and does not scale mutable modifiers or persistent roster G.

## Controlled runtime acceptance

Task 13 records normalized evidence in:

```text
analysis/runtime-observations/gate-system2-milestone-6c-validation.json
SHA-256: ea9e16df7ce264a338712aef40efe5baf74741013567547005ebd2708a0c0fb9
```

The acceptance matrix deliberately separates three evidence methods:

1. Exact-profile extract, install, rebuild, and binary inspection.
2. Execution of the exact generated ARM32 module in the repository instruction interpreter.
3. A clean DeSmuME run of the same rebuilt ROM.

The emitted-module controls prove the complete approved arithmetic and selector matrix: non-Aquos, Aquos, tied/leading owner, behind owner, non-owner, human-owned, AI-owned, two distinct seeded weighted outcomes, constructor bypass, scripted supersession, unrelated-Gate passthrough, and malformed-trailer fallback. This does not claim that every arithmetic vector occurred naturally; the seven controls are exact emitted-module executions.

The live rebuilt-ROM run proves:

- title and menu entry;
- Battle Arena setup and live-play entry;
- an Aquos Bakugan selection and successful throw;
- a bounded match-local repoint of the player's existing arena entry to owned Gate slot 0 / Gate ID 19;
- the standard Battle Arena quit path;
- declining the save prompt;
- return to a responsive Battle Arena menu;
- completion of the built-in Battle tutorial through its supported skip prompt;
- return to the responsive Tutorial menu;
- the generated module present at `0x0228BC20`;
- all 64 cache bytes zero after tutorial completion.

The prototype Battle Arena control changes only match-local arena and Gate-slot state and is not written to the save. The separate tutorial-completion smoke may update tutorial progress and is excluded from that save-data control. Raw screenshots, ROMs, states, battery saves, selected memory files, and debugger output remain local and uncommitted; only normalized values and SHA-256 hashes are stored in the repository.

## Milestone 6C acceptance boundary

The exact build, emitted runtime behavior, live boot/battle compatibility, normal exit, tutorial completion, cache-clear proof, and persistent-state scope controls now pass. Arena ID, full-roster conversion, reusable archetypes, power budgets, additional conditions/effects, fatigue, Ability interaction, AI evaluation, presentation, and save-format changes remain outside Milestone 6C.

## Final repository verification

The complete implementation and documentation tree was committed at:

```text
407e21cbe6419d41835a11caaf576bc5395c2189
```

The final verification commands produced:

```text
Host repository suite:       540 passed, 39 expected environment-gated skips
Exact Milestone 6C controls: 9 passed
Python compilation:          passed
Whitespace validation:       passed
Ruff:                        unavailable in the execution runtime
Strict mypy:                 unavailable in the execution runtime
```

The exact-ROM controls include the guarded raw/overlay workspace rebuild, all
four exact overlay hook/module checks, the deterministic bounded ROM build,
malformed-data fail-closed behavior, legacy Gate samples, and core-G
compatibility.

Repository-boundary inspection found:

- no tracked ROM, save, emulator-state, capture-image, archive, or generated
  module/trailer binary;
- no tracked file larger than 5 MiB;
- no untracked generated module, trailer, ROM, or debugger-state candidate;
- no modification outside the approved Milestone 6C implementation,
  verification, documentation, and test scope.

Because a Git commit cannot contain its own SHA-1, the commit above is the exact
verified implementation/documentation head. The following status-only commit
records these results; the complete suite is rerun after that commit and its
exact head is reported in the pull request and final handoff.
