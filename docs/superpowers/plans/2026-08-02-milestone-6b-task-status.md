# Milestone 6B Task Status

- Task 1: complete
- Task 2: complete
- Task 3: in progress
- Tasks 4–13: pending

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

Task 2 confirmed the complete ownership and participant-targeting model required by Gate Card System 2.0.

### Completed checkpoints

1. 2A — static candidate inventory
2. 2B — canonical Gate owner
3. 2C — challenger and combatant mapping
4. 2D — human and AI identity
5. 2E — effect targeting rules
6. 2F — normalized artifact, resolver, tests, symbols, documentation, and exact-binary verification

### Confirmed runtime model

- `battle object +0x06` is the canonical Gate-owner participant index.
- `session +0x28D` selects the defender or stationary-target descriptor.
- `session +0x28E` selects the challenger or active/thrown descriptor.
- The low nibble of descriptor byte `+0x0F` is the actual participant index.
- Combatant record 0 is the defender record at `battle object +0x0C..+0x1F`.
- Combatant record 1 is the challenger record at `battle object +0x20..+0x33`.
- `participant +0xC8 == NULL` identifies human control.
- `participant +0xC8 != NULL` identifies AI control.
- `battle-result controller +0x21` is a signed winner-record index: `-1` unresolved, `0` defender, `1` challenger.
- The loser is derived as `winner_record_index XOR 1` after a valid result.

### System 2.0 targeting contract

The pure resolver supports owner, defender, challenger, self, opponent, both combatants, winner, loser, human combatants, and AI combatants. It fails closed for unresolved results, equal-descriptor fallbacks, missing explicit self/opponent sources, noncombatant sources, and combatant-only owner effects when the Gate owner is not currently battling.

### Main artifacts

- `analysis/gates/ownership-and-participants.json`
- `analysis/gates/effect-targeting-rules.json`
- `analysis/gates/gate-owner-lifecycle.json`
- `analysis/gates/combatant-record-mapping.json`
- `analysis/gates/challenger-ordering.json`
- `analysis/gates/human-ai-identity.json`
- `analysis/symbols/gate_system2_context.csv`
- `docs/gate-card-system-2-runtime-context.md`
- `src/bakugan_ds/gates/participants.py`

### Verification

Python CI at branch head `55c043482543d5a44ff5acf79ad45068b417b222` completed successfully:

```text
254 passed
12 expected environment-gated skips
0 failed
```

Python compilation, Ruff, strict mypy, the complete repository test suite, changed-file whitespace checks, and exact-binary participant/result-region verification passed.

## Task 3

Current checkpoint: **3C — captured-Gate counter identity and relationship to participant `+0xEE`**.

Task 3 checkpoints:

1. 3A — static match-score candidate inventory: complete
2. 3B — runtime score-changing result and no-change control: complete
3. 3C — captured-Gate counter identity and relationship to score: pending
4. 3D — victory threshold and comparison path: pending
5. 3E — update timing, round lifetime, scripted behavior, and reset: pending
6. 3F — normalized artifact, validators, symbols, tests, CI, and task completion: pending

### Checkpoint 3A result

Static candidate evidence is stored in `analysis/gates/match-score-candidates.json` at commit `e61452d70f57785c3ac18a23c985b419131864cd`.

- participant byte `+0xEE` is cleared by participant construction;
- result finalization resolves the winning participant, sets adjacent byte `+0xFE`, increments `+0xEE`, and stores it back;
- independent consumers compare or combine `+0xEE` values from participant objects;
- result-controller `+0x21` and `+0x0E` are rejected as score counters because Task 2 confirmed them as winner and loser record indices;
- adjacent participant `+0xF4` remains reserved for the captured-Gate investigation.

### Checkpoint 3B attempt 1

A bounded negative result is stored in `analysis/gates/match-score-runtime-attempt-1.json` at commit `cb527249848ccb6a4a67fd79fa24a92ab643b60b`.

The first runtime attempt stopped because the previous DeSmuME executable, process, GDB connection, and save state had not survived the execution-session boundary. No stale runtime address was reused and no semantic confidence was promoted.

### Checkpoint 3B confirmed result

Runtime evidence is stored in `analysis/gates/match-score-runtime-winner-update.json` at commit `ce9327bf2eb91e2df3fd1aed7dae81b55e81dd1e`.

A newly rebuilt and checksum-verified DeSmuME ARM9 GDB bundle booted the exact B6RE revision-0 ROM through a clean new profile into the standalone Battle tutorial. No executable save state was loaded.

At `0x022423F0`, the settled winner was combatant record 0. The result path resolved that record to participant index 1 and live participant pointer `0x022E2640`. Participant index 0 was at `0x022E24E0`.

Across the exact update block ending at `0x0224242C`:

```text
participant 1 (winner) +0xEE: 2 -> 3
participant 0 (other)  +0xEE: 2 -> 2
participant 1 (winner) +0xFE: 0 -> 1
participant 0 (other)  +0xFE: 0 -> 0
```

This confirms participant `+0xEE` as authoritative participant-owned state incremented exactly for the settled winner, with the other combatant providing the required no-change control. Byte `+0xFE` is recorded but remains semantically unnamed.

Checkpoint 3B does not yet prove that `+0xEE` specifically means captured Gate Cards or establish the final victory threshold. Those questions remain isolated to checkpoints 3C and 3D.
