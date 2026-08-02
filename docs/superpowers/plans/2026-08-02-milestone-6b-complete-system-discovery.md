# Milestone 6B Complete Gate System Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Confirm every runtime dependency required by Gate Card System 2.0 except arena ID, prove loader/cache infrastructure without changing gameplay, and produce a fail-closed readiness report for Milestone 6C.

**Architecture:** Extend the dependency-free `bakugan_ds.gates` analysis package with focused domain modules for participants, match state, Gate state, battle history/RNG, Ability Cards, landing context, difficulty, effect timing, data format, loader/cache validation, and final readiness evaluation. Each module consumes copyright-safe normalized evidence, validates exact field semantics and lifetimes, and emits deterministic JSON. Runtime instrumentation may observe or validate infrastructure but must preserve original Gate bonuses, fixed battle types, results, AI behavior, and roster values.

**Tech Stack:** Python 3.11 standard library, frozen dataclasses and `StrEnum`, `argparse`, JSON/CSV, `struct`, `zlib.crc32`, pytest 8.3, Ruff, strict mypy, the existing workspace/rebuild/patch APIs, BLZ/LZ10 utilities, and the existing DeSmuME ARM9 GDB workflow.

## Global Constraints

- Support only profile `b6re_rev0`; fail closed for every other profile.
- Arena ID is the only allowed unresolved field at Milestone 6B completion.
- Every mandatory field must be `confirmed`; `candidate` and `probable` block readiness.
- A mandatory field requires semantics, owner structure, width, signedness, initialization, mutation, lifetime, reset, player/AI behavior, scripted behavior, and executable or runtime evidence.
- A field confirmed absent must use `presence: "absent"`, `confidence: "confirmed"`, and document the safe replacement-state plan.
- Preserve the merged core-G curve and protected overlay-7 offsets `0x23C18–0x23C1C`, `0x23CB0–0x23CF8`, and `0x23D78–0x23D7C`.
- Future percentage scaling uses compressed battle core G before mutable modifiers, never persistent roster G.
- Do not change Gate bonuses, battle-type selection, Ability behavior, AI decisions, match results, or roster values.
- Loader-only instrumentation may validate synthetic data but must fall back to legacy behavior and produce unchanged gameplay results.
- Add no runtime Python dependency. Use standard-library serialization, checksums, and validation.
- Never assign ROM IDs from external guide order.
- Commit no ROM, rebuilt ROM, executable, complete original table, complete game-text catalog, RAM dump, save, save state, screenshot, or raw debugger log.
- Keep raw captures and complete local reports below ignored `work/reports/gates/`.
- All committed JSON uses two-space indentation, sorted keys, a final newline, and atomic replacement.
- Exact-ROM tests skip unless user-owned local inputs are supplied.
- Clean executable launches are required for final runtime observations; executable save states are not final evidence.
- Failed analysis, instrumentation, serialization, or patch preparation must leave the workspace unchanged.
- Milestone 6B ends with no live System 2.0 gameplay effect.

## File Map

Create focused modules under `src/bakugan_ds/gates/`:

```text
discovery.py
readiness.py
participants.py
match_state.py
gate_state.py
history.py
ability.py
landing.py
difficulty.py
timing.py
record.py
loader.py
```

Extend:

```text
src/bakugan_ds/gates/cli.py
src/bakugan_ds/gates/context.py
src/bakugan_ds/gates/selector.py
src/bakugan_ds/gates/storage.py
```

Commit normalized artifacts:

```text
analysis/gates/milestone-6b-requirements.json
analysis/gates/ownership-and-participants.json
analysis/gates/match-score-and-capture.json
analysis/gates/gate-reuse-and-removal.json
analysis/gates/battle-history-and-rng.json
analysis/gates/ability-card-state.json
analysis/gates/landing-and-shot-context.json
analysis/gates/difficulty-context.json
analysis/gates/effect-timing.json
analysis/gates/loader-and-cache.json
analysis/gates/system2-record-v1.json
analysis/gates/milestone-6c-readiness.json
analysis/symbols/gate_system2_context.csv
```

Commit documentation:

```text
docs/gate-card-system-2-runtime-context.md
docs/gate-card-system-2-data-format.md
docs/superpowers/plans/2026-08-02-milestone-6b-verification.md
```

---

### Task 1: Common Discovery Schema and Requirement Manifest

