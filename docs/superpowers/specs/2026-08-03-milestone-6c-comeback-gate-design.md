# Milestone 6C Gate System 2.0 Comeback Prototype Design

## Status

Approved design for the first live Gate Card System 2.0 prototype.

- Repository profile: `b6re_rev0`
- Base milestone: Milestone 6B complete
- Prototype card: global Gate Card ID `19`, Juggernoid
- Sole deferred context field: `arena_id`
- No arena-dependent condition or effect is permitted
- Full-roster conversion, fatigue, Ability interference, AI changes, presentation changes, and adaptive difficulty remain out of scope

This specification authorizes a separate implementation plan. It does not itself authorize code changes before that plan is written and approved under the project workflow.

## Goal

Milestone 6C will activate the existing System 2.0 infrastructure for one experimental Gate while preserving exact legacy behavior for every unrelated Gate and every invalid-data path.

The prototype must exercise the complete minimum engine:

```text
validated raw-trailer record
+ selected-record cache
+ fixed-point hybrid G calculation
+ attribute modifier
+ weighted battle-type selection
+ condition evaluation
+ target resolution
+ effect dispatch
+ complete legacy fallback
```

Juggernoid will become a bounded comeback-oriented Gate. It will still provide a moderate bonus to both combatants, favor Aquos, prefer Scratch battles without forcing them, and grant an additional bonus only to the Gate owner's combatant when the owner's side is behind.

## Confirmed foundations

The implementation must use the existing confirmed contracts rather than introducing replacement interpretations.

- Global card ID `19` maps to Juggernoid.
- Attribute order is `Pyrus, Aquos, Subterra, Haos, Darkus, Ventus`.
- Juggernoid's original fixed battle type is Scratch, type ID `0`.
- The selected Gate owner is available through the confirmed battle-local ownership path.
- Participant captured-Gate match score is the byte at participant `+0xEE`.
- Team score aggregation uses the teammate participant index at `+0xF2`.
- The compressed core-G snapshot is available before the Gate calculation hook.
- The confirmed weighted selector is ARM9 function `0x02021A30`.
- Explicit constructor battle types and scripted battle-type overrides retain precedence.
- The 64-byte match-local cache is initialized from a validated selected record and cleared at battle completion.
- The version-1 `G2DT` trailer contains a 32-byte header and 103 ordered 40-byte records.
- Original overlay-7 BSS ownership and the protected core-G compression regions must remain unchanged.

## Scope

### In scope

- Load and validate the selected version-1 Gate record.
- Enable one new archetype, one condition, one effect, and the minimum target and timing values required by the prototype.
- Calculate Juggernoid's hybrid Gate bonus for both combatants.
- Apply an owner-behind rider to the Gate owner's combatant only.
- Replace Juggernoid's normal fixed-metadata battle-type fallback with a weighted roll.
- Preserve explicit and scripted battle-type overrides.
- Preserve complete original behavior for Gate IDs `1-103` other than `19`.
- Fail closed on missing, malformed, unsupported, stale, or context-invalid data.
- Produce deterministic host-side calculation traces and exact-ROM/runtime validation evidence.

### Out of scope

- Arena-dependent rules.
- Gate fatigue or activation limits.
- Battle-history repeat penalties.
- Ability Card disabling or modification.
- Post-Ability, capture, removal, or result effects.
- New player-facing descriptions or activation UI.
- AI deck evaluation or Gate-selection changes.
- Full Gate roster conversion or balance values.
- Save-data changes or persistent System 2.0 state.
- New attribute relationship systems beyond Juggernoid's six record-local modifiers.

## Prototype record

The authoring representation for Gate ID `19` is:

```yaml
card_id: 19
archetype: 1
flags: 0
flat_bonus_g: 60
percent_q8_8: 20
attribute_modifiers: [0, 30, 0, 0, 0, 0]
battle_weights: [50, 30, 30, 30, 30, 30]
preferred_type: 0
condition_id: 1
effect_id: 1
drawback_id: 0
effect_value: 40
drawback_value: 0
activation_limit: 0
fatigue_rate: 0
target_mode: 1
timing_phase: 0
condition_value: 0
secondary_effect_id: 0
secondary_condition_id: 0
secondary_value: 0
reserved: 0
```

The numeric values introduced by Milestone 6C are intentionally minimal.

### Archetype IDs

| ID | Meaning |
|---:|---|
| `0` | Legacy passthrough |
| `1` | Comeback |

### Condition IDs

| ID | Meaning |
|---:|---|
| `0` | None |
| `1` | Gate-owner side is behind |

### Effect IDs

