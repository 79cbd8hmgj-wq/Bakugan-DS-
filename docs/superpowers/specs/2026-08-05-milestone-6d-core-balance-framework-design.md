# Milestone 6D Gate System 2.0 Core Balance Framework Design

## Status

Reconstructed and approved design for the deterministic Gate Card System 2.0 balance framework.

- Repository profile: `b6re_rev0`
- Base milestone: Milestone 6C merged at `6cfa600093e887c191957180c04a53b8d26c0948`
- Existing live prototype: Gate ID `19`, Juggernoid
- Record format: version-1 `G2DT`, 32-byte header plus 103 ordered 40-byte records
- Runtime module: overlay-7 region `0x0228BC20-0x02293C20`
- Match-local cache: `0x02293C20-0x02293C60`
- Sole deferred context field: `arena_id`

This document replaces the lost chat-only Milestone 6D design. It preserves the decisions already approved before that chat was lost. It authorizes a separate implementation plan and implementation branch. It does not authorize Milestone 6E full-roster values.

## Goal

Milestone 6D converts the one-off Juggernoid prototype engine into a reusable deterministic balance framework without converting the complete Gate roster.

The completed framework must provide:

```text
fixed internal power budgets
+ seven recognizable archetypes
+ record-local attribute relationships
+ bounded battle-type weighting
+ reusable score, owner, and landing conditions
+ deterministic target resolution
+ reusable G effects and explicit drawbacks
+ exact legacy fallback
```

Milestone 6D preserves Juggernoid as the only live System 2.0 card in the shipping authoring roster. The other archetypes are exercised through reviewed host fixtures and exact emitted-ARM tests. Activating additional cards remains Milestone 6E.

## Approved scope

### In scope

- Preserve and generalize the existing fixed-point hybrid Gate calculation.
- Define seven fixed archetypes backed by shared composable mechanics.
- Define deterministic internal power-budget accounting and archetype budget bands.
- Define record-local attribute relationship tiers and validation rules.
- Define bounded six-type battle-weight rules that prevent forced outcomes.
- Add reusable conditions based on Gate ownership, match score, and the confirmed landing result `Gate Card won`.
- Add reusable target modes for current combatant, Gate owner, and non-owner combatant.
- Add reusable signed G effects and explicit signed G drawbacks during the pre-Gate calculation phase.
- Generalize the Python reference model, deterministic traces, authoring validation, and emitted ARM dispatcher.
- Preserve Juggernoid's exact Milestone 6C behavior and exact phase precedence.
- Preserve exact legacy behavior for every unrelated Gate in the committed 6D authoring roster.
- Produce a deterministic balance report and Milestone 6E handoff contract.

### Out of scope

- Activating System 2.0 records for Gate IDs other than `19`.
- Full-roster assignment, card-by-card tuning, or player-facing descriptions.
- Ability Card disabling, preserving, copying, consuming, or modifying.
- Activation counters, Gate fatigue, reuse limits, and battle-history penalties.
- Arena-dependent conditions or effects.
- Post-Ability, capture, result, removal, or match-completion effects.
- Random effects other than the confirmed weighted battle-type selector.
- AI deck construction, Gate evaluation, or battle decision changes.
- UI, activation messages, descriptions, debug overlays, or presentation changes.
- Save-data changes or persistent System 2.0 state.
- Adaptive difficulty or player-performance weighting.

## Compatibility requirements

The implementation must preserve all Milestone 6C contracts:

- Gate ID `19` remains the only live System 2.0 record.
- Juggernoid remains `60 + trunc_toward_zero(core_G * 20 / 256)`, Aquos `+30 G`, owner-behind `+40 G`.
- Juggernoid weights remain `(50, 30, 30, 30, 30, 30)`.
- Explicit constructor battle types bypass System 2.0 weighting.
- Scripted overrides supersede the provisional weighted result.
- Complete-payload CRC32 validation remains mandatory.
- Invalid records clear the cache and route to original behavior.
- Invalid live calculation context falls back completely for that combatant.
- Weighted-selector failure falls back only for the selector phase.
- The merged bounded core-G patch remains untouched.
- Original overlay-7 BSS ownership remains unchanged.
- No frame-critical filesystem read is introduced.

