# Runtime G-Power Trace — Milestone 4B

## Result

Milestone 4B confirms the initial battle G-Power record, Gate Card attribute
lookup, final target-total calculation, and separate UI counter animation for
the exact `B6RE` USA revision 0 ROM.

A controlled Pyrus Serpenoid tutorial replay produced:

- Opponent: **230 + 180 = 410**.
- Player: **190 + 100 = 290**.

Heap addresses may move between runs. Record offsets, component addresses,
instructions, and captured operands are the stable evidence.

## Confirmed runtime record

The G-Power fields begin at participant-entry offset `+0x0C` within adjacent
`0x14`-byte entries:

| Field offset from `entry + 0x0C` | Confirmed role | Player value |
| --- | --- | ---: |
| `+0x00` | Animated/current displayed G | 290 |
| `+0x02` | Target total G | 290 |
| `+0x04` | Base snapshot G | 190 |
| `+0x06` | Gate Card attribute bonus G | 100 |

One observed container began at `0x022E58E0`. The opponent fields began at
`0x022E58EC`; the player fields began at `0x022E5900`.

## Constructor and starting snapshot

Overlay 7 constructor **`0x0223CFE8`** forms each starting snapshot from a
12-byte participant source record:

```text
0x0223D0F0  ldrh r2, [r1, #4]
0x0223D0F4  ldrh r1, [r1, #6]
0x0223D0F8  add   r1, r2, r1
0x0223D0FC  strh  r1, [r6, #12]
```

Confirmed arithmetic:

```text
base_snapshot_g = source_core_g + source_mutable_modifier
```

The tutorial records contain `230 + 0` and `190 + 0`. Function
**`0x022696B4`** initializes normal core-G records from source values stored in
tens and scales them by ten.

The field at source-record `+0x06` must not be named as an exclusively
level-growth field. Function **`0x0226A380`** applies signed changes to this
field, clamps it to zero on the low end, and clamps `core_g + modifier` to 990.
It is therefore a **general mutable G modifier** used by multiple gameplay
paths.

## Confirmed Gate-bonus addition

The target total is calculated at:

```text
0x0223D278  ldrh r2, [r5, #12]   ; base snapshot
0x0223D27C  ldrh r1, [r5, #18]   ; Gate attribute bonus
0x0223D288  add   r0, r2, r1
0x0223D28C  strh  r0, [r5, #14]  ; target total
```

Write watchpoints on both target fields stopped at post-store PC
`0x0223D290`:

- Opponent: `r2 = 230`, `r1 = 180`, `r0 = 410`.
- Player: `r2 = 190`, `r1 = 100`, `r0 = 290`.

A narrower watchpoint on the player's Gate-bonus field at `0x022E5906` also
captured initialization to zero at `0x0223D12C` and the real `100` assignment at
`0x0223D274` with `r1 = 100`.

## Confirmed Gate Card attribute lookup

ARM9 helper **`0x02065BF4`** indexes the runtime table at
**`0x020A15AC`**:

```text
gate_attribute_bonus_g = gate_table[card_id * 6 + attribute_id] * 10
target_total_g = base_snapshot_g + gate_attribute_bonus_g
```

The tutorial card row was `[10, 5, 18, 10, 5, 8]`. Pyrus selects column zero,
so `10 * 10 = 100` and `190 + 100 = 290`.

The earlier guide-matching ARM9 region `0x0205EFBA`–`0x0205F173` remains a
probable source-data region. Its relationship to runtime table `0x020A15AC` has
not been demonstrated.

## Display animation is separate

Function **`0x0223DDAC`** moves displayed G toward target G by three per frame.
It is a presentation tween, not the formula.

## Separated `+30` callsites

The two `+30` callers are not the same system:

- **`0x0222B500` — probable field G-Power Boost pickup.** It appears in a
  three-case field-pickup handler, applies `+30` through `0x0226A380`, and does
  not increment participant byte `+0xFD`. The game guide independently records
  the yellow field G-Power Boost as `+30`.
- **`0x0222D154` — probable level-up or progression award.** It applies `+30`
  and immediately increments participant byte `+0xFD`, clamping that counter to
  99. The game documents that leveling increases G-Power, but the exact role of
  `+0xFD`—level, experience step, upgrade count, or another counter—has not yet
  been observed at runtime.

The user-supplied reference table contains 38 forms, each with a +250 G
minimum-to-maximum range. That supports progression tuning but does not prove
that each level uses a flat `+30` or identify the final-level adjustment.

## Candidate evolution model

Evolution is not yet runtime-confirmed. Evolved forms may select separate
identity or source-stat records with their own core G values, but this remains a
candidate until an evolution event or evolved save is traced through
`0x022696B4`.

Participant field `+0x0A`, used by later target rewrites, also remains a
candidate temporary Ability Card, minigame, or battle modifier.

## Rejected false positive

ARM9 `0x02007EB8` is a BLZ decompression loop that reused the watched heap after
battle. It is not G-Power logic.

## Repository boundary

Only normalized observations, addresses, formulas, confidence labels, hashes,
and tests are committed. ROM bytes, RAM dumps, screenshots, save states,
disassembly captures, and copied guide tables remain local.