| ID | Meaning |
|---:|---|
| `0` | None |
| `1` | Add G to the current Gate bonus |

### Target modes

| ID | Meaning |
|---:|---|
| `0` | Current combatant |
| `1` | Gate-owner combatant |

### Timing phases

| ID | Meaning |
|---:|---|
| `0` | Pre-Gate calculation |

Every other value is unsupported in Milestone 6C and invalidates the selected record for live System 2.0 behavior.

## Legacy passthrough records

The trailer still contains ordered records for Gate IDs `1-103`.

Every record other than ID `19` must use a canonical legacy-passthrough form:

```yaml
archetype: 0
flags: 0
flat_bonus_g: 0
percent_q8_8: 0
attribute_modifiers: [0, 0, 0, 0, 0, 0]
battle_weights: [0, 0, 0, 0, 0, 0]
preferred_type: 255
condition_id: 0
effect_id: 0
drawback_id: 0
effect_value: 0
drawback_value: 0
activation_limit: 0
fatigue_rate: 0
target_mode: 0
timing_phase: 0
condition_value: 0
secondary_effect_id: 0
secondary_condition_id: 0
secondary_value: 0
reserved: 0
```

A legacy-passthrough record must not alter Gate G, battle type, context, state, RNG, or timing. It immediately routes to the original behavior.

## Hybrid G calculation

### Inputs

The calculation uses only confirmed battle-local values:

- compressed core G for the current combatant;
- current combatant attribute ID `0-5`;
- selected validated Juggernoid record;
- Gate owner participant identity;
- current combatant participant identity;
- authoritative solo or team match scores.

Persistent roster G is not read for percentage scaling.

### Base formula

For each combatant:

```text
scaled_component = trunc_toward_zero(compressed_core_g * percent_q8_8 / 256)

base_gate_bonus =
    flat_bonus_g
    + scaled_component
    + attribute_modifiers[current_attribute]
```

For Juggernoid:

```text
base_gate_bonus =
    60
    + trunc_toward_zero(compressed_core_g * 20 / 256)
    + attribute_modifier
```

The Aquos modifier is `+30 G`; all other prototype attribute modifiers are zero.

### Comeback condition

The condition is true only when both are true:

```text
current_combatant_participant == gate_owner_participant
owner_side_score < opposing_side_score
```

A tied score does not activate the condition.

Solo score:

```text
side_score = participant[+0xEE]
```

Team score:

```text
side_score =
    participant[+0xEE]
    + teammate(participant[+0xF2])[+0xEE]
```

The effect adds `effect_value`, which is `+40 G`, to the current Gate bonus.

```text
effective_gate_bonus = base_gate_bonus + 40
```

The condition and effect are evaluated during each combatant's own Gate calculation. Target mode `1` resolves the Gate owner's combatant. The effect executes only when that resolved target is the combatant currently being calculated. This prevents cross-record writes, duplicate application, and dependence on combatant construction order.

### Arithmetic policy

- Inputs are promoted to signed 32-bit intermediates.
- Q8.8 multiplication and division use integer arithmetic.
- Division rounds toward zero.
- The effective Gate bonus is clamped to signed 16-bit range before integration with the battle record.
- The final target-total G is clamped to unsigned 16-bit range.
- No floating-point operation is permitted.
- Overflow, invalid attribute IDs, invalid participant resolution, or invalid score context invalidates System 2.0 for that calculation and executes the complete legacy Gate calculation instead.

### Required vectors

| Compressed core G | Attribute | Owner state | Expected Gate bonus |
|---:|---|---|---:|
| `190` | Pyrus | not behind | `74` |
| `190` | Aquos | not behind | `104` |
| `190` | Pyrus | behind | `114` |
| `190` | Aquos | behind | `144` |
| `525` | Pyrus | not behind | `101` |
| `525` | Aquos | not behind | `131` |
| `525` | Pyrus | behind | `141` |
| `525` | Aquos | behind | `171` |

The non-owner never receives the `+40 G` rider, even when the Gate owner's side is behind.

## Weighted battle-type selection

Juggernoid uses the six unsigned-byte weights:

| Type ID | Label | Weight | Probability |
|---:|---|---:|---:|
| `0` | Scratch | `50` | `25%` |
| `1` | Timing | `30` | `15%` |
| `2` | Pop | `30` | `15%` |
| `3` | Spin | `30` | `15%` |
| `4` | Trace | `30` | `15%` |
| `5` | Bound | `30` | `15%` |

The total is `200`.

### Selection precedence

