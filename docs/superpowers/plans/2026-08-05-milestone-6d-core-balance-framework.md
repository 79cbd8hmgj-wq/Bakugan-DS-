# Milestone 6D Core Balance Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalize the merged Juggernoid prototype into a deterministic Gate Card System 2.0 balance framework with seven archetypes, fixed internal budgets, bounded battle weights, record-local attribute relationships, reusable conditions, targeting, G effects, explicit drawbacks, and exact legacy fallback while keeping Juggernoid as the only live converted Gate.

**Architecture:** Add four focused pure-Python modules for balance analysis, conditions, effects, and generic calculation. Extend the version-1 authoring validator and CLI to produce a deterministic Milestone 6D report. Generalize the existing fixed-size emitted ARM32 module so its runtime dispatcher consumes the same IDs and rules as the host reference model, while retaining the Milestone 6C loader, cache, hooks, CRC validation, legacy replay, and transactional installer.

**Tech Stack:** Python 3.11 standard library, frozen dataclasses, `IntEnum`, JSON, `struct`, deterministic integer arithmetic, pytest 8.3, Ruff, strict mypy, the existing ARM32 emitter/interpreter, exact workspace/rebuild APIs, and the established DeSmuME ARM9 GDB workflow.

## Global Constraints

- Support only profile `b6re_rev0`.
- Use `docs/superpowers/specs/2026-08-05-milestone-6d-core-balance-framework-design.md` as the source of truth.
- Base all work on merged commit `6cfa600093e887c191957180c04a53b8d26c0948` or a descendant containing no later conflicting Gate changes.
- Preserve the physical version-1 40-byte Gate record and 4,152-byte trailer geometry.
- Preserve Gate ID `19` Juggernoid exactly: flat `60`, percentage `20`, Aquos `+30`, owner-behind `+40`, weights `(50, 30, 30, 30, 30, 30)`.
- Preserve exact Milestone 6C loader, complete-payload CRC, selected-record cache, hook precedence, and fallback behavior.
- Keep Gate ID `19` as the only live nonlegacy record in the committed Milestone 6D authoring roster.
- Exercise all other archetypes only through authored test fixtures and exact emitted-module tests.
- Attribute order is `Pyrus, Aquos, Subterra, Haos, Darkus, Ventus`.
- Battle-type order is `Scratch, Timing, Pop, Spin, Trace, Bound`.
- Use signed 32-bit intermediates, integer division toward zero, signed-16 Gate-bonus clamp, and unsigned-16 successful target-total clamp.
- Do not read `arena_id`.
- Do not modify Ability state, activation counters, fatigue, battle history, AI, presentation, save data, or persistent roster data.
- Do not introduce any random effect other than the confirmed weighted battle-type selector.
- Preserve protected core-G offsets `0x23C18-0x23C1C`, `0x23CB0-0x23CF8`, and `0x23D78-0x23D7C`.
- Preserve runtime module range `0x0228BC20-0x02293C20` and cache range `0x02293C20-0x02293C60`; module growth is not authorized.
- Every installation and workspace change is transactional.
- Commit no ROM, rebuilt ROM, module binary, trailer binary, save, save state, screenshot, RAM dump, raw debugger log, or copied original Gate table.
- Exact-ROM tests skip unless the user-owned local reference files are supplied.
- Final verification follows `.github/workflows/ci.yml`: complete pytest suite, Python compilation, Ruff on changed Python, strict mypy on changed package source, and `git diff --check`.

## File Map

### Create

```text
config/gates/milestone-6d-system2-v1.json
src/bakugan_ds/gates/balance.py
src/bakugan_ds/gates/conditions.py
src/bakugan_ds/gates/effects.py
analysis/gates/milestone-6d-balance-contract.json
analysis/gates/milestone-6d-runtime-contract.json
analysis/runtime-observations/gate-system2-milestone-6d-validation.json
docs/gate-card-system-2-balance-framework.md
docs/superpowers/plans/2026-08-05-milestone-6d-verification.md
tests/unit/test_gate_balance.py
tests/unit/test_gate_conditions.py
tests/unit/test_gate_effects.py
tests/unit/test_gate_milestone_6d_authoring.py
tests/unit/test_gate_milestone_6d_runtime_module.py
tests/integration/test_gate_milestone_6d_build.py
tests/integration/test_gate_milestone_6d_reference.py
tests/test_gate_milestone_6d_artifacts.py
tests/test_gate_milestone_6d_runtime_evidence.py
```

### Modify

