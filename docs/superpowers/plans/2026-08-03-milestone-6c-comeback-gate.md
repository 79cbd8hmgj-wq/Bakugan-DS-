# Milestone 6C Comeback Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first live Gate Card System 2.0 engine and activate the approved Juggernoid comeback prototype while preserving exact legacy behavior for every unrelated Gate and every invalid-data path.

**Architecture:** Extend the existing evidence-first Gate package in three layers. A pure Python reference layer owns authoring validation, hybrid-G arithmetic, score/target resolution, weighted selection, deterministic traces, and fallback classification. A generic workspace override layer makes the approved raw NitroFS trailer and overlay-7 layout changes reproducible through the normal validator/rebuilder. A dependency-free ARM32 module generator emits the loader, cache, calculator, condition/effect dispatcher, weighted selector wrapper, legacy replay stubs, hooks, symbols, and fixed 0x8000-byte module from reviewed source definitions rather than committing an opaque executable blob.

**Tech Stack:** Python 3.11 standard library, frozen dataclasses and `IntEnum`/`StrEnum`, JSON, `struct`, `zlib.crc32`, deterministic ARM32 word emission, pytest 8.3, Ruff, strict mypy, the existing workspace/patch/rebuild APIs, and the established DeSmuME ARM9 GDB workflow.

## Global Constraints

- Support only profile `b6re_rev0`; every other profile fails closed before writing.
- Use the approved specification `docs/superpowers/specs/2026-08-03-milestone-6c-comeback-gate-design.md` as the source of truth.
- Prototype only global Gate Card ID `19`, Juggernoid.
- Juggernoid values are exactly: flat `60 G`, Q8.8 percentage `20`, Aquos modifier `+30 G`, other attribute modifiers `0`, weights `(50, 30, 30, 30, 30, 30)`, owner-behind rider `+40 G`.
- Attribute order remains `Pyrus, Aquos, Subterra, Haos, Darkus, Ventus`.
- Q8.8 percentage scaling uses compressed battle core G, never persistent roster G and never the post-Gate target total.
- Integer division rounds toward zero; no floating-point operations are allowed.
- Gate bonus arithmetic uses signed 32-bit intermediates, clamps the effective Gate bonus to signed 16-bit, and clamps final target total G to unsigned 16-bit.
- A tied score does not satisfy `OWNER_BEHIND`.
- Team score is participant `+0xEE` plus teammate `+0xEE`, with teammate index from participant `+0xF2`.
- The comeback rider applies only while calculating the Gate-owner combatant; the non-owner never receives it.
- Weighted selection runs only for the normal constructor fallback. Explicit constructor types bypass it, and scripted overrides supersede it.
- A structurally invalid prototype record invalidates all System 2.0 behavior. A live calculation-context failure falls back completely for that combatant. An unexpected weighted-selector failure falls back only for the battle-type phase.
- Gate IDs other than `19` must not alter Gate G, battle type, RNG state, cache history, participant state, save data, or presentation.
- Arena ID remains deferred and must not be read by host logic, emitted ARM code, tests, traces, or runtime evidence.
- Activation limits, fatigue, drawbacks, secondary effects, battle-history penalties, Ability effects, AI evaluation, descriptions, UI, full-roster balance, and save changes remain out of scope.
- Preserve the merged core-G patch and protected overlay-7 offsets `0x23C18-0x23C1C`, `0x23CB0-0x23CF8`, and `0x23D78-0x23D7C`.
- Preserve the original overlay-7 payload, materialize its original `0x640` BSS as zero-backed payload bytes, append exactly `0x8000` module bytes, reserve exactly `0x40` new BSS bytes, and move the arena low boundary to `0x02293C60`.
- Commit no ROM, rebuilt ROM, module binary, raw Gate table, complete game text catalog, save, save state, screenshot, RAM dump, or raw debugger log.
- Generated module and trailer binaries remain local build products. Commit only source definitions, hashes, symbols, normalized observations, and deterministic tests.
- Every write is transactional. Any validation, generation, patch, or rebuild failure leaves the workspace unchanged.
- Exact-ROM tests skip unless user-owned local inputs are supplied.
- Final verification follows `.github/workflows/ci.yml`: complete pytest suite, Python compilation, Ruff on changed Python files, strict mypy on changed package source files, and `git diff --check`.

## File Map

### Create

```text
config/gates/milestone-6c-system2-v1.json
patches/gate-system2-milestone-6c-hooks.json
src/bakugan_ds/workspace/overrides.py
src/bakugan_ds/gates/authoring.py
src/bakugan_ds/gates/system2.py
src/bakugan_ds/gates/runtime_context.py
src/bakugan_ds/gates/arm32.py
src/bakugan_ds/gates/runtime_module.py
src/bakugan_ds/gates/install.py
analysis/gates/milestone-6c-runtime-contract.json
analysis/gates/milestone-6c-build-contract.json
analysis/runtime-observations/gate-system2-milestone-6c-validation.json
docs/gate-card-system-2-prototype.md
docs/superpowers/plans/2026-08-03-milestone-6c-verification.md
tests/unit/test_workspace_overrides.py
tests/unit/test_gate_authoring.py
tests/unit/test_gate_system2.py
tests/unit/test_gate_runtime_context.py
tests/unit/test_gate_arm32.py
tests/unit/test_gate_runtime_module.py
tests/unit/test_gate_install.py
tests/test_gate_milestone_6c_artifacts.py
tests/test_gate_milestone_6c_runtime_evidence.py
tests/integration/test_workspace_overrides_reference.py
tests/integration/test_gate_milestone_6c_reference.py
tests/integration/test_gate_milestone_6c_build.py
```

### Modify

```text
src/bakugan_ds/workspace/model.py
src/bakugan_ds/workspace/extract.py
src/bakugan_ds/workspace/validate.py
src/bakugan_ds/workspace/rebuild.py
src/bakugan_ds/workspace/manifest.py
src/bakugan_ds/gates/record.py
src/bakugan_ds/gates/history.py
src/bakugan_ds/gates/loader.py
src/bakugan_ds/gates/hooks.py
src/bakugan_ds/gates/cli.py
src/bakugan_ds/gates/__init__.py
src/bakugan_ds/cli.py
README.md
```

