# Milestone 6B Task Status

## Current summary

- Tasks 1–7: complete
- Task 8: complete
- Task 9: pending
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

## Task 7 — landing and shot context

**Status:** complete.

Confirmed runtime state:

- throw-controller `+0x1D2` is the authoritative unsigned landing-result code;
- selected Bakugan slot is `+0x1D3`;
- active participant is `+0x1D4`;
- teammate participant is `+0x1D5`;
- main shot-controller `+0x6198` is copied to throw-controller `+0x1DF` as the authoritative shot-condition category;
- `+0x1E8` is the one-based attachment-descriptor index and is not a landing result or arena ID;
- dispatcher `0x02255640` provides the final common read-only evaluation boundary after the primary and optional alternate evaluators complete.

Two distinct natural standing outcomes were captured:

```text
result 3
active participant 0
selected slot 1
shot condition 0
→ contested Gate battle
```

```text
result 2
active participant 1
selected slot 1
shot condition 0
→ unopposed Stand without battle
```

An earlier natural control confirmed result `1` immediately before the `GATE CARD WON!` presentation. Codes `0` and `4` remain numeric rather than receiving unsupported universal labels.

Human and AI shot-condition sources converge on the same category:

- human participant shot-setup byte `+0x10` at `0x02260A64`;
- AI-controller byte `+0x7E` at `0x02260B04`;
- shared shot-controller storage `+0x6198` through constructor `0x0226A988`;
- ordinary copy to throw `+0x1DF` at `0x0226B5C4`;
- alternate or scripted copy at `0x0226D488`.

A clean battery-save tutorial launch used the same ordinary shot-condition copy and primary/alternate evaluator pipeline. The guided throw retained result `0`, produced no arena attachment, displayed the retry path, and reset the throw fields for another attempt. This confirms scripted behavior without falsely naming result code `0`.

Arena ID remains the sole approved deferred field. Transient projected grid bytes and the attachment index are not promoted to arena identity.

Primary normalized implementation and evidence:

- `src/bakugan_ds/gates/landing.py`
- `analysis/gates/landing-and-shot-context.json`
- `analysis/gates/landing-shot-candidates.json`
- `analysis/symbols/gate_system2_context.csv`
- `tests/unit/test_gate_landing.py`
- `tests/test_gate_landing_artifact.py`
- `tests/integration/test_gate_landing_reference.py`

GitHub Python CI run `30859631532` passed at commit `d677edad0f8d16f3b8ca7f32a1eda401af6d8006` with:

```text
347 passed
23 expected environment-gated skips
0 failed
```

Compilation, changed-file Ruff, strict mypy, and whitespace checks passed. A fresh local exact-overlay verification against SHA-256 `82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1` confirmed all 12 committed instruction-region hashes and all 16 inventoried direct calls across the throw constructor, primary evaluator, alternate evaluator, and shared attachment helper.

No ROM, save, save state, screenshot, raw debugger log, or RAM dump was committed.

## Task 8 — difficulty context

**Status:** complete.

Confirmed:

- the authoritative unsigned difficulty byte is shared Battle Arena configuration `0x020D433C +0x96` (`0x020D43D2`);
- overlay 1 decodes selected-opponent descriptor byte `+0x0E` bits 5–6 and stores the result through menu state `+0x25C`;
- overlay 7 reads the same shared byte directly at `0x02232664`;
- the AI consumer accepts the numeric domain `0`, `1`, and `2`, then writes a separate derived three-halfword parameter tuple;
- Easy value `0` was observed from a natural menu selection;
- Normal value `1` was observed through a reversible write to the confirmed authoritative field and changed the derived AI output;
- the available profile kept Hard locked, so value `2` remains executable-accepted but is not promoted as a runtime-confirmed semantic label;
- `0x020D4968` is a progression/unlock-bit accumulator and is rejected as either the difficulty field or the direct Normal/Hard unlock source.

Primary normalized implementation and evidence:

- `src/bakugan_ds/gates/difficulty.py`
- `analysis/gates/difficulty-context.json`
- `analysis/symbols/gate_system2_context.csv`
- `tests/unit/test_gate_difficulty.py`
- `tests/test_gate_difficulty_artifact.py`
- `tests/integration/test_gate_difficulty_reference.py`

Local final verification completed with:

```text
360 passed
27 expected environment-gated skips
0 failed
```

Compilation, changed-file Ruff, strict mypy, whitespace checks, 13 focused model/artifact tests, and four exact-overlay integration checks passed. No ROM, save, save state, screenshot, raw debugger log, or RAM dump was committed.

## Task 9 — effect timing boundaries

**Status:** pending.

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

Task 13 begins only after Tasks 8–9 are complete and the generated readiness report contains no failures with `arena_id` as the sole allowed deferred field.
