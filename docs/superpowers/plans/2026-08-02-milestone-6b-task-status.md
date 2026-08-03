# Milestone 6B Task Status

- Task 1: complete
- Task 2: complete
- Task 3: complete
- Task 4: complete
- Task 5: complete
- Tasks 6–13: pending

All remaining work follows `docs/superpowers/plans/2026-08-02-milestone-6b-checkpoint-policy.md`, but execution continues across completed task boundaries unless runtime evidence or an external dependency is genuinely required.

Each task remains divided into small, independently recoverable checkpoints. Each checkpoint must end with a commit, status update, normalized evidence summary, or documented negative result before another checkpoint begins.

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

**Status:** complete.

Task 4 checkpoints:

1. 4A — static Gate-state and mutation-path inventory: complete
2. 4B — runtime normal capture and arena-removal transition: complete
3. 4C — reuse, alternate/scripted paths, lifetime, and reset: complete
4. 4D — activation-counter presence or confirmed absence and replacement storage: complete
5. 4E — normalized model, validators, lifecycle documentation, exact-binary tests, CI, and task completion: complete

### Confirmed model

- Participant Gate-slot state `0` is selectable or unassigned in the ordinary placement path.
- Gate-slot state `1` is assigned to an active arena placement.
- Gate-slot state `2` is unavailable to ordinary placement selection, but is not a universal captured or removed Boolean because scripted setup may assign it before battle.
- Participant `+0xF8` is an ordinary available-slot cache maintained when Gate-slot state crosses the zero/nonzero boundary; scripted setup may override it directly.
- Physical Gate removal is the arena-entry occupied transition `1 -> 0`, the matching board-grid clear, and the decrement of session `+0x294`.
- Capture is a composite result event: winner score `+0xEE`, capture-history ledger and count `+0xF4`, then physical arena removal and owner-slot unavailability.
- Combatant descriptor cleanup is separate from arena removal and uses session `+0x295` plus arena-entry descriptor linkage.
- Active-placement transfer restores the old owner slot to `0`, changes owner and Gate-slot identity, assigns the replacement slot state `1`, and leaves the arena entry occupied.
- Participant and session construction are the authoritative reset boundaries; destruction invalidates object addresses without clearing every field in place.
- The exact original Gate lifecycle contains no per-Gate activation counter.
- Future System 2.0 activation state is `activation_count_by_arena_entry[12]`, reserved at offsets `0x2C..0x37` of the approved future 64-byte overlay-7 match-local BSS cache `0x02293C20..0x02293C60`. It is not implemented during Milestone 6B.

### Normalized implementation and evidence

- `src/bakugan_ds/gates/gate_state.py`
- `analysis/gates/gate-reuse-and-removal.json`
- `analysis/gates/gate-state-candidates.json`
- `analysis/gates/gate-removal-runtime.json`
- `analysis/gates/gate-state-lifecycle.json`
- `analysis/gates/gate-activation-counter-audit.json`
- `analysis/symbols/gate_system2_context.csv`
- `docs/gate-card-runtime-lifecycle.md`
- `tests/unit/test_gate_state.py`
- `tests/test_gate_state_artifact.py`
- `tests/integration/test_gate_state_reference.py`

### Final verification

GitHub Python CI run `30769106006` completed successfully at branch commit `64a9d1f13736bb2438926fb48dc2c6a155acfcf8`:

```text
276 passed
14 expected environment-gated skips
0 failed
```

Python compilation, changed-file Ruff, strict mypy, and changed-file whitespace checks passed. The exact decoded-overlay and runtime-ARM9 Gate-lifecycle integration guard also passed locally, including all nine committed instruction-region hashes, all seven lifecycle direct-call inventories, and all 18 direct overlay-7 calls to the Gate-bonus accessor.

## Task 5

**Status:** complete.

### Confirmed model

- The original Gate battle-type selector remains fixed metadata and has no RNG or previous-type input.
- ARM9 function `0x02021A30` is a reusable unsigned-byte weighted-index selector. It accepts `r0 = count` and `r1 = weight pointer`, returns `-1` for a zero total, and otherwise returns the half-open cumulative bucket index.
- Its 64-bit LCG state is stored at `0x020D42E8`. The production seed wrapper at `0x020219DC` uses the system timer; direct initializer `0x020219EC` supports deterministic isolated controls.
- An explicit constructor type `0..5` bypasses the normal fallback; constructor type `-1` permits it.
- Scripted override codes `1..6` supersede the provisional type.
- The exact original Gate selector maintains no battle-type history.
- Future history uses cache bytes `+0x38..+0x3B` for previous type, second previous type, consecutive count, and valid count. It updates once with the final selected type immediately before dispatch and does not overlap activation counters at `+0x2C..+0x37`.

### Normalized implementation and evidence

- `src/bakugan_ds/gates/history.py`
- `src/bakugan_ds/gates/selector.py`
- `analysis/gates/battle-history-and-rng.json`
- `tests/unit/test_gate_history.py`
- `tests/unit/test_gate_selector_precedence.py`
- `tests/test_gate_history_artifact.py`
- `tests/integration/test_gate_rng_reference.py`

### Final verification

GitHub Python CI run `30833671048` completed successfully at branch commit `e3b3c1dfb1f617c5cf72aa3e85d2ed1fd7eaebd7`.

Python compilation, changed-file Ruff, strict mypy, the full test suite, and changed-file whitespace checks passed. Exact-binary tests are environment-gated in CI and were also validated locally against runtime ARM9 SHA-256 `7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e` and overlay-7 SHA-256 `82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1`.

Task 6 is the next pending runtime-context task. Static-only Tasks 10 and 11 may proceed independently while Tasks 6–9 await or collect live evidence.
