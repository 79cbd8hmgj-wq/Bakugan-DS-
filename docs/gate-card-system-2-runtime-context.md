# Gate Card System 2.0 Runtime Context

Milestone 6B replacement-boundary contract for B6RE revision 0. No live System 2.0 gameplay effect is enabled.

## Boundary

- `ready_for_milestone_6c = true`; sole deferred key: `arena_id`.
- Hooks validate record, cache, context, and phase, then fail closed to original behavior.
- No ROM, save/state, screenshot, RAM dump, raw log, or complete copied table is committed.

## Confirmed requirements

| Requirement | Presence / width | Owner / access | Init, mutation, lifetime, reset | Player/AI and scripts | Evidence |
|---|---|---|---|---|---|
| `ability_available` | present/8 | participant Ability slots and available-count cache; participant +0x6E + slot*4 state | Participant construction initializes slots/count; zero-to-nonzero transitions decrement availability. | Shared by both participants; scripts may disable slots. | `ability-card-state.json:ability_available` |
| `ability_resolved` | present/8 | Ability effect scene; scene +0x4D terminal state 20 | Effect state machine starts from constructed state; state 19 cleans up before terminal completion. | Both combatants share terminal cleanup; card branches converge. | `ability-card-state.json:ability_resolved` |
| `ability_selected` | present/8 | battle preparation object and Ability descriptor; slot or 0xFF | No selection is 0xFF; accepted slot/ID enters the descriptor; reset with battle preparation. | Shared descriptor geometry; disabled slots force 0xFF. | `ability-card-state.json:ability_selected` |
| `ability_used` | present/8 | participant Ability slot and count cache; state 2 and +0xF9 count | Available state 0 becomes state 2; count decreases; consumed state persists until participant reset. | Shared consumption contract; scripts may also seed state 2. | `ability-card-state.json:ability_used` |
| `battle_type_history` | absent/None | absent from original selector; current type only exists in battle object | No original initialization, mutation, lifetime, or reset; replacement is match-local cache history. | Original human/AI and scripted paths have no history. | `battle-history-and-rng.json:battle_type_history` |
| `cache_initialization` | confirmed/— | loader/cache artifact; normalized executable and runtime evidence | Valid trailer initializes one selected record and metadata; invalid input leaves cache invalid. | Shared original behavior unless validation succeeds. | `loader-and-cache.json:cache_initialization` |
| `cache_invalidation` | confirmed/— | loader/cache artifact; battle-completion clear hook | All 64 bytes clear after normal result/removal; no save persistence. | Shared cleanup path; scripted behavior preserves fail-closed invalid state. | `loader-and-cache.json:cache_invalidation` |
| `cache_reset` | confirmed/— | loader/cache artifact; match-local cache | Construction/reset leaves cache invalid until a validated selected record is loaded. | Shared for human and AI; scripts do not bypass validation. | `loader-and-cache.json:cache_reset` |
| `calculation_trace_format` | present/8 | deterministic JSON calculation trace v1 | Ordered integer source components and final result; reset per calculation. | Identical fields for human and AI; records final overrides/fallback. | `system2-record-v1.json:calculation_trace_format` |
| `captured_gate_count` | present/8 | participant object +0xF4 and six-entry ledger at +0x84 | Constructor clears ledger/count; capture appends then increments; lifetime is participant-owned. | Same winner-relative update for human and AI; scripted paths may append explicitly. | `match-score-and-capture.json:captured_gate_count` |
| `challenging_participant` | present/8 | session +0x28E descriptor mapped through descriptor participant nibble | Collision/setup selects descriptor before battle construction; reset with session descriptor state. | Same mapping for human or AI challenger; scripts may select alternate descriptors. | `ownership-and-participants.json:challenging_participant` |
| `combatant_identity` | present/16 | battle object plus source session descriptors | Constructor resolves defender then challenger participant and fills two combatant records. | Record order is independent of player/AI identity; scripts use same mapping. | `ownership-and-participants.json:combatant_identity` |
| `difficulty` | present/8 | shared Battle Arena config at 0x020D433C +0x96 | Menu decodes descriptor bits 5–6 and stores value; AI reads it directly; next setup overwrites it. | Selected opponent difficulty affects AI; no equivalent human modifier was found. | `difficulty-context.json:difficulty` |
| `effect_target` | present/16 | hook-local normalized context over owner/defender/challenger/winner/loser | Computed per effect after phase validation; no original state mutation; discarded after invocation. | Same pointer-based resolution for human and AI; invalid scripted context fails closed. | `ownership-and-participants.json:effect_target` |
| `arena_id` | deferred/None | arena context unresolved | Not confirmed; no mutation or replacement use approved in version 1. | Not confirmed for player, AI, or scripts. | `landing-and-shot-context.json:arena_id` |
| `gate_activation_count` | absent/None | absent from original Gate lifecycle | No original storage; replacement uses match-local per-entry counters. | Not applicable originally; scripts do not create a counter. | `gate-reuse-and-removal.json:gate_activation_count` |
| `gate_capture_state` | present/8 | winner match score +0xEE, capture ledger/count, active placement | Constructor clears state; result increments score, appends ledger, then removes placement. | Winner-relative and shared by human/AI; script-seeded score is distinguished from capture. | `gate-reuse-and-removal.json:gate_capture_state` |
| `gate_owner` | present/8 | battle object +0x06 | Constructor clears then derives owner from arena entry and participant Gate slot; next constructor resets. | Shared representation for human- and AI-owned Gates; scripted setup still supplies arena owner. | `ownership-and-participants.json:gate_owner` |
| `gate_removal_state` | present/8 | arena entry occupied byte, board-grid reference, session +0x294 | Session construction clears; removal changes occupied/grid/count; transfer preserves occupancy. | Canonical arena-entry removal is shared; owner slot may already be unavailable in scripts. | `gate-reuse-and-removal.json:gate_removal_state` |
| `gate_reuse_state` | present/8 | participant Gate-slot state and +0xF8 availability cache | Constructor initializes state 0; placement sets 1; removal sets 2; transfer returns old slot to 0. | Same setter/selector for human and AI; scripts may seed state 2 and override count. | `gate-reuse-and-removal.json:gate_reuse_state` |
| `gate_record_geometry` | present/32 | 103 fixed GateRecordV1 entries | Offset = 32 + (card_id - 1) * 40; deterministic ordered serialization; immutable after load. | Same record geometry for every participant and scripted battle. | `system2-record-v1.json:gate_record_geometry` |
| `g2dt_header_geometry` | present/32 | 32-byte little-endian G2DT trailer header | Deterministically built; parser validates version/geometry/CRC before records are exposed. | Shared data format; malformed scripted or normal loads fail closed. | `system2-record-v1.json:g2dt_header_geometry` |
| `human_ai_identity` | present/32 | participant +0xC8 optional AI-controller pointer | Constructor clears; later human slots remain null and AI slots receive controller; destructor frees it. | Null = human, non-null = AI; scripts retain the same object contract. | `ownership-and-participants.json:human_ai_identity` |
| `landing_result` | present/8 | throw controller +0x1D2 | Constructor initializes zero; primary/alternate evaluators assign result; reset for next throw. | Shared evaluator field; scripted retry may leave code 0 without universal semantic label. | `landing-and-shot-context.json:landing_result` |
| `malformed_fallback` | confirmed/— | loader/cache validation contract | Missing/truncated/invalid geometry/CRC leaves cache invalid and preserves legacy path. | Same fail-closed behavior for human, AI, and scripts. | `loader-and-cache.json:malformed_fallback` |
| `match_score` | present/8 | participant +0xEE | Constructor clears; normal winner increments once; scripts may seed after construction; lifetime is participant object. | Same update and threshold for human/AI; team mode aggregates teammate +0xEE. | `match-score-and-capture.json:match_score` |
| `nitrofs_close` | confirmed/— | exact carrier FSFile lifecycle | Close follows final read and ends file-object use; error paths preserve fail-closed state. | Shared loader operation. | `loader-and-cache.json:nitrofs_close` |
| `nitrofs_open` | confirmed/— | FSFile, archive pointer, file ID 2762 | Open initializes the 72-byte FSFile for the carrier; failure prevents seek/read. | Shared loader operation. | `loader-and-cache.json:nitrofs_open` |
| `nitrofs_read` | confirmed/— | FSFile current position, destination, requested size | Exact return/short-read behavior is checked; insufficient bytes invalidate trailer load. | Shared loader operation. | `loader-and-cache.json:nitrofs_read` |
| `nitrofs_seek` | confirmed/— | FSFile and carrier-relative trailer offset | Seek precedes reads; errors invalidate the load without mutating gameplay state. | Shared loader operation. | `loader-and-cache.json:nitrofs_seek` |
| `original_bss_preservation` | confirmed/— | overlay-7 layout contract | Original 0x640-byte BSS is retained; new cache/module storage is separate. | Shared executable layout. | `loader-and-cache.json:original_bss_preservation` |
| `overlay_growth` | confirmed/— | overlay-7 module layout | Separate 0x8000-byte System 2.0 module region is reserved without shifting original BSS ownership. | Shared executable layout. | `loader-and-cache.json:overlay_growth` |
| `authoring_schema` | present/8 | schemas/gate-system2-v1.schema.json | Version 1 requires every field and forbids additions; validation occurs before serialization. | Not participant-specific; arena-dependent fields excluded. | `system2-record-v1.json:authoring_schema` |
| `serializer` | present/8 | bakugan_ds.gates.record pure host functions | Deterministic header/record/trailer serialization; no external mutation; parse reconstructs exact records. | Same bytes for all battle contexts. | `system2-record-v1.json:serializer` |
| `shot_condition` | present/8 | main shot controller +0x6198 copied to throw +0x1DF | Human or AI source category is stored in shared controller then copied on ordinary/alternate paths. | Human and AI converge; scripts use the alternate copy path when applicable. | `landing-and-shot-context.json:shot_condition` |
| `timing_ability_activation` | present/32 | Ability scene/source/descriptor at 0x0221A6B4 | Valid after selection; may apply battle-local riders; rollback preserves original descriptor/consumption. | Shared boundary with explicit participant resolution; 0xFF bypasses activation. | `effect-timing.json:timing_ability_activation` |
| `timing_ability_resolution` | present/32 | Ability scene/participants/battle at 0x0221B8D0 | Valid at terminal state; post triggers run once; rollback keeps legacy result and clears temporary state. | Shared boundary; card branches converge after cleanup. | `effect-timing.json:timing_ability_resolution` |
| `timing_battle_result` | present/32 | result controller/battle/combatants at 0x022423E0 | Settled winner/loser context before capture mutation; invalid winner continues legacy path. | Shared result boundary; specialized paths fail closed. | `effect-timing.json:timing_battle_result` |
| `timing_battle_start` | present/32 | battle/type controller/combatants at 0x02241908 | Common convergence after type-controller creation; effects may touch battle-local state only. | Forced/scripted types converge here; rollback ignores temporary System 2.0 state. | `effect-timing.json:timing_battle_start` |
| `timing_gate_capture` | present/32 | winner/result/ledger at 0x022423F0 | Score/ledger update occurs once; rollback executes only original sequence. | Shared winner-relative boundary; script score seeds are not capture. | `effect-timing.json:timing_gate_capture` |
| `timing_gate_removal` | present/32 | session/arena entry/owner slot at 0x022626B8 | Placement/grid/count and System 2.0 entry state clear; rollback completes legacy removal. | Shared removal; script may have owner slot already state 2. | `effect-timing.json:timing_gate_removal` |
| `timing_match_reset` | present/32 | session/participants/cache at 0x0225FD5C | Clears match-local System 2.0 state; rollback leaves cache invalid and continues constructors. | Shared reset; scripts may seed score/slots afterward. | `effect-timing.json:timing_match_reset` |
| `timing_post_battle_type` | present/32 | battle/script context at 0x0224183C | Final type is stable; history may update once; rollback dispatches legacy final type. | Script override codes already applied before this boundary. | `effect-timing.json:timing_post_battle_type` |
| `timing_post_gate` | present/32 | battle/combatant record at 0x0223D290 | Core, Gate bonus, and target total are valid; only battle-local total/state may be written. | Shared boundary; scripted completion occurs after stores. | `effect-timing.json:timing_post_gate` |
| `timing_pre_battle_type` | present/32 | result controller/battle at 0x0223E338 | Explicit/fallback selection context valid; rollback uses explicit value or legacy selector. | Explicit constructor argument bypasses metadata selection. | `effect-timing.json:timing_pre_battle_type` |
| `timing_pre_gate` | present/32 | battle/combatant/cache at 0x0223D1D0 | Gate identity/core/attribute valid; invalid cache uses legacy lookup. | Shared boundary; tutorial skip occurs later. | `effect-timing.json:timing_pre_gate` |
| `timing_round_reset` | present/32 | battle object/children at 0x0223D3F4 | Destroys per-battle objects and invalidates pointers; external match history remains. | Scene routes converge on destruction. | `effect-timing.json:timing_round_reset` |
| `trailer_validation` | confirmed/— | loader/cache validation contract | Exact G2DT geometry/order/CRC required before cache population. | Shared loader behavior. | `loader-and-cache.json:trailer_validation` |
| `validator` | present/8 | G2DTHeader.validate and GateRecordV1.validate | Every parser/serializer fails closed on unsupported values; no state mutation. | Same failure policy for all battles/scripts. | `system2-record-v1.json:validator` |
| `victory_threshold` | present/8 | Gate match-victory helper constant 3 | Compile-time immediate; no runtime mutation; applies to solo score or team aggregate. | Same threshold for human and AI; script-seeded score is evaluated normally. | `match-score-and-capture.json:victory_threshold` |
| `weighted_rng` | present/32 | ARM9 global LCG state and 0x02021A30 weighted selector | Seed wrapper initializes state; call consumes unsigned byte weights; zero total returns -1. | Control-identity agnostic; explicit/scripted type overrides retain precedence. | `battle-history-and-rng.json:weighted_rng` |