```text
explicit constructor type 0-5
    -> use explicit type; do not call System 2.0 weighted selection

constructor type -1 with validated Juggernoid record
    -> call weighted selector 0x02021A30 with six record weights

constructor type -1 without a valid System 2.0 prototype record
    -> call original fixed-metadata selector 0x022433AC

scripted override code 1-6
    -> overwrite the provisional type exactly as the original game does

final type
    -> dispatch through the original six-way constructor path
```

Milestone 6C does not update battle history. The reserved history bytes remain zero and unused.

### Weighted-selector failure policy

Record validation requires the prototype's weight sum to be positive and every weight to fit the existing unsigned-byte contract. Therefore, a validated prototype record cannot intentionally request a zero-total roll.

If the confirmed weighted helper nevertheless returns `-1`, only the battle-type decision falls back to the original fixed metadata selector. Earlier validated Gate-G behavior is not rolled back because the phases are separate and the original battle object has already consumed the Gate result. The implementation must record this as a diagnostic failure path. This is a phase-local fail-closed rule, not permission for partial malformed-record behavior.

## Runtime architecture

The new overlay module is divided into focused units with explicit interfaces.

### Loader and cache

```text
LoadSelectedGateRecord(card_id)
ValidateSelectedRecord(record, card_id)
InvalidateGateCache()
```

Responsibilities:

- open NitroFS file ID `2762` through the confirmed interface;
- seek to the validated `G2DT` trailer;
- validate header geometry, version, order, CRCs, and selected record identity;
- copy only the selected 40-byte record and metadata into the 64-byte cache;
- leave the cache invalid on every failure;
- perform no filesystem reads during frame-critical battle processing;
- clear all 64 bytes at the confirmed battle-completion boundary.

### Context normalization

```text
BuildGateCalculationContext(battle, combatant)
BuildBattleTypeContext(battle)
```

Responsibilities:

- resolve Gate ID and owner;
- resolve the current combatant participant and attribute;
- expose compressed core G;
- expose solo or team score values;
- reject invalid, stale, scripted, or unavailable pointers;
- never read `arena_id`.

### Calculation and dispatch

```text
CalculateHybridGateBonus(record, context)
EvaluateGateCondition(record, context)
ResolveGateTarget(record, context)
DispatchGateEffect(record, context, bonus)
```

Responsibilities:

- use pure integer calculations;
- keep the base hybrid calculation separate from conditional effects;
- apply the effect at most once to the current combatant;
- return a result object containing component values, final value, and fallback status;
- perform no direct save or persistent roster writes.

### Battle-type selection

```text
SelectSystem2BattleType(record, context)
```

Responsibilities:

- run only in the original normal fallback path;
- call the confirmed ARM9 weighted selector;
- preserve explicit and scripted precedence;
- return the original metadata selector result on phase-local failure.

### Legacy replay

```text
RunLegacyGateBonus()
RunLegacyBattleTypeSelector()
```

Responsibilities:

- replay the displaced original instructions and calls exactly;
- preserve the merged core-G compression patch;
- avoid sharing partially calculated System 2.0 values with the fallback path.

## Fallback contract

### Record-level invalidation

The selected record is invalid for all System 2.0 behavior when any of the following is true before live calculation:

- trailer missing or truncated;
- invalid magic, version, geometry, record order, or CRC;
- selected card ID does not match the requested card;
- flags or reserved fields are nonzero;
- unsupported archetype, condition, effect, target, timing, drawback, or secondary ID;
- unsupported nonzero activation, fatigue, drawback, or secondary values;
- malformed attribute or weight vector;
- prototype weight sum is zero;
- hook guard or executable-layout guard fails.

An invalid selected record leaves the cache invalid and routes both the Gate-G and normal battle-type paths to complete original behavior.

### Calculation-level fallback

A structurally valid prototype record may still encounter invalid live context. For that combatant's Gate calculation, any unresolved Gate owner, participant, attribute, core-G value, score aggregation, or target causes the complete original Gate calculation to run. No partial flat, percentage, attribute, condition, or effect value may survive.

### Phase-local battle-type fallback

A valid record with a valid calculation may later encounter a battle-type-specific failure. An unexpected weighted-selector failure or invalid result uses the original fixed metadata selector for that battle-type phase. Explicit and scripted overrides remain authoritative.

### Unrelated Gates

Gate IDs other than `19` always execute original Gate-G and original battle-type behavior. Their cache record may be parsed and validated as legacy passthrough, but it must not alter gameplay or consume the weighted RNG.

## Calculation trace

Host and instrumentation traces use the existing version-1 deterministic trace format and must include, in order:

```text
card_id
combatant_participant
owner_participant
compressed_core_g
attribute_id
flat_bonus_g
percent_q8_8
scaled_component
attribute_modifier
base_gate_bonus
owner_side_score
opposing_side_score
condition_result
effect_value
effective_gate_bonus
legacy_fallback
fallback_reason
```

Battle-type traces must include:

```text
explicit_type_argument
record_valid
weights
weight_total
weighted_result
scripted_override_code
final_type
legacy_fallback
fallback_reason
```

Normal release builds do not display these traces to the player.

## Hook and memory constraints

The implementation must preserve the confirmed Milestone 6B layout:

- System 2.0 module: `0x0228BC20-0x02293C20`;
- 64-byte cache: `0x02293C20-0x02293C60`;
- original overlay-7 BSS size and addresses unchanged;
- battle-arena low boundary at `0x02293C60`;
- protected core-G compression offsets untouched.

The guarded hook boundaries remain:

| Purpose | Boundary | Legacy fallback |
|---|---:|---|
| Gate bonus | `0x0223D258-0x0223D278` | original table lookup, multiply-by-ten conversion, and store |
| Context/effect access | `0x0223D288-0x0223D290` | original add and target-total store |
| Battle-type selector | call at `0x0223E350` | original fixed selector `0x022433AC` |
| Expanded-data lookup | entry `0x022433AC` | displaced prologue and original continuation |

No hook may touch the protected core-G patch regions documented by Milestone 6B.

## Testing strategy

### Host unit tests

- exact Q8.8 rounding for positive, zero, and bounded negative schema values;
- all eight required calculation vectors;
- all six attribute indices;
- owner ahead, tied, and behind;
- non-owner calculation while owner is behind;
- solo and team score aggregation;
- human-owned and AI-owned Gate context;
- order independence between the two combatant calculations;
- signed-16 Gate-bonus and unsigned-16 target-total clamping;
- every unsupported enum and nonzero deferred field;
- record-level, calculation-level, and phase-local fallback distinctions;
- deterministic weighted selector controls with known seeds;
- explicit constructor bypass and scripted override precedence;
- legacy passthrough records do not consume RNG.

### Artifact and exact-binary tests

- exact version-1 header and record geometry;
- 103 sorted records and canonical passthrough records;
- Juggernoid record exact bytes;
- carrier file and trailer CRC guards;
- overlay module, cache, BSS, and arena boundaries;
- all hook-byte hashes;
- protected core-G patch bytes unchanged;
- no change to save-data structures or persistent roster data;
- no `arena_id` access in the prototype module.

### Runtime tests

The patched ROM must demonstrate:

1. Juggernoid loads a valid record into the cache.
2. A non-Aquos combatant receives the expected hybrid bonus.
3. An Aquos combatant receives the additional `+30 G` modifier.
4. A tied or leading Gate owner receives no comeback rider.
5. A behind Gate owner receives exactly `+40 G`.
6. The opposing combatant never receives the rider.
7. Human-owned and AI-owned Juggernoid use the same rules.
8. Juggernoid produces at least two controlled weighted battle-type outcomes under known RNG seeds.
9. Explicit constructor and scripted battle types bypass or supersede the weighted result.
10. An unrelated Gate reproduces its original G totals and fixed battle type.
11. A malformed prototype trailer reproduces complete original Juggernoid behavior.
12. The battle completes and returns to a responsive surrounding game state.
13. All 64 cache bytes clear at battle completion.
14. Persistent roster G, Gate inventory, save data, and unrelated battle state remain unchanged.

## Acceptance criteria

Milestone 6C is complete only when all of the following are true:

- the selected record loader, cache, parser, hybrid calculator, condition evaluator, target resolver, effect dispatcher, and weighted selector are implemented;
- Juggernoid demonstrates the approved prototype behavior in a rebuilt exact-profile ROM;
- all other Gate IDs preserve original behavior;
- malformed and context-invalid paths fail closed as specified;
- exact-ROM integration checks and runtime controls pass;
- the merged core-G compression patch is unchanged;
- no arena ID, save-data change, fatigue, Ability interaction, AI change, presentation change, or full-roster balance work is introduced;
- the final branch head passes the repository's complete test, compile, Ruff, strict mypy, and whitespace gates;
- the implementation evidence clearly distinguishes host proof, executable proof, and controlled runtime proof.

## Subsequent milestone boundary

Completion of this prototype does not approve Milestone 6D values or mechanics. Hybrid scaling standards, reusable attribute relationships, archetypes, power budgets, bounded probability policy, and the wider condition/effect library require a separate design review after the prototype is validated.