---

### Task 1: Generic Raw-Payload and Overlay-Layout Overrides

**Files:**
- Create: `src/bakugan_ds/workspace/overrides.py`
- Modify: `src/bakugan_ds/workspace/model.py`
- Modify: `src/bakugan_ds/workspace/extract.py`
- Modify: `src/bakugan_ds/workspace/validate.py`
- Modify: `src/bakugan_ds/workspace/rebuild.py`
- Modify: `src/bakugan_ds/workspace/manifest.py`
- Test: `tests/unit/test_workspace_overrides.py`
- Test: `tests/integration/test_workspace_overrides_reference.py`

**Interfaces:**
- Produces `WorkspaceLayout.modified_raw_nitrofs`.
- Produces `WorkspaceLayout.build_overrides`.
- Produces `RawNitroFsOverride(file_id, path, expected_size, expected_sha256, replacement_size, replacement_sha256)`.
- Produces `OverlayLayoutOverride(overlay_id, expected_ram_size, expected_bss_size, replacement_ram_size, replacement_bss_size, replacement_flags)`.
- Produces `BuildOverrides(format_version, profile_id, raw_nitrofs, overlays)`.
- Produces `load_build_overrides(path) -> BuildOverrides | None`.
- Produces `write_build_overrides(path, overrides) -> None`.
- Later tasks may write one raw override and one overlay override without bypassing normal workspace validation.

- [ ] **Step 1: Write failing layout and override-model tests.**

```python
def test_workspace_layout_exposes_raw_override_directory(tmp_path: Path) -> None:
    layout = WorkspaceLayout.from_root(tmp_path / "work")
    assert layout.modified_raw_nitrofs == tmp_path / "work/modified/raw/nitrofs"
    assert layout.build_overrides == tmp_path / "work/manifests/build-overrides.json"


def test_overlay_override_requires_exact_original_geometry() -> None:
    override = OverlayLayoutOverride(
        overlay_id=7,
        expected_ram_size=0x721A0,
        expected_bss_size=0x640,
        replacement_ram_size=0x7A7E0,
        replacement_bss_size=0x40,
        replacement_flags=0,
    )
    override.validate()
```

- [ ] **Step 2: Run `python -m pytest tests/unit/test_workspace_overrides.py -v`; confirm the new attributes and classes are missing.**

- [ ] **Step 3: Implement strict immutable override models and deterministic JSON I/O.**

```python
@dataclass(frozen=True)
class RawNitroFsOverride:
    file_id: int
    path: str
    expected_size: int
    expected_sha256: str
    replacement_size: int
    replacement_sha256: str

    def validate(self) -> None:
        if self.file_id < 0:
            raise WorkspaceError("raw override file ID must be nonnegative")
        safe_relative_path(self.path)
        if min(self.expected_size, self.replacement_size) < 0:
            raise WorkspaceError("raw override sizes must be nonnegative")
        _require_sha256(self.expected_sha256, "expected raw SHA-256")
        _require_sha256(self.replacement_sha256, "replacement raw SHA-256")
```

`BuildOverrides.validate()` must reject duplicate file IDs, duplicate paths, duplicate overlay IDs, unsupported profiles, unchanged replacements, nonzero overlay compression flags, and any overlay whose replacement RAM plus BSS geometry is inconsistent.

- [ ] **Step 4: Extend extraction to create an empty `modified/raw/nitrofs/` directory and no override manifest.** No original file is copied into that directory.

- [ ] **Step 5: Extend workspace validation.** For each raw override:
  - match file ID and path against the existing manifest;
  - verify `original/raw/nitrofs/<path>` against `expected_size` and `expected_sha256`;
  - verify `modified/raw/nitrofs/<path>` against replacement size/hash;
  - reject a simultaneous decoded NitroFS modification for the same path;
  - reject unmanifested files in `modified/raw/nitrofs/`.

For each overlay override:
  - match the exact original `ram_size` and `bss_size`;
  - allow the modified decoded overlay to match `replacement_ram_size`;
  - require `replacement_bss_size >= 0`;
  - reject any overlay layout change without a declared override.

- [ ] **Step 6: Extend rebuilding.** Raw override payloads bypass LZ10 recompression and enter the FAT exactly as supplied. Overlay overrides update the ARM9 overlay table fields at entry offsets `+0x08` (`ram_size`), `+0x0C` (`bss_size`), and `+0x1C` (`reserved/flags`), and the payload size must equal the replacement RAM size.

```python
def _write_overlay_layout_override(
    output: bytearray,
    table_offset: int,
    table_index: int,
    override: OverlayLayoutOverride,
) -> None:
    base = table_offset + table_index * 32
    struct.pack_into("<I", output, base + 0x08, override.replacement_ram_size)
    struct.pack_into("<I", output, base + 0x0C, override.replacement_bss_size)
    struct.pack_into("<I", output, base + 0x1C, override.replacement_flags << 24)
```

- [ ] **Step 7: Add transactional failure tests.** A stale raw hash, undeclared overlay growth, simultaneous decoded/raw edit, extra override file, or malformed manifest must leave all modified files and prior manifests byte-identical.

- [ ] **Step 8: Add the exact-reference integration test.** With the user-owned workspace, install a synthetic raw suffix and synthetic overlay growth, rebuild, then verify the FNT mapping, FAT count, overlay count, declared overlay geometry, and all unrelated payload hashes.

- [ ] **Step 9: Run focused tests, compileall, Ruff, and strict mypy.**

- [ ] **Step 10: Commit.**

```bash
git add src/bakugan_ds/workspace tests/unit/test_workspace_overrides.py \
  tests/integration/test_workspace_overrides_reference.py
git commit -m "feat: add guarded workspace build overrides"
```

---

### Task 2: Version-1 Authoring Loader and Approved Prototype Roster

**Files:**
- Create: `src/bakugan_ds/gates/authoring.py`
- Create: `config/gates/milestone-6c-system2-v1.json`
- Modify: `src/bakugan_ds/gates/record.py`
- Modify: `src/bakugan_ds/gates/cli.py`
- Test: `tests/unit/test_gate_authoring.py`
- Test: `tests/test_gate_milestone_6c_artifacts.py`

