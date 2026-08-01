# Verified ROM Layout Corrections

The Milestone 1 exact-ROM integration run corrected two values that appeared in
the original design and implementation-plan drafts. The values below are read
directly from the supported ROM header and overlay table and are enforced by
automated tests.

| Field | Superseded draft value | Verified value |
|---|---:|---:|
| File Name Table offset | `0x000FFD00` | `0x000FFC00` |
| ARM9 overlay load address | `0x0221A1C0` | `0x02219440` |

Additional verified overlay-table metadata:

- ARM9 overlay table ROM offset: `0x00071800`
- ARM9 overlay table size: `288` bytes
- ARM9 overlay count: `9`
- ARM7 overlay count: `0`
- FAT entries `0` through `8` are overlay payloads and are intentionally absent
  from the File Name Table.

`config/b6re_rev0.json`, `analysis/memory-map.yaml`, `analysis/overlays.yaml`,
and the reference-ROM integration test are the authoritative machine-checked
sources for these values.