**Files:**
- Create: `src/bakugan_ds/gates/discovery.py`
- Create: `src/bakugan_ds/gates/readiness.py`
- Create: `analysis/gates/milestone-6b-requirements.json`
- Test: `tests/unit/test_gate_discovery.py`
- Test: `tests/unit/test_gate_readiness.py`

**Interfaces:**
- `Presence(StrEnum)`: `present`, `absent`, `deferred`
- `RuntimeFieldEvidence(name, presence, width_bits, signed, owner_structure, access, initialization, mutations, lifetime, reset, player_ai_behavior, scripted_behavior, confidence, evidence)`
- `BehaviorCheck(name, confidence, evidence)`
- `DiscoveryArtifact(domain, fields, checks, unresolved)`
- `Requirement(name, artifact, field, allow_absent, allow_deferred)`
- `ReadinessFailure(requirement, reason)`
- `ReadinessResult(ready, confirmed, deferred, failures)`
- `load_discovery_artifact(path) -> DiscoveryArtifact`
- `load_requirements(path) -> tuple[Requirement, ...]`
- `evaluate_readiness(requirements, artifacts) -> ReadinessResult`

- [ ] **Step 1: Write failing field-completeness tests.**

```python
def test_required_field_rejects_probable_evidence() -> None:
    field = RuntimeFieldEvidence(
        name="gate_owner",
        presence=Presence.PRESENT,
        width_bits=8,
        signed=False,
        owner_structure="battle object",
        access="+0x20",
        initialization="constructor",
        mutations=("capture",),
        lifetime="match",
        reset="match reset",
        player_ai_behavior="shared",
        scripted_behavior="tutorial override documented",
        confidence=Confidence.PROBABLE,
        evidence="static candidate",
    )
    with pytest.raises(WorkspaceError, match="must be confirmed"):
        field.validate(required=True)
```

- [ ] **Step 2: Write the arena-only deferral test.**

```python
def test_readiness_allows_only_arena_id_to_be_deferred() -> None:
    requirements = (
        Requirement("gate_owner", "ownership", "gate_owner", False, False),
        Requirement("arena_id", "landing", "arena_id", False, True),
    )
    result = evaluate_readiness(requirements, synthetic_artifacts(arena_deferred=True))
    assert result.ready is True
    assert result.deferred == ("arena_id",)
```

- [ ] **Step 3: Run `python -m pytest tests/unit/test_gate_discovery.py tests/unit/test_gate_readiness.py -v`; confirm imports fail.**
- [ ] **Step 4: Implement strict immutable models and deterministic loaders.** Reject missing lifecycle fields, unsupported widths, empty evidence, deferred non-arena fields, and confirmed-absent fields without replacement-state plans.
- [ ] **Step 5: Commit the exact requirement manifest.** It must list these mandatory keys: `gate_owner`, `challenging_participant`, `combatant_identity`, `human_ai_identity`, `effect_target`, `match_score`, `captured_gate_count`, `victory_threshold`, `gate_activation_count`, `gate_reuse_state`, `gate_capture_state`, `gate_removal_state`, `battle_type_history`, `weighted_rng`, `ability_available`, `ability_selected`, `ability_used`, `ability_resolved`, `landing_result`, `shot_condition`, `difficulty`, every effect timing phase, loader operations, cache lifecycle, and version-1 record geometry. It must list only `arena_id` with `allow_deferred: true`.
- [ ] **Step 6: Run focused tests, compileall, Ruff, and mypy.**
- [ ] **Step 7: Commit:** `git commit -m "feat: add Gate discovery readiness schema"`.

---

### Task 2: Gate Ownership and Participant Identity

**Files:**
- Create: `src/bakugan_ds/gates/participants.py`
- Create: `analysis/gates/ownership-and-participants.json`
- Create: `tests/unit/test_gate_participants.py`
- Create: `tests/integration/test_gate_participants_reference.py`
- Modify: `analysis/symbols/gate_system2_context.csv`

**Interfaces:**
- `ParticipantRole(StrEnum)`: `gate_owner`, `challenger`, `combatant_0`, `combatant_1`, `human`, `ai`, `effect_target`
- `ParticipantEvidence(role, identity_source, owner_structure, access, initialization, transfer, reset, confidence, evidence)`
- `TargetMode(StrEnum)`: `owner`, `challenger`, `self`, `opponent`, `winner`, `loser`, `both`
- `ParticipantModel(entries, target_modes, scripted_paths)`
- `normalize_participant_artifact(payload) -> ParticipantModel`

