# Milestone 6E Complete Gate Roster Conversion Design

## Status

Milestone 6D is merged and verified. It provides the complete deterministic Gate Card System 2.0 semantic domain, emitted ARM dispatcher, transactional installer, exact-build contracts, and live-runtime baseline. Milestone 6E activates that framework across Gate IDs `1..103` without adding new runtime mechanics.

This document is authoritative for Milestone 6E. It does not reopen Milestone 6D's seven archetypes, budget model, fixed-point arithmetic, condition IDs, target modes, effect IDs, fallback behavior, memory geometry, or scope exclusions.

## Goal

Replace the 102 remaining legacy passthrough records with authored, validated System 2.0 records so every Gate Card has:

- exactly one recognizable archetype;
- a bounded hybrid G-Power identity;
- a bounded six-type battle-weight profile;
- one deterministic field rule expressed through the supported condition, target, effect, or drawback domain;
- an internal power budget inside its archetype band;
- a readable sidecar identity and balance rationale;
- deterministic host, emitted-ARM, exact-ROM, and bounded live verification.

Gate ID `19`, Juggernoid, remains the frozen Milestone 6D reference fixture unless a separately reviewed defect requires a change.

## Hard scope boundary

Milestone 6E may use only the deterministic semantics already merged in Milestone 6D:

- compressed-core hybrid G calculation;
- six record-local attribute modifiers;
- bounded weights for Scratch, Timing, Pop, Spin, Trace, and Bound;
- conditions: none, owner behind, owner ahead, score tied, owner score zero, owner at match point, opponent at match point, and confirmed `Gate Card won` landing;
- targets: current combatant, Gate owner, and Gate non-owner;
- effects: none, add signed G, and subtract magnitude G;
- one explicit drawback in the live record;
- timing phase `0`, pre-Gate calculation.

Milestone 6E must not add or silently emulate:

- Ability Card manipulation;
- activation limits or fatigue;
- battle-history or repeat penalties;
- arena-ID rules;
- AI evaluation changes;
- presentation or description-engine changes;
- save-data changes;
- persistent progression changes;
- secondary live effects;
- new condition, target, effect, or timing IDs.

Those remain later design gates.

## Authoritative inputs

The conversion uses four distinct information classes and must not conflate them:

1. **Confirmed ROM identity** — Gate ID, runtime record identity, and any confirmed original mapping.
2. **Reference names** — the uploaded Gate Card guide may assist naming, but guide order must never define ROM IDs.
3. **Original gameplay observations** — useful for preserving recognizable themes, but not copied as an unreviewed balance target.
4. **New authored System 2.0 design** — the actual Milestone 6E mechanics, budgets, rationales, and sidecar metadata.

Every name-to-ID mapping must carry a confidence value. Unconfirmed names remain explicitly provisional and cannot silently become authoritative.

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

## Canonical deliverables

Milestone 6E adds:

- `config/gates/milestone-6e-system2-v1.json` — all 103 runtime records;
- `config/gates/milestone-6e-roster-metadata.json` — names, confidence, archetype identity, design tier, rationale, and review notes;
- `analysis/gates/milestone-6e-roster-contract.json` — deterministic roster-wide invariants and hashes;
- `analysis/gates/milestone-6e-balance-contract.json` — archetype distribution, budget distribution, evaluation-matrix bounds, and duplicate review;
- `docs/gate-card-system-2-complete-roster.md` — readable roster design and scope boundary;
- deterministic CLI validation and report support;
- host, emitted-module, exact-build, and live-runtime evidence.

Generated ROMs, extracted tables, debugger logs, screenshots, saves, and copyrighted binary payloads remain local and untracked.

## Runtime-record requirements

For every Gate ID `1..103`:

- `card_id` equals its one-based roster position;
- `archetype` is one of the seven nonlegacy archetypes;
- no record uses archetype `0`;
- all semantic IDs are supported by Milestone 6D;
- all reserved and deferred fields remain zero;
- `activation_limit` and `fatigue_rate` remain zero;
- timing phase remains zero;
- secondary condition/effect/value fields remain zero;
- the battle-weight vector satisfies all Milestone 6D bounds;
- the net budget satisfies the selected archetype band;
- the archetype invariants pass;
- the record has a matching sidecar metadata entry.

The final installer must reject any roster containing a legacy record, missing ID, duplicate ID, unsupported semantic, stale metadata identity, or budget violation.

## Seven archetype identities

The fixed archetypes remain:

- **Comeback** — bounded reward when the owner is behind or has zero score;
- **Power** — most gross budget comes from dependable G influence;
- **Skill** — meaningful bounded battle-type pressure;
- **Control** — deterministic targeting or score/landing-based control over G outcomes;
- **Risk** — above-normal gross value purchased with an explicit drawback;
- **Attribute** — pronounced positive and negative record-local attribute profile;
- **Chaos** — unusual deterministic weighting paired with an explicit drawback.

There is no mandatory equal quota. Distribution must be justified by card identity, avoid collapsing most cards into one archetype, and preserve meaningful representation for all seven archetypes. The committed balance contract records and reviews the final distribution.

## Sidecar identity model

Runtime records remain compact and contain no display strings. The metadata sidecar stores, for each card:

- Gate ID;
- confirmed or provisional name;
- mapping confidence and evidence reference;
- selected archetype;
- design tier: early/common, mid, rare/specialized, or high-risk conditional;
- concise gameplay identity;
- G influence summary;
- battle-weight summary;
- condition/target/effect/drawback summary;
- internal budget and band;
- differentiation rationale;
- review status.

The sidecar is authoring evidence, not a save or runtime format.

### Authoring-only roster families

The metadata also records one authoring-only family that mirrors the original
three card-type blocks without creating a new runtime semantic:

- Gate IDs `1..39`: Bakugan-character / Gold cards;
- Gate IDs `40..71`: environmental-field / Silver cards;
- Gate IDs `72..103`: tactical-conditional / Copper cards.

These ranges are corroborated by the canonical global card-name ID domain and
the reference type inventory. Guide row order remains forbidden for assigning
individual card IDs. The family field organizes review and template selection
only; it is never serialized into the 40-byte runtime record.

## Power and effective-swing bands

The existing budget model remains authoritative. Reference-value analysis evaluates the complete roster across compressed core G values:

```text
190, 400, 525, 650, 695
```

and all six attributes.

Expected effective swings remain design targets rather than automatic runtime clamps:

- early/common: approximately `70..130 G`;
- mid: approximately `110..180 G`;
- rare/specialized: approximately `140..220 G`;
- high-risk conditional: up to approximately `250 G`, requiring a real drawback.

Any result outside its stated design tier must be documented and reviewed. Signed negative outcomes are allowed only when they express a deliberate drawback or opposing-attribute identity and remain within existing numeric safety bounds.

## Whole-roster evaluation matrix

Every record is evaluated over a deterministic matrix containing:

- five compressed core G reference values;
- six attributes;
- owner and non-owner combatant targeting;
- solo score states covering tied, ahead, behind, zero score, and both match-point directions;
- landing context missing, nonwinning, and confirmed `Gate Card won` where relevant.

The report records minimum, maximum, conditional branches, target branches, attribute spread, preferred battle type, maximum probability, gross budget, and net budget.

Missing required landing context must continue to produce exact legacy fallback, not a guessed false condition.

## Differentiation and duplicate policy

Exact duplicate live records are forbidden.

The analysis tool generates:

- exact runtime-signature duplicates — hard failure;
- identical evaluation-matrix outputs — hard failure unless the battle-weight identity is materially different and documented;
- potential dominance pairs — review findings, not automatic failures;
- repeated names or conflicting ID mappings — hard failure;
- cards lacking a concise differentiation rationale — hard failure.

A card is not differentiated merely by a small numerical increase. The combination of G profile, weight profile, condition, target, and drawback must create a readable reason to choose it.

## Juggernoid compatibility fixture

Gate ID `19` remains byte-for-byte equivalent to the merged Milestone 6D authored record and serves as:

- the cross-version serializer fixture;
- the host/emitted parity fixture;
- the exact-build hash continuity check;
- the live tutorial compatibility fixture.

Changing Juggernoid requires a separate reviewed commit with explicit before/after balance evidence.

## Installer and fallback behavior

The Milestone 6D transactional and fail-closed behavior remains unchanged:

- invalid authoring fails before trailer generation;
- invalid whole-roster contracts fail before workspace mutation;
- installation is atomic;
- malformed runtime data clears the cache;
- invalid calculation context uses complete original Gate behavior for that combatant;
- selector-only failure uses original fixed metadata for that phase;
- explicit constructor and scripted battle-type overrides retain precedence.

Although all 103 committed records are intended to be live, runtime fallback remains mandatory for corruption and invalid context.

## Live verification strategy

Natural emulator testing cannot exhaust all 103 cards. Milestone 6E therefore separates claims:

1. **Host and exact emitted-ARM matrix** — exhaustive across all 103 records and the deterministic evaluation matrix.
2. **Exact-ROM build validation** — complete trailer, module, cache, hooks, and deterministic double rebuild.
3. **Bounded live sampling** — at least one representative from every archetype, plus Juggernoid, one landing-conditioned Gate, one owner/non-owner Control Gate, one match-point condition, and one high-risk drawback Gate.
4. **Regression paths** — tutorial completion, standard Battle Arena exit, unrelated menu responsiveness, cache clearing, and core-G compression protection.

Live evidence must not be described as exhaustive natural testing of every card.

## Completion criteria

Milestone 6E is complete only when:

- all 103 IDs are nonlegacy and metadata-complete;
- all authoring, budget, weight, and archetype checks pass;
- exact and evaluation-output duplicates are resolved;
- all 103 records pass host/emitted-ARM parity;
- two exact rebuilds are byte-identical;
- protected Milestone 6C/6D ranges and memory geometry remain unchanged;
- bounded live representatives complete and return to responsive game states;
- all 64 cache bytes clear after each completed sampled battle;
- the full local and GitHub CI suites pass;
- temporary workflows, payloads, ROMs, saves, screenshots, and generated binaries are absent from the final diff.

## Handoff

Milestone 6F may introduce advanced stateful mechanics only through a separate design review. Milestone 6E's completed roster becomes the stable deterministic baseline for fatigue, activation history, advanced ownership rules, AI, and presentation work.