```text
src/bakugan_ds/gates/record.py
src/bakugan_ds/gates/authoring.py
src/bakugan_ds/gates/system2.py
src/bakugan_ds/gates/runtime_context.py
src/bakugan_ds/gates/runtime_module.py
src/bakugan_ds/gates/install.py
src/bakugan_ds/gates/cli.py
src/bakugan_ds/gates/__init__.py
src/bakugan_ds/cli.py
tests/support/arm32_interpreter.py
tests/unit/test_gate_authoring.py
tests/unit/test_gate_system2.py
tests/unit/test_gate_runtime_module.py
tests/unit/test_gate_install.py
tests/unit/test_gate_cli.py
README.md
docs/gate-card-system-2-roadmap.md
```

---

### Task 1: Freeze Milestone 6D Semantic IDs and Record Accessors

**Files:**
- Modify: `src/bakugan_ds/gates/record.py`
- Modify: `src/bakugan_ds/gates/__init__.py`
- Test: `tests/unit/test_gate_milestone_6d_authoring.py`

**Interfaces:**
- Produces `GateArchetype(IntEnum)` with IDs `LEGACY=0`, `COMEBACK=1`, `POWER=2`, `SKILL=3`, `CONTROL=4`, `RISK=5`, `ATTRIBUTE=6`, `CHAOS=7`.
- Produces `GateConditionId(IntEnum)` with IDs `NONE=0`, `OWNER_BEHIND=1`, `OWNER_AHEAD=2`, `SCORE_TIED=3`, `OWNER_SCORE_ZERO=4`, `OWNER_AT_MATCH_POINT=5`, `OPPONENT_AT_MATCH_POINT=6`, `LANDING_GATE_CARD_WON=7`.
- Produces `GateEffectId(IntEnum)` with IDs `NONE=0`, `ADD_SIGNED_G=1`, `SUBTRACT_MAGNITUDE_G=2`.
- Produces `GateTargetMode(IntEnum)` with IDs `CURRENT_COMBATANT=0`, `GATE_OWNER=1`, `GATE_NON_OWNER=2`.
- Produces `GateTimingPhase(IntEnum)` with `PRE_GATE_CALCULATION=0`.
- Produces signed accessors for `effect_value`, `drawback_value`, and `secondary_value` without changing serialized bytes.

- [ ] **Step 1: Write failing enum and signed-field tests.**

```python
def test_milestone_6d_semantic_ids_are_frozen() -> None:
    assert int(GateArchetype.COME_BACK if False else GateArchetype.COMEBACK) == 1
    assert int(GateArchetype.CHAOS) == 7
    assert int(GateConditionId.LANDING_GATE_CARD_WON) == 7
    assert int(GateTargetMode.GATE_NON_OWNER) == 2


def test_signed_effect_values_round_trip_through_record_bytes() -> None:
    record = replace(legacy_passthrough_record(7), effect_value=-40)
    decoded = GateRecordV1.from_bytes(record.to_bytes())
    assert decoded.effect_value == -40
```

Use `GateArchetype.COMEBACK` directly in the committed test; the conditional expression above is only to make the intended exact identifier unmistakable.

- [ ] **Step 2: Run `python -m pytest tests/unit/test_gate_milestone_6d_authoring.py -v`; confirm the new enums or signed behavior are absent.**
- [ ] **Step 3: Add the exact enums and signed decoding/encoding helpers.** Preserve the existing record field order and total size.
- [ ] **Step 4: Reject booleans, out-of-width integers, unsupported timing IDs, and nonzero reserved values in base structural validation.** Semantic support by milestone remains in authoring validation, not raw decoding.
- [ ] **Step 5: Run existing record, authoring, loader, and Milestone 6C tests to prove byte compatibility.**
- [ ] **Step 6: Commit.**

```bash
git add src/bakugan_ds/gates/record.py src/bakugan_ds/gates/__init__.py \
  tests/unit/test_gate_milestone_6d_authoring.py
git commit -m "feat: freeze Gate System 2.0 balance IDs"
```

---

### Task 2: Attribute Relationship Tiers and Profile Validation

**Files:**
- Create: `src/bakugan_ds/gates/balance.py`
- Create: `tests/unit/test_gate_balance.py`

**Interfaces:**
- Produces `AttributeRelation(StrEnum)` values `PRIMARY`, `SECONDARY`, `NEUTRAL`, `OPPOSED`.
- Produces `classify_attribute_modifier(value: int) -> AttributeRelation`.
- Produces `AttributeProfileReport(modifiers, tiers, minimum, maximum, spread, positive_count, negative_count)`.
- Produces `analyze_attribute_profile(record: GateRecordV1) -> AttributeProfileReport`.
- Produces `validate_attribute_profile(record: GateRecordV1) -> None`.

- [ ] **Step 1: Write failing exact-boundary tests.**

