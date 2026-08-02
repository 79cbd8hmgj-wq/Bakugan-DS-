# Gate Card Runtime Lifecycle

**Supported profile:** `b6re_rev0` — Bakugan: Battle Brawlers, Nintendo DS, USA revision 0

This document separates original Gate reuse eligibility, capture bookkeeping, physical arena removal, scene cleanup, object lifetime, and future System 2.0 activation history. These mechanisms are related by result ordering but are not interchangeable fields.

## Participant Gate-slot state

Each participant owns Gate-slot records beginning at:

```text
participant +0x54 + gate_slot_index * 4
```

The Gate ID is the halfword at record `+0x00`. The lifecycle state is the byte at record `+0x02`, equivalent to:

```text
participant +0x56 + gate_slot_index * 4
```

Confirmed values:

| Value | Meaning |
|---:|---|
| `0` | Selectable or unassigned in the ordinary placement path |
| `1` | Assigned to an active arena placement |
| `2` | Unavailable to ordinary placement selection |

State `2` must not be renamed to a universal captured or removed flag. Scripted setup can assign it before battle, and the tutorial capture observed an active arena Gate whose owner slot was already state `2`.

The central setter is `0x0226A404`. In ordinary paths it also maintains participant byte `+0xF8` when a slot crosses the zero/nonzero boundary:

```text
0 -> nonzero: +0xF8 decrements
nonzero -> 0: +0xF8 increments
nonzero -> nonzero: +0xF8 unchanged
```

Scripted setup at `0x0226A48C` can directly override Gate-slot states and force `+0xF8 = 0`. Therefore, `+0xF8` is an ordinary availability cache, not a universal derived count.

## Arena placement

The session owns twelve arena-placement entries. The relevant common fields are:

```text
session +0x1C + arena_entry_index * 8 +0x00 = owner Gate-slot index
session +0x1C + arena_entry_index * 8 +0x01 = owner participant index
session +0x1C + arena_entry_index * 8 +0x02 = occupied byte
session +0x294                              = active arena-placement count
```

### Allocation

Arena allocation begins at `0x02262638`:

```text
select an unoccupied arena entry
record owner participant and Gate-slot identity
occupied: 0 -> 1
owner Gate-slot state: 0 -> 1
establish board-grid reference
session +0x294: N -> N+1
```

### Removal

Arena removal begins at `0x022626B8`:

```text
owner Gate-slot state: nonzero -> 2
occupied: 1 -> 0
board-grid reference: 1 -> 0
session +0x294: N -> N-1
```

A controlled runtime capture around the ordinary result call confirmed:

```text
arena occupied:          1 -> 0
board-grid reference:    1 -> 0
session +0x294:          1 -> 0
owner Gate-slot state:   2 -> 2
owner participant +0xF8: 0 -> 0
```

The idempotent `2 -> 2` slot write is why physical removal must be identified through the arena occupied byte and board-grid clear rather than participant state `2` alone.

### Active-placement transfer

Transfer begins at `0x02262714`:

```text
old owner Gate-slot state -> 0
arena entry owner and Gate-slot identity -> replacement
replacement Gate-slot state -> 1
```

The arena entry stays occupied, so `session +0x294` does not change. No decoded-overlay-7 path restores a Gate after its arena record has already been removed.

## Capture bookkeeping

The original game does not maintain one per-Gate captured Boolean. Capture is a composite result event:

```text
settled winner +0xEE increments
capture-history record appended at winner +0x84 + index * 6
winner +0xF4 increments
active arena placement removed
owner Gate-slot state written to 2
```

The authoritative captured-Gate match score is participant `+0xEE`. Participant `+0xF4` is a separate capture-history entry count. Physical removal is the arena entry occupied transition. These fields must not be substituted for one another.

## Scene and descriptor cleanup

Arena removal and combatant scene cleanup are separate operations.

Descriptor attachment begins at `0x02262768`. Descriptor detachment begins at `0x02262828`. The normal result path removes the arena placement first, then detaches the defender and challenger descriptors.

Related state:

```text
session +0x295    = active descriptor or scene-object count
arena entry +0x21 = linked descriptor index plus one
```

Neither field is an activation counter.

## Activation count

The original exact Gate lifecycle contains no per-Gate activation counter.

The bounded audit covered:

- every direct overlay-7 caller of Gate-slot mutation;
- all arena allocation, removal, and transfer callers;
- descriptor attachment and detachment callers;
- battle construction and result finalization;
- participant and session construction and destruction;
- scripted Gate setup and ordinary slot selection;
- all 18 direct overlay-7 calls to ARM9 Gate-bonus accessor `0x02065BF4`.

Rejected activation candidates include `session +0x294`, `session +0x295`, arena entry `+0x21`, participant `+0xF8`, participant `+0xEE`, participant `+0xF4`, Gate-slot state bytes, and battle-object Gate identity fields.

## Future System 2.0 replacement state

System 2.0 must add match-local activation history without repurposing original object or save-data bytes.

The approved future 64-byte overlay-7 BSS cache is:

```text
0x02293C20..0x02293C60
```

Reserved layout:

| Offset | Size | Purpose |
|---|---:|---|
| `0x00..0x27` | 40 | Validated selected System 2.0 Gate record |
| `0x28` | 1 | Selected global Gate card ID |
| `0x29` | 1 | G2DT format version |
| `0x2A` | 1 | Selected-record valid flag |
| `0x2B` | 1 | Selected arena-entry index; `0xFF` means none |
| `0x2C..0x37` | 12 | `activation_count_by_arena_entry[12]` |
| `0x38..0x3F` | 8 | Reserved zero bytes |

The activation counters are unsigned saturating bytes. Their future update contract is:

```text
session construction:
    clear all counters and selected-entry state

arena allocation:
    initialize the selected entry to zero

Gate battle construction:
    increment once after canonical Gate identity is established
    saturate at 255

active-placement transfer:
    reset the entry because Gate identity changed

arena removal:
    clear the entry and invalidate a matching selected entry

session or overlay teardown:
    do not persist activation history to save data
```

This cache is a future System 2.0 contract. Milestone 6B does not implement it or change gameplay.

## Reset and lifetime

Participant construction at `0x022696B4` clears Gate-slot records and initializes ordinary availability state. Session construction at `0x0225FD5C` clears arena-placement, board-grid, placement-count, and descriptor state.

Participant destruction at `0x02269C28` and `0x02269C5C` frees the object without performing an authoritative in-place Gate-state reset. Session teardown similarly ends address validity. New construction is the reset boundary.

System 2.0 must never cache participant, session, arena-entry, or Gate-slot pointers across teardown.

## Normalized evidence

- `analysis/gates/gate-state-candidates.json`
- `analysis/gates/gate-removal-runtime.json`
- `analysis/gates/gate-state-lifecycle.json`
- `analysis/gates/gate-activation-counter-audit.json`
- `analysis/gates/gate-reuse-and-removal.json`
- `analysis/symbols/gate_system2_context.csv`
