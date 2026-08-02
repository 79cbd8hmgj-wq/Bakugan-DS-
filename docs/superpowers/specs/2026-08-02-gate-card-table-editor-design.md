# Gate Card Table Discovery and Editor Design

## Status

Approved Milestone 6 direction, scoped as **Milestone 6A**: discover, verify, export, and safely edit the Gate Card attribute-bonus table for **Bakugan: Battle Brawlers (Nintendo DS, USA revision 0)**.

The actual numeric Gate Card rebalance is intentionally deferred to Milestone 6B. No balance values will be changed until the table extent, record format, card-ID domain, attribute order, and editable ROM representation are confirmed.

## Motivation

Milestones 1-5 established the complete analysis-to-build-to-emulator workflow:

- exact reference-ROM validation;
- deterministic extraction and rebuilding;
- guarded binary patches;
- static and runtime battle-engine analysis;
- a confirmed G-Power pipeline;
- the bounded core G-Power compression patch;
- clean-ROM tutorial completion and return to story.

The next approved target is Gate Card data. This is the lowest-risk continuation because the runtime lookup path is already confirmed and Gate bonuses remain deliberately separate from the core-G compression patch.

## Confirmed Runtime Baseline

The current evidence establishes the following behavior:

```text
gate_raw_value = gate_table[gate_card_id * 6 + attribute_id]
gate_bonus_g = gate_raw_value * 10
target_total_g = base_snapshot_g + gate_bonus_g
```

Confirmed runtime symbols:

| Role | Runtime address | Component |
|---|---:|---|
| Gate/attribute lookup helper | `0x02065BF4` | runtime-decompressed ARM9 |
| Gate attribute-bonus table base | `0x020A15AC` | runtime-decompressed ARM9 |
| Add base and Gate bonus | `0x0223D288` | overlay 7 |
| Store target total | `0x0223D28C` | overlay 7 |

Confirmed tutorial examples include:

```text
230 + 180 = 410
190 + 100 = 290
```

These values confirm the lookup-to-display unit conversion and the separation of core G from the Gate contribution. They do not, by themselves, establish the full table extent, every card ID, or the complete attribute enumeration.

## Source and Evidence Boundaries

Three source classes must remain distinct.

### 1. ROM-derived evidence

The user-owned reference ROM is authoritative for:

- table bytes;
- executable lookup behavior;
- card-ID values used at runtime;
- attribute IDs used at runtime;
- table extent and element format;
- editable binary location and compression mapping.

### 2. Runtime evidence

Controlled emulator traces are authoritative for:

- a specific card ID selecting a specific record;
- a specific attribute ID selecting a specific element;
- the displayed Gate bonus and resulting total;
- whether a rebuilt edit is used by the game.

### 3. External reference material

The locally supplied Gate Card guide is a research aid. It provides human-readable card names, card categories, battle types, six displayed attribute bonuses, and effect descriptions. It is not authoritative for ROM ordering or numeric IDs.

The implementation must never assume that guide row order equals ROM card-ID order. It must also avoid committing a copied guide table or other copyrighted source material.

## Unknowns That Must Be Resolved

Milestone 6A is complete only after the following are confirmed:

1. The exact table element width and signedness.
2. The exact number of records and valid card-ID range.
3. The six-value record stride.
4. The exact attribute-ID order.
5. The table's end boundary and adjacent data ownership.
6. The mapping from runtime address `0x020A15AC` to an editable ROM/workspace representation.
7. Whether the table can be patched directly in stored ARM9 bytes or requires decompression, editing, and deterministic recompression of the ARM9 runtime image.
8. At least several card-ID-to-name mappings established independently of guide order.
9. Whether all Gate Card classes use this same six-value table or whether some IDs use sentinel or effect-only records.

Unresolved points must be labeled `candidate` or `probable`; they cannot be represented as confirmed schema facts.

## Approaches Considered

### Approach A: Raw guarded binary replacements only

Each changed Gate record would be represented as a manual byte replacement.

Advantages:

- minimal implementation work;
- reuses the current `binary_replace` patch mechanism.

Disadvantages:

- difficult to review;
- exposes raw offsets and stored units to users;
- easy to mix attribute order;
- does not provide a reusable export or analysis workflow.