```python
@pytest.mark.parametrize(
    ("value", "expected"),
    [(-60, "opposed"), (-15, "opposed"), (-9, "neutral"), (0, "neutral"),
     (9, "neutral"), (10, "secondary"), (40, "secondary"),
     (41, "primary"), (75, "primary")],
)
def test_attribute_tier_boundaries(value: int, expected: str) -> None:
    assert classify_attribute_modifier(value).value == expected


def test_attribute_archetype_requires_positive_negative_and_spread() -> None:
    record = make_record(
        archetype=GateArchetype.ATTRIBUTE,
        attribute_modifiers=(50, 20, 0, 0, -20, -40),
    )
    validate_attribute_profile(record)
```

- [ ] **Step 2: Run the focused test and confirm `balance.py` is absent.**
- [ ] **Step 3: Implement tier classification with exact ranges.** Reject values outside `-100..100` before classification.
- [ ] **Step 4: Implement profile reporting in the fixed attribute order.**
- [ ] **Step 5: Implement archetype rules.** Attribute requires `max >= 40`, `min <= -20`, and spread `>= 60`; non-Attribute records allow at most two positive affinity entries above neutral; legacy requires all zero.
- [ ] **Step 6: Add rejection tests for three positive affinities, inadequate spread, hidden out-of-range values, and nonzero legacy values.**
- [ ] **Step 7: Run focused tests, Ruff, and strict mypy.**
- [ ] **Step 8: Commit.**

```bash
git add src/bakugan_ds/gates/balance.py tests/unit/test_gate_balance.py
git commit -m "feat: validate Gate attribute relationship profiles"
```

---

### Task 3: Bounded Battle-Weight Analysis

**Files:**
- Modify: `src/bakugan_ds/gates/balance.py`
- Test: `tests/unit/test_gate_balance.py`

**Interfaces:**
- Produces `BattleWeightPressure(StrEnum)` values `NEUTRAL`, `MILD`, `STRONG`, `EXTREME_BOUNDED`.
- Produces `BattleWeightReport(weights, total, maximum, minimum, preferred_type, pressure, budget_cost, maximum_probability_basis_points)`.
- Produces `analyze_battle_weights(record: GateRecordV1) -> BattleWeightReport`.
- Produces `validate_battle_weights(record: GateRecordV1) -> None`.

- [ ] **Step 1: Add failing tests for exact accepted vectors.**

```python
@pytest.mark.parametrize(
    ("weights", "pressure", "cost"),
    [
        ((30, 30, 30, 30, 30, 30), "neutral", 0),
        ((50, 30, 30, 30, 30, 30), "mild", 10),
        ((60, 24, 24, 24, 24, 24), "strong", 20),
        ((80, 24, 24, 24, 24, 24), "extreme_bounded", 30),
    ],
)
def test_weight_pressure_uses_integer_probability(
    weights: tuple[int, ...], pressure: str, cost: int
) -> None:
    report = analyze_battle_weights(make_record(weights=weights))
    assert report.pressure.value == pressure
    assert report.budget_cost == cost
```

- [ ] **Step 2: Add failing rejection tests for zero weights, values below `10`, values above `80`, totals below `120`, totals above `300`, maximum probability above `40%`, ratio above `4`, and preferred type not referencing a maximum.**
- [ ] **Step 3: Implement validation with integer cross-multiplication.** Do not use `float`, `Decimal`, or percentage rounding to decide a band.
- [ ] **Step 4: Preserve legacy-passthrough all-zero weights and `preferred_type=255` as a separate exact path.**
- [ ] **Step 5: Verify Juggernoid is classified `MILD`, total `200`, cost `10`, and maximum probability `2500` basis points.**
- [ ] **Step 6: Run focused and existing selector tests.**
- [ ] **Step 7: Commit.**

```bash
git add src/bakugan_ds/gates/balance.py tests/unit/test_gate_balance.py
git commit -m "feat: bound Gate battle-type weighting"
```

---

### Task 4: Deterministic Power-Budget Calculator and Archetype Invariants

**Files:**
- Modify: `src/bakugan_ds/gates/balance.py`
- Test: `tests/unit/test_gate_balance.py`

**Interfaces:**
- Produces `GateBudgetBreakdown(flat_cost, percentage_cost, attribute_cost, effect_cost, battle_weight_cost, negative_attribute_credit, drawback_credit, gross_budget, net_budget)`.
- Produces `calculate_gate_budget(record: GateRecordV1) -> GateBudgetBreakdown`.
- Produces `validate_archetype_invariants(record, attribute_report, weight_report, budget) -> None`.
- Produces `analyze_gate_balance(record) -> GateBalanceReport`.

- [ ] **Step 1: Write failing exact Juggernoid budget test.**