- [ ] **Step 1: Write failing tests for duplicate roles and ambiguous effect targeting.**

```python
def test_participant_model_requires_unambiguous_owner_and_challenger() -> None:
    model = ParticipantModel(entries=(confirmed_role("gate_owner"),), target_modes=(), scripted_paths=())
    with pytest.raises(WorkspaceError, match="challenger"):
        model.validate()
```

- [ ] **Step 2: Implement normalization and require confirmed entries for all roles.** Require exact participant-to-combatant mapping and explicit player/AI representation.
- [ ] **Step 3: Trace the canonical owner and challenger from Gate placement through battle construction, result, capture, and match reset.** Do not promote the Gate-card-get cut-in actor byte unless gameplay reads the same source.
- [ ] **Step 4: Capture clean normal, AI, and tutorial/scripted scenarios.** Record owner/challenger values, combatant record association, human/AI flag, effect recipient derivation, mutation points, and reset.
- [ ] **Step 5: Add exact-ROM integration assertions for each committed address/hash and selected normalized observation.**
- [ ] **Step 6: Commit only addresses, offsets, hashes, selected values, and confidence evidence.** Add symbols with `component,runtime_address,component_offset,name,confidence,evidence`.
- [ ] **Step 7: Run participant unit, artifact, and integration tests.**
- [ ] **Step 8: Commit:** `git commit -m "docs: confirm Gate ownership and participants"`.

---

### Task 3: Match Score, Captured Gates, and Victory State

**Files:**
- Create: `src/bakugan_ds/gates/match_state.py`
- Create: `analysis/gates/match-score-and-capture.json`
- Create: `tests/unit/test_gate_match_state.py`
- Create: `tests/integration/test_gate_match_state_reference.py`
- Modify: `analysis/symbols/gate_system2_context.csv`

**Interfaces:**
- `CounterOwner(StrEnum)`: `player`, `opponent`, `shared`
- `CounterEvidence(name, owner, width_bits, access, initial_value, update_function, reset_function, lifetime, confidence, evidence)`
- `MatchStateEvidence(score_counters, capture_counters, victory_threshold, result_timing, scripted_paths)`
- `normalize_match_state_artifact(payload) -> MatchStateEvidence`

- [ ] **Step 1: Write failing tests requiring two participant counters, a victory threshold, and update/reset functions.**

```python
def test_match_state_rejects_presentation_only_counter() -> None:
    counter = confirmed_counter("player_score")
    counter = replace(counter, update_function="", evidence="UI draw only")
    with pytest.raises(WorkspaceError, match="update function"):
        counter.validate()
```

- [ ] **Step 2: Implement strict counter and threshold validation.** Require authoritative gameplay update paths rather than display-only values.
- [ ] **Step 3: Trace battle result to score/capture mutation, Gate-card-get presentation, victory comparison, next-round setup, and match reset.**
- [ ] **Step 4: Observe a score-changing result and a no-change control.** Where a full match is practical, confirm the victory threshold and final reset. Record tutorial/story alternatives separately.
- [ ] **Step 5: Add integration tests matching committed instruction hashes and counter geometry.**
- [ ] **Step 6: Run focused and exact-ROM tests.**
- [ ] **Step 7: Commit:** `git commit -m "docs: confirm Gate match score and capture state"`.

---

### Task 4: Gate Activation Count, Reuse, Capture, Removal, and Reset

**Files:**
- Create: `src/bakugan_ds/gates/gate_state.py`
- Create: `analysis/gates/gate-reuse-and-removal.json`
- Create: `tests/unit/test_gate_state.py`
- Create: `tests/integration/test_gate_state_reference.py`
- Modify: `docs/gate-card-runtime-lifecycle.md`

**Interfaces:**
- `GateStateKind(StrEnum)`: `activation_count`, `reusable`, `captured`, `removed`, `reset`
- `GateStateEvidence(kind, presence, owner_structure, access, initialization, mutations, reset, confidence, evidence, replacement_plan)`
- `GateStateModel(states, transitions, safe_extension_storage)`
- `normalize_gate_state_artifact(payload) -> GateStateModel`