## Version-1 record interpretation

The physical 40-byte record does not change. Milestone 6D expands the supported semantic domain of existing fields.

### Archetype IDs

| ID | Name | Identity |
|---:|---|---|
| `0` | Legacy passthrough | Exact original Gate behavior |
| `1` | Comeback | Gains value from a bounded score disadvantage |
| `2` | Power | Most budget is committed to dependable G influence |
| `3` | Skill | Most non-G budget is committed to battle-type influence |
| `4` | Control | Uses deterministic targeting or conditions to constrain who benefits |
| `5` | Risk | Purchases above-normal upside with an explicit drawback |
| `6` | Attribute | Uses a pronounced positive and negative attribute profile |
| `7` | Chaos | Uses unusual but deterministic weighting and an explicit drawback |

The IDs intentionally preserve Milestone 6C's existing `Comeback = 1` value.

### Condition IDs

| ID | Name | Deterministic rule |
|---:|---|---|
| `0` | None | Always true for a present effect |
| `1` | Owner behind | Owner-side score is lower than opposing-side score |
| `2` | Owner ahead | Owner-side score is higher than opposing-side score |
| `3` | Score tied | Owner-side score equals opposing-side score |
| `4` | Owner score zero | Owner-side score equals `0` |
| `5` | Owner at match point | Owner-side score equals or exceeds `2` but is below victory |
| `6` | Opponent at match point | Opposing-side score equals or exceeds `2` but is below victory |
| `7` | Gate Card won landing | Confirmed throw-controller landing result equals `1` |

The authoritative victory threshold remains `3`. Conditions `5` and `6` therefore match effective side score `2` in normal valid play, while retaining the explicit range check for defensive validation.

No condition may read `arena_id`, difficulty, Ability state, activation count, history, or persistent save data.

### Target modes

| ID | Name | Rule during one combatant calculation |
|---:|---|---|
| `0` | Current combatant | Current calculation is eligible |
| `1` | Gate owner | Eligible only when current participant is the Gate owner |
| `2` | Gate non-owner | Eligible only when current participant is not the Gate owner |

Target resolution is a predicate over the combatant currently being calculated. It never performs a cross-record write and is independent of combatant construction order.

### Effect and drawback IDs

| ID | Name | Rule |
|---:|---|---|
| `0` | None | No modifier |
| `1` | Add signed G | Add the signed value to the current Gate bonus |
| `2` | Subtract magnitude G | Subtract the absolute value from the current Gate bonus |

`effect_value`, `drawback_value`, and `secondary_value` are interpreted as signed 16-bit authoring values after record decoding. Milestone 6D uses the primary effect and explicit drawback fields. Secondary effects remain serialized and validated as zero in the committed live roster, but the pure framework may exercise one secondary test fixture to prove deterministic sequencing for Milestone 6E.

### Timing phases

Only timing phase `0`, pre-Gate calculation, is supported. Any other timing phase invalidates live System 2.0 behavior and executes the exact legacy path.

### Deferred state fields

The following fields must remain zero in every Milestone 6D live record:

```text
activation_limit
fatigue_rate
reserved
```

Battle-history cache bytes remain untouched.

## Hybrid G calculation

The base calculation remains:

```text
scaled_component = trunc_toward_zero(compressed_core_g * percent_q8_8 / 256)

base_gate_bonus =
    flat_bonus_g
    + scaled_component
    + attribute_modifiers[current_attribute]
```

Then the deterministic dispatch pipeline runs:

```text
primary_condition
-> primary_target
-> primary_effect
-> drawback_condition
-> drawback_target
-> drawback
-> optional secondary fixture path in host/emitted-ARM tests only
-> signed-16 Gate-bonus clamp
```

The final target-total G remains clamped to unsigned 16-bit only on a successful System 2.0 calculation. The legacy path preserves original wrapping behavior exactly.

Every intermediate uses signed 32-bit integer arithmetic. No floating-point instruction or host calculation is allowed.

