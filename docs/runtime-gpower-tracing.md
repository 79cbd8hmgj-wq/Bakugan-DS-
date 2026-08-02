# Runtime G-Power Trace — Milestone 4B

## Result

Milestone 4B confirms the initial battle G-Power record layout, the arithmetic
that adds the stored Gate bonus to the base snapshot, and the separate UI
counter animation for the exact `B6RE` USA revision 0 ROM.

A deterministic tutorial replay produced two adjacent 20-byte participant
entries:

- Opponent: **230 + 180 = 410**.
- Player Serpenoid: **190 + 100 = 290**.

The owning allocation moved between emulator runs, but the participant stride,
field offsets, arithmetic instructions, and operands remained stable.

## Confirmed runtime record

The G-Power fields begin at participant-entry offset `+0x0C`:

| Field offset from `entry + 0x0C` | Confirmed role | Player value |
| --- | --- | ---: |
| `+0x00` | animated/current displayed G | 290 |
| `+0x02` | target total G | 290 |
| `+0x04` | base snapshot G | 190 |
| `+0x06` | stored Gate bonus G | 100 |

Participant entries use a `0x14` (20-byte) stride. One captured container began
at `0x022E58E0`; the opponent G-Power fields began at `0x022E58EC` and the
player fields at `0x022E5900`. These absolute RAM addresses are examples, not
fixed symbols.

## Constructor and initial base snapshot

The record constructor begins at **`0x0223CFE8`** in overlay 7, relative offset
`0x00023BA8`.

The first participant's initial G value is formed at:

```text
0x0223D0F0  ldrh r2, [r1, #4]
0x0223D0F4  ldrh r1, [r1, #6]
0x0223D0F8  add   r1, r2, r1
0x0223D0FC  strh  r1, [r6, #12]
```

The second participant follows the same pattern at `0x0223D100` through
`0x0223D10C`.

Confirmed arithmetic:

```text
initial_base_snapshot = source_u16_04 + source_u16_06
```

**Probable, not confirmed:** `source_u16_04` is the stored species/base
component and `source_u16_06` is a growth, level, or evolution contribution.
The controlled level-1 battle does not separate those meanings.

## Confirmed Gate-bonus addition

The target total is calculated at:

```text
0x0223D278  ldrh r2, [r5, #12]   ; base snapshot
0x0223D27C  ldrh r1, [r5, #18]   ; stored Gate bonus
0x0223D288  add   r0, r2, r1
0x0223D28C  strh  r0, [r5, #14]  ; target total
0x0223D290  cmp   r4, #2
```

Write watchpoints on both target fields stopped at post-store PC
**`0x0223D290`** and preserved the operands:

- Opponent: `r2 = 230`, `r1 = 180`, `r0 = 410`.
- Player: `r2 = 190`, `r1 = 100`, `r0 = 290`.

Therefore the runtime-confirmed formula is:

```text
target_total_g = base_snapshot_g + gate_attribute_bonus_g
```

The ordinary preceding branch calls ARM9 helper `0x02065BF4`, then multiplies
its return value by ten before storing the bonus at entry offset `+0x12`.
That code behavior is confirmed statically, but the helper's exact
card/attribute semantics remain probable rather than runtime-confirmed.

## Display animation is separate

The overlay 7 function at **`0x0223DDAC`** reads the current and target fields
and moves the displayed value toward the target by three per frame. It is a
presentation tween, not the total-G formula.

## Later battle adjustments

The state function at `0x0221A7D0` contains later target writes at
`0x0221B3F8`, `0x0221B40C`, and `0x0221B438`. Those paths use participant field
`+0x0A`. Its exact Ability Card, minigame, or temporary-modifier meaning remains
candidate evidence.

## Rejected false positive

A prior watchpoint stopped at ARM9 `0x02007EB8` after the battle. The surrounding
instructions identify overlay decompression reusing the same RAM, not G-Power
logic.

## Evidence boundary

The investigation used a user-supplied ROM, DeSmuME save states, screenshots,
RAM captures, and disassembly. Those files are **not committed**. The repository
stores only normalized addresses, operands, formulas, confidence labels, and
tests.

Milestone 4B does not yet semantically separate level growth from evolution, or
fully name the helper/table that supplies the stored Gate bonus.
