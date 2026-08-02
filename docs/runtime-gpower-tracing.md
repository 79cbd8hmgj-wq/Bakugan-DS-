# Runtime G-Power Trace — Milestone 4B

## Result

Milestone 4B confirms the initial battle G-Power record, the Gate Card
attribute-bonus path, the final target-total calculation, and the separate UI
counter animation for the exact `B6RE` USA revision 0 ROM.

A controlled tutorial battle produced these records:

- Player Serpenoid: **190 + 100 = 290**.
- Opponent Bakugan: **230 + 180 = 410**.

The same four unsigned 16-bit fields appeared in two adjacent **20-byte**
records. Their allocation address changed between emulator runs, but their
relative offsets and values remained stable.

## Confirmed runtime record

Each battle participant record begins 12 bytes into the owning container and
uses a 20-byte stride:

| Record offset | Confirmed role | Controlled player value |
| --- | --- | ---: |
| `+0x00` | animated/current displayed G | 290 |
| `+0x02` | target total G | 290 |
| `+0x04` | base snapshot G | 190 |
| `+0x06` | Gate Card attribute bonus G | 100 |

One captured allocation placed the opponent record at `0x022E58EC` and the
player record at `0x022E5900`. Another run placed the same layout at
`0x022E596C` and `0x022E5980`. These absolute addresses are examples, not fixed
symbols.

## Constructor and initial base snapshot

The constructor begins at **`0x0223CFE8`** in overlay 7, component-relative
offset `0x00023BA8`.

The first participant's initial G value is formed at:

```text
0x0223D0F0  ldrh r2, [r1, #4]
0x0223D0F4  ldrh r1, [r1, #6]
0x0223D0F8  add   r1, r2, r1
0x0223D0FC  strh  r1, [r6, #12]
```

The second participant follows the same pattern at `0x0223D100` through
`0x0223D10C`. The constructor then copies those values into each record's base
snapshot field and clears the Gate-bonus fields.

Therefore the confirmed arithmetic is:

```text
initial_base_snapshot = source_u16_04 + source_u16_06
```

**Probable, not confirmed:** `source_u16_04` is the stored species/base G-Power
component, while `source_u16_06` is a growth, level, or evolution contribution.
The tutorial's level-1 Serpenoid totals 190, but one controlled battle does not
separate level growth from evolution state.

## Gate Card attribute bonus

For each record, the constructor derives an attribute index and calls the ARM9
helper at `0x02065BF4`. The ordinary path multiplies the helper result by ten and
stores it in the record's `+0x06` bonus field. This is consistent with the
compact divided-by-ten Gate rows found statically in ARM9.

The target total is then calculated at:

```text
0x0223D278  ldrh r2, [r5, #12]   ; base/current snapshot
0x0223D27C  ldrh r1, [r5, #18]   ; Gate attribute bonus
0x0223D288  add   r0, r2, r1
0x0223D28C  strh  r0, [r5, #14]  ; target total
```

Confirmed formula:

```text
gate_attribute_bonus_g = lookup(card_id, attribute_id) * 10
target_total_g = base_snapshot_g + gate_attribute_bonus_g
```

The controlled values validate both records exactly: `190 + 100 = 290` and
`230 + 180 = 410`.

## Display animation is separate

A write watchpoint on the displayed field stopped inside the overlay 7 function
at **`0x0223DDAC`**, component-relative offset `0x0002496C`. That function reads
the current and target fields and moves the displayed value toward the target by
three per frame. It is a UI tween, not the central G-Power formula.

This distinction explains why a watchpoint on `+0x00` produces many writes while
the actual total at `+0x02` remains stable.

## Later battle adjustments

The state function at `0x0221A7D0` contains later writes at `0x0221B3F8`,
`0x0221B40C`, and `0x0221B438`. Those paths add the record field at `+0x0A` to
an existing G value and update the target field. The field is a candidate for a
temporary Ability Card, battle, or minigame modifier, but its exact source is
not yet confirmed.

## Rejected false positive

A watchpoint also stopped at ARM9 `0x02007EB8`. The surrounding instructions and
register state identify an overlay decompression loop that reused the same RAM
after the battle. It is explicitly excluded from the G-Power pipeline.

## Evidence and repository boundary

The local investigation used a user-supplied ROM, DeSmuME save states, RAM
dumps, screenshots, and disassembly. Those files are **not committed**. The
repository stores only normalized observations, addresses, formulas, confidence
labels, and tests.

## Remaining confidence boundary

Milestone 4B confirms the initial base-snapshot sum, Gate/attribute bonus, final
target total, record layout, and display tween. A later controlled matrix is
still required to assign exact semantic names to `source_u16_04`,
`source_u16_06`, and the temporary `+0x0A` field across levels, evolutions, and
Ability Card effects.