## Attribute relationship framework

Milestone 6D does not invent a universal elemental combat wheel. Relationships are record-local authoring tiers encoded by the existing six signed attribute modifiers.

### Relationship tiers

| Tier | Allowed modifier |
|---|---:|
| Primary affinity | `+25` to `+75 G` |
| Secondary affinity | `+10` to `+40 G` |
| Neutral | `-9` to `+9 G` |
| Opposed | `-60` to `-15 G` |

All six values must remain within `-100..+100 G`.

### Profile rules

- A non-Attribute archetype may use at most two positive affinity entries and is not required to include an opposed entry.
- An Attribute archetype must contain at least one modifier `>= +40`, at least one modifier `<= -20`, and a maximum-minus-minimum spread of at least `60 G`.
- A legacy passthrough record must contain six zero modifiers.
- Attribute order remains `Pyrus, Aquos, Subterra, Haos, Darkus, Ventus`.
- The authoring report must label each entry by tier but must not claim the tiers are original-game or anime canon.

## Bounded battle-type weighting

Weights remain six unsigned bytes in the confirmed order:

```text
Scratch, Timing, Pop, Spin, Trace, Bound
```

### Valid live weight vector

A nonlegacy System 2.0 record must satisfy all of the following:

- Each weight is within `10..80`.
- Total weight is within `120..300`.
- Every battle type remains possible.
- Maximum probability is at most `40%`.
- Maximum weight divided by minimum weight is at most `4`.
- `preferred_type` is `0..5` and references one of the maximum-weight entries.

A vector with all equal weights is neutral and consumes the confirmed weighted selector only when the record explicitly uses System 2.0 selection. The committed 6D roster does not activate new records, so unrelated Gates continue to use original fixed metadata and consume no System 2.0 RNG.

### Weight-pressure tiers

The deterministic balance report classifies vectors by maximum probability:

| Maximum probability | Classification | Budget cost |
|---:|---|---:|
| `<= 20%` | Neutral | `0` |
| `> 20%` and `<= 25%` | Mild | `10` |
| `> 25%` and `<= 33.34%` | Strong | `20` |
| `> 33.34%` and `<= 40%` | Extreme bounded | `30` |

Percentages are compared using integer cross-multiplication, never floating point.

## Internal power budget

Every nonlegacy record receives a deterministic internal budget score. The budget is not shown to players and does not alter runtime arithmetic.

### Component costs

All divisions use ceiling integer arithmetic.

```text
positive flat cost        = ceil(max(flat_bonus_g, 0) / 25) * 15
positive percentage cost  = ceil(max(percent_q8_8, 0) / 16) * 5
positive attribute cost   = sum(ceil(value / 25) * 6 for value > 0)
negative attribute credit = min(18, sum(ceil(abs(value) / 25) * 3 for value < 0))
```

Conditioned positive G effects use:

| Condition class | Cost per started `25 G` |
|---|---:|
| None, owner ahead, score tied | `10` |
| Owner behind, owner score zero | `7` |
| Either side at match point | `6` |
| Gate Card won landing | `5` |

```text
primary effect cost = ceil(positive_effect_magnitude / 25) * condition_rate
```

Explicit drawback credit uses `5` points per started `25 G`, capped at `30`. Negative base flat or percentage values are not permitted as hidden drawback credit; drawbacks must use the explicit drawback fields or negative attribute modifiers.

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

### Budget bands

| Archetype | Required net band | Additional rule |
|---|---:|---|
| Comeback | `85..115` | Requires owner-behind or owner-score-zero condition |
| Power | `90..110` | At least 70% of gross budget comes from flat, percentage, and attribute G |
| Skill | `90..110` | Battle-weight cost is at least `20` |
| Control | `85..110` | Uses owner/non-owner targeting or a score/landing condition |
| Risk | `85..120` | Gross budget is at least `110` and explicit drawback credit is nonzero |
| Attribute | `90..110` | Satisfies the Attribute profile rules |
| Chaos | `90..120` | Uses extreme-bounded or strong asymmetric weights and explicit drawback credit |

