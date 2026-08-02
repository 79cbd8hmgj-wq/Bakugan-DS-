# Gate Card System 2.0 Reverse-Engineering Foundation Design

## Status

Approved replacement for the earlier Milestone 6A Gate-table-editor design.

This specification establishes **Gate Card System 2.0** as the long-term Gate Card roadmap and defines a revised **Milestone 6A** focused on reverse-engineering the original Gate system deeply enough to support that roadmap safely.

Milestone 6A does not implement the new Gate engine or rebalance the card roster. It confirms the original data, activation lifecycle, battle-type selection path, battle context, storage options, and hook feasibility. Milestone 6B will use those confirmed findings to implement the first data-driven System 2.0 prototype.

The superseded design remains useful as historical context for the legacy six-value table, but it is no longer the active implementation target.

## Product Direction

Gate Card System 2.0 changes Gate Cards from passive attribute-bonus tables into configurable field-rule cards.

Every completed System 2.0 Gate Card is intended to control three independent dimensions:

1. **G-Power influence**
2. **Battle-type influence**
3. **A unique field rule**

The long-term result should follow this model:

```text
Gate Card result =
    moderate scalable G bonus
    + attribute relationship
    + weighted battle-type preference
    + one unique field effect
    + optional condition or drawback
```

The system must remain understandable to players. Internal weights and conditions may be complex, but displayed descriptions must explain the effective rule rather than expose raw implementation values.

## Relationship to the Existing Core-G Patch

The bounded core-G compression patch remains authoritative:

```text
core <= 400: unchanged
core > 400: 200 + floor(core / 2)
```

Any future percentage-based Gate component must use the **compressed battle core-G snapshot**, not the original persistent roster value. Otherwise, Gate scaling could restore part of the late-game inflation removed by Milestone 5.

The intended future formula is:

```text
effective_gate_bonus =
    flat_bonus
    + percentage_of_compressed_core_g
    + attribute_modifier
    + conditional_modifier
```

System 2.0 must use integer or fixed-point arithmetic with documented rounding. It must not depend on floating-point behavior.

## Confirmed Runtime Baseline

The original game currently applies Gate bonuses through:

```text
gate_raw_value = gate_table[gate_card_id * 6 + attribute_id]
gate_bonus_g = gate_raw_value * 10
target_total_g = compressed_core_g + gate_bonus_g
```

Confirmed symbols:

| Role | Runtime address | Component |
|---|---:|---|
| Gate/attribute lookup helper | `0x02065BF4` | runtime-decompressed ARM9 |
| Gate attribute-bonus table base | `0x020A15AC` | runtime-decompressed ARM9 |
| Add base and Gate bonus | `0x0223D288` | overlay 7 |
| Store target total | `0x0223D28C` | overlay 7 |
| Battle record initializer | `0x0223CFE8` | overlay 7 |

Confirmed examples include:

```text
230 + 180 = 410
190 + 100 = 290
```

These findings confirm the original lookup and displayed-unit conversion. They do not yet confirm the full Gate table extent, all card IDs, activation lifecycle, ownership state, battle-type selector, or effect paths.

## Evidence Rules

### ROM-derived evidence

The user-owned reference ROM is authoritative for executable behavior, table bytes, record formats, code references, storage layout, and ID domains.

### Runtime evidence

Controlled emulator traces are authoritative for state ownership, activation timing, selected card IDs, attribute IDs, battle-type results, and observed behavior after a rebuilt patch.

### External reference material

The locally supplied Gate Card guide and Gate Card System 2.0 proposal are design and research inputs. They are not authoritative for ROM ordering, numeric IDs, function addresses, or existing implementation details.

Guide order must never assign ROM IDs automatically. The repository must not contain a copied complete guide table.

### Confidence labels

Every discovery must use the existing confidence model:

- `confirmed`: demonstrated through executable evidence and runtime validation;
- `probable`: strong evidence but not yet directly observed;
- `candidate`: useful lead requiring validation.

Only confirmed fields may become required inputs to the System 2.0 runtime context.

## Long-Term Roadmap

### Milestone 6A - Reverse-engineering foundation

Confirm the legacy Gate data, activation lifecycle, battle-type selector, usable battle context, expansion storage options, and safe hook points.

### Milestone 6B - System 2.0 engine prototype

Implement the expanded data format, centralized Gate calculation, battle-type weighting, condition/effect dispatch, and one experimental Gate Card.

### Milestone 6C - Core balance framework

Define hybrid scaling, attribute relationships, archetypes, power budgets, probability bounds, and the initial reusable effect library.

### Milestone 6D - Full roster conversion

Convert and rebalance the complete Gate Card roster with one clear identity per card and remove purely inferior duplicates.

### Milestone 6E - Advanced stateful mechanics

Add battle-type history, fatigue, ownership and contest mechanics, comeback conditions, risk conditions, secondary effects, and drawbacks.

