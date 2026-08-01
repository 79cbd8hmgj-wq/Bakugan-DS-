# Rebuilding and Guarded Patching

## Exact-copy builds

`bakugan-ds rebuild` validates the source ROM and the complete extracted
workspace before creating an output. When every file in `modified` still
matches its decoded reference hash, the source ROM is copied exactly. The
output SHA-256 therefore remains:

`7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b`

The output report is written beside the ROM as `<output>.build.json`.

## Changed builds

The original ROM remains the template for headers, tables, executable regions,
and all data outside FAT-backed payloads. Changed builds:

1. validate all immutable original files and workspace mappings;
2. reuse exact compressed bytes for unchanged payloads;
3. deterministically LZ10-compress changed resources that were originally LZ10;
4. store changed overlays uncompressed at exactly their declared `ram_size`;
5. clear the changed overlay's compression flag and compressed-size metadata;
6. repack FAT payloads in original physical order with `0x200` alignment;
7. update every FAT start/end pair;
8. preserve the original 128 MB ROM size;
9. reparse the result before atomically installing it.

ARM9 and ARM7 edits are permitted only when their sizes remain unchanged.

## Overlay fallback

The project currently decodes BLZ but does not encode BLZ. An edited overlay is
therefore stored uncompressed. Nintendo DS overlay metadata supports this: the
FAT range becomes the full decoded executable size, while the reserved overlay
word is cleared so the loader does not attempt backward decompression.

For overlay 7, an edited build must have:

- payload size: `467360` bytes;
- overlay flag: `0`;
- compressed-size field: `0`;
- load address unchanged at `0x02219440`.

## Guarded patch schema

```json
{
  "format_version": 1,
  "profile_id": "b6re_rev0",
  "patches": [
    {
      "id": "example",
      "type": "binary_replace",
      "target": "overlay:7",
      "offset": 4096,
      "expected": "00112233",
      "replacement": "44556677",
      "rationale": "Documented behavior change"
    }
  ]
}
```

Supported targets are `arm9`, `arm7`, `overlay:<id>`, and
`nitrofs:<original FNT path>`. Expected and replacement byte strings must be
valid hexadecimal and exactly the same length. All guards are evaluated in
memory before any modified target is written. Stale expected bytes fail closed.

Patch application reports are written under `workspace/manifests` using the
patch filename, for example `patch-example.json`.