This is acceptable as a temporary verification method but not as the final editor interface.

### Approach B: Fully generic table-edit framework

A broad schema language would support arbitrary record layouts and component mappings.

Advantages:

- reusable for Gate Cards, Ability Cards, Bakugan data, shops, and future tables.

Disadvantages:

- too much abstraction before a second confirmed table exists;
- increases validation and maintenance complexity;
- risks designing around assumptions rather than real formats.

This is deferred.

### Approach C: Gate-specific schema on a small fixed-record primitive — recommended

Implement one narrow fixed-record editing primitive and register a single Gate Card schema.

Advantages:

- readable and safe;
- small enough to verify thoroughly;
- reusable internally without exposing a premature general-purpose DSL;
- can later support additional schemas without changing the Gate interface.

Milestone 6A will use this approach.

## Scope

### Included

- locating the complete Gate attribute-bonus table;
- mapping its runtime address to the editable workspace;
- confirming element width, record count, attribute order, and ID domain;
- exporting a local numeric report from a user-owned ROM;
- adding a Gate-specific fixed-record schema;
- applying full-record guarded edits;
- rebuilding and structurally validating the ROM;
- emulator verification of edited Gate bonuses;
- generating local balance-analysis metrics;
- documenting confirmed and unresolved card-ID mappings.

### Excluded

- selecting final rebalance numbers;
- changing Gate effects;
- changing battle/minigame types;
- changing card availability or shop prices;
- changing Gate Card names or graphics;
- changing Ability Cards;
- adding new attribute passive mechanics;
- adding a global Gate-scaling hook;
- committing the complete original Gate table or copied guide data.

## Architecture

### 1. Gate table locator

Add a profile-specific locator that begins from the confirmed runtime table base and resolves it to an editable component and component-relative offset.

The locator must:

- require the exact `b6re_rev0` ROM profile;
- identify whether the target belongs to stored ARM9, an ARM9 compressed region, or another canonical runtime image;
- refuse ambiguous mappings;
- record both runtime and stored offsets;
- verify a stable table-region hash before export or editing.

The implementation must choose the smallest correct write path after discovery:

- direct stored-ARM9 patching when runtime bytes have a stable direct representation; or
- deterministic ARM9 decompression/edit/recompression when the table exists only in a compressed runtime section.

The design does not assume either result in advance.

### 2. Gate table schema

Register one schema identifier:

```text
gate_card_attribute_bonus_v1
```

The confirmed schema will define:

- component identifier;
- runtime table base;
- stored table offset or runtime-image mapping;
- record count;
- record stride;
- element encoding;
- attribute order;
- stored-unit-to-G conversion;
- allowed stored and displayed ranges;
- table-region hash.

The schema file must not contain the complete original table.

### 3. Local export command

Add a command equivalent to:

```bash
bakugan-ds gate export WORKSPACE OUTPUT.json
```

The export is generated locally from the user's extracted workspace and is ignored by Git.

Each record contains only ROM-derived numeric data and evidence metadata:

```json
{
  "card_id": 12,
  "runtime_address": "0x020A15F4",
  "component_offset": "0x00000000",
  "raw_values": [18, 6, 9, 14, 13, 5],
  "bonuses_g": [180, 60, 90, 140, 130, 50],
  "confidence": "confirmed"
}
```

The exact example offset above is illustrative and must not be copied into implementation tests unless independently calculated.

The export may include optional local labels, but numeric card IDs remain the canonical identity.

### 4. Optional local label mapping

A user-maintained, ignored JSON or CSV file may associate card IDs with reference names and categories:

```json
{
  "12": {
    "name": "local reference label",
    "source": "user-supplied reference",
    "confidence": "confirmed"
  }
}
```

Rules:

- labels never determine table offsets;
- guide order never assigns IDs automatically;
- a label becomes `confirmed` only after independent runtime or executable evidence;
- label mismatch never changes ROM data;
- the repository may commit selected evidence-backed names used in documentation, but not a copied full guide table.

### 5. Gate edit manifest

Add a Gate-specific edit format built on the fixed-record primitive:

