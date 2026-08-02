# Milestone 6A Gate Card System 2.0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic analysis tooling and evidence that maps the original Gate Card data, activation lifecycle, battle-type selector, usable battle context, expansion-storage options, and safe hook boundaries required by Gate Card System 2.0.

**Architecture:** Add a dependency-free `bakugan_ds.gates` analysis package beside the existing workspace, patching, and static-analysis packages. It consumes extracted workspaces plus local-only runtime images or debugger captures, emits deterministic normalized evidence, and exposes `bakugan-ds gate` analysis commands. Milestone 6A does not implement hybrid Gate calculations, new field effects, altered battle-type probabilities, or a card rebalance.

**Tech Stack:** Python 3.11 standard library, `argparse`, frozen dataclasses and `StrEnum`, JSON/CSV, pytest 8.3, the existing extraction/rebuild/patch APIs, BLZ decompression, and the existing DeSmuME ARM9 GDB workflow.

## Global Constraints

- Support only profile `b6re_rev0`; fail closed for every other profile.
- Preserve the merged core-G curve and protected overlay-7 instruction ranges.
- Future percentage Gate scaling uses compressed battle core G, never persistent roster G.
- Add no runtime dependency. Machine-validated evidence uses deterministic JSON.
- Never assign ROM IDs from the uploaded guide's row order.
- Commit no ROM, rebuilt ROM, executable, complete Gate table, RAM dump, save, save state, screenshot, debugger log, or copied guide table.
- Keep complete exports and raw captures below ignored `work/reports/gates/`.
- Use only `candidate`, `probable`, and `confirmed`; only confirmed fields may enter the Milestone 6B context.
- All generated JSON uses two-space indentation, sorted keys, a final newline, and atomic replacement.
- Exact-ROM tests skip unless their user-owned local inputs are supplied.
- Failed analysis or instrumentation must leave the workspace unchanged.
- Milestone 6A may observe and instrument original behavior but may not implement a System 2.0 gameplay effect.

## File Map

Create `src/bakugan_ds/gates/` with focused modules: `model.py`, `io.py`, `runtime_image.py`, `legacy.py`, `identity.py`, `lifecycle.py`, `selector.py`, `context.py`, `storage.py`, `hooks.py`, and `cli.py`.

Commit normalized evidence under `analysis/gates/`:

- `legacy-table-metadata.json`
- `card-id-evidence.json`
- `activation-lifecycle.json`
- `battle-type-selector.json`
- `battle-context.json`
- `hook-feasibility.json`
- `expansion-strategy.md`

Commit selected symbols to `analysis/symbols/gate_cards.csv` and `analysis/symbols/battle_types.csv`. Complete local tables and captures remain ignored.

---

### Task 1: Evidence Models and Deterministic I/O

**Files:**
- Create: `src/bakugan_ds/gates/__init__.py`
- Create: `src/bakugan_ds/gates/model.py`
- Create: `src/bakugan_ds/gates/io.py`
- Test: `tests/unit/test_gate_model.py`

**Interfaces:**
- `Confidence(StrEnum)`
- `AddressRef(component, runtime_address, component_offset, confidence, evidence)`
- `GateControlCase(card_id, attribute_id, expected_bonus_g, evidence_id)`
- `LegacyGateTableSpec(profile_id, runtime_address, element_width, signed, record_stride, record_count, attribute_order, region_sha256, confidence, control_cases)`
- `load_json_object(path) -> dict[str, object]`
- `write_evidence(path, payload) -> None`

- [ ] Write a failing test that validates six-attribute geometry and rejects a stride unequal to `element_width * 6`.

```python
def test_gate_spec_rejects_wrong_stride() -> None:
    spec = LegacyGateTableSpec(
        "b6re_rev0", 0x020A15AC, 1, False, 5, 2,
        ("pyrus", "aquos", "subterra", "haos", "darkus", "ventus"),
        "a" * 64, Confidence.CONFIRMED, (),
    )
    with pytest.raises(WorkspaceError, match="record stride"):
        spec.validate()
```

