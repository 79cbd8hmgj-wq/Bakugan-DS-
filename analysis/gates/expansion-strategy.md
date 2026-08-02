# Gate Card System 2.0 Expansion Storage Strategy

## Decision

**Primary:** hybrid raw-NitroFS trailer plus a guarded overlay-7 module and 64-byte BSS cache.

**Fallback:** raw-NitroFS trailer read into a 72-byte stack buffer without persistent cache.

The primary supports the complete Gate Card roster. The fallback preserves the same file format and full roster, but it is intended for the first Milestone 6B prototype because repeated filesystem access is less efficient.

## Confirmed capacity

The global card metadata marks IDs `0–103` as Gate-category entries and IDs `104–212` as Ability-category entries. ID `0` is the `-` placeholder, leaving **103 Gate Card definitions** at IDs `1–103`.

A fixed System 2.0 record is capped at 40 bytes. The complete trailer is:

```text
32-byte G2DT header
103 × 40-byte records
----------------------
4,152 bytes total
```

This capacity supports the approved roadmap fields without committing any original table or game text.

## Primary: hybrid

### NitroFS carrier

Use file ID `2762`, `font/mes_CardName.mes`, as an append-only raw carrier.

Confirmed original properties:

| Property | Value |
|---|---:|
| Raw LZ10 size | 2,840 bytes |
| Decoded message size | 6,524 bytes |
| Indexed message count | 213 |
| Raw SHA-256 | `76a03522a5031762eb51d07b72a19331bc06a5b6dc0eab60e227a199466d4c4e` |
| Decoded SHA-256 | `5a30adeb411f205ff90ad2e22d3f0adb78db5662cfbbbb2f4ff06a16ba262392` |

The LZ10 decoder reaches the declared 6,524-byte output after consuming 2,838 raw bytes. The original payload already contains two ignored trailing zero bytes. The repository's decoder also stops when the declared output size is reached and ignores remaining raw bytes.

System 2.0 therefore appends the 4,152-byte `G2DT` trailer **after the raw compressed stream**. Native message decoding remains byte-identical and retains its original allocation size. The custom Gate loader reads the trailer from the raw NitroFS file rather than through the message parser.

The trailer header must contain:

- magic `G2DT`;
- format version;
- fixed record size `40`;
- first supported card ID `1`;
- record count `103`;
- payload length;
- payload checksum;
- reserved bytes required to make the header exactly 32 bytes.

Missing magic, unsupported version, incorrect geometry, invalid card ID, short reads, or checksum failure must select the original legacy Gate behavior.

### Executable region and battle-local cache

Overlay 7 cannot simply grow into its existing BSS because original code contains absolute references to that BSS. The hybrid layout preserves those addresses by materializing the original `0x640` BSS bytes as zero-filled writable bytes in the expanded overlay payload, then appending the System 2.0 module.

| Region | Original | System 2.0 |
|---|---:|---:|
| Overlay-7 `ram_size` | `0x721A0` | `0x7A7E0` |
| Original BSS addresses | `0x0228B5E0–0x0228BC20` | preserved as zero-backed payload data |
| System 2.0 code region | none | `0x0228BC20–0x02293C20` (`0x8000` bytes) |
| Overlay-7 BSS size | `0x640` | `0x40` |
| Selected-record cache | none | `0x02293C20–0x02293C60` |
| Battle-arena low boundary | `0x0228BC20` | `0x02293C60` |
| Battle-arena high boundary | `0x023E0000` | unchanged |
| Arena capacity | 1,393,632 bytes | 1,360,800 bytes |

ARM9 function `0x020061D8` returns `0x0228BC20` as the battle arena's low boundary. Its function SHA-256 is `61a85f352aeb7cd1ff1846cf109a3f46e063cee8ad409d335a0686208cec6802`. The four-byte literal at `0x02006264` is `20bc2802`, SHA-256 `7aff087442df57ce6203666128e65dc2b442f1ad3de1ba8e4c03282cf7b8d952`.

Overlay-table entry 7 has SHA-256 `6fe6eade1de5331451ff0e59ef7ad5634699fdf2d52476697da59fab4b0fbbf2`. Its `ram_size` field is at ROM offset `0x000718E8`; its BSS field is at `0x000718EC`.

Milestone 6B must atomically:

1. append `0x640` zero bytes that preserve the original BSS addresses;
2. append an exactly `0x8000`-byte guarded System 2.0 module;
3. change `ram_size` from `0x721A0` to `0x7A7E0`;
4. change BSS from `0x640` to `0x40`;
5. change the arena-low literal from `0x0228BC20` to `0x02293C60`.