A budget failure is an authoring failure. It does not silently normalize or modify the record.

### Juggernoid compatibility

The approved Juggernoid record must remain valid. Under this budget model it scores:

```text
flat:       45
percentage: 10
Aquos:      12
owner-behind effect: 14
mild weights: 10
net total: 91
```

That lies inside the Comeback band.

## Archetype invariants

### Comeback

- Requires condition `OWNER_BEHIND` or `OWNER_SCORE_ZERO`.
- Requires a positive primary effect.
- Ties never activate an owner-behind effect.

### Power

- Uses no extreme-bounded battle vector.
- Uses no explicit drawback unless gross budget exceeds the normal band.
- At least 70% of gross budget is direct G influence.

### Skill

- Uses strong or extreme-bounded battle weighting.
- Effective G at reference core values must remain below the Power archetype ceiling established by the analyzer.

### Control

- Uses target mode `GATE_OWNER` or `GATE_NON_OWNER`, or a nontrivial deterministic condition.
- Does not manipulate Ability Cards in Milestone 6D.

### Risk

- Requires a nonzero explicit drawback.
- Requires gross budget `>= 110` before credits.
- The drawback must be capable of activating under the same confirmed context domain as the reward.

### Attribute

- Must satisfy the required positive, negative, and spread rules.
- No more than 60% of gross budget may come from universal flat and percentage components.

### Chaos

- Remains deterministic.
- Requires strong or extreme-bounded asymmetric weights.
- Requires a nonzero explicit drawback.
- May not use random G, random targeting, unsupported timing, or hidden history state.

## Condition evaluation

All score conditions use authoritative solo or team score projection:

```text
solo side score = participant +0xEE
team side score = participant +0xEE + reciprocal teammate +0xEE
```

The owner and opposing sides must resolve to distinct validated participant sets. Invalid teammate linkage, descriptor identity, participant pointers, or score range causes a complete calculation-level legacy fallback.

The landing condition reads only the confirmed throw-controller result value `1`, meaning `Gate Card won`. Values `0`, `2`, `3`, and `4` remain unnamed and unsupported.

## Effect sequencing and fallback

For a structurally valid record:

1. Build and validate the calculation context.
2. Calculate flat, percentage, and attribute components.
3. Evaluate the primary condition.
4. Resolve the primary target predicate.
5. Apply the primary effect when both are true.
6. Evaluate and apply the explicit drawback through the same bounded dispatcher.
7. Apply an optional secondary test-fixture effect only in pure host and emitted-module tests; committed live records keep secondary fields zero.
8. Clamp and store the successful result.

Any invalid context or unsupported semantic value causes complete legacy fallback for that combatant. No partially calculated System 2.0 component may survive.

The weighted battle-type phase remains independent. An unexpected weighted-selector failure uses the original fixed selector without rolling back an already completed valid Gate-G phase.

## Reference-value analysis

The analyzer must evaluate every nonlegacy authored record at compressed core G values:

```text
190, 400, 525, 650, 695
```

For every value it evaluates all six attributes, owner/non-owner targets, and every supported true/false condition boundary. It reports:

- minimum, maximum, and mean effective Gate bonus;
- attribute spread;
- condition upside;
- explicit drawback magnitude;
- maximum battle-type probability;
- gross and net budget;
- archetype invariant results;
- fallback-invalid reasons.

The analyzer is deterministic JSON and never edits authored values.

## Runtime architecture

### Pure reference modules

```text
balance.py
    archetypes, budget scoring, attribute tiers, weight bounds, analysis report

conditions.py
    score and landing condition evaluation

effects.py
    target predicates, signed G effects, explicit drawback sequencing

system2.py
    generic hybrid calculation and deterministic trace integration
```

### Authoring and CLI

```text
authoring.py
    version-1 record parsing, semantic validation, live-roster policy

cli.py
    validate and report Milestone 6D configuration
```

### Emitted ARM module

The existing deterministic ARM32 generator must emit generic equivalents of:

```text
g2_evaluate_condition
g2_matches_target
g2_apply_effect
g2_calculate_gate_bonus
```