- [ ] Run `python -m pytest tests/unit/test_gate_model.py -v`; confirm import failure.
- [ ] Implement immutable dataclasses, strict enum parsing, hash/range/ID validation, and deterministic I/O by reusing `workspace.manifest.write_json_atomic`.
- [ ] Run focused tests and `python -m compileall -q src/bakugan_ds/gates tests/unit/test_gate_model.py`.
- [ ] Commit: `git commit -m "feat: add Gate evidence models"`.

---

### Task 2: Runtime ARM9 and Stored-Image Mapping

**Files:**
- Create: `src/bakugan_ds/gates/runtime_image.py`
- Test: `tests/unit/test_gate_runtime_image.py`
- Modify: `tests/integration/conftest.py`
- Create: `tests/integration/test_gate_system_runtime_inputs.py`

**Interfaces:**
- `RuntimeImage(component, sha256, source_encoding)`
- `RuntimeStoredMapping(runtime_address, runtime_offset, workspace_component, decoded_offset, mapping_kind, decoded_sha256, stored_sha256, directly_patchable)`
- `load_runtime_arm9(path, base_address=0x02000000)`
- `load_workspace_arm9(workspace, base_address=0x02000000)`
- `runtime_slice(image, address, length)`
- `map_runtime_region(runtime_image, workspace_image, address, length)`

- [ ] Write failing address and exact-region tests.

```python
def test_runtime_mapping_requires_exact_same_region(tmp_path: Path) -> None:
    a = tmp_path / "runtime.bin"
    b = tmp_path / "workspace.bin"
    a.write_bytes(b"abcdefgh")
    b.write_bytes(b"abcdefgh")
    mapping = map_runtime_region(load_runtime_arm9(a), load_runtime_arm9(b), 0x02000002, 4)
    assert mapping.runtime_offset == mapping.decoded_offset == 2
```

- [ ] Run `python -m pytest tests/unit/test_gate_runtime_image.py -v`; confirm import failure.
- [ ] Implement bounds-safe `Component` mapping. `load_workspace_arm9()` reads `original/arm9.bin`, uses `is_blz()` and `decompress_blz()` when required, and preserves stored/decoded hashes.
- [ ] Mark a region directly patchable only when the stored image is uncompressed and stored/runtime offsets are identical.
- [ ] Add `reference_runtime_arm9` using `BAKUGAN_DS_RUNTIME_ARM9`; skip when unset and fail when the path is invalid.
- [ ] Add an integration probe asserting that 16 bytes at confirmed helper `0x02065BF4` match between local runtime ARM9 and decoded workspace ARM9.
- [ ] Run unit tests and `python -m pytest tests/integration/test_gate_system_runtime_inputs.py --collect-only -q`.
- [ ] Commit: `git commit -m "feat: map runtime and stored ARM9 images"`.

---

### Task 3: Legacy Gate Table Parser and Metadata

**Files:**
- Create: `src/bakugan_ds/gates/legacy.py`
- Test: `tests/unit/test_gate_legacy.py`
- Test: `tests/integration/test_gate_legacy_reference.py`
- Create after confirmation: `analysis/gates/legacy-table-metadata.json`

**Interfaces:**
- `LegacyGateRecord(card_id, raw_values, bonuses_g)`
- `legacy_spec_from_dict(payload)`
- `parse_legacy_table(image, spec, verify_hash=True)`
- `legacy_metadata(image, spec, mapping)`
- `export_legacy_table(path, records, spec)`

- [ ] Write failing unsigned/signed row and stale-hash tests.

```python
def test_unsigned_rows_scale_to_display_g(tmp_path: Path) -> None:
    path = tmp_path / "runtime.bin"
    path.write_bytes(bytes([10, 8, 12, 9, 7, 11]))
    spec = confirmed_synthetic_spec(address=0x02000000, count=1, sha256=sha256(path))
    record = parse_legacy_table(load_runtime_arm9(path), spec)[0]
    assert record.bonuses_g == (100, 80, 120, 90, 70, 110)
```