```json
{
  "format_version": 1,
  "profile": "b6re_rev0",
  "schema": "gate_card_attribute_bonus_v1",
  "edits": [
    {
      "card_id": 12,
      "expected_bonuses_g": {
        "pyrus": 180,
        "aquos": 60,
        "subterra": 90,
        "haos": 140,
        "darkus": 130,
        "ventus": 50
      },
      "replacement_bonuses_g": {
        "pyrus": 160,
        "aquos": 70,
        "subterra": 100,
        "haos": 130,
        "darkus": 120,
        "ventus": 60
      }
    }
  ]
}
```

The values above demonstrate the format only and are not approved balance changes.

Safety requirements:

- full six-value records are required;
- expected values guard every edited record;
- displayed values must convert exactly to stored units;
- duplicate card IDs are rejected;
- unknown attributes are rejected;
- missing attributes are rejected;
- all guards are validated before any target is written;
- failures are atomic;
- edits are applied in deterministic card-ID order;
- the report records old and new raw bytes, displayed values, and offsets.

### 6. CLI behavior

Planned commands:

```bash
bakugan-ds gate inspect WORKSPACE
bakugan-ds gate export WORKSPACE OUTPUT.json
bakugan-ds gate apply WORKSPACE EDITS.json
```

`inspect` prints table metadata and confidence status without dumping the complete table by default.

`export` creates a local report.

`apply` writes guarded record changes to the modified workspace and emits a deterministic patch report.

The existing general `bakugan-ds patch` command remains supported. Gate edits may compile internally into guarded binary replacements, but users should not need to author raw byte patches.

## Table Discovery Workflow

1. Reproduce the existing runtime lookup at `0x02065BF4`.
2. Disassemble the complete helper and its callers.
3. Confirm the element load instruction and signedness.
4. Confirm the multiplication by six and card-ID source width.
5. Identify all code references to `0x020A15AC` or its literal-pool entry.
6. Determine the maximum legal card ID from validation code, loops, inventory structures, or adjacent tables.
7. Inspect bytes before and after the candidate table for structural boundaries.
8. Compare several ROM records against independently observed runtime Gate bonuses.
9. Establish the attribute-ID order through controlled attribute changes.
10. Map the runtime region to stored workspace bytes.
11. Perform a reversible one-record edit.
12. Rebuild, boot, observe the changed bonus, complete the battle path, and return to story.

No table count or ID mapping is confirmed solely because values visually resemble the guide.

## Balance Analysis Output

Milestone 6A generates local analysis but does not choose final tuning values.

The local report should calculate:

- minimum, maximum, mean, and median bonus per attribute;
- each record's range and specialization spread;
- total bonus sum per record;
- records that are strictly dominated by another record across all six attributes;
- records that are equal or near-equal across attributes;
- extreme single-attribute specialization;
- Gate bonus size as a percentage of representative compressed core-G values;
- distribution by locally supplied card category when labels are available.

The report must distinguish facts from recommendations. It may identify candidates for later tuning but must not generate or apply an automatic rebalance.

## Milestone 6B Handoff

After Milestone 6A produces a confirmed local export and analysis report, a separate design decision will select the Gate rebalance model.

Milestone 6B must answer:

- whether Gold, Silver, and Copper cards require separate tuning rules;
- whether high universal bonuses should be reduced;
- how much specialization should be preserved;
- whether Gate bonuses are too large relative to compressed late-game core G;
- whether effect-bearing cards need different numeric budgets;
- which cards should remain intentionally exceptional.

No Milestone 6B patch begins without user approval of those balance principles and proposed values.

## Error Handling

Commands must fail with concise, distinct errors for:

- unsupported ROM profile;
- missing or inconsistent workspace manifests;
- unresolved runtime-to-stored mapping;
- table-region hash mismatch;
- ambiguous table boundary;
- unconfirmed attribute order;
- card ID outside the confirmed range;
- duplicate card ID;
- missing or unknown attribute;
- bonus not divisible by the confirmed G-unit scale;
- bonus outside the confirmed encoded range;
- stale expected record;
- decompression or recompression failure;
- output component size or metadata mismatch.

A failed apply operation must leave every modified target unchanged.

## Testing Strategy

### Unit tests

Use repository-safe synthetic fixtures to test:

- fixed-record table parsing;
- runtime-address-to-record calculation;
- element encoding and G-unit conversion;
- complete-record validation;
- duplicate and missing attribute rejection;
- range and divisibility validation;
- stale expected-record rejection;
- atomic multi-record failure;
- deterministic edit ordering and report output;
- balance-analysis metrics.

### Reference-ROM integration tests

When `BAKUGAN_DS_ROM` is supplied locally, verify:

- exact profile validation;
- confirmed table base resolution;
- confirmed table-region hash;
- confirmed record stride and count;
- several independently verified runtime examples;
- local export determinism;
- one controlled record edit changes only the intended table bytes;
- stale guards fail atomically;
- rebuilt ROM size and metadata remain valid;
- all unrelated FAT payloads remain byte-identical;
- the existing core-G compression patch remains unchanged.

### Emulator verification

A controlled test patch must:

1. boot from a clean rebuilt ROM;
2. create or load a suitable profile without restoring executable RAM from a save state;
3. enter a battle using a confirmed Gate Card ID;
4. observe an unchanged control attribute;
5. observe at least one deliberately edited attribute bonus;
6. verify `target_total_g = base_snapshot_g + edited_gate_bonus_g`;
7. complete or safely exit the battle path;
8. return to the surrounding story or menu state;
9. confirm continued input responsiveness.

The validation record must state exactly what was observed and must not claim broader story or card coverage than was tested.

## Repository Layout

Expected additions:

```text
src/bakugan_ds/gates/
├── __init__.py
├── locate.py
├── schema.py
├── export.py
├── edit.py
└── analysis.py

config/
└── gate_card_attribute_bonus_v1.json

analysis/
├── candidates/
│   └── gate_card_table.yaml
└── symbols/
    └── gate_cards.csv

docs/
├── gate-card-table.md
└── superpowers/
    ├── specs/
    └── plans/

tests/
├── unit/
│   ├── test_gate_schema.py
│   ├── test_gate_edit.py
│   └── test_gate_analysis.py
└── integration/
    └── test_gate_table_reference.py
```

Exact filenames may be adjusted to follow existing package conventions, but component boundaries must remain narrow and testable.

## Documentation Requirements

The finished milestone must document:

- confirmed lookup formula;
- table base, component, and relative offset;
- record encoding and count;
- attribute order;
- stored-to-display conversion;
- confidence evidence for each claim;
- local export and edit commands;
- legal boundary and ignored output paths;
- how to add optional local labels;
- emulator verification scope;
- the unresolved questions handed to Milestone 6B.

## Copyright and Repository Boundary

The repository may contain:

- code;
- schemas;
- addresses and offsets;
- hashes;
- formulas;
- minimal guarded bytes required for patches;
- selected normalized runtime examples;
- evidence-backed documentation.

The repository must not contain:

- the ROM or rebuilt ROM;
- extracted ARM9 or game assets;
- RAM dumps or save states;
- screenshots used for local verification;
- the complete original Gate Card table;
- a copied GameFAQs table;
- a full game-text name database.

Generated exports and local label mappings must be ignored by Git.

## Success Criteria

Milestone 6A succeeds when a contributor can:

1. provide the exact supported ROM and extract a workspace;
2. resolve the confirmed Gate table from runtime address to editable bytes;
3. inspect the confirmed table schema without relying on guide order;
4. export all records locally in readable displayed-G units;
5. apply a full-record edit using card ID and named attributes;
6. receive atomic failure when expected values are stale;
7. rebuild a structurally valid ROM;
8. observe the edited Gate bonus in a real battle;
9. complete or safely exit the battle and return to a responsive game state;
10. generate a local balance report suitable for designing Milestone 6B;
11. reproduce the same edited bytes and output hash from the same inputs.

## Implementation Sequence

The later implementation plan should divide work into the following order:

1. static lookup and table-boundary confirmation;
2. runtime-to-stored ARM9 mapping;
3. schema and synthetic tests;
4. local export command;
5. fixed-record guarded edit engine;
6. Gate CLI commands and reports;
7. local balance-analysis report;
8. exact-ROM integration tests;
9. controlled emulator verification;
10. documentation and evidence normalization.