- [ ] **Step 1: Write a failing confirmed-absence test.**

```python
def test_absent_activation_counter_requires_replacement_plan() -> None:
    state = GateStateEvidence(
        kind=GateStateKind.ACTIVATION_COUNT,
        presence=Presence.ABSENT,
        owner_structure="none found",
        access="none",
        initialization="none",
        mutations=("none",),
        reset="none",
        confidence=Confidence.CONFIRMED,
        evidence="complete reference scan",
        replacement_plan="",
    )
    with pytest.raises(WorkspaceError, match="replacement plan"):
        state.validate()
```

- [ ] **Step 2: Implement state and transition validation.** Accept confirmed absence only with bounded executable-search evidence and a safe new match-local storage plan.
- [ ] **Step 3: Distinguish board removal, capture bookkeeping, scene cleanup, and object destruction.** Trace repeated round setup and attempt to observe the same Gate or Gate slot across transitions.
- [ ] **Step 4: Confirm an original activation counter or confirm its absence.** If absent, document exact new history/cache bytes and reset point without implementing them live.
- [ ] **Step 5: Update the lifecycle document with confirmed capture/removal/reuse semantics.** Remove prior probable labels only when evidence supports confirmation.
- [ ] **Step 6: Run state, lifecycle, artifact, and exact-ROM tests.**
- [ ] **Step 7: Commit:** `git commit -m "docs: confirm Gate reuse and removal lifecycle"`.

---

### Task 5: Weighted-Selection RNG and Battle-Type History

**Files:**
- Create: `src/bakugan_ds/gates/history.py`
- Modify: `src/bakugan_ds/gates/selector.py`
- Create: `analysis/gates/battle-history-and-rng.json`
- Create: `tests/unit/test_gate_history.py`
- Modify: `tests/unit/test_gate_selector.py`
- Create: `tests/integration/test_gate_rng_reference.py`

**Interfaces:**
- `RngEvidence(function, calling_convention, output_width_bits, output_range, seed_source, deterministic_controls, confidence, evidence)`
- `HistoryEvidence(storage, entry_width_bits, capacity, update_timing, reset_timing, player_ai_behavior, confidence, evidence)`
- `WeightedSelectionSpec(type_count=6, weight_width_bits=8, total_max=1530, fallback="legacy_fixed_metadata")`
- `weighted_index(weights: tuple[int, ...], roll: int) -> int`
- `validate_weight_vector(weights) -> None`

- [ ] **Step 1: Write failing pure-Python weight tests.**

```python
def test_weighted_index_uses_half_open_cumulative_ranges() -> None:
    weights = (2, 1, 0, 0, 0, 1)
    assert [weighted_index(weights, roll) for roll in range(4)] == [0, 0, 1, 5]
```

- [ ] **Step 2: Implement deterministic integer weight validation.** Reject negative weights, six zeros, more or fewer than six entries, and rolls outside `[0, sum(weights))`.
- [ ] **Step 3: Locate and validate a game RNG function.** Record call/return convention, output range, seed behavior, scripted behavior, and a controlled sequence or bounded distribution observation.
- [ ] **Step 4: Confirm where new previous-type history can live, how it updates after selection, and how it resets at round and match boundaries.** Do not modify the live selector.
- [ ] **Step 5: Confirm precedence:** explicit constructor override and scripted override must bypass or supersede future weights exactly as documented.
- [ ] **Step 6: Add exact-ROM tests for RNG function bytes, history storage geometry, and selector fallback boundaries.**
- [ ] **Step 7: Commit:** `git commit -m "docs: confirm Gate RNG and battle history"`.

---

### Task 6: Ability Card State and Timing

**Files:**
- Create: `src/bakugan_ds/gates/ability.py`
- Create: `analysis/gates/ability-card-state.json`
- Create: `tests/unit/test_gate_ability.py`
- Create: `tests/integration/test_gate_ability_reference.py`
- Modify: `analysis/symbols/gate_system2_context.csv`

**Interfaces:**
- `AbilityPhase(StrEnum)`: `available`, `selected`, `activated`, `resolved`, `used`, `reset`
- `AbilityStateEvidence(participant, phase, owner_structure, access, width_bits, value_domain, initialization, mutation, reset, confidence, evidence)`
- `AbilityTimingEvidence(activation_boundary, resolution_boundary, gate_bonus_relation, battle_type_relation)`
- `AbilityModel(states, timing, scripted_paths)`