Changing only part of this set would overwrite original globals, leave code outside the loaded overlay, or overlap the battle arena.

The new BSS stores one validated selected record, its card ID, format version, and a valid flag. Overlay loading zeroes the cache. Battle completion clears the valid flag. Every consumer must fall back to legacy behavior if the cache is invalid.

## Fallback: raw NitroFS without cache

The fallback uses the same `G2DT` trailer and malformed-data rules. At battle construction it reads:

```text
32-byte header
40-byte selected record
-----------------------
72-byte stack buffer
```

It requires no heap allocation, BSS growth, overlay metadata change, or persistent cache. It is viable for Milestone 6B and the complete roster, but repeated filesystem access is unsuitable for frame-critical effects. The fallback should read once during battle construction, compute the prototype's initial outputs, and retain original behavior for non-prototype Gates.

## Candidate comparison

| Candidate | Viable | Scope | Decision |
|---|---|---|---|
| NitroFS | Yes | Complete roster, slower fallback | Existing raw LZ10 trailer, 72-byte stack read, no new FNT entry |
| Expanded executable or overlay | No | None | No confirmed standalone full-roster region; ARM9 is BLZ-compressed; uncoordinated overlay growth is unsafe |
| Dedicated overlay | No | None | Nine fixed overlays, no tenth loader route, unresolved lifetime/addressing |
| Hybrid | Yes | Complete roster, primary | Raw NitroFS trailer plus guarded 32 KiB overlay module and 64-byte selected-record cache |

### NitroFS-only requirements

Confirmed:

- the carrier exists in the fixed FNT/FAT mapping;
- the raw LZ10 trailer leaves native decoded bytes unchanged;
- generic filesystem seek/read functions are already used by ARM9 loader `0x02023504`;
- a 72-byte stack read avoids heap allocation;
- deterministic construction is `original_raw + exact_trailer` before normal FAT repacking;
- malformed data falls back to legacy behavior.

Risk: filesystem reads are slower than memory and cannot be placed in per-frame logic.

### Expanded executable or overlay

Confirmed constraints:

- overlay 7 is fixed at 467,360 decoded bytes in the original ROM;
- the current rebuilder requires changed overlays to retain `ram_size`;
- ARM9 is BLZ-compressed and no deterministic BLZ compressor exists;
- the 72 zero Gate-table bytes for global IDs `201–212` are insufficient for the complete roster.

Unresolved and therefore non-viable as a standalone storage strategy:

- safe in-place code/data space;
- deterministic ARM9 recompression;
- full-roster capacity without the NitroFS data source;
- uncoordinated overlay growth that preserves original BSS addresses and arena ownership.

The selected hybrid strategy resolves the overlay-growth portion through one exact atomic layout rather than treating arbitrary executable expansion as generally safe.

### Dedicated overlay

Confirmed constraints:

- the overlay table contains nine entries;
- all ARM9 overlays load at `0x02219440`;
- the current rebuild verifies that overlay counts remain unchanged.

Unresolved and therefore non-viable:

- a tenth overlay-table slot;
- loader and unload coordination;
- address ownership while overlay 7 is active;
- relocation and call routing;
- FNT/FAT expansion.

## Rebuild contract

Milestone 6B must add a narrow guarded raw-trailer operation rather than treating the trailer as decoded message content:

1. verify the exact original raw carrier SHA-256;
2. verify no existing `G2DT` trailer is present;
3. append exactly 4,152 bytes;
4. prove native LZ10 decoding equals the original 6,524-byte payload;
5. repack the FAT deterministically;
6. report old/new raw hashes and file offsets;
7. reject stale, duplicate, oversized, or malformed trailers atomically.

For the primary, the rebuild must additionally guard and update:

- overlay-7 payload length `0x721A0 → 0x7A7E0`, including preserved BSS zeros and an exact `0x8000`-byte module;
- overlay-7 `ram_size` metadata at ROM offset `0x000718E8`;
- overlay-7 BSS metadata `0x640 → 0x40` at ROM offset `0x000718EC`;
- ARM9 arena-low literal `0x0228BC20 → 0x02293C60` at runtime address `0x02006264`.

## Rejected assumptions

- Adding a new named NitroFS file is not supported by the current fixed FNT/FAT rebuild.
- Zero bytes are not automatically free executable space.
- Growing overlay code or changing BSS without preserving original BSS addresses and moving the arena boundary atomically is unsafe.
- The full System 2.0 table will not be loaded or cached in RAM.
- Missing or malformed System 2.0 data will never disable the original Gate system.
