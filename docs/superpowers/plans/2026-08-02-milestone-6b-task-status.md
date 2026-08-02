# Milestone 6B Task Status

- Task 1: complete
- Task 2: complete
- Task 3: complete
- Task 4: in progress
- Tasks 5–13: pending

All remaining work follows `docs/superpowers/plans/2026-08-02-milestone-6b-checkpoint-policy.md`.

Each task is divided into small, independently recoverable checkpoints. Each checkpoint must end with a commit, status update, normalized evidence summary, or documented negative result before another checkpoint begins. The assistant stops for user review after each completed task.

## Task 1

Task 1 added the common discovery schema, confirmed-absence rules, arena-only deferral policy, fail-closed readiness evaluator, and the complete requirement manifest.

Verification at commit `ec7ed6f78931f6e06d694a40bd6ad735147de03e`:

```text
240 passed
11 expected environment-gated skips
0 failed
```

Compilation, changed-file Ruff, strict mypy, and whitespace checks passed.

## Task 2

**Status:** complete.

Task 2 confirmed Gate ownership, defender/challenger ordering, combatant identity, human/AI identity, winner/loser mapping, effect targeting, lifecycle behavior, and exact-binary guards.

The normalized implementation and evidence remain in:

- `analysis/gates/ownership-and-participants.json`
- `analysis/gates/effect-targeting-rules.json`
- `analysis/gates/gate-owner-lifecycle.json`
- `analysis/gates/combatant-record-mapping.json`
- `analysis/gates/challenger-ordering.json`
- `analysis/gates/human-ai-identity.json`
- `analysis/symbols/gate_system2_context.csv`
- `docs/gate-card-system-2-runtime-context.md`
- `src/bakugan_ds/gates/participants.py`

Python CI completed with 254 passed, 12 expected environment-gated skips, and 0 failures. Python compilation, Ruff, strict mypy, whitespace checks, and exact-binary participant/result-region verification passed.

## Task 3

**Status:** complete.

Task 3 checkpoints:

1. 3A — static match-score candidate inventory: complete
2. 3B — runtime score-changing result and no-change control: complete
3. 3C — capture-history counter identity and relationship to score: complete
4. 3D — victory threshold and comparison path: complete
5. 3E — update timing, round lifetime, scripted behavior, and reset: complete
6. 3F — normalized artifact, validators, symbols, tests, CI, and task completion: complete

### Confirmed model

- Participant `+0xEE` is the authoritative captured-Gate match score.
- Participant `+0xF4` is a separate count of populated six-byte capture-history records at `participant +0x84 + index * 6`.
- The ordinary result path resolves the winner, sets winner `+0xFE`, increments winner `+0xEE`, appends capture history, increments `+0xF4`, and evaluates victory later.
- Solo victory is `participant[+0xEE] >= 3`.
- Team victory is `participant[+0xEE] + teammate[+0xEE] >= 3`; the teammate index comes from participant `+0xF2` when the confirmed team flag is enabled.
- Participant construction clears score and capture history. Confirmed mode/script setup may seed both primary scores afterward.
- Score remains valid through result and post-result presentation while the participant object is live.
- Participant destruction invalidates and frees the object without clearing `+0xEE` in place.

### Normalized implementation and evidence

- `src/bakugan_ds/gates/match_state.py`
- `analysis/gates/match-score-and-capture.json`
- `analysis/gates/match-score-candidates.json`
- `analysis/gates/match-score-runtime-winner-update.json`
- `analysis/gates/capture-history-counter.json`
- `analysis/gates/match-score-victory-threshold.json`
- `analysis/gates/match-score-lifecycle.json`
- `analysis/symbols/gate_system2_context.csv`
- `docs/gate-card-system-2-runtime-context.md`
- `tests/unit/test_gate_match_state.py`
- `tests/test_gate_match_state_artifact.py`
- `tests/integration/test_gate_match_state_reference.py`

### Final verification

GitHub Python CI run `30766338199` completed successfully at branch commit `ceedcea815bfe3b10e0f8b3ddd639b928424297f`:

```text
265 passed
13 expected environment-gated skips
0 failed
```

Python compilation, changed-file Ruff, strict mypy, and changed-file whitespace checks passed. The exact decoded-overlay integration test also passed locally against overlay-7 SHA-256 `82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1`.

## Task 4

**Status:** in progress.

Current checkpoint: **4E — normalized model, validators, lifecycle documentation, exact-binary tests, CI, and task completion**.

Task 4 checkpoints:

1. 4A — static Gate-state and mutation-path inventory: complete
2. 4B — runtime normal capture and arena-removal transition: complete
3. 4C — reuse, alternate/scripted paths, lifetime, and reset: complete
4. 4D — activation-counter presence or confirmed absence and replacement storage: complete
5. 4E — normalized model, validators, lifecycle documentation, exact-binary tests, CI, and task completion: pending

### Checkpoint 4A

`analysis/gates/gate-state-candidates.json` at commit `d84859fbf9ee696b49dce8b82226feb946b4b898` separates the original Gate-state mechanisms without promoting candidate names beyond the evidence.

Static evidence identifies:

- `participant +0x56 + gate_slot_index * 4` as a three-value Gate-slot state byte. Arena allocation writes `1`, arena transfer writes old `0` and new `1`, and arena removal writes `2`.
- `participant +0xF8` as a byte adjusted only when Gate slots enter or leave state `0`, making it the probable available-Gate-slot count.
- `session +0x1C + arena_entry_index * 8 +0x02` as the probable arena-placement occupied byte.
- `session +0x294` as the probable active arena-placement count.
- `0x022626B8` as the arena-placement removal path and `0x02262828` as a separate combatant descriptor/scene cleanup path.

The normal result path increments score and capture history first, then removes the defender's arena placement, writes Gate-slot state `2`, clears the board reference, decrements the arena-placement count, and separately cleans both combatant descriptors.

No per-Gate activation increment appears in the audited placement, removal, transfer, result, and Gate-slot setter paths. This was resolved through the bounded exhaustive audit in Checkpoint 4D.

### Checkpoint 4B

`analysis/gates/gate-removal-runtime.json` at commit `66f8658e24721bd55c71c05a17f10bcbbfa09510` records a clean pre/post transition across the common result path's call to arena-placement removal `0x022626B8`.

The runtime was paused at `0x02242498`, after winner score and capture-history bookkeeping but before board removal, and again at `0x022424B4`, immediately after the removal helper returned but before combatant descriptor cleanup.

Confirmed transition:

```text
arena record +0x02: 1 -> 0
board-grid reference: 1 -> 0
session +0x294: 1 -> 0
owner Gate-slot state: 2 -> 2
owner participant +0xF8: 0 -> 0
non-owner Gate-slot entries: unchanged
```

This confirms the arena-record presence byte, the corresponding board-grid reference clear, and `session +0x294` as an active arena-placement count for the observed table and path. It also rejects the narrow interpretation that participant Gate-slot value `2` uniquely means “captured” or “removed”: in the tutorial scenario, the active owner slot already contained `2` before removal, so the helper's write of `2` was idempotent.

### Checkpoint 4C

`analysis/gates/gate-state-lifecycle.json` at commit `5c009b2f8d20fd9fa6f86cfc0148ba9912689086` confirms the Gate-slot state machine, ordinary transfer behavior, scripted overrides, and reset boundaries.

- State `0` is the ordinary selectable or unassigned state. Participant construction clears the Gate-slot entries, and the ordinary selector at `0x0226A5E8` counts and chooses only zero-state slots.
- State `1` is assigned to an active arena placement. Allocation writes `1`; active-placement transfer writes `1` to the replacement slot.
- State `2` is unavailable to ordinary placement selection, but is not uniquely captured or removed. Arena removal writes `2`, while multiple scripted setup paths also write `2` before battle.
- Active-placement transfer at `0x02262714` returns the old slot to `0`, changes the arena entry's owner and slot identity, and marks the replacement slot `1` without changing active-placement count.
- No dedicated decoded-overlay-7 path was found that restores a removed state-2 Gate after its arena record is cleared.
- Participant construction initializes Gate slots to zero and `+0xF8` from configured Gate count. Session construction clears arena records, board-grid state, and `+0x294`.
- Scripted setup at `0x0226A48C` directly overrides Gate-slot values and writes `+0xF8 = 0`; it can make the cache diverge from a simple count of zero-state slots.
- Destruction ends object validity without clearing Gate state in place. New construction is the authoritative reset boundary.

### Checkpoint 4D

`analysis/gates/gate-activation-counter-audit.json` at commit `b607f54c66fc30eec295991b1a8e5647f4db808f` confirms that the exact B6RE revision-0 Gate lifecycle contains no original per-Gate activation counter.

The bounded exhaustive audit covered every direct decoded-overlay-7 caller of Gate-slot mutation, arena allocation/removal/transfer, descriptor attachment/detachment, and battle construction; the complete constructor, result, reset, scripted setup, and teardown regions; all 18 direct overlay-7 callers of ARM9 Gate-bonus accessor `0x02065BF4`; and every known adjacent participant, session, arena-record, battle-object, score, capture-history, placement-count, and descriptor-count candidate.

Rejected activation-count candidates include:

- `session +0x294`, confirmed as active arena-placement count;
- `session +0x295` and arena entry `+0x21`, confirmed as descriptor/scene linkage state;
- participant `+0xF8`, confirmed as an ordinary available-slot cache with scripted overrides;
- participant `+0xEE` and `+0xF4`, already confirmed as match score and capture-history count;
- Gate-slot state bytes, which hold enumerated lifecycle state rather than an incrementing count;
- battle-local Gate ID/owner fields and the pure ARM9 Gate-bonus table accessor, neither of which mutates activation history.

System 2.0 must allocate new match-local activation state. The safe contract reserves `activation_count_by_arena_entry[12]` as unsigned saturating bytes at offsets `0x2C..0x37` of the already approved future 64-byte overlay-7 BSS cache `0x02293C20..0x02293C60`. The array resets at session construction, initializes on arena allocation, increments once after canonical Gate identity is established during battle construction, resets when an active placement changes Gate identity, and clears when the placement is removed. No original object byte or save-data field is repurposed, and the cache is not implemented in Milestone 6B.

Checkpoint 4E will consolidate the confirmed Gate state into the normalized artifact, validators, lifecycle documentation, exact-binary tests, and final Task 4 verification.