Full field semantics and executable/runtime evidence are preserved in the referenced normalized artifacts.

## Confirmed-absent state and replacement storage

- `battle_type_history`: absent; cache `+0x38..+0x3B` stores recent final types.
- `gate_activation_count`: absent; twelve saturating bytes at cache `+0x2C..+0x37`, indexed by arena entry.
- post-removal Gate reuse: no ordinary restore path; future reuse is explicit match-local behavior.

## Effect phases

| Phase | Boundary | Valid context | Mutation / rollback |
|---|---:|---|---|
| `pre_gate` | `0x0223D1D0` | Gate ID; Gate owner; core G; attribute | Read validated context; invalid cache uses legacy lookup. / Use legacy Gate lookup. |
| `post_gate` | `0x0223D290` | core G; Gate bonus G; target total G | Write battle-local target total and System 2.0 state only. / Replay original add/store. |
| `pre_battle_type` | `0x0223E338` | Gate ID; combatants; explicit type argument | Choose candidate type 0..5 or preserve -1 fallback. / Use explicit value or legacy selector. |
| `post_battle_type` | `0x0224183C` | final type; history cache; override code | Update match-local history once; do not alter final type. / Dispatch legacy final type. |
| `battle_start` | `0x02241908` | final type; Gate totals; Ability selections | Apply battle-start effects to battle-local state only. / Ignore temporary System 2.0 state. |
| `ability_activation` | `0x0221A6B4` | Ability slot; Ability ID; source; target | Consume selected slot and apply battle-local riders. / Preserve legacy descriptor and consumption. |
| `ability_resolution` | `0x0221B8D0` | Ability ID; source; target; post-effect G | Run post-Ability triggers once. / Keep legacy result; clear temporary state. |
| `battle_result` | `0x022423E0` | winner; loser; final totals; margin | Evaluate result conditions before capture mutation. / Reject invalid winner and continue legacy path. |
| `gate_capture` | `0x022423F0` | winner; match score; capture count; Gate owner | Increment score once and append one ledger entry. / Execute original score/ledger sequence only. |
| `gate_removal` | `0x022626B8` | arena index; owner; occupied; grid; placement count | Clear placement/grid/count and System 2.0 cache state. / Zero System 2.0 state; complete legacy removal. |
| `round_reset` | `0x0223D3F4` | completed round context; persistent match history | Destroy per-battle objects; retain external match history. / Discard stale pointers. |
| `match_reset` | `0x0225FD5C` | match config; arena state; activation/history cache | Clear all match-local System 2.0 state. / Leave cache invalid and continue constructors. |