```python
def test_juggernoid_budget_is_91() -> None:
    report = analyze_gate_balance(approved_juggernoid_record())
    assert report.budget.flat_cost == 45
    assert report.budget.percentage_cost == 10
    assert report.budget.attribute_cost == 12
    assert report.budget.effect_cost == 14
    assert report.budget.battle_weight_cost == 10
    assert report.budget.net_budget == 91
```

- [ ] **Step 2: Write one valid fixture for each archetype and assert its net band and mandatory invariant.** Fixtures must be newly authored and must not use copied original Gate values.
- [ ] **Step 3: Write one invalid fixture for each archetype.** Examples: Comeback without a score disadvantage condition; Power below 70% direct-G share; Skill with mild weights; Risk without a drawback; Attribute without spread; Chaos without drawback.
- [ ] **Step 4: Implement ceiling integer division helper `_ceil_div_nonnegative(value, divisor)`.** Reject negative inputs at the helper boundary.
- [ ] **Step 5: Implement the exact component costs and credit caps from the specification.**
- [ ] **Step 6: Implement gross/net budget and archetype band checks.** No automatic normalization is permitted.
- [ ] **Step 7: Add edge tests at every band endpoint and one point outside each endpoint.**
- [ ] **Step 8: Run the full balance test file, Ruff, and strict mypy.**
- [ ] **Step 9: Commit.**

```bash
git add src/bakugan_ds/gates/balance.py tests/unit/test_gate_balance.py
git commit -m "feat: add fixed Gate power budgets"
```

---

### Task 5: Reusable Score and Landing Conditions

**Files:**
- Create: `src/bakugan_ds/gates/conditions.py`
- Modify: `src/bakugan_ds/gates/runtime_context.py`
- Create: `tests/unit/test_gate_conditions.py`
- Modify: `tests/unit/test_gate_runtime_context.py`

**Interfaces:**
- Produces `GateConditionContext(owner_side_score, opposing_side_score, landing_result)`.
- Produces `evaluate_gate_condition(condition_id, context, condition_value=0) -> bool`.
- Extends normalized runtime calculation context with optional confirmed `landing_result` without reading `arena_id`.

- [ ] **Step 1: Write failing truth-table tests for all eight condition IDs.** Include true and false cases.
- [ ] **Step 2: Add solo and reciprocal-team context tests.** Owner and opposing score projection must match the existing authoritative participant `+0xEE` and teammate `+0xF2` rules.
- [ ] **Step 3: Add exact match-point tests.** Score `2` is true; scores `0`, `1`, and `>=3` are false.
- [ ] **Step 4: Add landing tests.** Only landing result `1` satisfies `LANDING_GATE_CARD_WON`; unavailable landing context and values `0`, `2`, `3`, `4` return false for the pure evaluator and are rejected when a live record requires the condition.
- [ ] **Step 5: Implement the pure evaluator with exhaustive enum dispatch.** Unsupported IDs raise the existing Gate validation error; they never default true.
- [ ] **Step 6: Extend runtime-context normalization only through already confirmed landing evidence.** A record that does not use the landing condition must not require a throw controller.
- [ ] **Step 7: Add invalid-pointer, invalid-team, score-overflow, and unavailable-landing fallback tests.**
- [ ] **Step 8: Run condition, runtime-context, and Milestone 6C regression tests.**
- [ ] **Step 9: Commit.**

```bash
git add src/bakugan_ds/gates/conditions.py src/bakugan_ds/gates/runtime_context.py \
  tests/unit/test_gate_conditions.py tests/unit/test_gate_runtime_context.py
git commit -m "feat: add deterministic Gate conditions"
```

---

### Task 6: Target Resolution, Signed Effects, and Explicit Drawbacks

**Files:**
- Create: `src/bakugan_ds/gates/effects.py`
- Create: `tests/unit/test_gate_effects.py`

**Interfaces:**
- Produces `GateEffectContext(current_participant, owner_participant)`.
- Produces `matches_gate_target(target_mode, context) -> bool`.
- Produces `apply_gate_effect(effect_id, value, gate_bonus) -> int` using signed 32-bit checked arithmetic.
- Produces `dispatch_gate_modifiers(record, condition_context, effect_context, gate_bonus) -> GateModifierTrace`.