**Interfaces:**
- Produces `load_authoring_document(path) -> tuple[GateRecordV1, ...]`.
- Produces `legacy_passthrough_record(card_id) -> GateRecordV1`.
- Produces `validate_milestone_6c_roster(records) -> None`.
- Produces CLI `bakugan-ds gate build-trailer AUTHORING OUTPUT`.
- Produces the exact 4,152-byte trailer used by the installer.

- [ ] **Step 1: Write failing tests for the exact prototype and 102 passthrough records.**

```python
def test_approved_roster_has_one_live_record() -> None:
    records = load_authoring_document(PROTOTYPE_PATH)
    assert len(records) == 103
    live = [record for record in records if record.archetype != 0]
    assert [record.card_id for record in live] == [19]
    juggernoid = live[0]
    assert juggernoid.flat_bonus_g == 60
    assert juggernoid.percent_q8_8 == 20
    assert juggernoid.attribute_modifiers == (0, 30, 0, 0, 0, 0)
    assert juggernoid.battle_weights == (50, 30, 30, 30, 30, 30)
    assert juggernoid.effect_value == 40
```

- [ ] **Step 2: Run the test and confirm `authoring.py` and the config file are absent.**

- [ ] **Step 3: Implement dependency-free JSON-to-record parsing.** Require `format_version == 1`, 103 sorted records, every schema field, no extra record fields, integer-not-boolean values, and the existing `GateRecordV1.validate()` checks.

- [ ] **Step 4: Add Milestone 6C semantic validation.**

```python
def validate_milestone_6c_roster(records: tuple[GateRecordV1, ...]) -> None:
    for record in records:
        if record.card_id == 19:
            if record != approved_juggernoid_record():
                raise WorkspaceError("Gate 19 does not match the approved prototype")
        elif record != legacy_passthrough_record(record.card_id):
            raise WorkspaceError(
                f"Gate {record.card_id} must remain canonical legacy passthrough"
            )
```

A canonical passthrough must use archetype `0`, zero modifiers/weights/effects/deferred values, `preferred_type=255`, and no nonzero reserved fields.

- [ ] **Step 5: Commit the complete authored JSON.** It is newly authored configuration, not copied original table data.

- [ ] **Step 6: Add `build-trailer`.** The command validates the approved roster, calls `build_trailer()`, writes atomically, and prints size, SHA-256, record count, and payload CRC.

- [ ] **Step 7: Add repeatability tests.** Two invocations from the same source must produce byte-identical trailers; changing any prototype value must change the trailer hash and still fail the Milestone 6C roster validator.

- [ ] **Step 8: Run focused tests and CLI tests.**

- [ ] **Step 9: Commit.**

```bash
git add src/bakugan_ds/gates/authoring.py src/bakugan_ds/gates/record.py \
  src/bakugan_ds/gates/cli.py config/gates/milestone-6c-system2-v1.json \
  tests/unit/test_gate_authoring.py tests/test_gate_milestone_6c_artifacts.py
git commit -m "feat: add approved Gate System 2.0 roster"
```

---

### Task 3: Pure Hybrid-G Calculation and Deterministic Trace

**Files:**
- Create: `src/bakugan_ds/gates/system2.py`
- Test: `tests/unit/test_gate_system2.py`

**Interfaces:**
- Produces `System2Archetype(IntEnum)`.
- Produces `System2Condition(IntEnum)`.
- Produces `System2Effect(IntEnum)`.
- Produces `System2Target(IntEnum)`.
- Produces `System2Timing(IntEnum)`.
- Produces `FallbackScope(StrEnum)` and `FallbackReason(StrEnum)`.
- Produces `GateCalculationContext`.
- Produces `GateCalculationTrace`.
- Produces `GateCalculationResult`.
- Produces `calculate_gate_bonus(record, context) -> GateCalculationResult`.

- [ ] **Step 1: Write the eight approved vector tests and the non-owner control.**

```python
@pytest.mark.parametrize(
    ("core_g", "attribute_id", "behind", "expected"),
    [
        (190, 0, False, 74),
        (190, 1, False, 104),
        (190, 0, True, 114),
        (190, 1, True, 144),
        (525, 0, False, 101),
        (525, 1, False, 131),
        (525, 0, True, 141),
        (525, 1, True, 171),
    ],
)
def test_juggernoid_vectors(
    core_g: int, attribute_id: int, behind: bool, expected: int
) -> None:
    context = calculation_context(
        core_g=core_g,
        attribute_id=attribute_id,
        current_participant=1,
        owner_participant=1,
        owner_score=0 if behind else 1,
        opposing_score=1,
    )
    result = calculate_gate_bonus(approved_juggernoid_record(), context)
    assert result.effective_gate_bonus == expected
    assert result.fallback_scope is FallbackScope.NONE
```

- [ ] **Step 2: Run the tests and confirm the module is absent.**

- [ ] **Step 3: Implement exact fixed-point helpers.**

```python
def trunc_div_toward_zero(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise WorkspaceError("denominator must be positive")
    if numerator >= 0:
        return numerator // denominator
    return -((-numerator) // denominator)


def clamp_i16(value: int) -> int:
    return min(0x7FFF, max(-0x8000, value))


def clamp_u16(value: int) -> int:
    return min(0xFFFF, max(0, value))
```

- [ ] **Step 4: Implement strict record semantics.** Archetype `0` returns `FallbackScope.RECORD` without consuming any System 2.0 value. Archetype `1` accepts only condition `1`, effect `1`, target `1`, timing `0`, zero drawback/secondary/fatigue/activation fields, and card ID `19`.

- [ ] **Step 5: Implement the calculation in this exact order.**
  1. Validate context.
  2. Calculate `scaled_component = trunc_div_toward_zero(core_g * percent_q8_8, 256)`.
  3. Read one signed attribute modifier.
  4. Sum flat, scaled, and attribute components.
  5. Evaluate owner-behind only when `current_participant == owner_participant`.
  6. Add `effect_value` once when true.
  7. Clamp the effective Gate bonus to signed 16-bit.
  8. Clamp `core_g + effective_gate_bonus` to unsigned 16-bit.
  9. Return an ordered immutable trace.

