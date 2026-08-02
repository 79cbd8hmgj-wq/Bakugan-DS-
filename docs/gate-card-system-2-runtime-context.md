# Gate Card System 2.0 Runtime Context

**Milestone:** 6B complete-system discovery  
**Current completed domain:** ownership and participant targeting

This document records only confirmed runtime context. Later Milestone 6B tasks will extend it with score, capture, Gate reuse, Ability Card, landing, difficulty, timing, RNG, and loader lifecycles.

## Evidence boundary

The original game does not contain the proposed generic System 2.0 effect-target dispatcher. The target modes below are a new deterministic resolver contract built from confirmed original runtime fields.

No target resolver may infer participant identity from:

- combatant record number alone;
- Gate ownership alone;
- player-versus-AI assumptions;
- participant byte `+0xF2`;
- presentation-only actor fields.

Missing, unresolved, or contradictory context must suppress the new effect and preserve legacy behavior.

## Canonical Gate owner

The active Gate owner is stored as an unsigned participant index at:

```text
battle object +0x06
```

The battle constructor at `0x0223CFE8` derives it from the selected arena-placement record:

```text
arena placement byte +0 = owner's Gate-slot index
arena placement byte +1 = Gate-owner participant index
```

The owner participant and Gate-slot index resolve the active Gate ID, which is stored at `battle object +0x04`.

The owner fields survive result processing and tutorial-skip completion. The next battle constructor clears and rederives them. Destruction ends their validity.

## Defender and challenger

The session pair stores **descriptor indices**, not participant indices:

```text
session +0x28D = defender or stationary-target descriptor
session +0x28E = challenger or active/thrown descriptor
```

Each descriptor is 20 bytes:

```text
session +0x7C + descriptor_index * 20
```

The actual participant index is the low nibble of descriptor byte `+0x0F`.

The paired setter is `0x02262A64`. An exhaustive audit of all seven direct overlay-7 callers confirmed that the target descriptor is passed first and the active descriptor second. Equal-descriptor fallback calls do not represent a normal distinct challenge and must fail closed for pair-dependent effects.

The battle object uses the same ordering:

```text
combatant record 0: battle object +0x0C..+0x1F = defender
combatant record 1: battle object +0x20..+0x33 = challenger
```

Record order is independent of Gate ownership and human/AI identity.

## Human and AI control identity

The authoritative control discriminator is:

```text
participant object +0xC8
```

Interpretation:

```text
NULL     = human-controlled participant
non-NULL = AI-controlled participant
```

The non-null value points to a participant-owned AI decision object. System 2.0 may test pointer presence but must not persist or expose the pointer as a stable ABI.

Participant construction:

1. Clears `+0xC8`.
2. Uses a one-participant human prefix in ordinary local modes.
3. In modes 6 and 7, calls ARM9 helper `0x0202F134` to count active multiplayer participant slots and uses that count as the human prefix.
4. Allocates and stores an AI controller only for participants after the human prefix.

AI battle setup and shot planning branch directly on this same null/non-null pointer. AI state reset preserves the pointer. Participant destruction releases the controller and ends validity.

Participant byte `+0xF2` is a team/slot remap and is **not** the human/AI flag.

## Winner and loser

The battle-result controller constructed at `0x0223E238` stores a signed combatant-record winner index at:

```text
battle-result controller +0x21
```

Values:

```text
-1 = unresolved or no normal winner
 0 = combatant record 0 won
 1 = combatant record 1 won
```

The field is initialized to `-1`. The two result paths write only `0` or `1`:

- direct result resolution at `0x02241A64`;
- calculated result helper `0x02244440`, stored at `0x0224209C`.

Later presentation, reward, progression, and final-state code consumes the same signed index. The result controller also caches the opposite record index at `+0x0E` for loser presentation, but System 2.0 should derive:

```text
loser_record_index = winner_record_index XOR 1
```

This avoids reading `+0x0E` before the original presentation write.

Participant mapping remains:

```text
winner index 0 -> defender participant
winner index 1 -> challenger participant
loser -> the other participant
```

Winner and loser targeting is unavailable while the winner field is `-1`.

## System 2.0 target modes

| Mode | Resolution | Required context |
|---|---|---|
| `owner` | Canonical Gate-owner participant | Live battle object |
| `defender` | Participant from descriptor selected by `+0x28D` | Distinct combatant pair |
| `challenger` | Participant from descriptor selected by `+0x28E` | Distinct combatant pair |
| `self` | Explicit effect-source participant | Explicit source; live mapping for combatant-only effects |
| `opponent` | Other combatant relative to explicit source | Explicit source matching exactly one distinct combatant |
| `both` | Ordered unique tuple: defender, challenger | Distinct combatant pair |
| `winner` | Settled winner record mapped to participant | Winner index `0` or `1` |
| `loser` | Opposite settled record mapped to participant | Winner index `0` or `1` |
| `human` | Live combatants whose `+0xC8` is null | Live participant objects |
| `ai` | Live combatants whose `+0xC8` is non-null | Live participant objects |

`self` and `opponent` are always relative to an explicit effect source. They must never silently mean Gate owner, player, defender, or challenger.

## Fail-closed rules

- Reject winner and loser while the signed winner index is `-1` or outside `0..1`.
- Reject opponent, both, winner, and loser when no distinct pair exists.
- Reject self and opponent without an explicit source participant.
- Reject opponent when the source is not exactly one live combatant.
- Do not convert a non-battling Gate owner into defender, challenger, or opponent.
- Deduplicate human and AI target sets while preserving defender-then-challenger order.
- Do not persist participant pointers, battle pointers, result pointers, controller pointers, or resolved target tuples in Gate data.

## Normalized artifacts

- `analysis/gates/ownership-and-participants.json`
- `analysis/gates/effect-targeting-rules.json`
- `analysis/gates/gate-owner-lifecycle.json`
- `analysis/gates/combatant-record-mapping.json`
- `analysis/gates/challenger-ordering.json`
- `analysis/gates/human-ai-identity.json`
- `analysis/symbols/gate_system2_context.csv`
