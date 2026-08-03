# Milestone 6B Task Status

## Current summary

- Tasks 1–6: complete
- Tasks 7–9: pending
- Tasks 10–12: complete
- Task 13: pending

All remaining work follows `docs/superpowers/plans/2026-08-02-milestone-6b-checkpoint-policy.md`, but execution continues across completed task boundaries unless runtime evidence or an external dependency is genuinely required.

Each task remains divided into small, independently recoverable checkpoints. Each checkpoint must end with a commit, status update, normalized evidence summary, or documented negative result before another checkpoint begins.

## Task 1 — common discovery schema and requirements

**Status:** complete.

Task 1 added the common discovery schema, confirmed-absence rules, arena-only deferral policy, fail-closed readiness evaluator, and complete requirement manifest.

Verification at commit `ec7ed6f78931f6e06d694a40bd6ad735147de03e` completed with 240 passed, 11 expected environment-gated skips, and 0 failures. Compilation, Ruff, strict mypy, and whitespace checks passed.

## Task 2 — ownership and participant identity

**Status:** complete.

Confirmed Gate ownership, defender/challenger ordering, combatant identity, human/AI identity, winner/loser mapping, effect targeting, lifecycle behavior, and exact-binary guards.

Primary normalized evidence:

- `analysis/gates/ownership-and-participants.json`
- `analysis/gates/effect-targeting-rules.json`
- `analysis/gates/gate-owner-lifecycle.json`
- `analysis/gates/combatant-record-mapping.json`
- `analysis/gates/challenger-ordering.json`
- `analysis/gates/human-ai-identity.json`
- `src/bakugan_ds/gates/participants.py`

Final CI completed with 254 passed, 12 expected environment-gated skips, and 0 failures. Compilation, Ruff, strict mypy, whitespace checks, and exact participant/result-region verification passed.

## Task 3 — match score and capture state

**Status:** complete.

Confirmed:

- participant `+0xEE` is the authoritative captured-Gate match score;
- participant `+0xF4` counts populated six-byte capture-history records at `participant +0x84 + index * 6`;
- solo victory is score `>= 3`;
- team victory is participant score plus teammate score `>= 3`;
- participant construction is the authoritative reset boundary.

Primary normalized evidence:

- `src/bakugan_ds/gates/match_state.py`
- `analysis/gates/match-score-and-capture.json`
- `analysis/gates/match-score-victory-threshold.json`
- `analysis/gates/match-score-lifecycle.json`

Final CI completed with 265 passed, 13 expected environment-gated skips, and 0 failures. Compilation, Ruff, strict mypy, whitespace checks, and exact decoded-overlay verification passed.

## Task 4 — Gate reuse, capture, removal, and reset

**Status:** complete.

Confirmed:

- Gate-slot state `0` is selectable/unassigned;
- state `1` is assigned to an active arena placement;
- state `2` is unavailable to ordinary placement and may also be script-seeded;
- physical removal, capture bookkeeping, descriptor cleanup, and object destruction are separate events;
- the original game contains no per-Gate activation counter;
- future match-local activation counters are reserved at cache offsets `+0x2C..+0x37` without reusing original state.

Primary normalized evidence:

- `src/bakugan_ds/gates/gate_state.py`
- `analysis/gates/gate-reuse-and-removal.json`
- `analysis/gates/gate-state-lifecycle.json`
- `analysis/gates/gate-activation-counter-audit.json`

Final CI completed with 276 passed, 14 expected environment-gated skips, and 0 failures. Compilation, Ruff, strict mypy, whitespace checks, exact-region hashes, and direct-call inventories passed.

## Task 5 — weighted RNG and battle-type history

**Status:** complete.

Confirmed:

- the original Gate battle-type selector uses fixed metadata and no history;
- ARM9 `0x02021A30` is a reusable unsigned-byte weighted-index selector;
- explicit constructor and scripted overrides retain precedence;
- future history uses cache bytes `+0x38..+0x3B` and does not overlap activation counters.

Primary normalized evidence:

- `src/bakugan_ds/gates/history.py`
- `src/bakugan_ds/gates/selector.py`
- `analysis/gates/battle-history-and-rng.json`