- [ ] **Step 6: Add invalid-context and overflow tests.** Invalid attribute, participant, score, core G, target, enum, or record identity returns a complete calculation fallback and no partial component survives.

- [ ] **Step 7: Add negative Q8.8 rounding and clamp tests even though the approved record is positive.** This proves the version-1 arithmetic contract.

- [ ] **Step 8: Run focused tests, Ruff, and mypy.**

- [ ] **Step 9: Commit.**

```bash
git add src/bakugan_ds/gates/system2.py tests/unit/test_gate_system2.py
git commit -m "feat: implement Gate System 2.0 calculation model"
```

---

### Task 4: Confirmed Participant and Match-State Projection

**Files:**
- Create: `src/bakugan_ds/gates/runtime_context.py`
- Test: `tests/unit/test_gate_runtime_context.py`
- Modify: `src/bakugan_ds/gates/system2.py`

**Interfaces:**
- Consumes confirmed participant/match contracts from `participants.py` and `match_state.py`.
- Produces `ParticipantSnapshot(index, match_score, teammate_index)`.
- Produces `BattleSnapshot(gate_id, gate_owner, team_mode, participants)`.
- Produces `side_score(snapshot, participant_index) -> int`.
- Produces `build_gate_calculation_context(...) -> GateCalculationContext`.

- [ ] **Step 1: Write solo, team, human-owned, AI-owned, tied, behind, invalid-teammate, and combatant-order-independence tests.**

```python
def test_team_owner_score_uses_teammate_index() -> None:
    snapshot = BattleSnapshot(
        gate_id=19,
        gate_owner=1,
        team_mode=True,
        participants=(
            ParticipantSnapshot(0, 1, 1),
            ParticipantSnapshot(1, 0, 0),
            ParticipantSnapshot(2, 1, 3),
            ParticipantSnapshot(3, 1, 2),
        ),
    )
    assert side_score(snapshot, 1) == 1
    assert side_score(snapshot, 2) == 2
```

- [ ] **Step 2: Run the tests and confirm the module is absent.**

- [ ] **Step 3: Implement immutable snapshots with exact participant-index uniqueness and score bounds.** A solo participant ignores the teammate field. Team mode requires a distinct reciprocal teammate with a valid participant index.

- [ ] **Step 4: Implement opponent-side resolution.** For solo, use the only other active participant. For team mode, compare the owner pair against the other pair and reject ambiguous or incomplete pairings.

- [ ] **Step 5: Build calculation context without `arena_id`, difficulty, Ability state, landing state, history, or persistent roster fields.**

- [ ] **Step 6: Add trace-order tests.** Context projection must not depend on whether combatant record 0 or record 1 is evaluated first.

- [ ] **Step 7: Commit.**

```bash
git add src/bakugan_ds/gates/runtime_context.py \
  src/bakugan_ds/gates/system2.py tests/unit/test_gate_runtime_context.py
git commit -m "feat: project confirmed Gate runtime context"
```

---

### Task 5: Weighted Battle-Type Reference Model

**Files:**
- Modify: `src/bakugan_ds/gates/history.py`
- Modify: `src/bakugan_ds/gates/selector.py`
- Test: `tests/unit/test_gate_system2.py`
- Test: `tests/unit/test_gate_runtime_context.py`

**Interfaces:**
- Produces `advance_weighted_lcg(seed) -> int`.
- Produces `weighted_roll_from_state(seed, total) -> tuple[int, int]`.
- Produces `System2BattleTypeResult`.
- Produces `select_system2_battle_type(record, constructor_type, scripted_override, rng_state, legacy_type) -> System2BattleTypeResult`.

- [ ] **Step 1: Write exact deterministic LCG and bucket tests using the confirmed constants.**

```python
def test_confirmed_lcg_transition() -> None:
    next_state = advance_weighted_lcg(0x0000000012345678)
    assert next_state == (
        0x0000000012345678 * 0x5D588B656C078965 + 0x00269EC3
    ) & 0xFFFFFFFFFFFFFFFF
```

- [ ] **Step 2: Write precedence tests.**
  - explicit type `0-5` returns immediately and does not advance RNG;
  - valid normal fallback advances RNG once and selects from six weights;
  - scripted override replaces the provisional result;
  - passthrough record returns the legacy type and does not advance RNG;
  - invalid result uses phase-local legacy fallback.

- [ ] **Step 3: Implement `weighted_roll_from_state` to match the confirmed ARM9 helper.** Use the high 32 bits of the advanced 64-bit state and compute the half-open roll without floating point.

- [ ] **Step 4: Reuse `validate_weight_vector()` and `weighted_index()`.** Do not create a second weight validator.

- [ ] **Step 5: Return the exact trace fields from the approved specification:** explicit argument, validity, six weights, total, weighted result, scripted override, final type, fallback scope, and reason.

- [ ] **Step 6: Run all Gate calculation and selector unit tests.**

- [ ] **Step 7: Commit.**

```bash
git add src/bakugan_ds/gates/history.py src/bakugan_ds/gates/selector.py \
  tests/unit/test_gate_system2.py tests/unit/test_gate_runtime_context.py
git commit -m "feat: model System 2.0 weighted battle selection"
```

---

### Task 6: Dependency-Free ARM32 Emitter

**Files:**
- Create: `src/bakugan_ds/gates/arm32.py`
- Test: `tests/unit/test_gate_arm32.py`

**Interfaces:**
- Produces `Condition(IntEnum)`.
- Produces `Register(IntEnum)`.
- Produces `ArmProgram`.
- Produces `label(name)`, `word(value)`, `align(alignment)`, `literal(name, value)`.
- Produces encoders for `B`, `BL`, `BX`, data processing, multiply, halfword/byte/word load/store, stack push/pop, compare, conditional move, and literal-pool loads.
- Produces `ArmProgram.build(base_address, final_size) -> BuiltArmProgram`.
- `BuiltArmProgram` contains `image`, `symbols`, and `relocations`.

- [ ] **Step 1: Write exact branch-range and encoding tests.**