- [ ] Run `python -m pytest tests/unit/test_gate_legacy.py -v`; confirm failure.
- [ ] Implement width-aware little-endian parsing, signedness, six-element validation, `* 10` displayed conversion, and exact table-region hash guard.
- [ ] Disassemble complete helper `0x02065BF4`, identify the load width/signedness and card-ID bounds, inspect references to `0x020A15AC`, and prove the end boundary from executable evidence rather than guide length.
- [ ] Map the full table region through `RuntimeStoredMapping`; record mapping kind, decoded offset, stored/decoded hashes, and direct-patch status.
- [ ] Commit metadata only. Write complete rows only to `work/reports/gates/legacy-table.json`.
- [ ] Add an integration test that reconstructs the spec from metadata, verifies the region hash and stored mapping, and checks every committed control case.
- [ ] Run focused and exact-runtime tests.
- [ ] Commit: `git commit -m "feat: confirm legacy Gate table geometry"`.

---

### Task 4: `bakugan-ds gate` Analysis CLI

**Files:**
- Create: `src/bakugan_ds/gates/cli.py`
- Modify: `src/bakugan_ds/cli.py`
- Test: `tests/unit/test_gate_cli.py`
- Modify: `tests/unit/test_cli.py`

**Commands:**

```text
bakugan-ds gate inspect WORKSPACE --runtime-arm9 PATH --metadata PATH
bakugan-ds gate export-legacy WORKSPACE OUTPUT --runtime-arm9 PATH --metadata PATH
bakugan-ds gate report-context WORKSPACE OUTPUT --evidence PATH
```

- [ ] Write a failing nested-command dispatch test.

```python
def test_gate_export_dispatches(monkeypatch, tmp_path) -> None:
    calls = []
    monkeypatch.setattr(cli, "run_gate_command", lambda args: calls.append(args) or 0)
    assert cli.main(["gate", "export-legacy", str(tmp_path / "w"), str(tmp_path / "o.json"),
                     "--runtime-arm9", str(tmp_path / "r.bin"),
                     "--metadata", "analysis/gates/legacy-table-metadata.json"]) == 0
    assert calls[0].gate_command == "export-legacy"
```

- [ ] Run CLI tests; confirm `gate` is initially unknown.
- [ ] Add a top-level `gate` parser, nested subparsers, and `run_gate_command()` dispatch.
- [ ] Validate workspace profile before reading or writing reports.
- [ ] `inspect` prints metadata only. `export-legacy` writes complete local data atomically and refuses tracked repository paths. `report-context` is wired but fails clearly until Task 8 evidence exists.
- [ ] Run CLI tests and `python -m bakugan_ds gate --help`.
- [ ] Commit: `git commit -m "feat: add Gate analysis CLI"`.

---

### Task 5: Card IDs and Attribute Order

**Files:**
- Create: `src/bakugan_ds/gates/identity.py`
- Test: `tests/unit/test_gate_identity.py`
- Create: `analysis/gates/card-id-evidence.json`
- Create: `analysis/symbols/gate_cards.csv`
- Create: `tests/test_gate_system_2_artifacts.py`
- Modify: `tests/integration/test_gate_legacy_reference.py`

**Interfaces:**
- `AttributeIdentity(attribute_id, name, confidence, evidence_id)`
- `GateIdentityMapping(card_id, label, runtime_case, confidence, evidence_id)`
- `normalize_identity_capture(payload)`

- [ ] Write failing normalization and copyright-boundary tests.

```python
def test_identity_capture_keeps_numeric_id_canonical() -> None:
    attributes, mappings = normalize_identity_capture({
        "attributes": [{"attribute_id": 0, "name": "synthetic-pyrus", "confidence": "confirmed", "evidence_id": "attr-1"}],
        "mappings": [{"card_id": 7, "label": "synthetic-card", "runtime_case": "case-1", "confidence": "confirmed", "evidence_id": "card-1"}],
    })
    assert attributes[0].attribute_id == 0
    assert mappings[0].card_id == 7
```

