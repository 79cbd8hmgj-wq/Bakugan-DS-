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

Current checkpoint: **2C.2 — challenger ordering policy**.

Task 2 checkpoints:

1. 2A — static candidate inventory: complete
2. 2B — canonical Gate owner: complete
   - 2B.1 — player-owned Gate capture: complete
   - 2B.2 — reverse-owner control: complete
   - 2B.3 — trace canonical Gate-owner source: complete
   - 2B.4 — owner lifetime, reset, and alternate-path validation: complete
3. 2C — challenger and combatant mapping: in progress
   - 2C.1 — descriptor-to-combatant mapping: complete
   - 2C.2 — challenger ordering policy: pending
4. 2D — human and AI identity: pending
5. 2E — effect targeting rules: pending
6. 2F — normalized artifact, tests, CI, and task completion: pending

### Checkpoint 2A result

Candidate-only static evidence is stored in `analysis/gates/ownership-participant-candidates.json` at commit `54f32929704d87cec44555578111b07d820c2ad4`.

It records the paired session fields, their setter and setup paths, their use by the battle constructor, candidate result-state readers, participant pointers, descriptor arrays, exact hashes, and unresolved semantics.

### Checkpoint 2B result

Canonical Gate ownership is confirmed across:

- player-owned and AI-owned runtime controls;
- arena-placement source tracing;
- battle object `+0x04` active Gate ID;
- battle object `+0x06` Gate owner participant index;
- result and final-state lifetime;
- tutorial-skip behavior;
- constructor reset and destructor validity boundaries.

The final lifecycle artifact is `analysis/gates/gate-owner-lifecycle.json` at commit `5afb3f3a6ea83718e7e284c0184e256bba1907f3`.

### Checkpoint 2C.1 result

Combatant mapping is stored in `analysis/gates/combatant-record-mapping.json` at commit `d1b61fa629005c3d53e22c9e2c830cc8d2011fc7`.

Confirmed behavior:

- session `+0x28D` is the descriptor index used to build combatant record 0;
- session `+0x28E` is the descriptor index used to build combatant record 1;
- descriptors are 20 bytes at session `+0x7C + descriptor_index * 20`;
- the low nibble of descriptor byte `+0x0F` is the actual participant object index;
- participant objects resolve through session `+0x0C + participant_index * 4`;
- record 0 occupies battle object `+0x0C..+0x1F` and record 1 occupies `+0x20..+0x33`;
- in the AI-owned control, descriptor order `0,1` resolved to participant order `1,0`;
- record 0 contained participant 1's `230 + 180 = 410` values;
- record 1 contained participant 0's `190 + 100 = 290` values;
- the Gate-calculation loop processes both records with a 20-byte stride.

Therefore `+0x28D/+0x28E` are confirmed descriptor indices and must not be exposed as participant IDs. Checkpoint 2C.2 must determine the policy that orders the descriptors and identify the canonical challenger independently of record index.

No later Task 2 field is considered confirmed until its own runtime and lifecycle evidence is complete.