```python
def test_encode_branch_to_module() -> None:
    instruction = encode_branch(
        source_address=0x0223D258,
        target_address=0x0228BC20,
        link=False,
        condition=Condition.AL,
    )
    assert decode_branch_target(0x0223D258, instruction) == 0x0228BC20
```

- [ ] **Step 2: Write tests for forward/backward branches, condition codes, word alignment, literal range, register lists, and rejection of Thumb addresses or out-of-range displacements.**

- [ ] **Step 3: Implement only the ARMv5TE encodings needed by the approved module.** Do not build a general assembler parser. All APIs take typed operands and emit reviewed 32-bit words.

- [ ] **Step 4: Implement deterministic labels and literal pools.** Duplicate symbols, unresolved labels, relocation overflow, nonzero padding, or image overflow are errors.

- [ ] **Step 5: Require `final_size=0x8000` to zero-pad the generated module and return a stable symbol map sorted by address.**

- [ ] **Step 6: Run exact-word tests on little-endian serialized output.**

- [ ] **Step 7: Commit.**

```bash
git add src/bakugan_ds/gates/arm32.py tests/unit/test_gate_arm32.py
git commit -m "feat: add deterministic ARM32 module emitter"
```

---

### Task 7: Runtime Module ABI, Layout, and Legacy Replay Stubs

**Files:**
- Create: `src/bakugan_ds/gates/runtime_module.py`
- Modify: `src/bakugan_ds/gates/hooks.py`
- Modify: `src/bakugan_ds/gates/loader.py`
- Test: `tests/unit/test_gate_runtime_module.py`
- Create: `analysis/gates/milestone-6c-runtime-contract.json`

**Interfaces:**
- Produces `RuntimeSymbol(name, address, size, purpose)`.
- Produces `RuntimeModule(image, symbols, hook_replacements, sha256)`.
- Produces `build_milestone_6c_module() -> RuntimeModule`.
- Produces symbols:
  - `g2_clear_cache`
  - `g2_validate_cache`
  - `g2_load_selected_record`
  - `g2_legacy_gate_bonus`
  - `g2_calculate_gate_bonus`
  - `g2_gate_bonus_hook`
  - `g2_context_store_hook`
  - `g2_select_battle_type`
  - `g2_selector_hook`
  - `g2_loader_trampoline`
  - `g2_clear_hook`

- [ ] **Step 1: Write a failing module-layout test.**

```python
def test_runtime_module_has_fixed_layout_and_symbols() -> None:
    module = build_milestone_6c_module()
    assert len(module.image) == 0x8000
    assert module.symbols["g2_clear_cache"].address == 0x0228BC20
    assert max(
        symbol.address + symbol.size for symbol in module.symbols.values()
    ) <= 0x02293C20
```

- [ ] **Step 2: Write tests requiring all four approved hook purposes plus loader and clear hooks, non-overlap, protected-range separation, exact return addresses, and zero-only unused module bytes.**

- [ ] **Step 3: Define the ARM ABI in the runtime contract artifact.**
  - wrappers preserve `r4-r11` and `lr` when they use them;
  - original hook live registers remain valid on return;
  - stack stays 8-byte aligned at ARM calls;
  - `r0-r3` are scratch unless the original boundary requires a result;
  - no routine writes outside battle-local records, the 64-byte cache, or its stack frame;
  - legacy replay stubs exactly reproduce displaced instructions and original calls.

- [ ] **Step 4: Implement the symbolized skeleton and legacy replay routines.** At this task boundary every live hook must deliberately route to legacy behavior; no System 2.0 result is enabled yet.

- [ ] **Step 5: Generate hook branch words and compare their source regions against the committed hook hashes before exposing them to the installer.**

- [ ] **Step 6: Add an image disassembly/word audit in tests.** Verify prologues, epilogues, branch targets, literal addresses, and no branch into cache or arena space.

- [ ] **Step 7: Commit.**

```bash
git add src/bakugan_ds/gates/runtime_module.py src/bakugan_ds/gates/hooks.py \
  src/bakugan_ds/gates/loader.py tests/unit/test_gate_runtime_module.py \
  analysis/gates/milestone-6c-runtime-contract.json
git commit -m "feat: define Gate System 2.0 runtime module"
```

---

### Task 8: Live Trailer Loader and Cache Validation Routine

**Files:**
- Modify: `src/bakugan_ds/gates/runtime_module.py`
- Modify: `src/bakugan_ds/gates/loader.py`
- Test: `tests/unit/test_gate_runtime_module.py`
- Test: `tests/integration/test_gate_milestone_6c_reference.py`

**Interfaces:**
- Implements `g2_load_selected_record`.
- Implements `g2_validate_cache`.
- Uses confirmed ARM9 functions:
  - `FS_InitFile 0x0200A7B4`
  - `FS_OpenFileFast 0x0200AA24`
  - `FS_CloseFile 0x0200AADC`
  - `FS_ReadFile 0x0200AC30`
  - `FS_SeekFile 0x0200AC40`
  - ROM archive `0x020BFCB4`.

- [ ] **Step 1: Add routine-contract tests for every failure edge.** Open failure, seek failure, short header read, bad magic/version/geometry/header CRC, invalid card ID, short record read, selected-record mismatch, unsupported prototype semantics, and close failure all leave 64 zero bytes.

- [ ] **Step 2: Emit `g2_clear_cache` as a bounded 16-word zero loop over `0x02293C20-0x02293C60`.**

- [ ] **Step 3: Emit the loader with a local 72-byte `FSFile` and bounded header/record stack storage.** The routine:
  1. clears cache;
  2. initializes the FSFile;
  3. opens file ID `2762`;
  4. seeks to raw offset `2840`;
  5. reads and validates the 32-byte header;
  6. computes selected record offset `32 + (card_id - 1) * 40`;
  7. seeks to `2840 + record_offset`;
  8. reads exactly 40 bytes;
  9. validates card ID and supported semantics;
  10. copies record and metadata into cache;
  11. closes the file on every opened path;
  12. returns cache-valid status in `r0`.