- [ ] **Step 1: Write failing tests requiring both participants and every phase.**
- [ ] **Step 2: Implement strict phase progression and authoritative-state validation.** UI selection alone cannot satisfy `activated`, `resolved`, or `used`.
- [ ] **Step 3: Trace Ability availability, selection, activation, resolution, consumed state, and reset for player and AI.**
- [ ] **Step 4: Record timing relative to Gate bonus calculation, battle-type selection, minigame start, and result resolution.**
- [ ] **Step 5: Observe one Ability-used scenario and one no-Ability control from clean executable launches.**
- [ ] **Step 6: Add exact-ROM tests for committed functions, fields, and selected observations.**
- [ ] **Step 7: Commit:** `git commit -m "docs: confirm Ability Card battle state"`.

---

### Task 7: Landing and Shot Context

**Files:**
- Create: `src/bakugan_ds/gates/landing.py`
- Create: `analysis/gates/landing-and-shot-context.json`
- Create: `tests/unit/test_gate_landing.py`
- Create: `tests/integration/test_gate_landing_reference.py`
- Modify: `analysis/symbols/gate_system2_context.csv`

**Interfaces:**
- `LandingOutcome(StrEnum)` using only outcomes proven by the executable
- `LandingFieldEvidence(name, value_domain, participant_source, owner_structure, access, initialization, reset, scripted_behavior, confidence, evidence)`
- `LandingContext(fields, evaluation_boundary, arena_id)`

- [ ] **Step 1: Write failing tests requiring confirmed `landing_result` and `shot_condition` while allowing only `arena_id` to be deferred.**

```python
def test_landing_context_allows_arena_only_deferred() -> None:
    context = LandingContext(
        fields=(confirmed_landing_result(), confirmed_shot_condition()),
        evaluation_boundary=confirmed_boundary(),
        arena_id=deferred_arena_field(),
    )
    context.validate()
```

- [ ] **Step 2: Implement exact value-domain and participant-association validation.** Do not predeclare outcome names before executable evidence.
- [ ] **Step 3: Trace shot/landing result into Gate activation and confirm the last safe evaluation boundary before the values are cleared or overwritten.**
- [ ] **Step 4: Observe at least two distinct landing or shot outcomes and one tutorial/scripted path.**
- [ ] **Step 5: Commit arena ID as `presence: "deferred"`, `confidence: "candidate"` or `probable`, with `allowed_exception: true`; no other field may use that exception.**
- [ ] **Step 6: Run unit, readiness, artifact, and exact-ROM tests.**
- [ ] **Step 7: Commit:** `git commit -m "docs: confirm landing and shot context"`.

---

### Task 8: Difficulty Context

**Files:**
- Create: `src/bakugan_ds/gates/difficulty.py`
- Create: `analysis/gates/difficulty-context.json`
- Create: `tests/unit/test_gate_difficulty.py`
- Create: `tests/integration/test_gate_difficulty_reference.py`
- Modify: `analysis/symbols/gate_system2_context.csv`

**Interfaces:**
- `DifficultyValue(value, label, evidence)`
- `DifficultyEvidence(owner_structure, access, width_bits, values, initialization, profile_change, battle_load, ai_consumers, reset, confidence, evidence)`
- `normalize_difficulty_artifact(payload) -> DifficultyEvidence`

- [ ] **Step 1: Write failing tests for duplicate values, missing battle-load evidence, and candidate confidence.**
- [ ] **Step 2: Implement strict value-domain and lifecycle validation.**
- [ ] **Step 3: Locate the authoritative profile or settings field, trace it into battle/AI logic, and distinguish direct difficulty reads from derived AI parameters.**
- [ ] **Step 4: Observe at least two difficulty settings in clean launches and record the same field/access path.**
- [ ] **Step 5: Add exact-ROM tests for setting storage, load function bytes, and selected normalized observations.**
- [ ] **Step 6: Commit:** `git commit -m "docs: confirm battle difficulty context"`.

---

### Task 9: Effect Timing Boundaries

**Files:**
- Create: `src/bakugan_ds/gates/timing.py`
- Create: `analysis/gates/effect-timing.json`
- Create: `tests/unit/test_gate_timing.py`
- Create: `tests/integration/test_gate_timing_reference.py`
- Modify: `analysis/symbols/gate_system2_context.csv`

