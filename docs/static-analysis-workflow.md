# Static Battle Analysis Workflow

## Inputs

Use the decoded executables produced by `bakugan-ds extract`:

- `original/arm9.bin`, base `0x02000000`
- `original/decoded/overlays/overlay_007.bin`, base `0x02219440`

Generate a local reference catalog as described in `reference-import.md`, then
run:

```bash
python -m bakugan_ds.analysis scan \
  --arm9 work/bakugan/original/arm9.bin \
  --overlay7 work/bakugan/original/decoded/overlays/overlay_007.bin \
  --reference references/generated/bakugan-guide.json \
  --output analysis/generated/static-analysis.json
```

The report records component hashes, keyword strings, exact pointer references,
nearby ARM function starts, exact scaled numeric matches, and proximity
clusters. Generated reports and catalogs remain outside version control.

## Ghidra handoff

Import overlay 7 as a raw little-endian ARM binary with language appropriate for
ARMv5TE. Set the image base to `0x02219440`. Its executable bytes end at
`0x0228B5E0`; create an uninitialized 1,600-byte BSS block ending at
`0x0228BC20`.

Run `tools/ghidra/ApplyBakuganSymbols.py` with
`analysis/symbols/overlay_0007.csv` as its only script argument. The script sets
the expected layout, disassembles candidate entry points, creates labels, and
adds evidence comments.

All nine overlays share a load address. Analyze each overlay in a separate
program or overlay-specific memory space.

## Evidence boundaries

A resource-name reference establishes code association, not semantic identity.
The three GP-effect candidates are useful entry points into battle code, but
none is the confirmed final G-Power formula. Numeric matches establish a
candidate data region, not its complete record layout.