The implementation must remain dependency-free and fit within the existing fixed `0x8000` module. If it cannot fit, that is a real design blocker; module growth is not implicitly authorized.

The loader, full-payload CRC, selected-record cache, hooks, legacy replay, and cache-clear lifecycle remain unchanged unless an exact guarded change is required by the generic dispatcher.

## Authoring policy

Milestone 6D adds `config/gates/milestone-6d-system2-v1.json`.

- It contains 103 ordered records.
- Gate ID `19` is byte-for-byte semantically identical to the approved Milestone 6C Juggernoid record.
- Every other Gate remains canonical legacy passthrough.
- Synthetic archetype fixtures live only in tests and are never serialized into the committed live roster.
- Building the trailer twice from the same document produces byte-identical output.
- Reinstalling the same 6D configuration is a no-op.
- Attempting to install over a partially divergent 6C or 6D workspace fails closed transactionally.

## Required verification

### Host tests

- Every enum and semantic ID round-trips deterministically.
- Juggernoid remains exactly compatible.
- Attribute tiers and profile invariants accept and reject exact boundary vectors.
- Weight bounds use integer arithmetic and reject forced or zero-probability outcomes.
- Budget calculations match exact vectors.
- Every condition has true, false, solo, team, owner, non-owner, and invalid-context controls where applicable.
- Every target and effect has exact signed and clamp boundary tests.
- Archetype fixtures pass only their own invariants.
- Legacy passthrough records perform no System 2.0 calculation or RNG call.

### Emitted-ARM tests

The exact emitted module must match the Python reference for:

- every condition ID;
- every target mode;
- positive and negative effects;
- drawback sequencing;
- signed-16 and unsigned-16 clamps;
- Juggernoid's complete Milestone 6C vector matrix;
- invalid-record and invalid-context legacy fallback;
- all six weighted-selector return values;
- explicit and scripted precedence.

### Exact-ROM controls

With the user-owned B6RE revision-0 ROM:

- deterministic install and rebuild succeeds;
- no unrelated FAT payload changes;
- protected core-G bytes remain exact;
- overlay and ARM9 guards match;
- trailer and runtime module hashes are deterministic;
- the rebuilt ROM remains exactly 134,217,728 bytes;
- no new live record other than Gate ID `19` is enabled.

### Live emulator acceptance

- Boot and menu remain responsive.
- Juggernoid retains its approved live behavior.
- At least one unrelated Gate follows original behavior.
- A battle or tutorial path completes and returns to a responsive surrounding menu.
- The 64-byte cache is cleared at completion.
- No save, persistent roster, Ability state, history byte, or activation counter is modified by the framework.

## Failure policy

The framework fails closed.

- Invalid authoring fails before trailer generation.
- Invalid budget or archetype invariants fail before installation.
- Missing or malformed runtime data clears the cache.
- Unsupported semantic IDs use exact original behavior.
- Invalid live context uses exact original Gate calculation for that combatant.
- Selector-only failure uses original fixed metadata for that phase.
- Transactional install failure leaves the workspace byte-identical.
- No runtime failure is converted into a guessed default System 2.0 value.

## Completion criteria

Milestone 6D is complete only when:

1. The deterministic framework and all seven archetype invariants exist in host code.
2. The generic condition, target, effect, and drawback dispatcher exists in the emitted ARM module.
3. Juggernoid is exactly regression-compatible with Milestone 6C.
4. No additional live Gate is activated.
5. The deterministic balance report validates the committed 6D roster.
6. Complete host, exact-module, exact-ROM, and live regression checks pass.
7. Documentation states clearly that full-roster conversion is Milestone 6E.
8. No copyrighted game data or generated binary product is committed.

## Milestone 6E handoff

Milestone 6E may assign System 2.0 records to Gate IDs `1-103` only after this framework is merged. Each converted card must:

- select exactly one of the seven archetypes;
- satisfy its archetype invariants and budget band;
- use only supported deterministic mechanics unless a later specification expands the engine;
- preserve bounded battle probabilities;
- receive a readable card identity and documented balance rationale;
- pass the reference-value analyzer before runtime testing.
