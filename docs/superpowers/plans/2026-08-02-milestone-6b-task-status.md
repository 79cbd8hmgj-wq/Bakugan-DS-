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

Current checkpoint: **2B.2 — reverse-owner control**.

Task 2 checkpoints:

1. 2A — static candidate inventory: complete
2. 2B — canonical Gate owner: in progress
   - 2B.1 — player-owned Gate capture: complete
   - 2B.2 — reverse-owner control: pending
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

This proves ownership for that capture but does not yet prove that `+0x28D` is always the canonical owner field. A reverse-owner control must show `+0x28D = 1`, `+0x28E = 0` when participant index 1 owns the contested Gate. Until then, the field semantics remain probable.

No Task 2 field is considered globally confirmed until the applicable runtime and lifecycle evidence is complete.
