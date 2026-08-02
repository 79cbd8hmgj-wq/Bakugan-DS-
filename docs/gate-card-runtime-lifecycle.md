# Gate Card Runtime Lifecycle

## Scope

This document records the original Gate Card lifecycle evidence needed by Gate Card System 2.0. It does not claim that the new system exists, and it does not copy the game's complete card data.

## Shared battle path

Overlay 7 constructs one battle object and processes both combatants through the same Gate-aware G-Power pipeline. The confirmed runtime equations are `230 + 180 = 410` for the opponent and `190 + 100 = 290` for the player.

| Transition | Runtime address | Confidence | Evidence boundary |
|---|---:|---|---|
| Placed to selected | `0x022433AC` | Candidate | A fallback helper derives one byte and the constructor stores it at object `+0x20`; the exact semantic field and owner source remain unresolved. |
| Selected to activated | `0x0223E334` | Confirmed | The battle object calls confirmed constructor `0x0223CFE8`, which reaches Gate helper `0x02065BF4` for both combatants. |
| Activated to battle started | `0x0223D288`–`0x0223D28C` | Confirmed | The Gate bonus is added to compressed base G and the target total is stored. |
| Battle started to resolved | `0x0223ED00` | Confirmed | State 4 calls battle-result state `0x0223F918` and advances only after completion. |
| Resolved to reset | `0x0223EEDC` | Probable | State 8 propagates a completion marker and sets the battle object done flag; the higher-level label “reset” is inferred. |

The dispatcher is `0x0223EA60`. Its state byte is object offset `+0x0C`, and the executable handles states `0` through `8`.

## AI and tutorial behavior

The Gate constructor is shared rather than player-only. One runtime capture observed opponent and player records produced by the same function and the same Gate formula. This is sufficient to classify the AI battle activation path as shared.

The tutorial is a scripted variant. It uses the normal Gate calculation and battle object, but the built-in minigame skip is a scripted bypass. Validation reached tutorial-completion dialogue, returned to the park story, and accepted another input. The exact branch from the skip control to result processing remains probable rather than confirmed.

## Gate capture cut-in

The generic cut-in constructor at `0x02271410` stores an event type byte at object `+0x19`. The indexed table at `0x0227C02C` maps event type `4` to `cutin_gate_card_get`. This establishes a probable post-result capture presentation path:

```text
resolved -> captured -> reset
```

The individual Gate Card ID is not consumed by this cut-in constructor, and the actor byte at `+0x18` has not yet been proven to be the canonical Gate-owner field.

## Unresolved lifecycle states

- **Removed:** scene cleanup, board removal, and capture bookkeeping have not yet been separated.
- **Reused:** no confirmed repeated-activation counter or reuse transition exists in current evidence.
- **Gate owner:** participant side fields are visible, but the canonical ownership field remains unresolved.

These gaps remain explicit inputs to the battle-context investigation. They must not become required System 2.0 fields until confirmed.

## Repository boundary

The repository contains addresses, offsets, formulas, selected normalized observations, hashes, and confidence labels. ROM bytes, save states, RAM captures, debugger logs, and screenshots remain local.
