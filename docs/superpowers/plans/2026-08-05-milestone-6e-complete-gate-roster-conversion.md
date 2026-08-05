# Milestone 6E Complete Gate Roster Conversion Implementation Plan

## Goal

Convert Gate IDs `1..103` from one live System 2.0 record plus 102 legacy passthroughs into a complete deterministic seven-archetype roster using only the semantics already merged in Milestone 6D.

## Governing specification

`docs/superpowers/specs/2026-08-05-milestone-6e-complete-gate-roster-conversion-design.md`

## Baseline

- Merged Milestone 6D commit: `8541867e7443f47bd24ea006e6a7be3f0fa1d54d`
- Complete local/GitHub suite: `679 passed`, `41 expected environment-gated skips`
- Focused exact/runtime suite: `44 passed`
- Rebuilt ROM SHA-256: `519edbd5f4e17db3513cff0451109036ad411b44f1f2fd8f8e635fb68d0ffc7c`
- Emitted module SHA-256: `8fa90c244d3710479e94903e099f9dbbe71b5ce8d86c52603383d2e4f42e7a1c`
- Frozen live reference Gate: ID `19`, Juggernoid

## Execution rules

- Use test-driven changes.
- Keep commits bounded by task.
- Do not introduce new runtime semantics.
- Do not infer ROM IDs from guide ordering.
- Keep original binary data and generated artifacts untracked.
- Preserve exact fallback and transactional installation.
- Treat checkpoints as recovery markers, not stopping points.

## Task 1 — Freeze the Milestone 6D entry contract

**Files**

- Add `analysis/gates/milestone-6e-entry-contract.json`
- Add `tests/test_gate_milestone_6e_entry_contract.py`

**Tests first**

Require:

- merged Milestone 6D hashes and geometry;
- exactly 103 source records;
- Juggernoid's exact authored record;
- current semantic ID tables;
- current archetype budget bands;
- current protected hook/core-G ranges;
- no new condition, target, effect, timing, cache, or module geometry.

**Acceptance**

The task fails against any stale or expanded semantic baseline.

## Task 2 — Add strict roster metadata models

**Files**

- Add `src/bakugan_ds/gates/roster_metadata.py`
- Add `tests/unit/test_gate_roster_metadata.py`
- Add `config/gates/milestone-6e-roster-metadata.json`

**Tests first**

Validate:

- IDs `1..103`, exactly once;
- nonempty name or explicit provisional label;
- confidence enum;
- evidence reference;
- archetype identity;
- design tier;
- concise identity and differentiation rationale;
- budget and review fields;
- no copied binary payloads or raw original-table dumps.

**Acceptance**

The initial metadata file may contain provisional mappings, but every provisional mapping is explicit and machine-counted.

## Task 3 — Build the authoritative Gate ID/name inventory

**Files**

- Add `analysis/gates/milestone-6e-id-name-map.json`
- Add `tests/test_gate_milestone_6e_id_name_map.py`
- Update roster metadata

**Work**

- Reuse confirmed repository mappings.
- Correlate guide names without assuming order.
- Use shop, ownership, runtime, or text-resource evidence where available.
- Record confirmed, probable, candidate, and unresolved mappings.

**Acceptance**

No name is promoted beyond its evidence. Every ID remains uniquely represented even if some labels are provisional.

## Task 4 — Add whole-roster evaluation and duplicate analysis

**Files**

- Add `src/bakugan_ds/gates/roster_analysis.py`
- Add `tests/unit/test_gate_roster_analysis.py`
- Add CLI report support

**Tests first**

Implement the complete deterministic matrix over:

- core G `190, 400, 525, 650, 695`;
- six attributes;
- owner/non-owner targets;
- tied/ahead/behind/zero/match-point scores;
- missing/nonwinning/winning landing context.

Detect:

- exact runtime duplicates;
- identical evaluation outputs;
- conflicting names or IDs;
- potential dominance pairs;
- out-of-tier swings;
- archetype-distribution warnings.

**Acceptance**

Hard duplicate classes reject authoring. Dominance findings require explicit review disposition.

## Task 5 — Define reusable authored templates

**Files**

- Add `config/gates/milestone-6e-archetype-templates.json`
- Add `src/bakugan_ds/gates/roster_templates.py`
- Add `tests/unit/test_gate_roster_templates.py`

**Work**

Define multiple valid starting templates for each of the seven archetypes without creating a new runtime format.

Templates must vary by:

- flat/percentage mix;
- attribute profile;
- bounded weight pressure;
- condition;
- target;
- primary effect;
- explicit drawback where required.

**Acceptance**

Every template independently passes Milestone 6D validation and no two templates are exact runtime duplicates.

## Task 6 — Convert Power and Attribute Gates

**Files**

- Add/update `config/gates/milestone-6e-system2-v1.json`
- Update metadata and balance fixtures
- Add batch-focused tests