- [ ] **Step 4: Do not recompute the full 4,120-byte payload CRC at battle time.** The installer already validates the complete authored trailer; live code validates header CRC, geometry, selected record identity, and exact supported semantics. Document this bounded runtime policy in the build/runtime contracts.

- [ ] **Step 5: Implement `g2_loader_trampoline`.** Replay `push {r3,lr}`, call the loader only when the selected Gate identity differs from a valid cache entry, then continue original selector function at `0x022433B0`.

- [ ] **Step 6: Implement `g2_clear_hook` at the confirmed post-removal boundary and return to `0x022424B8`.**

- [ ] **Step 7: Add exact ARM word, stack-frame, and address tests.**

- [ ] **Step 8: Add exact-reference hook-byte and module-layout integration tests.**

- [ ] **Step 9: Commit.**

```bash
git add src/bakugan_ds/gates/runtime_module.py src/bakugan_ds/gates/loader.py \
  tests/unit/test_gate_runtime_module.py \
  tests/integration/test_gate_milestone_6c_reference.py
git commit -m "feat: implement Gate System 2.0 runtime loader"
```

---

### Task 9: Live Hybrid-G, Context, Condition, Target, and Effect Dispatcher

**Files:**
- Modify: `src/bakugan_ds/gates/runtime_module.py`
- Modify: `src/bakugan_ds/gates/system2.py`
- Test: `tests/unit/test_gate_runtime_module.py`
- Test: `tests/integration/test_gate_milestone_6c_reference.py`

**Interfaces:**
- Implements `g2_calculate_gate_bonus`.
- Implements `g2_gate_bonus_hook`.
- Implements `g2_context_store_hook`.
- Mirrors the pure Python calculation exactly.

- [ ] **Step 1: Add machine-contract tests for the eight approved vectors using an ARM instruction interpreter fixture over the emitted routine.** The fixture supplies register/memory inputs and checks the returned bonus, target total, and fallback flag.

- [ ] **Step 2: Emit strict cache checks before any System 2.0 arithmetic.** Require valid flag `1`, version `1`, card ID `19`, record card ID `19`, archetype `1`, flags/reserved zero, supported condition/effect/target/timing, all deferred fields zero, and the exact approved values.

- [ ] **Step 3: Emit Q8.8 arithmetic with signed 32-bit multiply and arithmetic division by `256` that rounds toward zero.** Since the approved percentage is positive, runtime still verifies the generic signed policy against host tests.

- [ ] **Step 4: Emit attribute selection.** Attribute IDs outside `0-5` branch to `g2_legacy_gate_bonus`; Aquos index `1` adds `30`, all other approved entries add `0`.

- [ ] **Step 5: Resolve participant and score context from the confirmed structures.** Load Gate owner from battle object `+0x06`, current participant through the combatant/source mapping documented in `ownership-and-participants.json`, score from participant `+0xEE`, teammate from `+0xF2` only in team mode, and team flag from `0x020D433C + 0x98`. Any invalid pointer/index/pairing uses complete legacy calculation.

- [ ] **Step 6: Apply the rider only when current participant equals owner and owner-side score is strictly lower.** Add `40` exactly once.

- [ ] **Step 7: Clamp and store.** Gate bonus is signed-16 bounded before combatant `+0x12`; target total is unsigned-16 bounded before combatant `+0x0E`.

- [ ] **Step 8: Implement `g2_gate_bonus_hook`.** On success, store the calculated Gate bonus and return to `0x0223D278`. On any failure, call `g2_legacy_gate_bonus`, which reproduces attribute load, card-ID load, `0x02065BF4`, multiply-by-10, and store.

- [ ] **Step 9: Implement `g2_context_store_hook`.** Reproduce the original add/store for legacy and successful paths, clamp only the approved System 2.0 result, and return to `0x0223D290`.

- [ ] **Step 10: Add non-owner, tied, team, AI-owner, invalid-context, saturation, and order-independence interpreter tests.**

- [ ] **Step 11: Commit.**

```bash
git add src/bakugan_ds/gates/runtime_module.py src/bakugan_ds/gates/system2.py \
  tests/unit/test_gate_runtime_module.py \
  tests/integration/test_gate_milestone_6c_reference.py
git commit -m "feat: implement Juggernoid comeback calculation"
```

---

### Task 10: Live Weighted Selector and Original Precedence

**Files:**
- Modify: `src/bakugan_ds/gates/runtime_module.py`
- Modify: `src/bakugan_ds/gates/history.py`
- Modify: `src/bakugan_ds/gates/selector.py`
- Test: `tests/unit/test_gate_runtime_module.py`
- Test: `tests/integration/test_gate_milestone_6c_reference.py`

**Interfaces:**
- Implements `g2_select_battle_type`.
- Implements `g2_selector_hook`.
- Calls confirmed weighted helper `0x02021A30`.
- Calls legacy selector `0x022433AC` on phase-local failure.

- [ ] **Step 1: Add interpreter tests that seed the confirmed global LCG and compare emitted-routine results with `select_system2_battle_type()` for multiple known seeds.**

- [ ] **Step 2: Emit the selector wrapper.**
  - validate battle pointer and cache;
  - require Gate ID `19`;
  - pass `r0=6` and `r1=&cache[0x0B]` for the six record weights to `0x02021A30`;
  - accept only result `0-5`;
  - call legacy selector on invalid cache or result;
  - preserve the original caller clobber contract;
  - return the provisional type in `r0`.

- [ ] **Step 3: Preserve explicit constructor precedence by patching only the existing normal-fallback BL at `0x0223E350`.** The explicit constructor branch remains untouched.

- [ ] **Step 4: Preserve scripted override precedence by leaving the switch beginning `0x022417A8` untouched.**

- [ ] **Step 5: Prove unrelated Gates and invalid cache do not call the weighted helper and do not advance the RNG.**

- [ ] **Step 6: Prove this milestone does not update cache history bytes `+0x38-+0x3B`.**

- [ ] **Step 7: Commit.**

```bash
git add src/bakugan_ds/gates/runtime_module.py src/bakugan_ds/gates/history.py \
  src/bakugan_ds/gates/selector.py tests/unit/test_gate_runtime_module.py \
  tests/integration/test_gate_milestone_6c_reference.py
git commit -m "feat: implement weighted Juggernoid battle selection"
```

