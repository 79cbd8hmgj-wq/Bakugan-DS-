# Gate Card System 2.0 Core Balance Framework

## Status and live scope

Milestone 6D supplies the reusable deterministic balance framework for Gate Card System 2.0.

**Only Gate ID 19, Juggernoid, is live.** The other 102 records in `config/gates/milestone-6d-system2-v1.json` are canonical legacy passthroughs. **Full-roster conversion remains Milestone 6E.**

The framework does not implement Ability manipulation, fatigue, activation limits, battle-history penalties, AI evaluation, presentation changes, save changes, or arena-dependent rules.

## Seven archetypes

| ID | Archetype | Required identity |
|---:|---|---|
| 1 | Comeback | Bounded reward when the owner is behind or has zero score |
| 2 | Power | Most gross budget comes from dependable G influence |
| 3 | Skill | Meaningful bounded battle-type pressure |
| 4 | Control | Deterministic owner/non-owner targeting or score/landing conditions |
| 5 | Risk | Above-normal gross value purchased with an explicit drawback |
| 6 | Attribute | Pronounced positive and negative record-local attribute profile |
| 7 | Chaos | Unusual deterministic weighting plus an explicit drawback |

ID `0` remains exact legacy passthrough behavior. Archetypes are recognizable authoring identities built on shared conditions, targets, effects, and weight rules; they are not separate runtime engines.

## Hybrid G calculation

All live calculations use signed 32-bit integer arithmetic and compressed battle core G:

```text
scaled_component = trunc_toward_zero(compressed_core_g * percent_q8_8 / 256)

base_gate_bonus =
    flat_bonus_g
    + scaled_component
    + attribute_modifiers[current_attribute]
```

The dispatcher then evaluates the primary condition, target, effect, explicit drawback, and the final clamps. A valid System 2.0 Gate bonus is clamped to signed 16-bit; the resulting target total is clamped to unsigned 16-bit. Invalid context performs the complete original Gate calculation for that combatant.

## Record-local attribute relationships

The six modifier slots remain ordered:

```text
Pyrus, Aquos, Subterra, Haos, Darkus, Ventus
```

| Tier | Modifier |
|---|---:|
| Primary affinity | `+25..+75 G` |
| Secondary affinity | `+10..+40 G` |
| Neutral | `-9..+9 G` |
| Opposed | `-60..-15 G` |

Every entry must remain within `-100..+100 G`. These are authoring classifications, not claims of an original-game or anime-wide elemental wheel.

An Attribute Gate requires at least one modifier `>= +40`, one modifier `<= -20`, and a spread of at least `60 G`. A non-Attribute Gate may use at most two positive affinity entries. Legacy records use six zeros.

## Bounded battle-type weighting

Weight order is:

```text
Scratch, Timing, Pop, Spin, Trace, Bound
```

Every live vector must satisfy:

- each weight `10..80`;
- total `120..300`;
- every type remains possible;
- maximum probability at most `40%`;
- maximum-to-minimum ratio at most `4:1`;
- `preferred_type` identifies a maximum-weight entry.

Weight pressure is classified without floating point:

| Maximum probability | Class | Budget cost |
|---:|---|---:|
| `<=20%` | Neutral | 0 |
| `>20%` and `<=25%` | Mild | 10 |
| `>25%` and `<=33.34%` | Strong | 20 |
| `>33.34%` and `<=40%` | Extreme bounded | 30 |

Unrelated legacy Gates use original fixed metadata and consume no System 2.0 weighted-selection RNG.

## Internal power budget

The budget is an authoring and review tool. It does not alter runtime arithmetic and is never shown to players.

All divisions use ceiling integer arithmetic:

```text
positive flat cost        = ceil(max(flat_bonus_g, 0) / 25) * 15
positive percentage cost  = ceil(max(percent_q8_8, 0) / 16) * 5
positive attribute cost   = sum(ceil(value / 25) * 6 for value > 0)
negative attribute credit = min(18, sum(ceil(abs(value) / 25) * 3 for value < 0))
```

Positive primary effects cost per started `25 G`:

| Condition | Rate |
|---|---:|
| None, owner ahead, score tied | 10 |
| Owner behind, owner score zero | 7 |
| Either side at match point | 6 |
| Gate Card won landing | 5 |

