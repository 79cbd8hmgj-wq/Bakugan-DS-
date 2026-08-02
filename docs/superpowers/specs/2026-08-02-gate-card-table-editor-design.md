# Gate Card Table Discovery and Editor Design

## Status

Approved Milestone 6 direction, scoped as **Milestone 6A**: discover, verify, export, and safely edit the Gate Card attribute-bonus table for **Bakugan: Battle Brawlers (Nintendo DS, USA revision 0)**.

The actual numeric Gate Card rebalance is deferred to Milestone 6B. No balance values will be changed until the table extent, record format, card-ID domain, attribute order, and editable ROM representation are confirmed.

## Motivation

Milestones 1-5 established the full analysis-to-build-to-emulator workflow:

- exact reference-ROM validation;
- deterministic extraction and rebuilding;
- guarded binary patches;
- static and runtime battle-engine analysis;
- a confirmed G-Power pipeline;
- the bounded core G-Power compression patch;
- clean-ROM tutorial completion and return to story.

Gate Card data is the lowest-risk next target because the lookup path is already confirmed and Gate bonuses remain deliberately separate from core-G compression.

## Confirmed Runtime Baseline

The current evidence establishes:

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

Confirmed tutorial equations include:

```text
230 + 180 = 410
190 + 100 = 290
```

These observations confirm the lookup-to-display conversion and separation of core G from Gate contribution. They do not establish the full table extent, every card ID, or the complete attribute enumeration.

## Source and Evidence Boundaries

### ROM-derived evidence

The user-owned reference ROM is authoritative for:

- table bytes;
- lookup behavior;
- runtime card and attribute IDs;
- table extent and element format;
- editable binary location and compression mapping.

### Runtime evidence

Controlled emulator traces are authoritative for:

- a specific card ID selecting a specific record;
- a specific attribute ID selecting a specific element;
- the displayed Gate bonus and resulting total;
- whether a rebuilt edit is used by the game.

### External reference material

The locally supplied Gate Card guide is a research aid. It provides human-readable names, card categories, battle types, six displayed attribute bonuses, and effect descriptions. It is not authoritative for ROM ordering or numeric IDs.

Guide row order must never be treated as ROM card-ID order. The repository must not contain a copied guide table.

## Unknowns That Must Be Resolved

Milestone 6A is complete only after confirming:

1. Table element width and signedness.
2. Record count and valid card-ID range.
3. Record stride.
4. Exact attribute-ID order.
5. End boundary and adjacent data ownership.
6. Runtime address `0x020A15AC` mapped to an editable workspace representation.
7. Direct stored-byte patching versus ARM9 decompression/edit/recompression.
8. Several card-ID-to-name mappings established independently of guide order.
9. Whether all Gate Card classes use the same six-value table or whether some IDs are sentinel or effect-only records.

Unresolved points remain `candidate` or `probable`; they cannot appear as confirmed schema facts.

## Approaches Considered

### A. Raw guarded binary replacements

Advantages:

- minimal new code;
- reuses `binary_replace`.

Disadvantages:

- difficult to review;
- exposes raw offsets and stored units;
- easy to mix attribute order;
- provides no reusable export or analysis workflow.

This may be used for temporary verification only.

### B. Fully generic table-edit framework

Advantages:

- reusable for future tables.

Disadvantages:

- premature abstraction before a second table is confirmed;
- larger validation surface;
- likely to encode assumptions instead of evidence.

This is deferred.

### C. Gate-specific schema on a small fixed-record primitive - recommended

Implement one narrow fixed-record editing primitive and register a single Gate Card schema.

Advantages:

- readable and safe;
- small enough to verify thoroughly;
- internally reusable without exposing a premature general-purpose DSL;
- extensible later without changing the Gate interface.

Milestone 6A uses this approach.

## Scope

### Included

- locate and bound the Gate attribute-bonus table;
- map runtime address to editable workspace data;
- confirm encoding, count, attribute order, and ID domain;
- export a local numeric report from a user-owned ROM;
- add a Gate-specific fixed-record schema;
- apply full-record guarded edits;
- rebuild and structurally validate the ROM;
- verify edited Gate bonuses in an emulator;
- generate local balance-analysis metrics;
- document confirmed and unresolved card-ID mappings.

### Excluded

- final rebalance values;
- Gate effects;
- battle/minigame types;
- card availability or shop prices;
- card names or graphics;
- Ability Cards;
- new attribute passives;
- global Gate-scaling hooks;
- committing the complete original Gate table or copied guide data.

## Architecture

### 1. Gate table locator

