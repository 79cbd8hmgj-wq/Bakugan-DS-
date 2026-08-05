# Gate Card System 2.0 — Milestone 6C Prototype

## Status

Milestone 6C implements the first live data-driven Gate Card prototype for the exact `B6RE` USA revision-0 profile. Only global Gate ID `19`, Juggernoid, uses System 2.0 behavior. Every unrelated Gate remains an exact legacy passthrough.

## Juggernoid record

```text
card_id:              19
archetype:            comeback
flat_bonus_g:         60
percent_q8_8:         20
attribute_modifiers:  [0, 30, 0, 0, 0, 0]
battle_weights:       [50, 30, 30, 30, 30, 30]
condition:            Gate-owner side is behind
effect:               +40 G
recipient:            Gate-owner combatant
timing:               pre-Gate
```

The attribute order is Pyrus, Aquos, Subterra, Haos, Darkus, Ventus. The raw percentage value `20` is Q8.8 fixed point, or `20 / 256 = 7.8125%`.

## Live Gate formula

```text
scaled_component = trunc_toward_zero(compressed_core_g * 20 / 256)

base_gate_bonus =
    60
    + scaled_component
    + attribute_modifier

conditional_modifier =
    40 when the current combatant owns the Gate
       and the Gate-owner side score is lower
    0 otherwise

effective_gate_bonus = clamp_signed_16(
    base_gate_bonus + conditional_modifier
)

target_total_g = clamp_unsigned_16(
    compressed_core_g + effective_gate_bonus
)
```

Percentage scaling uses the already-compressed core-G snapshot. It does not scale mutable battle modifiers, persistent roster G, field pickups, or Ability effects.

Approved controls:

| Compressed core | Attribute | Owner state | Gate bonus |
|---:|---|---|---:|
| 190 | Pyrus | normal | 74 |
| 190 | Aquos | normal | 104 |
| 190 | Pyrus | behind | 114 |
| 190 | Aquos | behind | 144 |
| 525 | Pyrus | normal | 101 |
| 525 | Aquos | normal | 131 |
| 525 | Pyrus | behind | 141 |
| 525 | Aquos | behind | 171 |

A tied owner does not activate the comeback rider. A non-owner never receives the rider. Solo mode reads `participant +0xEE`; team mode adds the reciprocal teammate score selected by `participant +0xF2`.

## Battle-type weighting

Normal fallback uses six weights in confirmed type-ID order:

```text
Scratch: 50
Timing:  30
Pop:     30
Spin:    30
Trace:   30
Bound:   30
```

The total is 200, giving Scratch 25% and each other type 15%.

Precedence remains:

1. Explicit constructor type `0–5`: use it and do not call the weighted helper.
2. Constructor type `-1` with valid Juggernoid cache: call ARM9 weighted helper `0x02021A30` once.
3. Constructor type `-1` without valid prototype data: call original fixed selector `0x022433AC`.
4. A valid scripted override `1–6` supersedes the provisional type.
5. The final type enters the original six-way constructor path.

Milestone 6C does not update battle-type history.

## Runtime layout

```text
System 2.0 module:  0x0228BC20–0x02293C20  (0x8000 bytes)
Match-local cache: 0x02293C20–0x02293C60  (64 bytes)
Battle arena low:  0x02293C60
Battle arena high: 0x023E0000
```

The original overlay-7 `0x640`-byte BSS is materialized as zero-backed payload before the module. The new cache does not repurpose original participant, battle, arena, padding, or save bytes.

The `G2DT` trailer is appended to raw NitroFS file ID `2762` after its unchanged 2,840-byte LZ10 stream:

```text
Header:   32 bytes
Records:  103 × 40 bytes
Trailer:  4,152 bytes
Carrier:  6,992 bytes
```

Only the selected 40-byte record and metadata are cached.

## Fallback policy

### Record-level fallback

Missing or malformed trailer data, CRC failure, card-ID mismatch, unsupported enums, nonzero reserved/deferred fields, invalid vectors, zero prototype weights, or a failed hook/layout guard invalidates the cache. Gate calculation and battle-type selection both remain original.

### Calculation-level fallback

Unresolvable owner, participant, descriptor, attribute, compressed-core, score, teammate, or target context abandons the complete System 2.0 calculation for that combatant. No partial System 2.0 value is stored.

### Selector-phase fallback

An unexpected weighted-helper failure or out-of-range type uses the original fixed selector for the selector phase only. The earlier valid Gate-G calculation is not rolled back.

Unrelated Gates consume no System 2.0 weighted RNG and preserve the original six-byte lookup, `×10` conversion, and fixed battle metadata.

## Installation and rebuild

Start from an exact extracted workspace with the merged core-G compression patch:

```bash
bakugan-ds gate install-milestone-6c work/bakugan \
  --authoring config/gates/milestone-6c-system2-v1.json

bakugan-ds rebuild \
  "/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds" \
  work/bakugan \
  output/Bakugan-Gate-System2-M6C.nds
```

A dry run validates all inputs and reports every atomic change without writing:

```bash
bakugan-ds gate install-milestone-6c work/bakugan --dry-run
```

An identical reinstall is a no-op. A partial, stale, or divergent prior install is rejected.

## Rollback

The safest rollback is to extract a fresh workspace from the exact source ROM. For an existing workspace, restore the original ARM9, original decoded overlay 7, original raw carrier, and pre-install manifests together. Do not remove only one hook or generated product: the installer is intentionally atomic because the hooks, module, carrier, overlay metadata, and arena-low boundary form one compatibility unit.

## Validation boundary

The committed runtime evidence distinguishes:

- exact-ROM build inspection;
- controlled execution of the exact emitted ARM32 module for the complete formula and selector matrix;
- live DeSmuME boot, Battle Arena throw/exit, built-in Battle tutorial completion, cache clear, and responsive return.

It does not claim that every arithmetic vector occurred naturally in one match. Raw ROMs, screenshots, states, saves, memory files, and debugger output remain local and uncommitted.

## Explicit exclusions

Milestone 6C does not implement:

- arena-ID conditions;
- Gate fatigue or activation-count gameplay;
- Ability Card interaction;
- battle-history penalties;
- AI evaluation;
- description or activation UI changes;
- save-format changes;
- reusable archetypes or power budgets;
- additional conditions, effects, drawbacks, or secondary effects;
- complete Gate roster conversion or rebalance.

Those remain separate design and implementation boundaries beginning with Milestone 6D.
