# B6RE Disassembly Addendum

Generic Nintendo DS disassembly preparation, module-parameter scanning, overlay mapping, labelled-byte output, objdump diffs, and static-analysis helpers are documented by the standalone [NDS Disassembly Toolkit disassembly/analysis guide](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit/blob/main/docs/disassembly-and-analysis.md).

This document records the exact Bakugan B6RE evidence and stricter consumer policy layered on those mechanics.

## Bakugan CLI boundary

Bakugan exposes the toolkit-owned `disasm` command group through `bakugan-ds` while supplying the B6RE profile policy.

```bash
bakugan-ds disasm --help
```

ROM-level overlay reports are strict-profile by default in Bakugan. `--allow-unsupported` is read-only and is not a write-policy escape hatch.

## Confirmed ARM9 module parameters

For the supported B6RE revision-0 ROM:

```bash
bakugan-ds disasm module-params work/bakugan/original/arm9.bin \
  --base-address 0x02000000 \
  --output work/reports/disassembly/module-params.json
```

The exact reference fixture confirms:

```text
module params offset: 0x00000BA0
module params address: 0x02000BA0
compressed static end: 0x0206D6C0
static BSS end:         0x02219440
```

These are B6RE facts, not generic Nintendo DS assumptions.

## Confirmed overlay placement

```bash
bakugan-ds disasm overlay-map "/path/to/Bakugan - Battle Brawlers.nds" \
  --output work/reports/disassembly/overlays.json
```

For B6RE revision 0, all nine ARM9 overlays use the same load slot beginning at:

```text
0x02219440
```

That address exactly matches the confirmed ARM9 `static_bss_end` above.

Overlay 7's confirmed load address is also `0x02219440`; game-specific runtime analysis should continue to treat the overlapping overlays as separate executable contexts rather than one simultaneously resident address range.

## Labelled bytes and diffs

The mechanics are toolkit-owned, but Bakugan commands remain useful with B6RE evidence files:

```bash
bakugan-ds disasm labels work/bakugan/original/decoded/overlays/overlay_007.bin \
  work/labels/overlay7.txt \
  --vma 0x02219440 \
  --output work/disasm/overlay7-data.s
```

```bash
bakugan-ds disasm diff \
  work/bakugan/original/decoded/overlays/overlay_007.bin \
  work/rebuilt/overlay_007.bin \
  --vma 0x02219440 \
  --output work/reports/disassembly/overlay7.diff
```

Addresses, label files, analysis ranges, and semantic interpretation belong to Bakugan evidence. The rendering, disassembly invocation, and deterministic diff mechanics belong to the toolkit.

## Evidence boundary

A matching disassembly or resource-name association is supporting evidence, not proof of runtime semantics. Bakugan continues to require its normal evidence progression for gameplay claims: static candidate, exact-binary guard, controlled runtime confirmation where needed, normalized evidence artifacts, and regression coverage.

## Ownership boundary

Do not reintroduce generic NDS disassembly helpers in this repository. `bakugan_ds.disassembly` may remain as a compatibility re-export, but the underlying module-parameter, overlay-layout, labelled-byte, objdump, and diff implementation is toolkit-owned.
