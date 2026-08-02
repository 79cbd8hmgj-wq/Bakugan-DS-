# Persistent Player G-Power Storage

## Result

The player's current roster G-Power is stored directly in a persistent byte table,
not reconstructed in battle from a separately identified level or experience field.
The exact normal level-up commit path remains unresolved.

## Confirmed table

The global player-roster structure begins at runtime address `0x020D43F0`.
Its G-Power table begins at offset `0x460`, runtime address `0x020D4850`.
It is a 41 × 6 table: 41 Bakugan identities by six attributes.

| Property | Value |
| --- | ---: |
| Bakugan identities | 41 |
| Attributes per identity | 6 |
| Entries | 246 |
| Entry size | 1 byte |
| Stored unit | 10 G |

The confirmed index is:

```text
index = owner_bank * 246 + bakugan_id * 6 + attribute_id
```

The observed helper rejects owner banks other than zero, Bakugan IDs greater than
40, and attributes greater than five. The stored value is converted as:

```text
current_g = table[index] * 10
```

## Confirmed helpers

- `0x0202317C` — validates the identifiers and returns the table index.
- `0x020231C0` — converts an input G value to units of ten and stores one byte at
  roster offset `0x460`.
- `0x020231F4` — loads the stored byte and returns it multiplied by ten.
- `0x02023248` — returns a separate four-byte auxiliary record at roster offset
  `0x88 + identity_index * 4`; its two halfwords are not yet named.

These addresses were captured from the runtime-decompressed ARM9 image. Earlier
`0x02009Cxx` helper addresses were incorrect overlay-relative branch results and
must not be used.

## Known setter contexts

Direct setter calls are currently limited to initialization and scripted flows:

- ARM9 `0x02022CB4`: roster initialization/import loop.
- Overlay 0 `0x02222800` and `0x02222868`: new-game roster setup.
- Overlay 5 `0x0221E6AC`: fixed `440 G` assignment associated with Bakugan ID 36.
- Overlay 2 `0x0221B224`: fixed `670 G` assignment associated with Bakugan ID 37.

The user-supplied reference order makes IDs 36 and 37 probable Skyress and Storm
Skyress entries. That name mapping and the interpretation as a scripted evolution
transaction remain probable, not runtime-confirmed.

No direct overlay 7 call to the persistent setter was found. A normal level-up may
use an indirect call, generic save copy, or another commit path that is not yet
identified.

## Participant offset `+0xFD` is not level or experience

Participant byte `+0xFD` is battle-local state:

- initialized to zero at `0x02234D28` and `0x02269700`;
- incremented and clamped to 99 at `0x0222D158`–`0x0222D170` after a `+30 G`
  adjustment;
- copied into a battle-results object at `0x022502F8` beside offset `+0xFC`;
- cleared during battle-state paths at `0x02235718`, `0x022358C8`, and
  `0x02235A38`.

This lifecycle rules out persistent level, experience, or roster progression.
Its exact UI label is not proven, but a G-Power pickup/result counter is the
strongest current interpretation.

## Modding implication

A safe level-scaling patch must not modify the shared mutable-G channel or
participant byte `+0xFD`. The next patch must either:

1. identify the normal persistent-table level-up writer; or
2. apply a carefully bounded transformation to the persistent/core G value while
   leaving field pickups, temporary modifiers, and Gate Card bonuses unchanged.

No gameplay patch is included in this milestone.

## Repository boundary

ROM bytes, runtime RAM dumps, save states, screenshots, and copied guide tables are
not committed. This document records only normalized addresses, formulas,
callsite roles, and confidence boundaries.
