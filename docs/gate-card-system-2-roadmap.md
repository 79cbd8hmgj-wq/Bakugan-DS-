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

No System 2.0 gameplay effect is implemented by Milestone 6A or Milestone 6B. Milestone 6C is now complete and enables only the reviewed Juggernoid prototype; it does not authorize the full roster or the Milestone 6D balance framework.

## Milestone 6A — reverse-engineering foundation

Completed foundation:

- complete legacy table geometry and global ID domain;
- selected card-ID mappings established without guide ordering;
- Gate activation and result lifecycle;
- original fixed battle-type selector and scripted overrides;
- initial confirmed hook-safe battle context;
- scalable storage and executable-layout decision;
- four guarded hook boundaries;
- reversible unchanged-result runtime instrumentation;
- compatibility constraints for the merged core-G compression patch.

## Milestone 6B — complete System 2.0 discovery

Milestone 6B postpones the first prototype and confirms every runtime dependency required by the full System 2.0 design.

### Mandatory confirmation gate

All of the following must be confirmed before prototype implementation:

- canonical Gate ownership;
- challenging and contesting participant identity;
- human-versus-AI identity;
- effect recipient targeting;
- match score and captured-Gate counters;
- Gate activation, reuse, capture, removal, and reset behavior;
- previous battle-type history storage and reset;
- suitable weighted-selection RNG and calling convention;
- Ability Card usage state and timing;
- landing and shot conditions;
- difficulty setting and battle access path;
- battle result, G-margin, capture, round-reset, and match-reset timing;
- raw NitroFS open, seek, read, close, validation, and fallback behavior;
- overlay module growth and original BSS preservation;
- selected-record cache initialization and invalidation;
- final version-1 `G2DT` header and 40-byte Gate record;
- authoring schema, serializer, validator, and calculation trace format.

A field is not confirmed until its semantics, owner structure, width, signedness, initialization, lifetime, mutation, reset, player/AI behavior, scripted behavior, and runtime or executable evidence are documented.

Candidate or probable evidence blocks Milestone 6C.

### Arena-ID exception

Arena ID is the only allowed unresolved context field at the end of Milestone 6B.

Consequences:

- no arena-dependent condition or effect may appear in the first prototype;
- version-1 records must not require arena state;
- the format must retain a versioned or reserved path for arena-aware behavior later;
- every other required context field must be confirmed.

### Storage and executable boundaries to validate

Primary design under investigation:

- append a 4,152-byte `G2DT` trailer after the raw LZ10 stream of file ID `2762`, `font/mes_CardName.mes`;
- retain the native decoded 6,524-byte message payload unchanged;
- preserve original overlay-7 BSS addresses as `0x640` zero-backed payload bytes;
- append a guarded `0x8000`-byte module at `0x0228BC20–0x02293C20`;
- reserve a 64-byte BSS cache at `0x02293C20–0x02293C60`;
- move the battle-arena low boundary to `0x02293C60`.

Fallback design under investigation:

- use the same trailer;
- read the 32-byte header and one 40-byte selected record into a 72-byte stack buffer;
- perform no frame-critical repeated filesystem reads.

Milestone 6B may build loader-only instrumentation, but malformed, missing, unsupported, stale, or checksum-invalid data must use original Gate behavior and no gameplay result may change.

### Hook boundaries to validate

| Purpose | Original boundary | Required fallback |
|---|---:|---|
| Gate bonus | `0x0223D258–0x0223D278` | replay original table lookup, ×10 conversion, and store |
| Context/effect access | `0x0223D288–0x0223D290` | replay original add and target-total store |
| Battle-type selector | call at `0x0223E350` | call original fixed selector `0x022433AC` |
| Expanded-data lookup | entry `0x022433AC` | replay displaced prologue and continue original function |

The protected core-G offsets `0x23C18–0x23C1C`, `0x23CB0–0x23CF8`, and `0x23D78–0x23D7C` must remain untouched.

### Completion rule

Milestone 6B ends with an automated readiness report that fails closed unless:

- every mandatory context field is confirmed;
- arena ID is the only deferred field;
- loader, cache, record, timing, RNG, lifecycle, and fallback evidence are complete;
- exact-ROM integration checks pass;
- no Gate bonus, battle type, condition, effect, AI decision, or roster value has changed.

The complete design is documented in `docs/superpowers/specs/2026-08-02-gate-card-system-2-complete-discovery-design.md`.

## Milestone 6C — engine and first prototype — complete

Completed deliverables:

- deterministic 4,152-byte `G2DT` trailer and 103-record authoring roster;
- selected-record NitroFS loader and 64-byte match-local cache;
- guarded `0x8000`-byte overlay-7 runtime module;
- fixed-point hybrid Gate calculation using compressed core G;
- Aquos `+30 G` attribute modifier;
- Gate-owner-behind `+40 G` condition and target rule;
- weighted Scratch preference `(50, 30, 30, 30, 30, 30)`;
- explicit-constructor and scripted-override precedence;
- complete record-, calculation-, and selector-phase fallback;
- exact-ROM deterministic rebuild proof;
- controlled emitted-ARM runtime matrix;
- live rebuilt-ROM Battle Arena, tutorial-completion, cache-clear, and responsive-exit smoke tests.

Only Gate ID `19`, Juggernoid, is active. Arena ID remains deferred. Ability interaction, fatigue, history penalties, AI, presentation, saves, reusable effects, power budgets, and the full roster remain excluded.

## Milestone 6D — core balance framework

- Finalize hybrid flat/percentage scaling.
- Define attribute relationships.
- Define Gate archetypes and internal power budgets.
- Establish bounded battle-type weights and probability rules.
- Implement the initial reusable condition and effect library.

## Milestone 6E — complete roster conversion

- Convert IDs `1–103` to System 2.0 records.
- Assign one readable identity to every Gate.
- Remove purely inferior duplicates through differentiated rules rather than simple inflation.
- Validate power budgets against compressed core G.
- Preserve selected exceptional cards intentionally.

## Milestone 6F — advanced stateful mechanics

- Enable battle-type history and repeat penalties.
- Add Gate fatigue and activation limits.
- Add ownership and contest mechanics using confirmed fields.
- Add comeback, risk, secondary-effect, and drawback conditions.
- Persist only the minimum state required for one match unless a later design explicitly approves save changes.

## Milestone 6G — AI and presentation

- Teach AI to evaluate the new Gate definitions.
- Replace or extend card descriptions with understandable effects.
- Display why conditions and modifiers activated.
- Add debug output for effective bonus components and final battle-type scores.
- Keep internal weights hidden from normal player-facing text.

## Milestone 6H — optional adaptive difficulty

- Investigate bounded player-performance statistics by battle type.
- Integrate adaptation only after the base system, history, AI, and presentation are stable.
- Avoid hidden forced-loss behavior.
- Keep adaptation optional and separately reviewable.

## Approval boundary

Completing Milestone 6B authorizes a separate Milestone 6C design and implementation plan. It does not authorize a prototype before the readiness validator passes, and it does not authorize full-roster balance values, fatigue, adaptive difficulty, AI changes, or presentation changes without their later design reviews.
