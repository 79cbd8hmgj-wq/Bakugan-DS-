# Gate Card System 2.0 Roadmap

## Goal

Gate Card System 2.0 turns Gate Cards from six passive attribute numbers into data-driven field rules with three independent dimensions:

```text
G-Power influence
+ battle-type influence
+ one unique field rule
```

The complete target remains:

```text
moderate scalable G bonus
+ attribute relationship
+ weighted battle-type preference
+ one unique field effect
+ optional condition or drawback
```

No System 2.0 gameplay effect is implemented by Milestone 6A.

## Milestone 6A result

The reverse-engineering foundation provides:

- the complete legacy table geometry and global ID domain;
- selected card-ID mappings established without guide ordering;
- the Gate activation and result lifecycle;
- the original fixed battle-type selector and scripted overrides;
- a minimal confirmed hook-safe battle context;
- a scalable storage and executable-layout decision;
- four guarded hook boundaries;
- reversible unchanged-result runtime instrumentation;
- compatibility constraints for the merged core-G compression patch.

## Milestone 6B input contract

Milestone 6B implements one experimental System 2.0 Gate and must use these exact boundaries.

### Data storage

Primary:

- append a 4,152-byte `G2DT` trailer after the raw LZ10 stream of file ID `2762`, `font/mes_CardName.mes`;
- retain the native decoded 6,524-byte message payload unchanged;
- preserve original overlay-7 BSS addresses as `0x640` zero-backed payload bytes;
- append a guarded `0x8000`-byte module at `0x0228BC20–0x02293C20`;
- reserve a 64-byte BSS cache at `0x02293C20–0x02293C60`;
- move the battle-arena low boundary to `0x02293C60`.

Fallback:

- use the same trailer;
- read the 32-byte header and one 40-byte selected record into a 72-byte stack buffer;
- perform no frame-critical repeated filesystem reads.

Malformed, missing, unsupported, stale, or checksum-invalid data must use the original Gate behavior.

### Hook boundaries

| Purpose | Original boundary | Required fallback |
|---|---:|---|
| Gate bonus | `0x0223D258–0x0223D278` | replay original table lookup, ×10 conversion, and store |
| Context/effect access | `0x0223D288–0x0223D290` | replay original add and target-total store |
| Battle-type selector | call at `0x0223E350` | call original fixed selector `0x022433AC` |
| Expanded-data lookup | entry `0x022433AC` | replay displaced prologue and continue original function |

The protected core-G offsets `0x23C18–0x23C1C`, `0x23CB0–0x23CF8`, and `0x23D78–0x23D7C` must not be modified by System 2.0 hooks.

### First prototype record

The prototype Gate contains only:

```text
flat bonus
+ fixed-point percentage of compressed core G
+ one attribute modifier
+ one battle-type weight
+ one bounded condition/effect
```

Percentage scaling uses the compressed core-G register value before the mutable modifier. It must not use persistent roster G or the post-modifier base snapshot.

All arithmetic is integer or fixed-point with one documented rounding rule. Floating point is prohibited.

### Compatibility behavior

- Only one explicitly selected Gate ID uses the prototype definition.
- Every other Gate retains original six-byte bonus and fixed battle-type behavior.
- Invalid cache or trailer state immediately selects legacy behavior.
- Both player and AI combatants use the same calculation rules.
- Mutable modifiers, field pickups, persistent roster values, and the existing core-G curve remain unchanged.
- The rebuilt ROM must boot without executable save-state restoration, enter the controlled battle, complete or safely exit, return to responsive story or menu, and preserve unrelated Gate behavior.

## Milestone 6C — core balance framework

- Finalize hybrid flat/percentage scaling.
- Define attribute relationships.
- Define Gate archetypes and internal power budgets.
- Establish bounded battle-type weights and probability rules.
- Implement the initial reusable condition and effect library.

## Milestone 6D — complete roster conversion

- Convert IDs `1–103` to System 2.0 records.
- Assign one readable identity to every Gate.
- Remove purely inferior duplicates through differentiated rules rather than simple inflation.
- Validate power budgets against compressed core G.
- Preserve selected exceptional cards intentionally.

## Milestone 6E — advanced stateful mechanics

- Add battle-type history and repeat penalties.
- Add Gate fatigue and activation limits.
- Confirm and add ownership/contest behavior.
- Add comeback, risk, secondary-effect, and drawback conditions.
- Persist only the minimum state required for one match unless a later design explicitly approves save changes.

## Milestone 6F — AI and presentation

- Teach AI to evaluate the new Gate definitions.
- Replace or extend card descriptions with understandable effects.
- Display why conditions and modifiers activated.
- Add debug output for effective bonus components and final battle-type scores.
- Keep internal weights hidden from normal player-facing text.

## Milestone 6G — optional adaptive difficulty

- Investigate bounded player-performance statistics by battle type.
- Integrate difficulty only after the base system, history, AI, and presentation are stable.
- Avoid hidden forced-loss behavior.
- Keep adaptation optional and separately reviewable.

## Approval boundary

Completing Milestone 6A authorizes a separate Milestone 6B design and implementation plan. It does not authorize full-roster balance values, fatigue, adaptive difficulty, AI changes, or presentation changes without their later design reviews.