- [ ] **Step 1: Write failing target truth-table tests for current, owner, and non-owner.**
- [ ] **Step 2: Write failing effect tests.** `ADD_SIGNED_G` must add positive or negative signed values; `SUBTRACT_MAGNITUDE_G` must subtract `abs(value)` and reject the signed minimum if absolute-value conversion would overflow the supported intermediate policy.
- [ ] **Step 3: Write deterministic sequencing tests.** Primary reward executes before explicit drawback; both operate on the current calculation only; a false condition or target leaves the value unchanged.
- [ ] **Step 4: Implement checked signed-32 addition and final signed-16 clamp as separate helpers.**
- [ ] **Step 5: Implement `GateModifierTrace` containing condition results, target results, pre-effect bonus, primary delta, drawback delta, secondary delta, unclamped result, and final result.**
- [ ] **Step 6: Keep secondary live fields unsupported, but allow a test-only `dispatch_gate_modifiers(..., allow_secondary_fixture=True)` path used solely by host and emitted-module parity tests.** Production authoring never enables it.
- [ ] **Step 7: Add rejection tests for unsupported IDs, unsupported timing, invalid participants, and partial application.**
- [ ] **Step 8: Run focused tests and strict mypy.**
- [ ] **Step 9: Commit.**

```bash
git add src/bakugan_ds/gates/effects.py tests/unit/test_gate_effects.py
git commit -m "feat: add Gate effect and drawback dispatch"
```

---

### Task 7: Generic Reference Calculation and Deterministic Trace

**Files:**
- Modify: `src/bakugan_ds/gates/system2.py`
- Modify: `tests/unit/test_gate_system2.py`

**Interfaces:**
- Extends `calculate_system2_gate_bonus(record, context)` to use `conditions.py` and `effects.py` generically.
- Produces a stable `GateCalculationTrace` containing base components, condition/target decisions, effect/drawback deltas, budget identity, final bonus, and fallback reason.
- Preserves the existing Milestone 6C public entry points and result types where compatibility is required.

- [ ] **Step 1: Freeze all existing Juggernoid vectors as regression tests before refactoring.**
- [ ] **Step 2: Add one calculation vector for each archetype fixture.** Verify owner/non-owner, true/false condition, all six attributes, and clamp boundaries.
- [ ] **Step 3: Add complete-fallback tests for invalid attribute, owner, participant, score, teammate, landing, effect, target, and arithmetic context.** No base component may survive.
- [ ] **Step 4: Refactor the one-off Comeback branch into the generic sequence.**

```python
base = calculate_hybrid_components(record, context)
condition_context = build_condition_context(context)
effect_context = build_effect_context(context)
modifier_trace = dispatch_gate_modifiers(
    record,
    condition_context,
    effect_context,
    base.unclamped_bonus,
)
return build_success_result(base, modifier_trace)
```

- [ ] **Step 5: Ensure legacy passthrough exits before any System 2.0 condition, effect, analyzer, or weighted-selection work.**
- [ ] **Step 6: Serialize traces deterministically and reject unordered or floating values.**
- [ ] **Step 7: Run full System 2.0, selector, runtime-context, and Milestone 6C suites.**
- [ ] **Step 8: Commit.**

```bash
git add src/bakugan_ds/gates/system2.py tests/unit/test_gate_system2.py
git commit -m "refactor: generalize Gate System 2.0 calculation"
```

---

### Task 8: Milestone 6D Authoring Policy and Deterministic Balance Report

**Files:**
- Modify: `src/bakugan_ds/gates/authoring.py`
- Create: `config/gates/milestone-6d-system2-v1.json`
- Create: `tests/unit/test_gate_milestone_6d_authoring.py`
- Modify: `tests/unit/test_gate_authoring.py`

**Interfaces:**
- Produces `validate_milestone_6d_roster(records) -> tuple[GateBalanceReport, ...]`.
- Produces `build_milestone_6d_balance_report(records) -> dict[str, object]`.
- Produces `write_milestone_6d_balance_report(path, records) -> None`.

- [ ] **Step 1: Write failing tests asserting exactly 103 ordered records, Gate 19 exact compatibility, and 102 canonical passthrough records.**
- [ ] **Step 2: Copy the Milestone 6C authored roster to the new filename, preserving semantic values exactly.** Do not copy generated trailer bytes.
- [ ] **Step 3: Implement semantic validation for the expanded ID domain and budget rules.**
- [ ] **Step 4: Require deferred live fields to remain zero, secondary fields to remain zero, and timing to remain pre-Gate.**
- [ ] **Step 5: Implement reference-value analysis at core G values `190, 400, 525, 650, 695`, all six attributes, owner/non-owner, and supported condition boundaries.**
- [ ] **Step 6: Produce deterministic JSON with per-card components, budget, attribute profile, weight pressure, minimum/maximum/mean effective bonus, and validation status.** Use integer totals and rational numerator/denominator fields rather than floats.
- [ ] **Step 7: Add tests proving synthetic archetype fixtures can be analyzed but cannot appear in the committed live roster.**
- [ ] **Step 8: Add repeatability and mutation tests.** Two reports are byte-identical; changing any record changes the report and fails live-roster policy when appropriate.
- [ ] **Step 9: Run focused authoring and artifact tests.**
- [ ] **Step 10: Commit.**