### Milestone 6F - AI and presentation

Teach AI to evaluate the new system, update descriptions, display activated effects and conditions, and add debugging output for final calculations.

### Milestone 6G - Optional adaptive difficulty

Investigate bounded player-performance adaptation and difficulty-based weighting only after the base system, AI, and presentation are stable. This phase must avoid hidden forced-loss behavior.

## Milestone 6A Goals

Milestone 6A must answer the following questions with evidence:

1. What is the complete legacy Gate Card data model?
2. How does a Gate Card move from placement to activation, battle, capture, removal, or reuse?
3. Where is Gate ownership stored and how is the benefiting participant selected?
4. How is the battle type chosen, and what inputs influence it?
5. Which battle-state values can safely support conditions and effects?
6. Where can expanded System 2.0 data live without breaking ROM layout or runtime memory?
7. Where can the original calculation and selection paths be redirected safely?
8. Can the required hooks coexist with core-G compression and current overlay constraints?

## Milestone 6A Non-Goals

Milestone 6A will not:

- assign new bonuses to the Gate Card roster;
- implement archetypes or power budgets;
- implement hybrid scaling in normal gameplay;
- implement a generic effect dispatcher;
- change battle-type probabilities;
- add fatigue, performance adaptation, or difficulty behavior;
- modify AI decisions;
- rewrite descriptions or UI;
- change shops, unlocks, card names, or graphics;
- add a polished public Gate editor;
- claim a full source decompilation.

A minimal controlled patch may be used to verify a discovered mapping or hook site, but no System 2.0 gameplay feature is considered implemented until Milestone 6B.

## Workstream 1: Legacy Gate Data

The original six-value table remains the first workstream because it provides canonical card IDs and compatibility behavior.

Milestone 6A must confirm:

- element width and signedness;
- record stride;
- record count and legal card-ID range;
- attribute-ID order;
- table boundaries and adjacent data ownership;
- runtime-to-stored ARM9 mapping;
- whether some IDs are sentinels, unused, or effect-only;
- several card-ID-to-name mappings established independently of guide order.

Required local outputs:

```text
work/reports/gates/legacy-table.json
work/reports/gates/card-id-evidence.json
```

These files are generated from the user-owned ROM and ignored by Git.

The repository may contain schema metadata, hashes, selected normalized examples, and confidence evidence, but not the complete original table.

## Workstream 2: Gate Activation Lifecycle

Trace the Gate Card from placement through battle resolution.

The investigation must identify, where present:

- Gate placement or registration;
- active Gate selection;
- card owner identity;
- contesting participant identity;
- Bakugan landing or occupancy state;
- trigger timing for the attribute bonus;
- Gate activation count or equivalent state;
- first-use versus repeated-use behavior;
- capture, removal, persistence, or reset after battle;
- story or tutorial overrides;
- AI-specific activation paths.

The lifecycle should be documented as a state transition sequence rather than a list of isolated functions.

Expected normalized output:

```text
analysis/gates/activation-lifecycle.yaml
```

Each transition must record component, runtime address, relative offset, evidence, and confidence.

## Workstream 3: Battle-Type Selection Pipeline

System 2.0 requires Gate Cards to influence battle types without necessarily guaranteeing them. Milestone 6A must therefore locate the original selector before any scoring replacement is designed.

Confirm:

- the complete set of selectable battle types;
- the function or functions that choose the type;
- RNG call sites and random range;
- existing probability tables or weights;
- Gate Card inputs;
- Bakugan or attribute inputs;
- arena or story inputs;
- difficulty inputs;
- AI inputs;
- where the selected type is stored;
- whether the selector supports forced outcomes;
- whether tutorial or scripted battles bypass the normal selector.

The investigation must distinguish actual weighting from presentation labels in external references.

Expected normalized outputs:

```text
analysis/gates/battle-type-selector.yaml
analysis/symbols/battle_types.csv
```

## Workstream 4: Battle Context Model

The future effect dispatcher needs a small, explicit, evidence-backed context structure. Milestone 6A must map candidate runtime fields and classify each one.

Priority fields:

```text
active Gate card ID
Gate owner
contesting participant
current combatants
Bakugan attributes
compressed core G for each combatant
current Gate bonus
current match score or captured-Gate count
Ability Card usage state
Gate activation or reuse state
previous battle types
landing or shot condition
arena or field identifier
difficulty
human versus AI participant
```

For every field, record:

- semantic meaning;
- width and signedness;
- owning structure;
- lifetime;
- initialization and reset path;
- runtime address or access pattern;
- whether it is safe to read from a future hook;
- confidence.

Fields that cannot be confirmed remain excluded from the first System 2.0 context.

Expected output:

```text
analysis/gates/battle-context.yaml
```

## Workstream 5: Expansion Storage Strategy