---

### Task 11: Transactional Installer, Hook Patch Set, and CLI

**Files:**
- Create: `src/bakugan_ds/gates/install.py`
- Create: `patches/gate-system2-milestone-6c-hooks.json`
- Create: `analysis/gates/milestone-6c-build-contract.json`
- Modify: `src/bakugan_ds/gates/cli.py`
- Modify: `src/bakugan_ds/gates/__init__.py`
- Test: `tests/unit/test_gate_install.py`
- Test: `tests/test_gate_milestone_6c_artifacts.py`

**Interfaces:**
- Produces `InstallReport`.
- Produces `install_milestone_6c(workspace, authoring_path) -> InstallReport`.
- Produces CLI `bakugan-ds gate install-milestone-6c WORKSPACE --authoring PATH`.
- Writes:
  - raw carrier override;
  - expanded decoded overlay 7;
  - build override manifest;
  - guarded binary hook replacements;
  - ARM9 arena-low replacement;
  - deterministic install report.

- [ ] **Step 1: Write a failing dry-run/install-report test.**

```python
def test_install_report_declares_all_atomic_changes(reference_workspace: Path) -> None:
    report = install_milestone_6c(reference_workspace, PROTOTYPE_PATH, dry_run=True)
    assert report.profile_id == "b6re_rev0"
    assert report.raw_override.file_id == 2762
    assert report.overlay_override.overlay_id == 7
    assert {patch.patch_id for patch in report.binary_patches} == {
        "gate-system2-loader-hook",
        "gate-system2-bonus-hook",
        "gate-system2-context-hook",
        "gate-system2-selector-hook",
        "gate-system2-clear-hook",
        "gate-system2-arena-low",
    }
```

- [ ] **Step 2: Build the exact hook patch JSON from reviewed generated branch words and exact original bytes.** The committed file contains no module binary.

- [ ] **Step 3: Implement installer staging in a temporary directory.**
  1. validate workspace/profile and readiness artifact;
  2. load approved authoring;
  3. build trailer and module;
  4. append trailer to the exact original raw carrier;
  5. build expanded overlay from exact decoded overlay 7;
  6. construct build overrides;
  7. validate every hook expected byte and the ARM9 arena-low expected instruction;
  8. write all staged products;
  9. atomically replace target files and manifests only after every check passes.

- [ ] **Step 4: Refuse reinstall unless every existing output exactly matches the same generated hashes.** An identical reinstall is a no-op report; a partial or divergent prior install is an error.

- [ ] **Step 5: Add failure-atomicity tests for stale carrier, stale overlay, stale hook, wrong profile, invalid authoring, missing readiness, module overflow, and preexisting divergent overrides.**

- [ ] **Step 6: Add CLI output containing trailer hash, module hash, raw carrier size, overlay size, cache range, and applied patch count.**

- [ ] **Step 7: Commit.**

```bash
git add src/bakugan_ds/gates/install.py src/bakugan_ds/gates/cli.py \
  src/bakugan_ds/gates/__init__.py patches/gate-system2-milestone-6c-hooks.json \
  analysis/gates/milestone-6c-build-contract.json \
  tests/unit/test_gate_install.py tests/test_gate_milestone_6c_artifacts.py
git commit -m "feat: install Milestone 6C Gate System 2.0"
```

---

### Task 12: Exact-ROM Build, Determinism, and Regression Matrix

**Files:**
- Create: `tests/integration/test_gate_milestone_6c_build.py`
- Extend: `tests/integration/test_gate_milestone_6c_reference.py`
- Modify: `docs/superpowers/plans/2026-08-03-milestone-6c-verification.md`

**Interfaces:**
- Consumes the standard extract, installer, validate, and rebuild APIs.
- Produces local rebuilt ROM and normalized build report only when exact user-owned inputs are present.

- [ ] **Step 1: Add the exact-profile end-to-end integration test.**
  1. extract a fresh workspace;
  2. install Milestone 6C;
  3. rebuild;
  4. inspect rebuilt ROM;
  5. verify Gate carrier size `2840 + 4152`;
  6. parse trailer from raw carrier;
  7. verify overlay-7 RAM size `0x7A7E0`, BSS `0x40`, flags `0`;
  8. verify module bytes equal the generated image;
  9. verify cache and arena boundaries;
  10. verify every hook and ARM9 arena-low patch;
  11. verify protected core-G bytes;
  12. verify every unrelated FAT payload byte-identical.

- [ ] **Step 2: Rebuild twice from unchanged installed workspaces.** Require identical ROM SHA-256, build-report JSON, trailer, module, FAT layout, overlay table, and patch report.

- [ ] **Step 3: Add malformed-data build variants.** Corrupt magic, header CRC, selected record ID, prototype enum, record values, and cache metadata in isolated test copies; static runtime-model tests must predict full legacy fallback.

- [ ] **Step 4: Add a legacy Gate regression sample covering confirmed Gates `20` and `22` across all six attributes and fixed battle-type metadata.** No System 2.0 path may alter their original values.

- [ ] **Step 5: Add core-G compatibility assertions against all three protected ranges and the known high/low curve vectors.**

- [ ] **Step 6: Record exact local commands and expected skip behavior in the verification document.**

- [ ] **Step 7: Commit.**

```bash
git add tests/integration/test_gate_milestone_6c_build.py \
  tests/integration/test_gate_milestone_6c_reference.py \
  docs/superpowers/plans/2026-08-03-milestone-6c-verification.md
git commit -m "test: verify Milestone 6C exact ROM build"
```

---

### Task 13: Controlled Runtime Validation

**Files:**
- Create: `analysis/runtime-observations/gate-system2-milestone-6c-validation.json`
- Create: `tests/test_gate_milestone_6c_runtime_evidence.py`
- Modify: `docs/superpowers/plans/2026-08-03-milestone-6c-verification.md`

**Interfaces:**
- Consumes a clean rebuilt ROM, matching battery save, generated symbol map, and DeSmuME ARM9 GDB workflow.
- Produces normalized selected values, addresses, equations, hashes, and scope notes; no raw captures.

