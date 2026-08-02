# Milestone 6B Checkpoint Policy

This policy applies to Tasks 2–13 of the Milestone 6B complete-discovery plan.

## Purpose

Long debugger, repository, and analysis sequences have caused conversation freezes. Remaining work must therefore be executed as small, independently recoverable checkpoints rather than as uninterrupted task-sized runs.

## Required checkpoint behavior

For every task:

1. Work on only one task at a time.
2. Divide that task into checkpoints that each answer one narrow question or produce one narrow artifact.
3. Do not begin the next checkpoint until the current checkpoint has one of these durable outcomes:
   - a repository commit;
   - an updated task-status record;
   - a normalized local evidence summary with exact addresses, hashes, observations, and confidence;
   - a documented negative result describing what was tested and why it was insufficient.
4. After each checkpoint, report:
   - what was attempted;
   - what was confirmed, rejected, or left unresolved;
   - the commit SHA or evidence location;
   - the next single checkpoint.
5. Avoid large debugger dumps, full disassemblies, and long unbounded tool sequences in chat.
6. Store raw local debugger output outside the repository and reduce it to bounded evidence before continuing.
7. Never promote a field from candidate or probable to confirmed merely to complete a checkpoint.
8. If the chat freezes, resume from the latest durable checkpoint without repeating completed work.
9. Complete and verify the entire task before starting another task.
10. Stop for user review after each completed task.

## Default checkpoint size

A checkpoint should normally contain no more than:

- one runtime breakpoint or watchpoint objective;
- one structure-field interpretation;
- one executable function or call-path trace;
- one evidence artifact or validator;
- one focused test group;
- one CI correction cycle.

When a checkpoint begins expanding beyond one of those boundaries, split it before continuing.

## Task 2 checkpoint breakdown

Task 2 is divided into:

1. **2A — Static candidate inventory**
   - identify candidate participant-index fields, selected-combatant records, constructors, and result handlers;
   - record addresses and hashes without assigning final semantics.

2. **2B — Canonical Gate owner**
   - capture the authoritative owner value from placement through activation;
   - prove initialization, lifetime, mutation, and reset.

3. **2C — Challenger and combatant mapping**
   - map owner/challenger to combatant 0 and combatant 1;
   - verify both directions in a controlled scenario.

4. **2D — Human and AI identity**
   - confirm the authoritative human/AI representation;
   - verify normal and scripted/tutorial handling.

5. **2E — Effect targeting rules**
   - prove how owner, challenger, self, opponent, winner, loser, and both resolve to combatant records.

6. **2F — Task 2 artifact and tests**
   - commit normalized evidence, symbols, validators, unit tests, and exact-ROM integration checks;
   - run full CI;
   - update Task 2 status and stop for review.

Each Task 2 checkpoint must be completed and reported separately.

## Later task checkpoint guidance

- Task 3: separate score counters, captured-Gate counters, victory threshold, update timing, and reset.
- Task 4: separate activation count, reuse, capture bookkeeping, removal, and reset.
- Task 5: separate RNG identification, RNG behavior, weighted-selection math, history storage, and override precedence.
- Task 6: separate Ability availability, selection, activation, resolution, consumed state, and reset.
- Task 7: separate landing result, shot condition, participant association, evaluation timing, and arena deferral.
- Task 8: separate setting storage, value domain, battle load, AI consumers, and profile/reset behavior.
- Task 9: handle one effect-timing phase or tightly related phase pair per checkpoint.
- Task 10: separate header layout, record layout, serializer, parser, CRC, schema, and documentation.
- Task 11: separate NitroFS operations, trailer validation, overlay growth, cache initialization, cache invalidation, and fallback.
- Task 12: separate artifact validation, trailer validation, readiness evaluation, CLI wiring, and generated report.
- Task 13: separate documentation, each runtime scenario group, deterministic rebuild proof, final CI, and readiness handoff.

## Completion boundary

This checkpoint policy changes execution granularity only. It does not weaken the approved Milestone 6B evidence requirements, arena-only exception, testing requirements, or prohibition on live System 2.0 gameplay changes.