- [ ] Implement strict unique-ID normalization and deterministic JSON/CSV writing.
- [ ] Boot a clean rebuilt ROM, select a visibly identified Gate, break at `0x02065BF4`, and record card ID, attribute ID, raw value, displayed bonus, and resulting total.
- [ ] Repeat across all six attributes and at least three independently identified cards. Guide order is not evidence.
- [ ] Commit only selected confirmed mappings, six confirmed attributes, evidence IDs, and capture hashes. Set `complete_name_table_committed` to `false`.
- [ ] Extend integration tests to compare every committed mapping against parsed table values.
- [ ] Run identity, artifact, and exact-runtime tests.
- [ ] Commit: `git commit -m "docs: confirm Gate IDs and attribute order"`.

---

### Task 6: Gate Activation Lifecycle

**Files:**
- Create: `src/bakugan_ds/gates/lifecycle.py`
- Test: `tests/unit/test_gate_lifecycle.py`
- Create: `analysis/gates/activation-lifecycle.json`
- Create: `docs/gate-card-runtime-lifecycle.md`

**Interfaces:**
- `LifecycleState`: placed, selected, activated, battle_started, resolved, captured, removed, reused, reset.
- `LifecycleTransition(scenario, sequence, from_state, to_state, trigger, address, owner_source, card_id_source, evidence)`
- `normalize_lifecycle_capture(payload)` and `validate_lifecycle(transitions)`

- [ ] Write failing tests for ordering and disconnected transitions within one scenario.
- [ ] Implement unique per-scenario sequence validation, recognized states, evidence requirements, and continuous transition chains.
- [ ] Trace placement/registration, active selection, activation, battle start, result handling, capture/removal/reset, and a reuse path when supported.
- [ ] Trace one AI activation or prove AI shares the same functions. Record tutorial/scripted overrides separately.
- [ ] Commit normalized addresses, component offsets, triggers, owner/card sources, evidence, and confidence—not raw captures.
- [ ] Document normal, AI, and scripted state-transition tables.
- [ ] Add artifact tests requiring a path through `battle_started` and nonempty evidence for every transition.
- [ ] Run unit/artifact tests, compileall, and placeholder scan.
- [ ] Commit: `git commit -m "docs: map Gate activation lifecycle"`.

---

### Task 7: Battle-Type Selector and RNG

**Files:**
- Create: `src/bakugan_ds/gates/selector.py`
- Test: `tests/unit/test_gate_selector.py`
- Create: `analysis/gates/battle-type-selector.json`
- Create: `analysis/symbols/battle_types.csv`

**Interfaces:**
- `BattleTypeEvidence(type_id, label, confidence, evidence)`
- `SelectorInput(name, source, influence, confidence)`
- `BattleTypeSelectorEvidence(selector, rng_calls, random_range, types, inputs, result_storage, forced_paths)`
- `normalize_selector_capture(payload)`

- [ ] Write a failing duplicate-type-ID test.
- [ ] Implement validation for unique IDs, random-range ordering, nonempty evidence, and confidence boundaries.
- [ ] Break where the chosen type is stored/consumed, trace backward to selector and RNG, and record the complete type-ID domain.
- [ ] Compare at least two Gates and two attributes before claiming Gate or Bakugan influence.
- [ ] Record difficulty, arena, AI, and story inputs only when observed.
- [ ] Distinguish the normal selector from forced tutorial/scripted paths.
- [ ] Commit normalized selector evidence and symbol CSV with columns `component,runtime_address,component_offset,name,confidence,evidence`.
- [ ] Run selector and artifact tests.
- [ ] Commit: `git commit -m "docs: confirm battle-type selector"`.

---

### Task 8: Confirmed Battle Context