Explicit drawback credit is `5` points per started `25 G`, capped at `30`.

```text
gross_budget =
    positive flat cost
    + positive percentage cost
    + positive attribute cost
    + primary effect cost
    + battle-weight cost

net_budget =
    gross_budget
    - negative attribute credit
    - explicit drawback credit
```

| Archetype | Required net band |
|---|---:|
| Comeback | `85..115` |
| Power | `90..110` |
| Skill | `90..110` |
| Control | `85..110` |
| Risk | `85..120` |
| Attribute | `90..110` |
| Chaos | `90..120` |

Juggernoid scores `91`: flat 45, percentage 10, Aquos 12, owner-behind effect 14, and mild weights 10.

## Supported conditions

| ID | Condition |
|---:|---|
| 0 | None |
| 1 | Owner behind |
| 2 | Owner ahead |
| 3 | Score tied |
| 4 | Owner score zero |
| 5 | Owner at match point |
| 6 | Opponent at match point |
| 7 | Confirmed `Gate Card won` landing result |

The victory threshold is three, so a valid normal match-point score is two. Missing required landing context is invalid and uses the complete legacy calculation. No condition reads arena ID, difficulty, Ability state, activation count, history, or persistent data.

## Targets, effects, and drawbacks

Targets are predicates over the combatant currently being calculated:

| ID | Target |
|---:|---|
| 0 | Current combatant |
| 1 | Gate owner |
| 2 | Gate non-owner |

Effects and drawbacks use signed G values:

| ID | Operation |
|---:|---|
| 0 | None |
| 1 | Add signed G |
| 2 | Subtract magnitude G |

Target resolution never writes across combatant records. The framework supports only timing phase `0`, pre-Gate calculation. Unknown IDs, unsupported timing, invalid pointers, and invalid context fail closed.

## Fallback behavior

- Invalid authoring fails before trailer generation.
- Invalid budgets or archetype invariants fail before installation.
- Missing, malformed, stale, or checksum-invalid runtime data clears the cache.
- Unsupported semantic IDs use exact original behavior.
- Invalid calculation context uses the complete original Gate calculation for that combatant.
- Selector-only failure uses original fixed metadata for that phase.
- Explicit constructor battle types bypass weighting.
- Scripted overrides supersede provisional weighted results.
- Transactional install failure leaves the workspace byte-identical.

## Authoring and CLI

Validate the committed 103-record roster:

```bash
bakugan-ds gate validate-milestone-6d \
  --authoring config/gates/milestone-6d-system2-v1.json
```

Generate the deterministic balance report:

```bash
bakugan-ds gate report-milestone-6d \
  work/reports/gates/milestone-6d-balance.json \
  --authoring config/gates/milestone-6d-system2-v1.json
```

Install transactionally into an extracted workspace:

```bash
bakugan-ds gate install-milestone-6d work/bakugan \
  --authoring config/gates/milestone-6d-system2-v1.json
bakugan-ds rebuild "/path/to/game.nds" work/bakugan output/Bakugan-M6D.nds
```

Generated trailers, modules, extracted data, rebuilt ROMs, and balance reports derived from copyrighted inputs remain local and untracked.

## Runtime geometry

```text
Module: 0x0228BC20–0x02293C20
Cache:  0x02293C20–0x02293C60
Arena:  starts at 0x02293C60
```

The module remains exactly `0x8000` bytes. The cache remains exactly 64 bytes. The merged core-G compression ranges remain protected and unchanged.

## Rollback

Rollback is a rebuild operation, not a binary-copy operation:

1. Restore the Milestone 6C authoring/configuration and module-generation source from the merged Milestone 6C revision.
2. Extract or reset a clean supported workspace.
3. Install Milestone 6C and rebuild from the user-owned reference ROM.
4. Do not copy generated modules, overlays, carriers, or ROM images into the repository.

## Milestone 6E entry gate

Milestone 6E may activate Gate IDs `1..103` only after Milestone 6D is merged and all final checks pass. Every converted card must:

- select exactly one of the seven archetypes;
- satisfy its budget band and archetype invariants;
- use only supported deterministic mechanics;
- preserve bounded battle probabilities;
- receive a readable identity and documented rationale;
- pass deterministic authoring, emitted-module, exact-ROM, and bounded live checks.
