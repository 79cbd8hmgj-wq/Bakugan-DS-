# Gate Card System 2.0 — Complete Discovery Design

**Status:** Approved design direction

**Milestone:** 6B

**Branch:** `milestone-6b-complete-system-discovery`

## Purpose

Milestone 6B completes the reverse engineering required by the full Gate Card System 2.0 roadmap before any prototype gameplay effect is implemented.

Milestone 6A confirmed the legacy Gate table, global card IDs, attribute order, activation and result paths, the fixed battle-type selector, an initial hook-safe context, storage feasibility, and four guarded hook boundaries. It also identified several context fields whose semantics or lifetimes were still unresolved.

The first prototype is postponed. Milestone 6B must confirm every required runtime field and lifecycle listed below, with **arena ID as the only explicit exception**.

## Core principle

A context field is not available to System 2.0 merely because a plausible byte, pointer, or function exists.

A required field becomes confirmed only when evidence establishes:

1. its semantic meaning;
2. its exact owner structure and access path;
3. its width and signedness;
4. its initialization point;
5. its valid lifetime;
6. its mutation points;
7. its reset or destruction behavior;
8. whether it is shared by player and AI paths;
9. whether scripted battles bypass or replace it;
10. a controlled runtime observation or equivalent executable proof.

Candidate or probable evidence is insufficient for a required Milestone 6B field.

## Mandatory discovery workstreams

### 1. Gate ownership and participant identity

Confirm:

- canonical Gate owner;
- challenging or contesting participant;
- both combatant identities;
- which participant receives owner-only, opponent-only, winner-only, and loser-only effects;
- human-versus-AI identity;
- whether the same representation is used in normal, tutorial, story-scripted, and AI-versus-player battles;
- initialization, transfer, capture, removal, and reset behavior.

The generic Gate-card-get cut-in actor byte is not sufficient unless it is proven to be the canonical ownership source used by gameplay logic.

### 2. Match score and captured-Gate state

Confirm:

- current match score or equivalent win-state counter;
- captured Gate count for each participant;
- match victory threshold;
- score update function;
- score reset function;
- result-state timing relative to Gate capture and removal;
- whether story or tutorial battles use alternate counters;
- hook-safe access before and after battle resolution.

This workstream must distinguish presentation values from authoritative gameplay state.

### 3. Gate activation, reuse, capture, and removal

Confirm:

- activation count or prove that no original counter exists;
- repeated activation behavior;
- reusable versus one-use state;
- capture bookkeeping;
- board removal;
- object cleanup versus actual gameplay removal;
- reset timing at battle, round, and match boundaries;
- whether the original game can activate the same Gate more than once;
- a safe location for new fatigue or activation-history state.

Milestone 6B must not treat scene destruction as proof of Gate removal.

### 4. Battle-type history and weighted-selection RNG

Confirm:

- a suitable game RNG function and calling convention;
- output width and range;
- deterministic or seeded behavior;
- safe integer weighted-selection implementation;
- scripted override precedence;
- where selected battle type is committed;
- where previous battle types can be stored;
- update and reset timing for battle-type history;
- player and AI symmetry;
- repeat-penalty feasibility without save-format changes.

The original selector remains fixed metadata. Any weighted selection is new System 2.0 behavior and must have an independently validated fallback to the original selector.

### 5. Ability Card usage and timing

Confirm:

- authoritative Ability Card usage state for both participants;
- used, available, selected, and resolved states;
- activation and resolution handlers;
- whether usage is tracked per battle, round, or match;
- reset behavior;
- timing relative to Gate bonus calculation and battle-type selection;
- safe points for conditions such as “before an Ability is used,” “after an Ability resolves,” and “no Ability used.”

Presentation menus or card-selection UI are not authoritative unless tied to the gameplay state consumed by battle resolution.

### 6. Landing and shot conditions

Confirm:

- landing result data carried into Gate activation;
- shot type or launch quality where available;
- critical, clean, failed, bounced, or equivalent landing outcomes used by gameplay;
- participant association;
- initialization and reset behavior;
- whether tutorial and scripted paths replace these values;
- safe condition-evaluation timing.

Only conditions supported by confirmed gameplay state may enter the first System 2.0 effect library.

### 7. Difficulty

Confirm:

- authoritative difficulty setting;
- valid values and meaning;
- owner structure or persistent source;
- when it is loaded into battle logic;
- whether AI behavior reads it directly or through derived parameters;
- reset or profile-change behavior;
- safe read-only access for future difficulty-aware effects or AI evaluation.

Difficulty is mandatory discovery even if the first prototype does not use it.

### 8. Battle result and effect timing

Confirm authoritative timing and context for:

- pre-Gate calculation;
- post-Gate calculation;
- pre-battle-type selection;
- post-battle-type selection;
- battle start;
- Ability activation;
- Ability resolution;
- battle win or loss;
- G-Power margin;
- Gate capture;
- Gate removal;
- round reset;
- match reset.

For each timing point, document live registers, owner objects, valid context fields, mutation safety, scripted bypasses, and rollback behavior.

### 9. Expanded-data loader and cache lifecycle

Confirm and prototype only infrastructure behavior, not a gameplay effect:

- raw NitroFS open, seek, read, and close functions;
- exact file-ID access path for `font/mes_CardName.mes`;
- raw LZ10 trailer offset and validation flow;
- header and record checksum implementation;
- stack requirements for the 72-byte fallback read;
- overlay-growth metadata updates;
- original BSS preservation;
- System 2.0 module load address;
- selected-record cache initialization;
- cache invalidation and reset;
- malformed-data fallback;
- deterministic rebuild and rollback.

A loader-only instrumentation build may read and validate a synthetic trailer and report success without changing Gate bonuses, battle types, or results.

### 10. Final record and effect-dispatch requirements

Use confirmed findings to finalize:

- the 32-byte `G2DT` header;
- the fixed 40-byte Gate record;
- field widths and signedness;
- fixed-point percentage format;
- battle-type weight encoding;
- condition and effect IDs;
- drawback representation;
- reserved/versioned fields;
- checksum coverage;
- unsupported-version behavior;
- authoring JSON schema;
- deterministic binary serializer;
- validation errors;
- trace/debug output.

The record may reserve an arena-related field or effect capability, but **arena ID is not required to be confirmed in Milestone 6B**.

## Arena-ID exception

Arena ID is the only discovery item explicitly allowed to remain unresolved at Milestone 6B completion.

Requirements:

- document that arena ID is deferred;
- do not include arena-dependent conditions or effects in the first prototype;
- reserve no mandatory runtime dependency on arena state;
- ensure the record format can add arena-aware behavior through a later version or reserved field without invalidating version 1 records.

All other mandatory fields must be confirmed or Milestone 6B remains incomplete.

## Required artifacts

Milestone 6B should produce normalized evidence and documentation for:

```text
analysis/gates/ownership-and-participants.json
analysis/gates/match-score-and-capture.json
analysis/gates/gate-reuse-and-removal.json
analysis/gates/battle-history-and-rng.json
analysis/gates/ability-card-state.json
analysis/gates/landing-and-shot-context.json
analysis/gates/difficulty-context.json
analysis/gates/effect-timing.json
analysis/gates/loader-and-cache.json
analysis/gates/system2-record-v1.json
analysis/symbols/gate_system2_context.csv
docs/gate-card-system-2-runtime-context.md
docs/gate-card-system-2-data-format.md
```

Exact paths may change during implementation planning, but each workstream must end in a deterministic, reviewable artifact with confidence labels and copyright-safe evidence.

## CLI and analysis requirements

Extend the Gate analysis interface with commands or reports that can:

- validate each required context artifact;
- list confirmed and unresolved fields;
- verify all mandatory fields are confirmed except arena ID;
- serialize and parse a synthetic version-1 record;
- validate a synthetic `G2DT` trailer;
- report loader/cache geometry;
- reject missing evidence, duplicate fields, unsafe lifetimes, invalid widths, and incomplete reset semantics;
- generate a Milestone 6C readiness report.

The readiness report must fail closed. Candidate, probable, missing, or contradictory evidence for any mandatory field blocks the prototype milestone.

## Runtime evidence requirements

Use clean executable launches rather than executable save states for final runtime validation.

Required scenarios should include, where applicable:

- normal player battle;
- AI opponent path;
- tutorial or scripted battle;
- Ability Card usage and non-usage controls;
- Gate capture and match-score update;
- repeated Gate or round transition;
- landing-condition controls;
- at least two difficulty settings;
- loader success with a synthetic valid trailer;
- malformed or absent trailer fallback;
- clean battle exit and responsive surrounding game.

Raw ROM data, RAM dumps, save states, screenshots, complete tables, and debugger logs remain local. Commit only normalized observations, hashes, addresses, formulas, and bounded selected examples.

## Success criteria

Milestone 6B is complete only when:

1. every mandatory context field is `confirmed`;
2. arena ID is the only explicitly deferred field;
3. ownership and participant targeting are unambiguous;
4. match score, capture, reuse, and reset lifecycles are documented;
5. Ability Card state and timing are confirmed;
6. landing or shot conditions are confirmed;
7. difficulty is confirmed;
8. weighted-selection RNG and history storage are feasible and documented;
9. all effect timing boundaries are documented;
10. raw-trailer loading, validation, cache, and fallback are proven without gameplay changes;
11. the final version-1 record and authoring schema are fixed;
12. an automated readiness validator rejects incomplete evidence;
13. full tests, linting, typing, deterministic rebuild checks, and exact-ROM integration checks pass;
14. no Gate bonus, battle-type probability, condition, effect, or roster value has been changed.

## Non-goals

Milestone 6B does not:

- implement a System 2.0 Gate;
- change Gate bonuses;
- change battle-type selection;
- add fatigue or history to live gameplay;
- change Ability Card behavior;
- change AI decisions;
- add arena-dependent logic;
- rebalance the roster;
- change card descriptions or UI;
- change the save format.

## Handoff to Milestone 6C

Milestone 6C begins only after the readiness validator passes.

Milestone 6C will then implement:

- the data-driven loader and cache;
- the version-1 record parser;
- the calculation and condition dispatcher;
- weighted battle-type selection;
- one experimental Gate using confirmed context only;
- complete legacy fallback for every unrelated Gate and every malformed-data path.
