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

Current checkpoint: **4C — reuse, alternate/scripted paths, lifetime, and reset**.

Task 4 checkpoints:

1. 4A — static Gate-state and mutation-path inventory: complete
2. 4B — runtime normal capture and arena-removal transition: complete
3. 4C — reuse, alternate/scripted paths, lifetime, and reset: pending
4. 4D — activation-counter presence or confirmed absence and replacement storage: pending
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

No per-Gate activation increment appears in the audited placement, removal, transfer, result, and Gate-slot setter paths. This remains unresolved rather than confirmed absent until the bounded exhaustive audit in Checkpoint 4D.

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

Checkpoint 4C must now determine the Gate-slot values' lifecycle in normal and alternate/scripted paths, whether state `2` can return to `0`, and the exact session and participant reset boundaries.
