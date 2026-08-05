# Milestone 6E Complete Gate Roster Conversion Design

## Status

This specification defines the separately reviewed Milestone 6E conversion of all Gate Card IDs `1..103` to the deterministic Gate Card System 2.0 framework merged in Milestone 6D.

Milestone 6D is the implementation boundary. Milestone 6E changes authoring data, validation, reporting, installation contracts, and representative runtime acceptance. It does not expand the runtime semantic domain, module geometry, cache geometry, hook set, or save format.

## Goal

Convert every original Gate Card into a readable, bounded, strategically distinct System 2.0 record while preserving recognizable legacy identity:

- original attribute strengths and weaknesses remain visible;
- original fixed battle type remains the default preferred type;
- names and themes inform archetype, condition, target, reward, and drawback choices;
- evolved or high-tier cards become alternatives rather than strict upgrades;
- no card is made relevant solely through larger unconditional G values;
- every record remains executable by the merged generic Milestone 6D runtime.

## Approved scope

Milestone 6E may use only the deterministic mechanics already merged in Milestone 6D:

- flat signed G influence;
- Q8.8 percentage scaling from compressed core G;
- six record-local attribute modifiers;
- bounded six-type battle weights;
- owner-behind, owner-ahead, score-tied, owner-score-zero, match-point, and confirmed Gate-card-won landing conditions;
- current-combatant, Gate-owner, and Gate-non-owner targeting;
- signed add-G and subtract-magnitude-G effects;
- explicit signed drawbacks;
- exact legacy fallback for invalid runtime data.

The following remain deferred:

- Ability Card manipulation;
- fatigue or activation limits;
- battle-history repeat penalties;
- arena ID or arena-dependent conditions;
- AI evaluation changes;
- player-facing description or activation UI changes;
- save-data changes;
- adaptive difficulty;
- new timing phases;
- new condition, target, or effect IDs.

All deferred record fields remain zero.

## Source and copyright boundary

The exact in-game `mes_CardName.mes`, legacy six-value table, and metadata table are used locally to author and validate the conversion. The complete original name catalog and original table are not committed.

Committed artifacts may contain:

- global card IDs;
- converted System 2.0 records;
- archetype counts and balance summaries;
- generic identity slugs and rationale categories;
- hashes proving local source alignment;
- selected examples already established in project documentation.

The committed authoring roster does not require names at runtime. A local ignored research matrix maps each ID to its in-game name, original values, original fixed type, and authoring notes.

## Conversion approach

### Rejected approach A: fully automatic conversion

A formula based only on legacy mean, spread, and fixed type would be deterministic but would produce repeated templates and ignore thematic cards such as comeback, exchange, lockdown, bait, delayed attack, and high-risk fields.

### Rejected approach B: unstructured manual authoring

Hand-writing 103 unrelated records would preserve theme but make budgets, duplicate detection, regression review, and later tuning difficult to reproduce.

### Approved approach C: deterministic seed plus authored override

1. Generate a local seed from exact legacy data.
2. Preserve the rank order of the six legacy attribute values when generating the first attribute profile.
3. Preserve the legacy fixed battle type as the preferred type unless an override includes a written reason.
4. Classify the card into one of three roster families and one of seven archetypes.
5. Apply a reviewed archetype template.
6. Author card-specific values, condition, target, effect, and drawback within the existing budget rules.
7. Run duplicate, dominance, context-matrix, and effective-swing analysis.
8. Adjust only the smallest necessary fields until the roster passes.

The seed generator is an authoring aid. The committed converted roster is the source of truth.

## Roster families

### Family A — Bakugan-character Gates, IDs `1..39`

These cards preserve a recognizable relationship to the named Bakugan.

Default tendencies:

- pronounced legacy-derived attribute profile;
- original battle type remains preferred;
- Attribute, Power, Skill, and Comeback are the primary archetypes;
- evolved forms trade reliability for scaling, condition pressure, or narrower affinity rather than strictly increasing every output;
- universal legacy rows become Power, Skill, Comeback, or Chaos rather than featureless all-attribute bonuses.

### Family B — environmental and attribute fields, IDs `40..71`

These cards express battlefield conditions.

Default tendencies:

- Attribute, Control, Skill, and Chaos are primary;
- cyclic legacy attribute patterns remain recognizable;
- field names guide positive and opposed relationships locally, without creating a universal elemental wheel;
- low-energy or vacuum-like cards may use lower flat values, non-owner targeting, or drawbacks rather than becoming dead cards;
- duplicate legacy rows must diverge through condition, target, weights, or risk profile.

### Family C — tactical and conditional Gates, IDs `72..103`

These cards express decisions implied by names such as stand-off, delayed attack, bait and switch, lockdown, overtake, exchange, swap, reflexes, trap, cover, siphon, or wrath.

Default tendencies:

- Control, Comeback, Risk, Skill, and Chaos are primary;
- conditions and targeting carry more identity than attribute spread;
- high legacy means are not preserved as unconditional power;
- explicit drawbacks purchase high upside;
- cards suggesting exchange or denial use only the supported signed-G and target predicates, not unimplemented cross-record swaps or Ability denial.

## Archetype authoring rules

### Power

- dependable G influence is the largest gross-budget component;
- condition is normally `none`, `owner_ahead`, or `score_tied`;
- battle pressure is neutral or mild;
- at most two positive affinities;
- no strict dominance over another Power record across the reference matrix.

### Skill

- strong or extreme-bounded battle pressure is required;
- direct G influence remains lower than comparable Power cards;
- original fixed type is normally the unique maximum;
- every type remains possible;
- cards with the same preferred type must differ materially in G profile, condition, or target.

### Control

- Gate-owner/non-owner targeting or a score/landing condition is required;
- control is represented through supported signed G influence, not hidden state mutation;
- unconditional current-combatant-only records are rejected;
- battle pressure is neutral, mild, or strong.

### Comeback

- condition must be `owner_behind` or `owner_score_zero`;
- the conditional reward is meaningful but bounded;
- the owner receives the central benefit;
- tied or leading owners do not receive the comeback rider;
- evolved forms may trade base reliability for a stronger conditional reward.

### Risk

- explicit drawback is required;
- gross value must exceed the typical unconditional band before credit;
- reward and drawback target choices must be understandable from the committed rationale category;
- high-risk records are tested at both favorable and unfavorable contexts;
- effective swing may reach 250 G only with a real drawback.

### Attribute

- at least one primary and one opposed modifier are required by the merged invariant;
- legacy attribute rank order is preserved unless a documented thematic override exists;
- no more than three attributes may be positive above neutral without explicit review;
- flat and percentage components remain moderate so the profile, not generic power, defines the card.

### Chaos

- explicit drawback is required;
- weighting is unusual but still bounded;
- record uses a deterministic condition or target combination that does not fit the other six archetypes;
- Chaos is not a license for random effects, unsupported state, or arbitrary inflation.

## Soft roster-distribution bands

The final 103-card roster must fall within these review bands:

| Archetype | Minimum | Maximum |
|---|---:|---:|
| Power | 12 | 18 |
| Skill | 14 | 20 |
| Control | 14 | 20 |
| Comeback | 10 | 16 |
| Risk | 12 | 18 |
| Attribute | 18 | 26 |
| Chaos | 6 | 12 |

These are diversity guards, not quotas. The final exact counts are generated from the reviewed roster and committed in the Milestone 6E contract.

## Attribute-profile derivation

The local seed process centers each legacy six-value row around its median and maps its relative tiers to a bounded first draft:

- strongest legacy entry: primary affinity;
- second distinct high entry: secondary affinity where appropriate;
- middle entries: neutral or small secondary values;
- weakest distinct entry: opposed value;
- ties remain ties unless a thematic override is documented.

The final authoring values remain within `-100..+100 G` and pass the merged archetype invariants. Milestone 6E does not claim the resulting relationships form a universal anime attribute wheel.

## Battle-weight derivation

The original fixed battle type is the default preferred type.

Template pressures:

- neutral: near-even weights, maximum probability at most 20%;
- mild: maximum probability above 20% and at most 25%;
- strong: above 25% and at most 33.34%;
- extreme bounded: above 33.34% and at most 40%.

Power and Attribute cards normally use neutral or mild pressure. Skill requires strong or extreme-bounded pressure. Control, Comeback, and Risk may use mild or strong pressure. Chaos may use two co-maximum types or an unusual bounded distribution, but `preferred_type` still references a maximum entry.

A preferred-type override requires a committed generic rationale category. The complete original name is not required in the committed report.

## Effective-swing analysis

Every record is evaluated over this deterministic reference matrix:

- compressed core G: `190, 400, 525, 650, 695`;
- all six attributes;
- current combatant is owner and non-owner;
- scores `0–2` for both sides;
- landing result absent and confirmed Gate-card-won;
- all supported true and false condition branches;
- favorable and unfavorable drawback paths.

Review bands:

- early/common-style output: `70–130 G`;
- mid output: `110–180 G`;
- rare or specialized output: `140–220 G`;
- high-risk favorable output: at most `250 G`;
- signed negative outcomes remain bounded and intentional.

A card may cross more than one band across contexts. The report records minimum, median, maximum, owner-only maximum, non-owner maximum, and drawback result.

## Duplicate and dominance rules

### Exact signature uniqueness

No two live records may share all of:

- archetype;
- flat and percentage components;
- six attribute modifiers;
- six battle weights and preferred type;
- condition and condition value;
- target mode;
- effect and value;
- drawback and value.

### Contextual differentiation

Cards sharing an archetype and preferred type must differ in at least two gameplay dimensions: G profile, attribute profile, condition, target, pressure class, or drawback.