GitHub Python CI run `30833671048` passed at commit `e3b3c1dfb1f617c5cf72aa3e85d2ed1fd7eaebd7`. Compilation, Ruff, strict mypy, the full suite, whitespace checks, and local exact-binary guards passed.

## Task 6 — Ability Card state and timing

**Status:** complete.

Confirmed lifecycle:

```text
available slot state 0
→ selected slot or 0xFF
→ exact accepted slot changes to state 2
→ participant available count decreases
→ effect scene activates
→ effect reaches terminal state 20
→ consumed slot remains unavailable until participant reset
```

Two natural Ability uses were captured in one clean executable ARM9 debugger session:

- participant `0x022E2640`, combatant `0`, slot `2`, Ability `169`, states `0/0/0 -> 0/0/2`, count `3 -> 2`;
- participant `0x022E24E0`, combatant `1`, slot `0`, Ability `126`, states `0/0/0 -> 2/0/0`, count `3 -> 2`.

Both reached:

- activation `0x0221A6B4`;
- exact-slot consumption `0x0221A728` and shared setter `0x0226A448`;
- terminal resolution `0x0221B8D0`;
- responsive continued execution.

A clean scripted no-card control confirmed selector `0x0226A700` returns `0xFF` when all slots are unavailable.

Primary normalized implementation and evidence:

- `src/bakugan_ds/gates/ability.py`
- `analysis/gates/ability-card-state.json`
- `analysis/symbols/gate_system2_context.csv`
- `tests/unit/test_gate_ability.py`
- `tests/test_gate_ability_artifact.py`
- `tests/integration/test_gate_ability_reference.py`

GitHub Python CI run `30855721786` passed at commit `538668931f7d09974d37b404f8d5ae8b9288ac3a` with:

```text
335 passed
20 expected environment-gated skips
0 failed
```

Compilation, changed-file Ruff, strict mypy, and whitespace checks passed. A fresh local exact-overlay verification against SHA-256 `82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1` also confirmed all seven instruction-region hashes, all seven calls to `0x0226A448`, and all three calls to `0x0226A700`.

No ROM, save, save state, screenshot, raw debugger log, or RAM dump was committed.

## Tasks 7–9

**Status:** pending.

- Task 7: landing and shot context
- Task 8: difficulty context
- Task 9: effect timing boundaries

## Task 10 — System 2.0 record format

**Status:** complete.

The version-1 `G2DT` format is implemented with a 32-byte header, 40-byte records, 103 ordered Gate records, CRC validation, strict parsing, deterministic serialization, and no arena-dependent version-1 effects.

Primary files:

- `src/bakugan_ds/gates/record.py`
- `analysis/gates/system2-record-v1.json`
- `docs/gate-card-system-2-data-format.md`

## Task 11 — raw trailer loader and cache lifecycle

**Status:** complete.

Confirmed NitroFS open/seek/read/close behavior, exact carrier access, fail-closed trailer handling, overlay expansion, cache initialization for selected Gate ID 21, and complete 64-byte invalidation at battle completion.

Primary files:

- `src/bakugan_ds/gates/loader.py`
- `analysis/gates/loader-and-cache.json`
- `tests/integration/test_gate_loader_reference.py`
- `tests/integration/test_gate_loader_runtime_reference.py`

PR #30 merged at `db164a6ebb819f6ce9f4bcfcc8ef3531805a48dc` after exact-head CI completed with 323 passed, 18 expected environment-gated skips, and 0 failures.

## Task 12 — discovery CLI and readiness report

**Status:** complete.

The Gate CLI validates discovery artifacts and `G2DT` trailers, generates deterministic fail-closed readiness reports, rejects duplicate domains and non-arena uncertainty, and preserves atomic output behavior.

Primary files:

- `src/bakugan_ds/gates/cli.py`
- `src/bakugan_ds/gates/readiness.py`
- `tests/unit/test_gate_discovery_cli.py`

## Task 13 — final documentation and Milestone 6C handoff

**Status:** pending.

Task 13 begins only after Tasks 7–9 are complete and the generated readiness report contains no failures with `arena_id` as the sole allowed deferred field.
