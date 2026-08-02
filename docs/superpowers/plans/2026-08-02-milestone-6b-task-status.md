# Milestone 6B Task Status

- Task 1: complete
- Task 2: in progress
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

Current checkpoint: **2C — challenger and combatant mapping**.

Task 2 checkpoints:

1. 2A — static candidate inventory: complete
2. 2B — canonical Gate owner: complete
   - 2B.1 — player-owned Gate capture: complete
   - 2B.2 — reverse-owner control: complete
   - 2B.3 — trace canonical Gate-owner source: complete
   - 2B.4 — owner lifetime, reset, and alternate-path validation: complete
3. 2C — challenger and combatant mapping: pending
4. 2D — human and AI identity: pending
5. 2E — effect targeting rules: pending
6. 2F — normalized artifact, tests, CI, and task completion: pending

### Checkpoint 2A result

Candidate-only static evidence is stored in `analysis/gates/ownership-participant-candidates.json` at commit `54f32929704d87cec44555578111b07d820c2ad4`.

It records:

- the paired byte fields at session offsets `+0x28D` and `+0x28E`;
- their generic setter and repeated `0, 1` setup initialization;
- their use by the battle-record constructor;
- two candidate result-state readers;
- participant-pointer and 20-byte descriptor-array candidates;
- exact overlay-7 hashes and instruction-range hashes;
- all remaining semantic questions.

Verification:

```text
240 passed
11 expected environment-gated skips
0 failed
```

Compilation, changed-file Ruff, strict mypy, and whitespace checks passed.

### Checkpoint 2B.1 result

The player-owned tutorial capture is stored in `analysis/gates/ownership-runtime-player-owned.json` at commit `59f9985f30d5d74f328d07e8cad1b04b51677f74`.

The controlled clean-launch scenario established:

- P1/player placed Juggernoid, global Gate ID 19;
- participant index 0 maps to the 190 G player object and owns Gate IDs 19, 40, and 72;
- participant index 1 maps to the 230 G AI object and owns Gate IDs 21, 59, and 93;
- the active session pair is `+0x28D = 0`, `+0x28E = 1`;
- the battle constructor reached the confirmed 190 + 100 = 290 and 230 + 180 = 410 totals.

This proved ownership for that capture but did not prove that `+0x28D` was always the canonical owner field.

### Checkpoint 2B.2 result

The reverse-owner control is stored in `analysis/gates/ownership-runtime-ai-owned-control.json` at commit `4483d8df8a8231cefdfbe85b99d89b23c2290ce8`.

The controlled battle established:

- P2/AI participant index 1 owned the contested Gate;
- both Gate lookup calls entered `0x02065BF4` with global Gate ID 21;
- Gate ID 21 is present in participant index 1's Gate slots and absent from participant index 0's Gate slots;
- participant index 0 remained the 190 G P1/player object;
- participant index 1 remained the 230 G P2/AI object;
- session `+0x28D` and `+0x28E` remained `0, 1` instead of reversing.

Therefore the interpretation of `+0x28D/+0x28E` as canonical Gate owner followed by challenger is rejected with confirmed evidence. The pair remains a probable fixed participant/combatant ordering only.

### Checkpoint 2B.3 result

The confirmed owner-source path is stored in `analysis/gates/gate-owner-source-path.json` at commit `51d8e0ae0f10664e74fd92b40607cc80521eec08`.

For the observed clean-launch battle path:

- the arena-placement record stores Gate slot index at byte `+0` and Gate-owner participant index at byte `+1`;
- the battle constructor copies the owner index into battle object `+0x06`;
- the constructor selects the owner participant object and reads the Gate ID from `participant +0x54 + gate_slot_index * 4`;
- the active Gate ID is stored in battle object `+0x04`;
- in the AI-owned control, the placement record held slot `0`, owner participant `1`, and the resulting battle header held Gate ID `21`, owner `1`;
- constructor entry clears `+0x04` and `+0x06` before assigning the derived values;
- all assignments occur before the first Gate bonus lookup.

### Checkpoint 2B.4 result

The complete owner lifecycle is stored in `analysis/gates/gate-owner-lifecycle.json` at commit `5afb3f3a6ea83718e7e284c0184e256bba1907f3`.

Confirmed behavior:

- battle object `+0x04` remained Gate ID `21` and `+0x06` remained owner participant `1` at result-state entry `0x0223ED00`;
- both fields remained unchanged at final-state entry `0x0223EEDC`;
- both fields remained unchanged after the built-in tutorial skip reached its completion dialogue;
- arena-placement bytes for Gate slot `0` and owner participant `1` remained stable while separate transient state bytes were cleared;
- decoded overlay 7 contains one direct call to constructor `0x0223CFE8`, at `0x0223E334`;
- no later write in the battle-object class code changes `+0x04` or `+0x06`;
- the tutorial skip is downstream of normal construction and does not bypass owner derivation;
- destructors `0x0223D3F4` and `0x0223D478` release child resources and the battle object without clearing those fields;
- validity ends when the battle object is destroyed, and the next constructor resets both fields to zero before deriving the next Gate and owner.

Gate ownership is therefore confirmed for Task 2. Physical Gate capture, removal, and reuse bookkeeping remains assigned to Task 4 and was not inferred from stale battle-object memory.

No later Task 2 field is considered confirmed until its own runtime and lifecycle evidence is complete.