### Strict-dominance rejection

The deterministic report compares records within comparable target/condition groups. A record is rejected when another record has:

- equal or greater effective G in every applicable reference context;
- equal or stronger battle pressure toward the same preferred type;
- no greater drawback;
- and a strict advantage in at least one context.

Different conditions, targets, opposed profiles, or drawback exposure may justify apparent numerical advantages and are reported rather than automatically rejected.

## Authoring artifacts

Committed source-of-truth files:

- `config/gates/milestone-6e-system2-v1.json` — complete 103-record live roster;
- `analysis/gates/milestone-6e-roster-contract.json` — counts, hashes, archetype distribution, invariant summary, and representative IDs without the complete original name catalog;
- `docs/gate-card-system-2-roster-conversion.md` — authoring rationale and tuning boundaries;
- `analysis/gates/milestone-6e-task-status.json` — task and verification state.

Local ignored artifacts:

- exact ID/name/legacy-value research matrix;
- seed report;
- complete per-card rationale worksheet containing original names;
- generated balance and dominance reports derived from user-owned extracted data;
- ROMs, modules, overlays, saves, states, screenshots, and debugger logs.

## CLI and installation

Milestone 6E adds explicit commands rather than silently changing Milestone 6D commands:

```text
bakugan-ds gate seed-milestone-6e
bakugan-ds gate validate-milestone-6e
bakugan-ds gate report-milestone-6e
bakugan-ds gate install-milestone-6e
```

`seed-milestone-6e` requires exact local legacy resources and writes only to an ignored output path. Validation and reporting operate on the committed converted roster without requiring copyrighted inputs. Installation accepts either a pristine extracted workspace or the exact verified Milestone 6D state, stages all products transactionally, and preserves byte identity on failure.

## Runtime and binary boundaries

Milestone 6E reuses the merged Milestone 6D runtime module without semantic or geometric expansion:

```text
Module: 0x0228BC20–0x02293C20
Cache:  0x02293C20–0x02293C60
Arena:  starts at 0x02293C60
```

Required binary properties:

- module size remains `0x8000`;
- cache remains 64 bytes;
- hook count remains six;
- decoded-ARM9 arena-boundary replacement remains unchanged;
- protected core-G ranges remain unchanged;
- the trailer remains 103 ordered 40-byte records plus the existing header;
- only authoring/trailer content and resulting hashes change;
- invalid records and malformed payloads fail closed to exact original behavior.

## Verification strategy

### Host and authoring

- all 103 records are live and nonlegacy;
- IDs are complete, ordered, unique, and contiguous;
- every record passes semantic, budget, archetype, attribute, and battle-weight validation;
- distribution bands pass;
- exact signatures are unique;
- contextual differentiation passes;
- strict-dominance analysis has no unexplained failures;
- deterministic reports and serializers are byte-identical across runs.

### Exact emitted ARM

Execute every record against the exact emitted module over a bounded context matrix. Require host/emitted parity for:

- all six attributes;
- owner and non-owner calculation;
- true and false condition branches;
- score boundaries and match point;
- landing present, absent, and invalid;
- effects and drawbacks;
- signed and unsigned clamps;
- battle-weight selection and fallback;
- zero writes to Ability state, activation counters, history bytes, save data, and unrelated combatant records.

The matrix is controlled emitted-code evidence, not 103 naturally occurring battles.

### Exact rebuild

- install from pristine workspace and verified Milestone 6D workspace;
- require byte-identical outputs from two independent workspaces;
- verify the exact set of changed components;
- verify module/cache/hook geometry remains unchanged;
- verify complete 103-record trailer and payload CRC;
- verify rollback rebuilds the Milestone 6D image from source.

### Live DeSmuME

Naturally exercise representative cards, not every matrix vector:

- at least one card from each archetype;
- at least one Bakugan-character, environmental, and tactical family card;
- at least one owner-target and non-owner-target record;
- at least one true and false comeback condition;
- at least one explicit drawback;
- at least one strong or extreme-bounded Skill selector;
- at least one Attribute opposed matchup;
- complete and exit the exercised battle path;
- confirm responsive return and complete cache clearing.

No claim is made that all 103 cards occurred naturally in emulator testing.

## Rollback

Rollback remains source-driven:

1. start from a clean supported workspace;
2. install the merged Milestone 6D source and authoring roster;
3. rebuild from the user-owned exact ROM;
4. do not store or copy generated binary artifacts in the repository.

## Milestone 6F handoff

Milestone 6E completion authorizes a separate design for advanced stateful mechanics. It does not authorize fatigue, activation limits, history penalties, ownership transfer rules, Ability effects, AI, presentation, descriptions, save changes, or adaptive difficulty.

The handoff records:

- complete converted roster hash;
- archetype distribution;
- representative live-runtime evidence;
- known tuning outliers;
- intentionally deferred mechanics;
- exact runtime geometry and fallback contract.