```bash
git add src/bakugan_ds/gates/authoring.py config/gates/milestone-6d-system2-v1.json \
  tests/unit/test_gate_milestone_6d_authoring.py tests/unit/test_gate_authoring.py
git commit -m "feat: add Milestone 6D Gate balance authoring"
```

---

### Task 9: CLI Balance Validation and Reporting

**Files:**
- Modify: `src/bakugan_ds/gates/cli.py`
- Modify: `src/bakugan_ds/cli.py`
- Modify: `tests/unit/test_gate_cli.py`

**Interfaces:**
- Produces `bakugan-ds gate validate-milestone-6d AUTHORING`.
- Produces `bakugan-ds gate report-milestone-6d AUTHORING OUTPUT`.
- Existing Milestone 6C commands remain compatible.

- [ ] **Step 1: Write failing CLI tests for successful validation and report creation.**
- [ ] **Step 2: Write failure tests for budget, archetype, weight, attribute, secondary-field, and extra-live-card violations.** Verify nonzero exit and no partial output.
- [ ] **Step 3: Implement atomic output and concise deterministic stdout.** Print record count, live IDs, report SHA-256, Juggernoid net budget, and validation result.
- [ ] **Step 4: Ensure CLI exceptions use the existing user-facing error boundary and never emit a Python traceback for validation errors.**
- [ ] **Step 5: Run CLI and authoring tests.**
- [ ] **Step 6: Commit.**

```bash
git add src/bakugan_ds/gates/cli.py src/bakugan_ds/cli.py tests/unit/test_gate_cli.py
git commit -m "feat: add Gate balance framework CLI"
```

---

### Task 10: Emit Generic ARM32 Condition and Effect Helpers

**Files:**
- Modify: `src/bakugan_ds/gates/runtime_module.py`
- Modify: `src/bakugan_ds/gates/arm32.py`
- Modify: `tests/support/arm32_interpreter.py`
- Create: `tests/unit/test_gate_milestone_6d_runtime_module.py`
- Modify: `tests/unit/test_gate_arm32.py`
- Modify: `tests/unit/test_gate_runtime_module.py`

**Interfaces:**
- Emits `g2_evaluate_condition`.
- Emits `g2_matches_target`.
- Emits `g2_apply_effect`.
- Generalizes `g2_calculate_gate_bonus` to call those helpers.
- Produces symbol addresses in the existing runtime-module manifest.

- [ ] **Step 1: Extend the test interpreter only for exact ARM instructions required by the reviewed helper design.** Add unit tests for each new instruction before using it in module tests.
- [ ] **Step 2: Write failing exact emitted-helper tests for all condition IDs, target modes, effect IDs, and signed values.**
- [ ] **Step 3: Emit `g2_evaluate_condition`.** Use integer compares and explicit false return on unavailable required context.
- [ ] **Step 4: Emit `g2_matches_target`.** It returns `1` or `0` and performs no write.
- [ ] **Step 5: Emit `g2_apply_effect`.** Implement checked signed addition/subtraction and return success/failure separately from the numeric result.
- [ ] **Step 6: Preserve AAPCS-like project ABI:** stack remains 8-byte aligned; documented callee-saved registers are restored; writes remain limited to the current combatant record, cache, and current stack frame.
- [ ] **Step 7: Add exact Python-versus-ARM parity vectors.** Include Juggernoid, every archetype fixture, every condition boundary, both target sides, negative effects, drawbacks, and clamps.
- [ ] **Step 8: Assert the generated module remains exactly `0x8000` bytes and all symbol addresses remain inside `0x0228BC20-0x02293C20`.**
- [ ] **Step 9: Run focused module/interpreter tests, compilation, Ruff, and strict mypy.**
- [ ] **Step 10: Commit.**

```bash
git add src/bakugan_ds/gates/runtime_module.py src/bakugan_ds/gates/arm32.py \
  tests/support/arm32_interpreter.py tests/unit/test_gate_milestone_6d_runtime_module.py \
  tests/unit/test_gate_arm32.py tests/unit/test_gate_runtime_module.py
git commit -m "feat: emit generic Gate condition and effect dispatch"
```

---

### Task 11: Runtime Integration and Exact Legacy Fallback

**Files:**
- Modify: `src/bakugan_ds/gates/runtime_module.py`
- Modify: `src/bakugan_ds/gates/system2.py`
- Modify: `tests/unit/test_gate_milestone_6d_runtime_module.py`
- Modify: `tests/unit/test_gate_system2.py`