**Interfaces:**
- `EffectPhase(StrEnum)`: `pre_gate`, `post_gate`, `pre_battle_type`, `post_battle_type`, `battle_start`, `ability_activation`, `ability_resolution`, `battle_result`, `gate_capture`, `gate_removal`, `round_reset`, `match_reset`
- `TimingBoundaryEvidence(phase, component, address, component_offset, live_registers, owner_objects, valid_fields, mutations_allowed, scripted_bypass, rollback, confidence, evidence)`
- `TimingModel(boundaries)`

- [ ] **Step 1: Write a failing test requiring exactly one confirmed boundary for every phase.**
- [ ] **Step 2: Implement boundary validation.** Require component-relative address consistency, nonempty valid-field lists, mutation policy, scripted behavior, and rollback.
- [ ] **Step 3: Reuse confirmed Gate/selector/Ability/result symbols and trace missing capture, removal, round-reset, and match-reset boundaries.**
- [ ] **Step 4: Add reversible watchpoints or logging at selected phases.** Record no register/memory mutation and unchanged results.
- [ ] **Step 5: Add exact-ROM hash checks for every committed instruction range.**
- [ ] **Step 6: Commit:** `git commit -m "docs: confirm Gate effect timing boundaries"`.

---

### Task 10: Version-1 `G2DT` Header and 40-Byte Record

**Files:**
- Create: `src/bakugan_ds/gates/record.py`
- Create: `analysis/gates/system2-record-v1.json`
- Create: `tests/unit/test_gate_record.py`
- Create: `docs/gate-card-system-2-data-format.md`

**Interfaces:**
- `G2DT_MAGIC = b"G2DT"`
- `G2DT_VERSION = 1`
- `G2DT_HEADER_SIZE = 32`
- `GATE_RECORD_SIZE = 40`
- `G2DTHeader(version, header_size, record_size, first_card_id, record_count, flags, payload_size, payload_crc32, header_crc32, reserved)`
- `GateRecordV1(card_id, archetype, flags, flat_bonus_g, percent_q8_8, attribute_modifiers, battle_weights, preferred_type, condition_id, effect_id, drawback_id, effect_value, drawback_value, activation_limit, fatigue_rate, target_mode, timing_phase, condition_value, secondary_effect_id, secondary_condition_id, secondary_value, reserved)`
- `serialize_header()`, `parse_header()`, `serialize_record()`, `parse_record()`, `build_trailer()`, `parse_trailer()`

**Binary layout:**

```text
Header, 32 bytes
0x00 magic[4]             "G2DT"
0x04 version u16          1
0x06 header_size u16      32
0x08 record_size u16      40
0x0A first_card_id u16    1
0x0C record_count u16     103
0x0E flags u16            0 for v1
0x10 payload_size u32     4120
0x14 payload_crc32 u32
0x18 header_crc32 u32     CRC with this field zeroed
0x1C reserved u32         0

Record, 40 bytes
0x00 card_id u8
0x01 archetype u8
0x02 flags u16
0x04 flat_bonus_g s16
0x06 percent_q8_8 s16
0x08 attribute_modifiers[6] s8
0x0E battle_weights[6] u8
0x14 preferred_type u8
0x15 condition_id u8
0x16 effect_id u8
0x17 drawback_id u8
0x18 effect_value s16
0x1A drawback_value s16
0x1C activation_limit u8
0x1D fatigue_rate u8
0x1E target_mode u8
0x1F timing_phase u8
0x20 condition_value s16
0x22 secondary_effect_id u8
0x23 secondary_condition_id u8
0x24 secondary_value s16
0x26 reserved u16
```

- [ ] **Step 1: Write failing exact-size, signed-roundtrip, CRC, and malformed-geometry tests.**

```python
def test_gate_record_v1_is_exactly_40_bytes() -> None:
    encoded = serialize_record(synthetic_record(card_id=40, flat_bonus_g=-25))
    assert len(encoded) == 40
    assert parse_record(encoded).flat_bonus_g == -25
```