**Work**

- Assign reviewed Power and Attribute records.
- Preserve pronounced attribute identities without creating a universal elemental wheel.
- Keep non-Attribute positive affinity counts within existing limits.

**Acceptance**

Every converted record passes budget, weight, metadata, and evaluation tests. Juggernoid remains unchanged.

## Task 7 — Convert Skill and Control Gates

**Work**

- Author bounded battle-type identities for Skill Gates.
- Author deterministic target/score/landing identities for Control Gates.
- Ensure all six battle types remain reachable.
- Ensure missing landing context retains complete legacy fallback.

**Acceptance**

No Skill Gate is merely a Power Gate with one weight changed. No Control Gate relies on unsupported state.

## Task 8 — Convert Comeback Gates

**Work**

Use only owner-behind, owner-score-zero, score-tied, and match-point conditions already supported.

**Acceptance**

- Conditional rewards remain bounded.
- Nontriggered branches remain strategically usable where intended.
- Juggernoid remains the frozen compatibility fixture.

## Task 9 — Convert Risk and Chaos Gates

**Work**

- Require explicit, meaningful drawbacks.
- Pair unusual weight profiles with real costs.
- Keep maximum probabilities and ratios inside existing bounds.

**Acceptance**

No Risk or Chaos record receives above-normal gross value without drawback credit. High-risk conditional outcomes remain within documented design targets.

## Task 10 — Complete the 103-record authoring roster

**Files**

- Finalize `config/gates/milestone-6e-system2-v1.json`
- Finalize metadata
- Add `analysis/gates/milestone-6e-roster-contract.json`
- Add `analysis/gates/milestone-6e-balance-contract.json`

**Tests first**

Require:

- 103 unique nonlegacy records;
- 103 metadata entries;
- no unsupported or deferred fields;
- all seven archetypes represented and reviewed;
- no hard duplicate findings;
- every potential dominance finding dispositioned;
- Juggernoid exact compatibility.

**Acceptance**

The committed roster validates and reports deterministically from two independent runs.

## Task 11 — Prove host and emitted-ARM parity for all records

**Files**

- Extend emitted-module interpreter fixtures
- Add `tests/unit/test_gate_milestone_6e_runtime_parity.py`

**Work**

Execute every record over the complete evaluation matrix in both the host model and exact emitted ARM interpreter.

**Acceptance**

- Exact result and validity parity for every case.
- Exact selector parity for every weight vector and controlled RNG fixture.
- Invalid contexts preserve complete legacy fallback.
- No writes outside the current combatant record, cache, and stack boundary.

## Task 12 — Add transactional Milestone 6E installation and exact-build contracts

**Files**

- Extend installer and CLI for Milestone 6E
- Add `analysis/gates/milestone-6e-runtime-contract.json`
- Add exact-build integration tests

**Work**

Install the complete roster from:

- pristine extracted workspace;
- verified Milestone 6D workspace.

**Acceptance**

- Two independent exact rebuilds are byte-identical.
- Module remains `0x8000` bytes.
- Cache remains 64 bytes.
- Arena still begins at `0x02293C60`.
- Protected core-G and hook ranges remain exact.
- Failed installation leaves the workspace byte-identical.

## Task 13 — Perform bounded live representative acceptance

**Files**

- Add `analysis/runtime-observations/gate-system2-milestone-6e-validation.json`
- Add runtime-evidence tests

**Sample matrix**

Exercise:

- Juggernoid;
- at least one representative of each archetype;
- one landing-conditioned Gate;
- one owner/non-owner Control Gate;
- one owner-at-match-point or opponent-at-match-point Gate;
- one high-risk drawback Gate;
- tutorial completion and a standard Battle Arena exit.

**Acceptance**

- Expected records load.
- Sampled calculations and selectors match the host/emitted model.
- Battles exit to responsive game states.
- Cache clears completely after completion.
- No claim of exhaustive natural testing is made.

## Task 14 — Final documentation, CI, review, and merge

**Files**

- Add `docs/gate-card-system-2-complete-roster.md`
- Add `docs/superpowers/plans/2026-08-05-milestone-6e-verification.md`
- Update README and roadmap
- Add `analysis/gates/milestone-6e-task-status.json`

**Verification**

Run:

```bash
PYTHONPATH=src python -m pytest -q
python -m compileall -q src tests tools
git diff --check
```

Run Ruff and strict mypy in the configured GitHub CI environment. Run the exact-ROM suite with the user-owned reference inputs.

**Final review**

Confirm:

- no ROMs, saves, screenshots, extracted binaries, generated modules, or raw reports are tracked;
- no temporary workflow or synchronization payload remains;
- no new runtime semantics entered the diff;
- all 103 records are live and reviewed;
- Milestone 6F remains a separate design gate.

Mark the PR ready and merge only after exact-head CI and final diff review pass.
