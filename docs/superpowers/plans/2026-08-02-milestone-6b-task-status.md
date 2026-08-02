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

Current checkpoint: **3E — update timing, score lifetime, scripted behavior, and reset**.

Task 3 checkpoints:

1. 3A — static match-score candidate inventory: complete
2. 3B — runtime score-changing result and no-change control: complete
3. 3C — capture-history counter identity and relationship to score: complete
4. 3D — victory threshold and comparison path: complete
5. 3E — update timing, round lifetime, scripted behavior, and reset: pending
6. 3F — normalized artifact, validators, symbols, tests, CI, and task completion: pending

### Checkpoint 3A

`analysis/gates/match-score-candidates.json` at commit `e61452d70f57785c3ac18a23c985b419131864cd` identified participant byte `+0xEE` as the strongest static participant match-progress candidate. It is constructor-cleared, incremented for the settled winner, and consumed outside immediate result presentation.

### Checkpoint 3B

The successful runtime retry is stored in `analysis/gates/match-score-runtime-winner-update.json` at commit `ce9327bf2eb91e2df3fd1aed7dae81b55e81dd1e`.

Across `0x022423F0..0x0224242C` in a clean standalone Battle tutorial result:

```text
participant 1 (winner) +0xEE: 2 -> 3
participant 0 (other)  +0xEE: 2 -> 2
participant 1 (winner) +0xFE: 0 -> 1
participant 0 (other)  +0xFE: 0 -> 0
```

This confirms `+0xEE` as authoritative participant-owned match-progress state incremented exactly for the settled winner. `+0xFE` remains semantically unnamed.

### Checkpoint 3C

`analysis/gates/capture-history-counter.json` at commit `3ecda0c3a2f6fa1132e477394170b144d5338e8c` separates participant `+0xF4` from match score.

The process was paused after the winner's `+0xEE` update and immediately before the capture-ledger block. At that boundary:

```text
winner +0xEE = 3
winner +0xF4 = 0
winner capture entry 0 = empty
```

After `0x0224242C..0x02242498`:

```text
winner +0xEE = 3       unchanged
winner +0xF4 = 1       incremented
winner entry 0 = be0000000000
other  +0xF4 = 0       unchanged
```

Static evidence confirms that `participant +0xF4` indexes six-byte capture-history entries at `participant +0x84 + index * 6`. It is not the authoritative match-score field.

### Checkpoint 3D

`analysis/gates/match-score-victory-threshold.json` at commit `c2dce8bf3bc77fce08d7c11ad69e19e466aad03e` confirms the exact victory helper and threshold.

The helper at `0x02263150`:

- iterates the configured participant count from global match configuration `+0x97`;
- reads participant `+0xEE`;
- when team-mode flag `+0x98` is enabled, resolves the teammate through participant `+0xF2` and adds the teammate's `+0xEE`;
- compares the resulting individual or team score against `3` with an unsigned `>=` test;
- returns `1` when any participant or team reaches the threshold, otherwise `0`.

A single runtime call supplied both controls:

```text
participant 0 +0xEE = 2: threshold branch not taken
participant 1 +0xEE = 3: threshold branch taken
helper return r0 = 1
caller 0x0223E834 -> match-complete target 0x0223E8D4
```

This confirms participant `+0xEE` as the captured-Gate match score for standard Gate battles. Solo participants are tested individually; team mode sums the participant and teammate scores before applying the same victory threshold of three.

Checkpoint 3E will determine score initialization outside constructor-only evidence, round-to-round persistence, scripted seeding or bypasses, match completion lifetime, and final reset.