The original six-byte record cannot contain the proposed System 2.0 data. Milestone 6A must compare concrete storage approaches against the actual ROM and runtime constraints.

### Candidate A: New NitroFS configuration file

Potential advantages:

- clean data-driven authoring;
- expandable without enlarging ARM9 tables;
- easier balance iteration.

Required evidence:

- safe file-loading path during battle initialization;
- available heap or arena capacity;
- deterministic rebuild support;
- failure behavior for missing or malformed data;
- acceptable load timing.

### Candidate B: Expanded executable or overlay data region

Potential advantages:

- direct indexed access;
- no runtime file parser.

Required evidence:

- safe code or data space;
- overlay-size and BSS implications;
- relocation requirements;
- compatibility with compression and rebuilding.

### Candidate C: Dedicated new overlay

Potential advantages:

- isolated code and data;
- clearer ownership.

Required evidence:

- overlay table capacity or replacement strategy;
- load/unload coordination;
- address-space conflicts;
- call routing and relocation support.

### Candidate D: Hybrid model

Use compact IDs or cached fields in battle memory while loading full definitions from NitroFS or a dedicated region.

Milestone 6A must recommend one strategy with evidence and identify a fallback. It must not select a strategy solely because it is easiest to describe.

## Workstream 6: Hook and Dispatcher Feasibility

Locate safe integration points for the future conceptual interfaces:

```text
CalculateGateBonus(context, gate_data)
ScoreBattleTypes(context, gate_data, history)
EvaluateGateCondition(condition_id, context)
ApplyGateEffect(effect_id, value, context)
UpdateGateHistory(history, result)
```

Milestone 6A does not implement these complete routines. It must identify and validate the call boundaries needed for Milestone 6B.

For every proposed hook, record:

- original function and instruction range;
- component and runtime address;
- component-relative offset;
- calling convention and live registers;
- stack assumptions;
- overwritten behavior;
- return path;
- code-space strategy;
- compatibility with the core-G patch;
- failure and rollback strategy.

At minimum, feasibility must be established for:

1. replacing or wrapping the legacy Gate bonus lookup;
2. influencing or replacing the battle-type selector;
3. reading the confirmed battle context;
4. loading or locating expanded Gate data.

A small reversible instrumentation hook may be built to prove register and control-flow assumptions. It must preserve original gameplay behavior.

## Future System 2.0 Data Requirements

Milestone 6A must produce enough evidence for Milestone 6B to finalize a data structure supporting, at minimum:

```text
card ID
archetype
rarity or progression tier
flat bonus
fixed-point percentage bonus
six attribute modifiers
battle-type weights
preferred battle type
primary effect ID and value
secondary effect ID and value
activation condition
drawback condition
activation limit
fatigue rate
flags
```

These fields are roadmap requirements, not confirmed binary layout. Milestone 6B may revise widths or encoding based on the storage and runtime findings.

## Future Balance Principles Preserved by 6A

The following System 2.0 principles are approved for later milestones and must influence discovery priorities:

- effective swing matters more than raw stored G;
- stronger effects require smaller G bonuses or meaningful drawbacks;
- negative attribute values may fund stronger identities;
- Gate archetypes should be recognizable;
- Gate influence should tend toward battle types rather than always force them;
- repeats should be discouraged contextually rather than completely banned;
- ownership, match state, and landing conditions may enable effects;
- unique effects should be data-driven rather than one custom function per card;
- player-facing descriptions must explain activations;
- hidden performance adaptation is optional and deferred.

No exact power-budget costs, power bands, probability bounds, fatigue curve, or card assignment is finalized in Milestone 6A.

## CLI and Analysis Support

Milestone 6A may add analysis commands equivalent to:

```bash
bakugan-ds gate inspect WORKSPACE
bakugan-ds gate export-legacy WORKSPACE OUTPUT.json
bakugan-ds gate report-context WORKSPACE OUTPUT.json
```

These commands are analysis tools, not the final System 2.0 editor.

They must:

- require the exact supported ROM profile;
- avoid dumping copyrighted data by default;
- generate deterministic local reports;
- include confidence and source metadata;
- fail closed on ambiguous mappings;
- keep generated outputs outside source control.

## Error Handling

The investigation tooling must distinguish:

- unsupported ROM profile;
- missing or inconsistent workspace manifests;
- unresolved runtime-to-stored mapping;
- ambiguous table boundary;
- stale region hash;
- unconfirmed attribute order;
- unconfirmed card-ID range;
- unresolved lifecycle transition;
- ambiguous ownership source;
- selector bypass or scripted path;
- conflicting candidate battle-context fields;
- insufficient code or data space;
- unsafe hook overwrite;
- decompression or recompression failure;
- rebuilt component size or metadata mismatch.

A failed controlled patch must leave the modified workspace unchanged.