**Interfaces:**
- Generic runtime calculation consumes the existing cached 40-byte selected record.
- Legacy replay functions and hook boundaries remain the sole fallback targets.

- [ ] **Step 1: Add failing tests proving unsupported semantic IDs, unavailable required landing context, invalid score context, and arithmetic failures execute complete legacy fallback.**
- [ ] **Step 2: Add tests proving a false valid condition is not a fallback.** It produces a valid base hybrid result with zero conditional delta.
- [ ] **Step 3: Integrate helper calls into `g2_calculate_gate_bonus` without changing the loader or cache geometry.**
- [ ] **Step 4: Preserve selector phase separation.** Generic Gate-G success followed by selector failure still uses only the original fixed selector for that later phase.
- [ ] **Step 5: Add instruction-region and displaced-byte guards for every changed module-source decision.** The external overlay hooks remain unchanged unless exact generated symbol addresses require regenerated branch words.
- [ ] **Step 6: Re-run all Milestone 6C runtime-module vectors and require identical semantic results.**
- [ ] **Step 7: Verify no history byte, Ability state, activation counter, persistent value, or unrelated combatant record is written in interpreter traces.**
- [ ] **Step 8: Commit.**

```bash
git add src/bakugan_ds/gates/runtime_module.py src/bakugan_ds/gates/system2.py \
  tests/unit/test_gate_milestone_6d_runtime_module.py tests/unit/test_gate_system2.py
git commit -m "feat: integrate generic Gate runtime dispatch"
```

---

### Task 12: Transactional Milestone 6D Installer and Build Contracts

**Files:**
- Modify: `src/bakugan_ds/gates/install.py`
- Modify: `src/bakugan_ds/gates/cli.py`
- Create: `analysis/gates/milestone-6d-balance-contract.json`
- Create: `analysis/gates/milestone-6d-runtime-contract.json`
- Modify: `tests/unit/test_gate_install.py`
- Create: `tests/integration/test_gate_milestone_6d_build.py`
- Create: `tests/test_gate_milestone_6d_artifacts.py`

**Interfaces:**
- Produces `install_milestone_6d(workspace, authoring_path) -> Milestone6DInstallReport`.
- Produces CLI `bakugan-ds gate install-milestone-6d WORKSPACE --authoring PATH`.

- [ ] **Step 1: Write failing installer tests for pristine 6C workspace upgrade, pristine extracted workspace install, identical reinstall no-op, stale source rejection, and partial-divergence rejection.**
- [ ] **Step 2: Generate the validated trailer, balance report, module, expanded overlay, hooks, raw carrier override, and deterministic contract before replacing any workspace target.**
- [ ] **Step 3: Stage all products in a temporary directory and verify expected source hashes, replacement hashes, module size, cache geometry, overlay geometry, trailer geometry, and Juggernoid exact semantics.**
- [ ] **Step 4: Atomically replace targets only after every staged validation passes.**
- [ ] **Step 5: Record deterministic hashes and guarded-change counts in the two analysis contracts.** Generated binaries remain untracked.
- [ ] **Step 6: Add artifact tests that reject stale hashes, extra live records, changed protected core-G bytes, unsupported module growth, and missing rollback instructions.**
- [ ] **Step 7: Add exact integration rebuild controls behind the existing environment gates.**
- [ ] **Step 8: Run install, artifact, workspace, and rebuild tests.**
- [ ] **Step 9: Commit.**

```bash
git add src/bakugan_ds/gates/install.py src/bakugan_ds/gates/cli.py \
  analysis/gates/milestone-6d-balance-contract.json \
  analysis/gates/milestone-6d-runtime-contract.json \
  tests/unit/test_gate_install.py tests/integration/test_gate_milestone-6d-build.py \
  tests/test_gate_milestone_6d_artifacts.py
git commit -m "feat: install Milestone 6D transactionally"
```

Use the actual filename `tests/integration/test_gate_milestone_6d_build.py` in the commit command; the hyphenated spelling above must be corrected before committing.

---

### Task 13: Exact-ROM, Emitted-Module, and Live Runtime Acceptance

**Files:**
- Create: `tests/integration/test_gate_milestone_6d_reference.py`
- Create: `analysis/runtime-observations/gate-system2-milestone-6d-validation.json`
- Create: `tests/test_gate_milestone_6d_runtime_evidence.py`
- Create: `docs/superpowers/plans/2026-08-05-milestone-6d-verification.md`

**Interfaces:**
- Produces normalized exact-build and live-runtime evidence without committing copyrighted inputs.