- [ ] **Step 2: Implement little-endian `struct.Struct` serializers and CRC32 guards.** Require 103 records covering IDs 1–103 exactly once, sorted by ID.
- [ ] **Step 3: Validate Q8.8 percentage bounds and six-element signed attribute/unsigned weight vectors.** Reject unsupported IDs, flags, target modes, phases, and nonzero reserved fields.
- [ ] **Step 4: Generate `analysis/gates/system2-record-v1.json` from the exact layout and readiness-confirmed enum domains.** Arena-dependent condition/effect IDs must be absent from version 1.
- [ ] **Step 5: Document all offsets, scaling, CRC coverage, fallback behavior, and versioning rules.**
- [ ] **Step 6: Run record tests, compileall, Ruff, and mypy.**
- [ ] **Step 7: Commit:** `git commit -m "feat: define Gate System 2 record format"`.

---

### Task 11: Raw Trailer Loader, Overlay Layout, and Cache Lifecycle

**Files:**
- Create: `src/bakugan_ds/gates/loader.py`
- Modify: `src/bakugan_ds/gates/storage.py`
- Create: `analysis/gates/loader-and-cache.json`
- Create: `tests/unit/test_gate_loader.py`
- Create: `tests/integration/test_gate_loader_reference.py`
- Modify: `tests/integration/test_gate_system_runtime_inputs.py`

**Interfaces:**
- `NitroFsOperation(name, function, calling_convention, arguments, result, confidence, evidence)`
- `CacheLayout(module_start=0x0228BC20, module_size=0x8000, cache_start=0x02293C20, cache_size=0x40, arena_low=0x02293C60)`
- `LoaderEvidence(open_op, seek_op, read_op, close_op, file_id=2762, raw_size=2840, trailer_size=4152, stack_read_size=72, cache_layout, initialization, invalidation, fallback)`
- `append_validated_trailer(original_raw, trailer) -> bytes`
- `build_expanded_overlay(original_decoded, module) -> bytes`
- `validate_overlay_expansion(original, expanded, layout) -> None`

- [ ] **Step 1: Write failing geometry and native-decoding tests.**

```python
def test_expanded_overlay_preserves_original_bss_addresses() -> None:
    expanded = build_expanded_overlay(b"A" * 0x721A0, b"B" * 0x8000)
    assert len(expanded) == 0x7A7E0
    assert expanded[0x721A0:0x727E0] == b"\0" * 0x640
    assert expanded[0x727E0:0x7A7E0] == b"B" * 0x8000
```

- [ ] **Step 2: Implement deterministic trailer append and overlay-layout validation.** Reject existing magic, stale original hashes, wrong module size, nonzero preserved-BSS bytes, incorrect RAM/BSS metadata, or arena overlap.
- [ ] **Step 3: Trace raw NitroFS open, seek, read, and close functions and confirm file ID 2762 access.** Record exact arguments, return values, error behavior, and stack usage.
- [ ] **Step 4: Confirm cache initialization and invalidation boundaries.** A loader-only instrumentation build may validate a synthetic trailer and cache record but must return the original Gate value/type and clear the cache at battle completion.
- [ ] **Step 5: Test valid trailer, absent trailer, bad magic, bad CRC, short read, unsupported version, invalid card ID, and cache-reset scenarios.** Every failure uses legacy behavior.
- [ ] **Step 6: Add exact-ROM/rebuild integration checks for file hashes, decoded LZ10 identity, overlay length, metadata, arena boundary, and unrelated FAT identity.**
- [ ] **Step 7: Commit:** `git commit -m "feat: validate Gate trailer loader and cache"`.

---

### Task 12: Gate Discovery CLI and Fail-Closed Readiness Report

**Files:**
- Modify: `src/bakugan_ds/gates/cli.py`
- Modify: `src/bakugan_ds/cli.py`
- Create: `analysis/gates/milestone-6c-readiness.json`
- Create: `tests/unit/test_gate_discovery_cli.py`
- Modify: `tests/unit/test_gate_cli.py`
- Modify: `tests/test_gate_system_2_artifacts.py`

**Commands:**

```text
bakugan-ds gate validate-artifact ARTIFACT.json
bakugan-ds gate validate-trailer TRAILER.bin
bakugan-ds gate readiness --requirements analysis/gates/milestone-6b-requirements.json --evidence-dir analysis/gates --output OUTPUT.json
```

- [ ] **Step 1: Write failing nested-command and fail-closed tests.**

```python
def test_readiness_command_fails_when_non_arena_field_is_probable(tmp_path: Path) -> None:
    result = run_readiness(tmp_path, override=("gate_owner", "probable"))
    assert result == 4
    assert "gate_owner" in capsys.readouterr().err
```