**Files:**
- Create: `src/bakugan_ds/gates/context.py`
- Test: `tests/unit/test_gate_context.py`
- Create: `analysis/gates/battle-context.json`
- Modify: `src/bakugan_ds/gates/cli.py`
- Modify: `tests/unit/test_gate_cli.py`

**Interfaces:**
- `ContextLifetime`: battle, gate, match, persistent.
- `BattleContextField(name, width_bits, signed, owner_structure, access, lifetime, initialization, reset, safe_for_hook, confidence, evidence)`
- `load_context_fields(path)` and `confirmed_hook_context(fields)`

- [ ] Write a failing test proving only confirmed, safe, initialized, and reset-documented fields enter hook context.
- [ ] Implement unique-name validation, widths `{8,16,32}`, explicit lifetime, evidence, and safe-field filtering.
- [ ] Map in priority order: Gate ID, owner, contestant, combatants, attributes, compressed core G, Gate bonus, match score, Ability usage, Gate reuse, previous battle types, landing/shot condition, arena, difficulty, and human/AI identity.
- [ ] For each field record owner structure, width, signedness, lifetime, initialization, reset, access, confidence, and hook safety.
- [ ] Keep unresolved fields candidate and excluded.
- [ ] Enable `gate report-context` to write confirmed included fields plus excluded fields and reasons.
- [ ] Run context/CLI tests and help smoke.
- [ ] Commit: `git commit -m "feat: define confirmed Gate battle context"`.

---

### Task 9: Expansion Storage Strategy

**Files:**
- Create: `src/bakugan_ds/gates/storage.py`
- Test: `tests/unit/test_gate_storage.py`
- Create: `analysis/gates/expansion-strategy.md`
- Modify: `tests/test_gate_system_2_artifacts.py`

**Interfaces:**
- `StorageCandidate(name, confirmed_requirements, unresolved_requirements, risks, viable)`
- `StorageDecision(primary, fallback, candidates, evidence)`
- `validate_storage_decision(decision)`

- [ ] Write a failing test requiring distinct viable primary and fallback strategies.
- [ ] Require all four candidates: NitroFS, expanded executable/overlay, dedicated overlay, and hybrid.
- [ ] Measure NitroFS loader path, parse timing, heap headroom, and malformed-file behavior.
- [ ] Measure executable/overlay space, decompression mapping, relocations, size, and BSS implications.
- [ ] Measure dedicated-overlay table/load coordination and address conflicts.
- [ ] Measure hybrid cache source, size, lifetime, and reset path.
- [ ] A candidate is not viable while a loading, addressing, memory-safety, or deterministic-rebuild requirement is unresolved.
- [ ] Write `expansion-strategy.md` with confirmed constraints, all four candidates, primary, fallback, and rejected assumptions.
- [ ] Run storage/artifact tests and placeholder scan.
- [ ] Commit: `git commit -m "docs: select Gate System 2 storage strategy"`.

---

### Task 10: Hook Feasibility and Reversible Instrumentation

**Files:**
- Create: `src/bakugan_ds/gates/hooks.py`
- Test: `tests/unit/test_gate_hooks.py`
- Modify: `tests/integration/test_gate_system_runtime_inputs.py`
- Create: `analysis/gates/hook-feasibility.json`

**Interfaces:**
- `HookPurpose`: gate_bonus, battle_type_selector, context_access, expanded_data_lookup.
- `HookSite(purpose, address, instruction_length, expected_bytes_sha256, calling_convention, live_registers, stack_assumptions, overwritten_behavior, return_address, code_space_strategy, core_g_compatible, rollback, confidence, evidence)`
- `load_hook_sites(path)`, `validate_hook_sites(sites)`, and `normalize_hook_capture(payload)`

- [ ] Write failing tests requiring all four purposes, evidence, rollback, valid hashes, and core-G compatibility.
- [ ] Protect these overlay-7 ranges from hook overlap:

```python
CORE_G_PROTECTED_RANGES = (
    range(0x23C18, 0x23C1C),
    range(0x23CB0, 0x23CF8),
    range(0x23D78, 0x23D7C),
)
```

- [ ] Confirm one boundary for Gate bonus replacement/wrapping, selector influence, context access, and expanded-data lookup.
- [ ] For each boundary record component, runtime and relative addresses, instruction length/hash, calling convention, live registers, stack assumptions, overwritten behavior, return, code-space strategy, rollback, and evidence.
- [ ] Use an ARM9 GDB breakpoint/watchpoint at the selected Gate-bonus boundary to log arguments/result and continue without changing registers, stack, memory, or result.
- [ ] Run from a clean rebuilt ROM; verify a known Gate equation, complete or safely exit battle, and return to a responsive state.
- [ ] Commit normalized values and hashes only. No executable bytes or raw logs.
- [ ] Extend integration tests to map every hook into local components, verify expected-byte hashes, and prove protected core-G bytes remain unchanged.
- [ ] Run hook, artifact, and supplied-input integration tests.
- [ ] Commit: `git commit -m "docs: confirm Gate System 2 hook boundaries"`.

---

### Task 11: Full Validation and Milestone 6B Handoff

**Files:**
- Create: `docs/gate-card-legacy-system.md`
- Create: `docs/gate-card-system-2-roadmap.md`
- Modify: `README.md`
- Complete: `tests/test_gate_system_2_artifacts.py`

- [ ] Expand artifact tests to require confirmed legacy geometry, six attributes, lifecycle, normal selector or explicitly documented bypass, at least one safe context field, primary/fallback storage, and unchanged-result instrumentation.
- [ ] Reject committed JSON keys `raw_bytes`, `ram_dump`, `save_state`, `screenshot`, and `complete_gate_table`.
- [ ] Document the legacy formula, table mapping, encoding, count, ID domain, selected mappings, local export command, and copyright boundary.
- [ ] Document milestones 6B–6G and the exact 6B input contract: storage primary/fallback, four hook boundaries, minimal context, legacy fallback for non-prototype Gates, fixed-point arithmetic, clean-ROM battle exit, and core-G exclusions.
- [ ] Update README with bounded `gate inspect` and `gate export-legacy` examples and state that no System 2.0 gameplay effect exists yet.
- [ ] Run:

```bash
python -m pytest -v
BAKUGAN_DS_ROM="$BAKUGAN_DS_ROM" BAKUGAN_DS_RUNTIME_ARM9="$BAKUGAN_DS_RUNTIME_ARM9" \
  python -m pytest -m integration -v
python -m compileall -q src tests tools
python -m ruff check src tests tools
python -m mypy src/bakugan_ds
python - <<'PY'
import json
from pathlib import Path
for path in sorted(Path("analysis/gates").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
PY
! grep -R -nE 'TODO|TBD|FIXME' src/bakugan_ds/gates tests/unit/test_gate_*.py analysis/gates docs/gate-card-*.md
! git ls-files | grep -E '\.(nds|sav|dsv|ds[0-9]|bin)$'
git diff --check
```

- [ ] If ruff or mypy are unavailable, record the limitation without claiming success; pytest and compileall remain mandatory.
- [ ] Repeat clean-runtime validation: confirmed Gate ID, owner/combatants, selector or bypass, unchanged instrumentation result, safe battle exit, responsive story/menu, and intact core-G behavior.
- [ ] Commit: `git commit -m "docs: complete Gate System 2 foundation"`.

## Execution Boundary

Completing this plan does not authorize System 2.0 gameplay implementation. After 6A is reviewed and merged, write a separate Milestone 6B design selecting the concrete data format and exactly one prototype Gate containing:

```text
flat bonus
+ fixed-point percentage of compressed core G
+ one attribute modifier
+ one battle-type weight
+ one bounded condition/effect
```

All non-prototype Gates retain original behavior during Milestone 6B.
