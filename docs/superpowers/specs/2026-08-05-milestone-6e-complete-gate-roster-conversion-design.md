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