- [ ] **Step 1: Define the runtime evidence schema before capture.** Require source/rebuilt hashes, trailer/module hashes, prototype record values, cache lifecycle, calculation cases, weighted cases, override cases, fallback cases, battle completion, post-exit responsiveness, persistent-state controls, and local evidence hashes.

- [ ] **Step 2: Capture a valid Juggernoid cache load.** Confirm record ID `19`, version `1`, valid flag `1`, selected arena entry, and exact cached record bytes.

- [ ] **Step 3: Capture normal hybrid calculations.** At the Gate bonus and post-store boundaries record:
  - non-Aquos normal case;
  - Aquos normal case;
  - both combatants’ participant and owner identities;
  - base, scaled, attribute, conditional, effective, and target values.

- [ ] **Step 4: Capture tied/leading and behind owner controls.** The first must show no rider; the second must show exactly `+40 G`; the non-owner must remain unchanged in both.

- [ ] **Step 5: Capture human-owned and AI-owned Juggernoid.** Require the same formulas and target rules.

- [ ] **Step 6: Capture two deterministic weighted outcomes under known seeded controls.** Confirm the weighted helper is reached once, result is `0-5`, and final dispatch matches. Separately confirm explicit constructor bypass and scripted override supersession.

- [ ] **Step 7: Capture an unrelated Gate.** Confirm original six-byte lookup, multiply-by-10 bonus, fixed metadata type, no weighted RNG call, and no System 2.0 state change.

- [ ] **Step 8: Capture malformed trailer fallback in a separate rebuilt copy.** Confirm complete original Juggernoid Gate bonus and original Scratch selection.

- [ ] **Step 9: Complete and exit the battle.** Confirm all 64 cache bytes clear, the game returns to a responsive surrounding state, and no roster G, inventory, save, or unrelated battle state changes.

- [ ] **Step 10: Normalize and hash evidence.** Commit only selected values and hashes; keep raw logs, saves, screenshots, states, and ROMs ignored.

- [ ] **Step 11: Add tests that reject missing controls, inconsistent equations, wrong prototype values, incomplete fallback, missing exit proof, or unbounded claims.**

- [ ] **Step 12: Commit.**

```bash
git add analysis/runtime-observations/gate-system2-milestone-6c-validation.json \
  tests/test_gate_milestone_6c_runtime_evidence.py \
  docs/superpowers/plans/2026-08-03-milestone-6c-verification.md
git commit -m "test: validate Juggernoid System 2.0 runtime"
```

---

### Task 14: Documentation, Final Verification, and Milestone Handoff

**Files:**
- Create: `docs/gate-card-system-2-prototype.md`
- Modify: `README.md`
- Modify: `docs/gate-card-system-2-roadmap.md`
- Modify: `docs/gate-card-system-2-runtime-context.md`
- Modify: `docs/superpowers/plans/2026-08-03-milestone-6c-verification.md`
- Modify: `tests/test_gate_milestone_6c_artifacts.py`

**Interfaces:**
- Produces the player/developer-facing prototype description.
- Produces final Milestone 6C status with exact branch head and verification results.
- Does not authorize Milestone 6D values or mechanics.

- [ ] **Step 1: Document the exact live formula, values, weights, condition, target, timing, fallback scopes, runtime layout, install/rebuild commands, and rollback procedure.**

- [ ] **Step 2: Update the roadmap.** Mark Milestone 6C complete only after exact-ROM and runtime acceptance pass. Keep Milestone 6D as a separate design boundary for balance framework, archetypes, power budgets, and reusable effects.

- [ ] **Step 3: Add documentation tests requiring all approved exclusions and acceptance evidence.**

- [ ] **Step 4: Run the complete repository suite.**

```bash
python -m pytest -ra
python -m compileall -q src tests
ruff check src tests
mypy src/bakugan_ds
git diff --check
```

- [ ] **Step 5: Run the exact-ROM Gate integration set with local environment variables.**

```bash
BAKUGAN_DS_ROM=/absolute/path/to/Bakugan.nds \
BAKUGAN_DS_WORKSPACE=/absolute/path/to/workspace \
python -m pytest \
  tests/integration/test_workspace_overrides_reference.py \
  tests/integration/test_gate_milestone_6c_reference.py \
  tests/integration/test_gate_milestone_6c_build.py -v
```

- [ ] **Step 6: Re-run the full suite on the exact final branch head after every CI fix.** Record the final commit SHA, test counts, expected skips, rebuilt ROM hash, trailer hash, module hash, and runtime evidence hash in the verification document.

- [ ] **Step 7: Confirm repository boundaries.** No prohibited binary/capture files, no open superseded PRs, no untracked generated module/trailer, and no changed file outside the approved scope.

- [ ] **Step 8: Commit final documentation.**

```bash
git add README.md docs/gate-card-system-2-prototype.md \
  docs/gate-card-system-2-roadmap.md \
  docs/gate-card-system-2-runtime-context.md \
  docs/superpowers/plans/2026-08-03-milestone-6c-verification.md \
  tests/test_gate_milestone_6c_artifacts.py
git commit -m "docs: complete Milestone 6C Gate prototype"
```

- [ ] **Step 9: Open or update the implementation PR, wait for exact-head CI, review the complete diff against the approved specification, and merge only when every acceptance criterion is satisfied.**

## Self-Review Results

- **Spec coverage:** Every approved prototype value, arithmetic rule, score rule, target rule, selector precedence rule, storage/layout boundary, fallback scope, testing requirement, and exclusion maps to at least one task.
- **Architecture dependency:** Generic workspace overrides precede installer and exact-ROM work; pure host behavior precedes emitted ARM behavior; generated module precedes hook installation; static build proof precedes runtime promotion.
- **Placeholder scan:** Every task names concrete files, interfaces, validations, test cases, commands, and commit boundaries.
- **Type consistency:** `GateRecordV1`, `GateCalculationContext`, `GateCalculationResult`, `BuildOverrides`, `RuntimeModule`, and installer/report names are consistent across producer and consumer tasks.
- **Scope check:** The runtime loader, calculator/dispatcher, and selector are separable review gates but combine into one working vertical prototype. No independent later-milestone subsystem is included.