## Testing Strategy

### Unit tests

Use repository-safe synthetic fixtures for:

- fixed-record legacy-table parsing;
- runtime-to-stored address mapping;
- confidence validation;
- lifecycle transition serialization;
- battle-context schema validation;
- selector-weight trace representation;
- hook metadata validation;
- deterministic reports;
- atomic guarded instrumentation patches.

### Reference-ROM integration tests

With `BAKUGAN_DS_ROM` supplied locally, verify:

- exact ROM profile;
- legacy table base and region hash;
- confirmed record stride and table extent;
- deterministic legacy export;
- selected card-ID and attribute examples;
- confirmed function bytes at lifecycle and selector candidates;
- stored/runtime mapping for every confirmed symbol;
- controlled instrumentation changes only intended bytes;
- rebuilt ROM structural validity;
- core-G compression patch bytes remain unchanged;
- unrelated FAT payloads remain byte-identical unless an explicitly tested storage experiment requires otherwise.

### Emulator validation

Milestone 6A runtime validation must use a clean rebuilt ROM rather than restoring executable RAM from a save state.

Validation must demonstrate:

1. a confirmed Gate Card ID reaching the legacy lookup;
2. confirmed owner and combatant state at activation;
3. the normal battle-type selector or a documented scripted bypass;
4. at least one confirmed battle-context field beyond G and attribute;
5. reversible instrumentation at one proposed hook boundary without changing gameplay results;
6. completion or safe exit of the battle path;
7. return to a responsive story or menu state.

Milestone 6A must not claim a working System 2.0 effect or rebalance.

## Documentation Outputs

Expected repository additions include:

```text
analysis/gates/
├── activation-lifecycle.yaml
├── battle-type-selector.yaml
├── battle-context.yaml
├── expansion-strategy.md
└── hook-feasibility.yaml

analysis/candidates/
└── gate-card-system-2.yaml

analysis/symbols/
├── gate_cards.csv
└── battle_types.csv

docs/
├── gate-card-legacy-system.md
├── gate-card-runtime-lifecycle.md
└── gate-card-system-2-roadmap.md
```

Exact filenames may follow established repository conventions, but the evidence products must remain separated by responsibility.

## Copyright Boundary

The repository may contain:

- code and schemas;
- addresses, offsets, hashes, and formulas;
- normalized lifecycle and context evidence;
- minimal guarded bytes required for patches;
- selected runtime examples;
- design requirements and roadmap documentation.

It must not contain:

- ROMs or rebuilt ROMs;
- extracted executables or game assets;
- RAM dumps, save states, or screenshots;
- the complete original Gate table;
- copied GameFAQs tables;
- a complete game-text database.

Local exports and debugging artifacts must be ignored by Git.

## Success Criteria

Milestone 6A succeeds when the repository can support all of the following claims with evidence:

1. The legacy Gate table format, extent, attribute order, and ID domain are confirmed.
2. Several card IDs are mapped independently of guide order.
3. The Gate activation lifecycle is documented from placement or selection through post-battle handling.
4. Gate ownership and benefiting participant selection are confirmed.
5. The normal battle-type selector, RNG path, and scripted bypasses are distinguished.
6. A minimal confirmed battle-context model is available for future effects.
7. Expanded System 2.0 storage strategies are evaluated against actual memory and ROM constraints.
8. One primary storage strategy and one fallback are recommended.
9. Safe hook boundaries are confirmed for Gate bonus calculation, battle-type selection, context access, and expanded data lookup.
10. Reversible instrumentation proves at least one hook boundary without altering gameplay results.
11. The rebuilt ROM completes or exits the tested battle and returns to a responsive state.
12. Existing core-G compression behavior remains intact.
13. No copyrighted runtime artifacts are committed.

## Implementation Planning Order

The Milestone 6A implementation plan should proceed in this order:

1. confirm and export the legacy Gate table;
2. map card IDs and attribute order with controlled runtime cases;
3. trace the Gate activation lifecycle;
4. locate and validate the battle-type selector;
5. build the confirmed battle-context map;
6. evaluate expanded storage strategies;
7. identify hook boundaries and code-space options;
8. implement reversible instrumentation;
9. run exact-ROM integration and emulator validation;
10. normalize documentation and prepare the Milestone 6B handoff.

## Milestone 6B Handoff

Milestone 6B begins only after this specification's success criteria are met.

Its design must select the concrete storage format and implement:

- centralized hybrid Gate bonus calculation;
- fixed-point percentage scaling from compressed core G;
- six attribute modifiers;
- battle-type preference weights;
- a bounded condition evaluator;
- a generic effect dispatcher;
- one experimental System 2.0 Gate;
- original behavior for all non-prototype Gates;
- clean-ROM battle completion and exit validation.

The complete roster rebalance remains deferred to Milestones 6C and 6D.