## Match-local cache

Range: `0x02293C20–0x02293C60` (64 bytes).

| Offset | Size | Purpose |
|---:|---:|---|
| `0x00` | 40 | Validated `G2DT` record |
| `0x28` | 1 | Gate ID |
| `0x29` | 1 | Format version |
| `0x2A` | 1 | Valid flag |
| `0x2B` | 1 | Arena-entry index |
| `0x2C` | 12 | Activation counts |
| `0x38` | 4 | Battle-type history |
| `0x3C` | 4 | Reserved |

The cache loads only after trailer validation, remains match-local, and clears all 64 bytes at battle completion. It never reuses original participant, arena, battle, padding, or save bytes.

## Data, loader, and deferral

- `G2DT`: 32-byte header, 40-byte record, 103 records, 4,152-byte trailer.
- NitroFS carrier ID `2762`; exact open/seek/read/short-read/close behavior is guarded.
- Original overlay-7 BSS remains `0x640`; a separate `0x8000` module region is reserved.
- Missing, malformed, truncated, or CRC-invalid data preserves legacy behavior.
- `arena_id` is the only deferred field; version 1 has no arena-dependent condition/effect.

## Milestone 6C entry

One experimental data-driven Gate may use only the confirmed fields/phases above, with record/cache validation and legacy rollback.
