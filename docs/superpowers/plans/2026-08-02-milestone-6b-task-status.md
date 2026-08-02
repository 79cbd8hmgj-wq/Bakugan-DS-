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

Current checkpoint: **2E — effect targeting rules**.

Task 2 checkpoints:

1. 2A — static candidate inventory: complete
2. 2B — canonical Gate owner: complete
   - 2B.1 — player-owned Gate capture: complete
   - 2B.2 — reverse-owner control: complete
   - 2B.3 — trace canonical Gate-owner source: complete
   - 2B.4 — owner lifetime, reset, and alternate-path validation: complete
3. 2C — challenger and combatant mapping: complete
   - 2C.1 — descriptor-to-combatant mapping: complete
   - 2C.2 — challenger ordering policy: complete
4. 2D — human and AI identity: complete
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

### Checkpoint 2C.2 result

The challenger-ordering policy is stored in `analysis/gates/challenger-ordering.json` at commit `2a27761ac38275323ea0fde96813569a1dc807cf`.

Confirmed behavior:

- collision event `+0x16` stores the active or thrown Bakugan descriptor index;
- collision event `+0x29` stores the selected standing target descriptor index, with `0xFF` meaning no target;
- all seven direct overlay-7 callers of pair setter `0x02262A64` pass the active descriptor as `r2`, which is stored to session `+0x28E`;
- when a distinct target exists, callers pass that target as `r1`, which is stored to session `+0x28D`;
- session `+0x28D` therefore constructs combatant record 0 as the stationary target or defender;
- session `+0x28E` constructs combatant record 1 as the active or thrown challenger;
- the canonical challenging participant is the low nibble of descriptor byte `+0x0F` for the descriptor selected by `+0x28E`;
- this ordering is independent of Gate ownership and human/AI identity;
- two fallback call sites pass the same active descriptor for both arguments, so equal descriptor indices represent no distinct challenger/defender pair and must not be treated as a normal challenge;
- the existing AI-owned runtime control agrees with the static call-site audit: participant 0 contested participant 1's Gate and appeared in combatant record 1.

A fresh live collision-call capture was attempted but the GDB stream reset before producing a valid snapshot. That failed attempt was not used as evidence. Confidence comes from the exhaustive direct-call audit and the previously committed runtime controls.

Gate owner, combatant identity, and challenging participant are now confirmed for Task 2.

### Checkpoint 2D result

Human and AI control identity is stored in `analysis/gates/human-ai-identity.json` at commit `4b10ae990a6dc8bba85ff9064c3d112426db1b1d`.

Confirmed behavior:

- participant object `+0xC8` is the authoritative AI-controller pointer;
- a null pointer identifies a human-controlled participant;
- a non-null pointer identifies an AI-controlled participant;
- participant construction clears `+0xC8`, uses a one-participant human prefix in ordinary local modes, and allocates AI controllers for later participants;
- modes 6 and 7 replace the fixed prefix with the active multiplayer-slot count returned by ARM9 helper `0x0202F134`;
- AI-specific battle setup and shot planning explicitly branch on the presence of `+0xC8`;
- AI state reset preserves the identity pointer;
- the pointer remains stable until the participant and its controller are destroyed;
- the clean tutorial/story runtime control independently maps participant 0 to P1/player and participant 1 to the P2/AI opponent, matching the constructor policy;
- participant `+0xF2` remains a team/slot remap and is not used as the human/AI flag.

The System 2.0 context contract is:

```text
is_ai = read_u32(participant + 0xC8) != 0
```

The pointer may be tested only while the participant object is live and must never be persisted in Gate data or exposed as a stable controller-object ABI.

Gate owner, challenger/defender mapping, combatant participant identity, and human/AI identity are now confirmed. Checkpoint 2E will derive the exact participant sets for owner, challenger, defender, self, opponent, both combatants, human, and AI effect targets.
