# Milestone 6B Task Status

- Task 1: complete
- Task 2: complete
- Tasks 3–13: pending

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

**Status:** complete — awaiting user review before Task 3.

Task 2 confirmed the complete ownership and participant-targeting model required by Gate Card System 2.0.

### Completed checkpoints

1. 2A — static candidate inventory
2. 2B — canonical Gate owner
   - player-owned Gate control
   - reverse-owner AI control
   - canonical owner source
   - owner lifetime, reset, and alternate-path validation
3. 2C — challenger and combatant mapping
   - descriptor-to-combatant mapping
   - challenger ordering policy
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
- `battle-result controller +0x21` is a signed winner-record index:
  - `-1` unresolved;
  - `0` defender won;
  - `1` challenger won.
- The loser is derived as `winner_record_index XOR 1` after a valid result.

### System 2.0 targeting contract

The pure resolver supports:

- owner
- defender
- challenger
- self
- opponent
- both combatants
- winner
- loser
- human combatants
- AI combatants

The resolver fails closed for unresolved results, equal-descriptor fallbacks, missing explicit self/opponent sources, noncombatant sources, and combatant-only owner effects when the Gate owner is not currently battling.

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

The following passed in the same run:

- Python compilation
- Ruff on all changed Python files
- strict mypy on changed package files
- complete repository test suite
- changed-file whitespace checks

A separate local exact-binary verification against the supplied runtime ARM9 and decoded overlay 7 confirmed all nine guarded participant/result instruction regions and both expected component SHA-256 hashes.

No Gate bonus, battle-type selection, Ability Card behavior, AI decision, match result, roster value, ROM payload, or save format was changed.

## Next task

Task 3 will reverse-engineer authoritative match score, captured-Gate counts, victory threshold, score updates, capture timing, and reset behavior. It has not started.
