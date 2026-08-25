# Nintendo DS disassembly workflow

The Bakugan framework includes a small, game-agnostic disassembly preparation layer for
ARM9, ARM7, and overlay binaries. It complements the existing exact-ROM parser, workspace
extractor, BLZ codec, guarded patcher, and deterministic rebuilder; it does not replace them.

The behavior was clean-room reimplemented after reviewing generic concepts from an external
Nintendo DS disassembly-tool archive. No source from that archive is vendored here, and
Pokémon-specific scripts, hardcoded overlay IDs, and project-layout assumptions are excluded.

## 1. Find ARM9 Nitro module parameters

Use the stored or runtime-decoded ARM9 binary. Pass the component's load address so the report
contains both file-relative and runtime addresses.

```bash
bakugan-ds disasm module-params work/bakugan/original/arm9.bin \
  --base-address 0x02000000 \
  --output work/reports/disassembly/module-params.json
```

For the supported B6RE revision 0 ROM, the guarded reference test confirms:

```text
module params offset: 0x00000BA0
module params address: 0x02000BA0
compressed static end: 0x0206D6C0
static BSS end:         0x02219440
```

The module-parameter scanner requires an aligned Nitro block and ignores unaligned appearances
of the magic word. Multiple aligned candidates fail rather than selecting one arbitrarily.

## 2. Generate the overlay map

```bash
bakugan-ds disasm overlay-map "/path/to/Bakugan - Battle Brawlers.nds" \
  --output work/reports/disassembly/overlays.json
```

ROM-level reports require the exact supported profile by default. `--allow-unsupported` is
read-only and follows the same boundary as `bakugan-ds inspect`.

The report combines the existing validated overlay table with ARM9 module parameters and emits:

- overlay IDs and file IDs;
- RAM addresses, executable sizes, and BSS sizes;
- static initializer ranges;
- overlays that begin exactly at the ARM9 static-BSS boundary;
- groups that share a load address;
- direct `previous.ram_end == next.ram_address` placement relationships.

B6RE revision 0 uses one shared ARM9 overlay slot: all nine ARM9 overlays begin at
`0x02219440`, the confirmed ARM9 `static_bss_end`.

## 3. Emit labelled raw-byte assembly

A text file containing whitespace-separated runtime addresses can be used to split a flat binary
into stable labelled byte blocks:

```text
0x0223CFE8
0x0223D288
0x0223DDAC
```

```bash
bakugan-ds disasm labels work/bakugan/original/decoded/overlays/overlay_0007.bin \
  work/labels/overlay7.txt \
  --vma 0x02219440 \
  --output work/disasm/overlay7-data.s
```

The component base is always emitted as a label, so bytes before the first requested label are
never silently discarded. Labels outside the component are rejected.

This command is intended for data islands, unknown regions, and incremental assembly
reconstruction. It does not guess whether a region is code or data.

## 4. Diff original and reconstructed code

Install an ARM GNU binutils `objdump` compatible with Nintendo DS ARMv5TE code. The default
executable name is `arm-none-eabi-objdump`; another binary can be supplied with `--objdump`.

```bash
bakugan-ds disasm diff \
  work/bakugan/original/decoded/overlays/overlay_0007.bin \
  work/rebuilt/overlay_0007.bin \
  --vma 0x02219440 \
  --start 0x0223CFE8 \
  --end 0x0223D2A0 \
  --output work/reports/disassembly/overlay7.diff
```

For Thumb regions, add `--thumb`. The command disassembles both flat binaries with identical
machine, VMA, and range options and then produces a deterministic unified diff.

The diff is a reconstruction aid, not proof of semantic equivalence. Runtime-sensitive meanings
still require the project's normal evidence process: static candidate, exact-binary guard,
controlled runtime confirmation, normalized evidence, and regression coverage.

## Existing tools remain authoritative

The uploaded archive also contained filesystem extraction, overlay-table parsing, and Nintendo
backward-decompression utilities. Those behaviors were not duplicated because this repository
already has stricter implementations:

- `bakugan_ds.nds.fnt` and `bakugan_ds.nds.fat` for NitroFS structure;
- `bakugan_ds.nds.overlays` for validated overlay metadata;
- `bakugan_ds.compression.blz` for BLZ parse, decode, in-place decode, and deterministic encode;
- `bakugan_ds.workspace.extract` for deterministic editable workspaces;
- `bakugan_ds.workspace.rebuild` for exact/no-change rebuilds.

Pokémon-specific helpers and scripts that assume named overlays or a pret repository layout are
not part of the Bakugan workflow.