Add a profile-specific locator beginning from runtime table base `0x020A15AC`.

It must:

- require profile `b6re_rev0`;
- identify stored ARM9, compressed ARM9, or another canonical runtime image;
- refuse ambiguous mappings;
- record runtime and stored offsets;
- verify a stable table-region hash before export or editing.

The implementation chooses the smallest correct write path after discovery:

- direct stored-ARM9 patching when a stable direct representation exists; or
- deterministic ARM9 decompression, editing, and recompression when required.

The design does not assume either result in advance.

### 2. Gate table schema

Register:

```text
gate_card_attribute_bonus_v1
```

The confirmed schema defines:

- component identifier;
- runtime table base;
- stored offset or runtime-image mapping;
- record count and stride;
- element encoding;
- attribute order;
- stored-unit-to-G conversion;
- accepted ranges;
- table-region hash.

The schema must not contain the complete original table.

### 3. Local export

Add a command equivalent to:

```bash
bakugan-ds gate export WORKSPACE OUTPUT.json
```

The export is generated locally and ignored by Git. Each record includes card ID, resolved addresses, raw values, displayed-G values, and evidence confidence.

Shape example using explicitly synthetic values:

```json
{
  "card_id": 3,
  "raw_values": [10, 8, 12, 9, 7, 11],
  "bonuses_g": [100, 80, 120, 90, 70, 110],
  "confidence": "confirmed"
}
```

Resolved runtime and component offsets are included in real exports after mapping is confirmed.

Numeric card IDs remain canonical even when optional labels are present.

### 4. Optional local labels

A user-maintained ignored JSON or CSV file may associate card IDs with names and categories.

```json
{
  "3": {
    "name": "local reference label",
    "source": "user-supplied reference",
    "confidence": "confirmed"
  }
}
```

Rules:

- labels never determine offsets;
- guide order never assigns IDs automatically;
- a label is `confirmed` only after independent runtime or executable evidence;
- label mismatch never changes ROM data;
- selected evidence-backed names may appear in documentation, but no complete guide table is committed.

### 5. Gate edit manifest

Add a Gate-specific edit format built on the fixed-record primitive.

The following values are synthetic format examples, not approved tuning:

```json
{
  "format_version": 1,
  "profile": "b6re_rev0",
  "schema": "gate_card_attribute_bonus_v1",
  "edits": [
    {
      "card_id": 3,
      "expected_bonuses_g": {
        "pyrus": 100,
        "aquos": 80,
        "subterra": 120,
        "haos": 90,
        "darkus": 70,
        "ventus": 110
      },
      "replacement_bonuses_g": {
        "pyrus": 110,
        "aquos": 90,
        "subterra": 110,
        "haos": 90,
        "darkus": 80,
        "ventus": 100
      }
    }
  ]
}
```

Safety requirements:

- require all six attributes;
- guard the complete original record;
- require exact conversion from displayed G to stored units;
- reject duplicate IDs, missing attributes, and unknown attributes;
- validate every guard before writing any target;
- leave all targets unchanged on failure;
- apply edits in deterministic card-ID order;
- report old and new bytes, values, and offsets.

### 6. CLI behavior

Planned commands:

```bash
bakugan-ds gate inspect WORKSPACE
bakugan-ds gate export WORKSPACE OUTPUT.json
bakugan-ds gate apply WORKSPACE EDITS.json
```

`inspect` prints schema metadata and confidence status without dumping the full table.

`export` writes a local report.

`apply` writes guarded record changes and emits a deterministic patch report.

The existing general patch command remains supported. Gate edits may compile internally into guarded binary replacements, but users should not author raw byte patches.

## Discovery Workflow

1. Reproduce lookup helper `0x02065BF4`.
2. Disassemble the helper and relevant callers.
3. Confirm element load width and signedness.
4. Confirm multiplication by six and card-ID source width.
5. Identify references to `0x020A15AC` or its literal-pool entry.
6. Determine maximum legal card ID from validation code, loops, inventory structures, or adjacent tables.
7. Inspect data before and after the candidate table.
8. Compare several ROM records with independently observed runtime bonuses.
9. Establish attribute order through controlled attribute changes.
10. Map runtime data to stored workspace bytes.
11. Perform a reversible one-record edit.
12. Rebuild, boot, observe the edit, exit the battle path, and return to a responsive game state.

No table count or ID mapping is confirmed merely because values resemble the guide.

## Local Balance Analysis

Milestone 6A generates analysis but does not select tuning values.

The local report calculates:

- minimum, maximum, mean, and median per attribute;
- each record's range and specialization spread;
- total bonus sum per record;
- strict cross-attribute dominance;
- equal or near-equal records;
- extreme single-attribute specialization;
- Gate bonus size relative to representative compressed core-G values;
- category distributions when local labels are available.

The report separates facts from recommendations and must not generate or apply an automatic rebalance.

## Milestone 6B Handoff

After a confirmed export and analysis report, a separate design decision will determine:

- whether Gold, Silver, and Copper cards require separate rules;
- whether universal high bonuses should be reduced;
- how much specialization to preserve;
- whether bonuses are too large relative to compressed late-game core G;
- whether effect-bearing cards need separate numeric budgets;
- which cards should remain exceptional.

No Milestone 6B patch begins without user approval of principles and proposed values.

## Error Handling

Commands must distinguish:

- unsupported ROM profile;
- missing or inconsistent workspace manifests;
- unresolved runtime-to-stored mapping;
- table-region hash mismatch;
- ambiguous table boundary;
- unconfirmed attribute order;
- card ID outside confirmed range;
- duplicate card ID;
- missing or unknown attribute;
- value not divisible by the confirmed G-unit scale;
- value outside the confirmed encoded range;
- stale expected record;
- decompression or recompression failure;
- output size or metadata mismatch.

A failed apply operation leaves every modified target unchanged.

## Testing

### Unit tests

Use repository-safe synthetic fixtures for:

- fixed-record parsing;
- runtime-address-to-record calculation;
- encoding and G-unit conversion;
- complete-record validation;
- duplicate, missing, and unknown field rejection;
- range and divisibility checks;
- stale-record rejection;
- atomic multi-record failure;
- deterministic reports;
- balance metrics.

### Reference-ROM integration tests

With `BAKUGAN_DS_ROM` supplied locally, verify:

- exact profile validation;
- table-base resolution;
- table-region hash;
- record stride and count;
- several independently verified runtime examples;
- deterministic local export;
- one controlled edit changes only intended table bytes;
- stale guards fail atomically;
- rebuilt ROM remains structurally valid;
- unrelated FAT payloads remain byte-identical;
- core-G compression remains unchanged.

### Emulator verification

A controlled test patch must:

1. boot from a clean rebuilt ROM;
2. create or load a profile without restoring executable RAM from a save state;
3. enter a battle with a confirmed Gate Card ID;
4. observe an unchanged control attribute;
5. observe at least one edited attribute bonus;
6. verify `target_total_g = base_snapshot_g + edited_gate_bonus_g`;
7. complete or safely exit the battle path;
8. return to story or menu;
9. confirm continued input responsiveness.

The validation record must state exactly what was observed.

## Expected Repository Additions

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
├── candidates/gate_card_table.yaml
└── symbols/gate_cards.csv

docs/
└── gate-card-table.md

tests/
├── unit/
│   ├── test_gate_schema.py
│   ├── test_gate_edit.py
│   └── test_gate_analysis.py
└── integration/
    └── test_gate_table_reference.py
```

Exact filenames may follow existing package conventions, but boundaries must remain narrow and testable.

## Copyright Boundary

The repository may contain code, schemas, addresses, offsets, hashes, formulas, minimal guarded patch bytes, selected normalized runtime examples, and evidence-backed documentation.

It must not contain:

- ROMs or rebuilt ROMs;
- extracted ARM9 or game assets;
- RAM dumps or save states;
- verification screenshots;
- the complete original Gate table;
- a copied GameFAQs table;
- a complete game-text name database.

Generated exports and local labels must be ignored by Git.

## Success Criteria

Milestone 6A succeeds when a contributor can:

1. provide the exact supported ROM and extract a workspace;
2. resolve the Gate table from runtime address to editable bytes;
3. inspect a confirmed schema without relying on guide order;
4. export records locally in displayed-G units;
5. apply a full-record edit using card ID and named attributes;
6. receive atomic failure for stale expected values;
7. rebuild a structurally valid ROM;
8. observe the edited bonus in battle;
9. exit to a responsive game state;
10. generate a local report suitable for Milestone 6B;
11. reproduce the same changed bytes and output hash from identical inputs.

## Implementation Sequence

The implementation plan should proceed in this order:

1. static lookup and table-boundary confirmation;
2. runtime-to-stored ARM9 mapping;
3. schema and synthetic tests;
4. local export command;
5. fixed-record guarded editor;
6. Gate CLI and deterministic reports;
7. local balance analysis;
8. exact-ROM integration tests;
9. controlled emulator verification;
10. documentation and evidence normalization.