- [ ] **Step 2: Add artifact-type dispatch using each domain normalizer.** Unsupported schema IDs and duplicate domains fail.
- [ ] **Step 3: Implement readiness output with exact arrays:** `confirmed`, `deferred`, `failures`, `artifact_hashes`, `ready_for_milestone_6c`. Output must be deterministic and atomic.
- [ ] **Step 4: Require `deferred == ["arena_id"]` and zero failures.** Missing arena evidence is not acceptable; it must be explicitly present as the allowed deferred field.
- [ ] **Step 5: Validate all committed artifacts and generate `analysis/gates/milestone-6c-readiness.json`.** Do not manually set readiness to true; it must be produced by the validator.
- [ ] **Step 6: Add artifact tests prohibiting raw bytes, RAM dumps, save states, screenshots, complete original tables, and debugger logs.**
- [ ] **Step 7: Run CLI, readiness, artifact, compileall, Ruff, and mypy checks.**
- [ ] **Step 8: Commit:** `git commit -m "feat: add Gate discovery readiness gate"`.

---

### Task 13: Runtime Context Documentation, Full Verification, and Milestone 6C Handoff

**Files:**
- Create: `docs/gate-card-system-2-runtime-context.md`
- Create: `docs/superpowers/plans/2026-08-02-milestone-6b-verification.md`
- Modify: `README.md`
- Modify: `tests/test_gate_system_2_artifacts.py`
- Modify: relevant `tests/integration/test_gate_*_reference.py`

- [ ] **Step 1: Add one artifact test that enumerates every requirement and proves arena ID is the sole deferred key.**
- [ ] **Step 2: Document each confirmed field in a table with semantics, width, owner, access, initialization, mutation, lifetime, reset, player/AI behavior, scripted behavior, effect phases, and evidence ID.**
- [ ] **Step 3: Document confirmed-absent original fields and their approved match-local replacement storage.**
- [ ] **Step 4: Run clean runtime scenarios:** normal player battle, AI path, tutorial/scripted path, Ability used and unused controls, score/capture update, repeated round/Gate transition, two landing outcomes, two difficulty settings, valid synthetic trailer, malformed trailer fallback, and clean responsive exit.
- [ ] **Step 5: Run the complete test and quality gate.**

```bash
python -m compileall -q src tests tools
python -m ruff check src tests tools
python -m mypy src/bakugan_ds
python -m pytest -v
BAKUGAN_DS_ROM="$BAKUGAN_DS_ROM" \
BAKUGAN_DS_RUNTIME_ARM9="$BAKUGAN_DS_RUNTIME_ARM9" \
python -m pytest -m integration -v
git diff --check main...HEAD
```

- [ ] **Step 6: Rebuild twice from identical inputs and compare ROM SHA-256 plus build reports.** Confirm unchanged gameplay instrumentation modifies only the intended loader/layout bytes and unrelated FAT payloads remain byte-identical.
- [ ] **Step 7: Generate the final readiness report and assert:** `ready_for_milestone_6c == true`, `deferred == ["arena_id"]`, and `failures == []`.
- [ ] **Step 8: Record exact commands, totals, skipped environment-gated tests, direct-ROM results, hashes, and limitations in the verification document.**
- [ ] **Step 9: Update the README to state that Milestone 6B confirms complete context but implements no System 2.0 gameplay effect.**
- [ ] **Step 10: Commit:** `git commit -m "docs: complete Gate System 2 discovery"`.

---

## Self-Review Checklist

Before implementation begins, verify:

- Every mandatory domain in the approved specification has a task and artifact.
- Ownership, participant targeting, score, capture, reuse, history, RNG, Ability state, landing, difficulty, timing, loader/cache, and record format are all required.
- Arena ID is explicitly present and is the only allowed deferral.
- No task implements a live Gate bonus, weighted selector, condition, effect, AI change, or roster rebalance.
- Confirmed absence requires evidence and replacement storage.
- Player/AI and scripted behavior are required for every applicable field.
- The version-1 record contains no arena-dependent condition or effect.
- Every runtime experiment has a legacy fallback and unchanged-result requirement.
- Every task has a failing test, implementation step, passing test, and commit.
- The final readiness report is generated, not hand-authored.
