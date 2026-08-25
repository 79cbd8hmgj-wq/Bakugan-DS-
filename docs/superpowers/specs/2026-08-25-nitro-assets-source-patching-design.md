# Nitro Asset Intelligence and Source Patching Design

## Status

Approved design for integrating generally useful concepts from the supplied Tinke, NitroPacker, NDSFactory, and ndstool archives into the existing Bakugan DS evidence-first framework.

## Goal

Add two independent capabilities without replacing the repository's stricter Nintendo DS parsing, workspace, compression, guarded patching, or rebuild systems:

1. read-only Nitro asset intelligence for the exact B6RE ROM;
2. an optional external ARMv5TE C/ASM compilation bridge that produces guarded workspace patches.

The two capabilities are implemented and reviewed independently.

## Source-boundary policy

The supplied archives are reference material only. No GPL or other upstream implementation source is vendored or copied. The repository keeps clean-room Python implementations that follow its existing validation and error-handling conventions.

NDSFactory and ndstool primarily overlap capabilities already implemented more strictly in `bakugan-ds`, so their extraction/repacking code is not imported. Tinke is used only to identify relevant Nintendo Nitro format conventions. NitroPacker is used only to inform the architecture of an external source-compilation workflow.

## Stage 1: Nitro asset intelligence

### Command

`bakugan-ds assets inventory ROM [--profile PROFILE] [--output FILE] [--allow-unsupported] [--include-unknown]`

The command is read-only. It never modifies a ROM or workspace.

### Data flow

1. Validate or inspect the ROM through the existing profile and NDS parsers.
2. Iterate named NitroFS files from the existing FNT/FAT mapping. Overlay FAT entries are not treated as assets.
3. If a file is LZ10-wrapped, decode it with the existing strict LZ10 implementation.
4. Identify signed Nitro formats from the decoded four-byte file signature.
5. Identify raw tile/palette formats only from their file-name family because NTFT/NTFP do not provide equivalent self-identifying four-byte Nitro signatures.
6. Record evidence type, compression, raw/decoded sizes, decoded magic, extension family, and extension/signature agreement.
7. Emit deterministic JSON sorted by file ID/path and deterministic summary counts.

### Supported initial formats

Signature-confirmed:

- `BMD0` -> `NSBMD`
- `BTX0` -> `NSBTX`
- `SDAT` -> `SDAT`
- `NARC` -> `NARC`
- `RGCN` -> `NCGR`
- `RLCN` -> `NCLR`
- `RCSN` -> `NSCR`
- `BCA0` -> `NSBCA`
- `BMA0` -> `NSBMA`
- `BTP0` -> `NSBTP`
- `BTA0` -> `NSBTA`
- `BVA0` -> `NSBVA`

Extension-identified raw payloads:

- `*.ntft` and localized suffix variants -> `NTFT`
- `*.ntfp` and localized suffix variants -> `NTFP`

Localized suffix variants such as `.nsbmd_d` and `.nsbtx_f` are normalized to their base format family but still retain their literal extension in the record.

### Evidence rules

- A signed format is `signature` evidence only when the decoded magic matches a known signature.
- NTFT/NTFP are `extension` evidence, not signature evidence.
- A signed extension family with a conflicting known or missing signature is an explicit mismatch.
- Unknown files remain unknown; the scanner does not infer proprietary Bakugan formats from names alone.
- Malformed LZ10 data fails closed through the existing `RomFormatError` path.

### Exact B6RE acceptance fixture

The mounted exact B6RE ROM currently establishes the following reference facts:

- 11,005 FAT entries;
- 10,996 named NitroFS files;
- 678 signature-confirmed `BMD0`/NSBMD files when localized extension variants are included;
- 587 signature-confirmed `BTX0`/NSBTX files when localized extension variants are included;
- 327 NTFT files;
- 982 NTFP files;
- 1 SDAT file;
- zero signed extension/signature mismatches for these standard formats.

These counts are test fixtures for the exact supported ROM, not assumptions applied to arbitrary ROMs.

## Stage 2: guarded source patch bridge

### Purpose

Allow reviewed C or assembly source to be compiled with an external ARM toolchain while keeping `bakugan-ds` responsible for placement, bounds, exact-byte guards, workspace mutation, and ROM rebuilding.

### Non-goals

- Do not turn the repository into a general Nintendo DS SDK.
- Do not silently discover code caves or arena addresses.
- Do not automatically relocate existing game code.
- Do not bypass existing workspace manifests or overlay-growth guards.
- Do not require a specific devkitARM installation.

### Source-patch manifest

A source patch manifest is deterministic JSON with:

- `format_version: 1`;
- `profile_id: "b6re_rev0"`;
- a target component (`arm9`, `arm7`, or `overlay:<id>`);
- an explicitly approved runtime placement address and maximum byte budget;
- explicit ARM or Thumb instruction mode;
- one or more source paths rooted under the manifest directory;
- optional symbol definitions whose names and integer addresses are explicit;
- an expected SHA-256 of the target component before mutation;
- an expected byte sequence for each hook/replacement site;
- explicit hook destinations referencing emitted symbols;
- compiler/linker executable paths or command-line overrides supplied at invocation time rather than committed machine-specific paths.

### Build pipeline

1. Validate the manifest and workspace profile.
2. Resolve the target component and convert the approved runtime placement to a component-relative offset using existing ARM/overlay metadata.
3. Invoke an explicitly selected external compiler/assembler/linker using ARMv5TE-compatible flags and a generated temporary linker script.
4. Extract the flat emitted binary and a machine-readable symbol map.
5. Reject output larger than the manifest byte budget or outside the approved component range.
6. Generate ARM/Thumb branch encodings only for explicit hook records and guard every replaced instruction against expected bytes.
7. Write the compiled payload plus hooks into the workspace atomically.
8. For overlay growth, use the existing `OverlayLayoutOverride` path; no new unguarded overlay-table writer is introduced.
9. Emit a deterministic build report containing source hashes, tool invocations, emitted hashes, placements, hook bytes, and target hashes.
10. The existing `bakugan-ds rebuild` command remains the only ROM rebuild path.

### Safety and reproducibility

- External tools are optional and probed before use.
- Tests mock tool invocation for deterministic unit coverage; an opt-in integration test may exercise a real LLVM/devkitARM installation.
- The source bridge never downloads a toolchain.
- No source patch is applied if profile, target hash, placement, bounds, emitted size, hook guard, or instruction-mode validation fails.
- All temporary compiler products stay outside source-controlled workspace paths until validation succeeds.

## Existing systems that remain authoritative

- ROM profile validation;
- NDS header, FAT, FNT, and overlay parsing;
- LZ10 and BLZ handling;
- deterministic workspace extraction;
- guarded patch application;
- overlay geometry overrides;
- deterministic ROM rebuilding;
- disassembly/module/overlay mapping from PR #46.