- [ ] **Step 1: Run the complete host suite and record only passing, non-gated counts.**
- [ ] **Step 2: Install Milestone 6D twice into separate exact workspaces and rebuild twice.** Verify byte-identical manifests, trailers, modules, expanded overlays, build reports, and ROM outputs.
- [ ] **Step 3: Verify exact ROM size `134,217,728`, unchanged unrelated FAT payloads, unchanged protected core-G bytes, and exactly one live nonlegacy Gate record.**
- [ ] **Step 4: Execute the exact generated module in the repository ARM interpreter across the complete parity matrix.** Store normalized vector counts and hashes, not raw memory dumps.
- [ ] **Step 5: Boot the rebuilt ROM in the validated DeSmuME bundle.** Confirm title/menu responsiveness.
- [ ] **Step 6: Exercise Juggernoid through an available battle path and confirm its approved Milestone 6C arithmetic/selector behavior remains present.**
- [ ] **Step 7: Exercise one unrelated Gate and confirm original behavior and no System 2.0 weighted RNG call.**
- [ ] **Step 8: Complete or exit the battle/tutorial through a supported path and confirm responsive return plus all 64 cache bytes zero.**
- [ ] **Step 9: Verify no persistent roster G, save data, Ability slot state, activation counter, or history byte changed due to Milestone 6D.**
- [ ] **Step 10: Normalize evidence with exact executable hashes, branch head, commands, bounded claims, and rejected claims.**
- [ ] **Step 11: Add tests validating the evidence document against the exact contracts.**
- [ ] **Step 12: Commit.**

```bash
git add tests/integration/test_gate_milestone_6d_reference.py \
  analysis/runtime-observations/gate-system2-milestone-6d-validation.json \
  tests/test_gate_milestone_6d_runtime_evidence.py \
  docs/superpowers/plans/2026-08-05-milestone-6d-verification.md
git commit -m "test: validate Milestone 6D runtime framework"
```

---

### Task 14: Documentation, Full Regression, Review, and Milestone 6E Handoff

**Files:**
- Create: `docs/gate-card-system-2-balance-framework.md`
- Modify: `docs/gate-card-system-2-roadmap.md`
- Modify: `README.md`
- Modify: `tests/test_gate_milestone_6d_artifacts.py`

**Interfaces:**
- Produces the authoritative user/developer description of the merged framework and the Milestone 6E authoring contract.

- [ ] **Step 1: Document the seven archetypes, internal budget formula, attribute tiers, bounded battle weights, conditions, targets, effects, drawbacks, fallback behavior, and CLI commands.**
- [ ] **Step 2: State prominently that only Juggernoid is live and full-roster conversion is Milestone 6E.**
- [ ] **Step 3: Document rollback.** Restore the Milestone 6C authored configuration/module generation and rebuild; do not copy generated binaries into the repository.
- [ ] **Step 4: Update the roadmap to mark 6D complete only after merge and to define the exact 6E entry gate.**
- [ ] **Step 5: Add documentation-contract tests for prohibited claims, exact IDs, budget bands, module/cache ranges, and live-card count.**
- [ ] **Step 6: Run final verification.**

```bash
python -m pytest -q
python -m compileall -q src tests
python -m ruff check <all changed Python files>
python -m mypy --strict <all changed package source files>
git diff --check
```

- [ ] **Step 7: Review the complete branch diff against the specification.** Confirm no placeholder, copied original table, generated binary, oversized file, unsupported mechanic, arena read, or unreviewed live record.
- [ ] **Step 8: Confirm the branch is clean and record the exact head SHA and test counts in the verification document.**
- [ ] **Step 9: Commit.**

```bash
git add README.md docs/gate-card-system-2-roadmap.md \
  docs/gate-card-system-2-balance-framework.md \
  tests/test_gate_milestone_6d_artifacts.py
git commit -m "docs: complete Milestone 6D balance framework"
```

- [ ] **Step 10: Open a non-draft pull request only after all available verification passes.** The PR description must distinguish host/emitted-module proof from naturally observed emulator cases.
- [ ] **Step 11: Merge only after CI, final diff review, and any required live evidence pass.**

## Plan Self-Review

- Every specification requirement maps to at least one task.
- The physical record and trailer format remain unchanged.
- Juggernoid compatibility is tested in Tasks 4, 7, 10, 11, 12, and 13.
- All seven archetypes receive host fixtures and invariants without activating additional live cards.
- Attribute, weight, budget, condition, target, effect, drawback, authoring, CLI, emitted ARM, installer, exact-build, runtime, and documentation layers have separate test cycles.
- No task authorizes Ability effects, fatigue, history penalties, AI, presentation, arena context, save changes, or full-roster conversion.
- No placeholder, `TODO`, or unresolved identifier remains.
- The one accidental hyphenated test filename in Task 12 is explicitly corrected before execution and must not appear in the repository.
