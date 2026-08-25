# Guarded ARM Source Patching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile explicitly approved ARMv5TE C/ASM source into a bounded ARM9/ARM7/overlay runtime region, generate guarded ARM/Thumb hooks, and atomically update an extracted Bakugan workspace without bypassing existing profile, compression, or rebuild controls.

**Architecture:** `source_patch.py` owns manifest validation, component/runtime mapping, BLZ re-encode geometry selection, and branch encoding. `source_compile.py` owns deterministic external-tool commands, bounded linking, and symbol parsing. `source_apply.py` owns in-memory mutation, exact-size stored encoding, transactional workspace publication, and deterministic reporting. `source_patch_cli.py` exposes the workflow. Overlay files use the existing decoded workspace representation directly. BLZ-compressed ARM images are decoded, patched by runtime address, and deterministically recompressed to the exact original stored size before being written back. The existing `bakugan-ds rebuild` command remains the only ROM builder.

**Tech Stack:** Python 3.11, existing workspace/profile/BLZ modules, `clang --target=arm-none-eabi`, `ld.lld`, a user-selectable `nm`, argparse, pytest.

**Spec:** `docs/superpowers/specs/2026-08-25-nitro-assets-source-patching-design.md`

## Global Constraints

- No source address, code cave, overlay growth, or symbol address is guessed.
- The manifest must name the exact profile, target, runtime placement, byte budget, instruction mode, source paths, and pre-mutation decoded-runtime-image SHA-256.
- Hook sites require exact expected bytes.
- The first bridge does not generate ARM/Thumb interworking veneers; hook mode must match emitted-code mode.
- Source paths are relative to the manifest directory and path traversal is rejected.
- Subprocesses are argument arrays with `shell=False` semantics.
- Toolchains are never downloaded by the framework.
- C/ASM output must be freestanding and contain no BSS in this first bridge version.
- Output must fit the existing target runtime allocation. This command never invents new overlay geometry.
- ARM9/ARM7 compression must round-trip through the repository's strict BLZ implementation when applicable.
- The exact B6RE ARM9 uses the already-proven `0x8000` BLZ re-encode passthrough and exact 448,192-byte stored size; other BLZ targets retain observed geometry unless separate evidence proves another policy.
- All hook guards and overlap checks complete before runtime mutation.
- Target and report publication are transactional, with target rollback if report publication fails.

---

### Task 1: Source-patch manifest and runtime target mapping

**Files:**
- Create: `src/bakugan_ds/source_patch.py`
- Create: `tests/unit/test_source_patch.py`

**Interfaces:**
- Consumes: `WorkspaceManifest`, `WorkspaceLayout`, `RomProfile`, strict BLZ helpers.
- Produces: `SourcePatchManifest`, `SourceTarget`, `load_source_patch_manifest()`, `resolve_source_target()`.

- [x] **Step 1: Write failing manifest validation tests**

Covered valid overlay manifests plus failures for wrong format version, empty/wrong profile contracts, path traversal, duplicate source paths, unsupported target/mode, invalid SHA-256, zero/negative byte budget, unaligned placement, duplicate hook IDs, malformed expected hook bytes, and cross-state hooks without veneers.

- [x] **Step 2: Confirm RED**

The initial RED gate reached the intended missing-module failure after temporary lint-only test ordering was corrected.

- [x] **Step 3: Implement immutable manifest models and strict JSON loader**

Manifest shape:

```json
{
  "format_version": 1,
  "profile_id": "b6re_rev0",
  "target": "overlay:7",
  "runtime_address": 35755072,
  "max_size": 256,
  "mode": "arm",
  "expected_runtime_sha256": "...",
  "sources": ["src/injected.c"],
  "definitions": {"known_helper": 33711604},
  "hooks": [
    {
      "id": "call_injected",
      "runtime_address": 35757000,
      "expected": "000000ea",
      "symbol": "injected_entry",
      "link": true,
      "mode": "arm"
    }
  ]
}
```

Hook mode must match emitted-code mode in this first bridge. Cross-state ARM/Thumb control transfer requires an interworking veneer and therefore fails closed rather than being guessed.

- [x] **Step 4: Implement target resolution**

For overlays, runtime base/size comes from `WorkspaceManifest.overlays` and the decoded `modified/overlays/overlay_NNN.bin`.

For ARM9/ARM7, runtime base comes from `RomProfile.expected`. Valid BLZ storage is decoded before runtime-address translation; raw ARM storage maps directly. The exact B6RE ARM9 selects the existing proven `0x8000` re-encode passthrough geometry while preserving the exact 448,192-byte stored size.

Placement and hook ranges outside the decoded/runtime image are rejected, as are runtime placements whose approved byte budget exceeds the existing allocation.

- [x] **Step 5: Run focused tests and commit**

Implemented across the branch's manifest/runtime-mapping commits with regression coverage.

---

### Task 2: ARM and Thumb hook encoding

**Files:**
- Modify: `src/bakugan_ds/source_patch.py`
- Create: `tests/unit/test_source_patch_hooks.py`

- [x] **Step 1: Write exact branch-vector tests**

ARM hooks reuse the repository's ARM branch encoder. Thumb-1 unconditional B and BL have exact little-endian, forward/backward, alignment, and range-boundary coverage.

- [x] **Step 2: Implement `encode_hook()`**

Replacement bytes must exactly fit the guarded byte length. Out-of-range, unaligned, wrong-size, or cross-state hooks fail closed.

- [x] **Step 3: Run focused tests and commit**

Implemented with exact ARM/Thumb vector regression tests.

---

### Task 3: Deterministic external ARMv5TE compilation

**Files:**
- Create: `src/bakugan_ds/source_compile.py`
- Create: `tests/unit/test_source_patch_compile.py`

**Interfaces:**
- Produces deterministic tool commands, a temporary linker script, emitted image, parsed symbols, source hashes, and normalized command records.

- [x] **Step 1: Write command-construction tests**

Commands are explicit argument arrays equivalent to:

```text
clang --target=arm-none-eabi -mcpu=arm946e-s -marm|-mthumb \
  -ffreestanding -fno-builtin -fno-stack-protector \
  -fno-unwind-tables -fno-asynchronous-unwind-tables -c SOURCE -o OBJECT
```

The linker uses `ld.lld --entry=0` and a generated script beginning exactly at the approved runtime placement. It keeps `.text*`, `.rodata*`, and `.data*`, rejects nonzero `.bss`, discards unwind/comment/note sections, and asserts the byte budget.

- [x] **Step 2: Add definition/symbol-map tests**

Definitions become validated, sorted `--defsym=name=0xADDRESS` arguments. `nm -n --defined-only` output is parsed deterministically and duplicate symbol names fail closed.

- [x] **Step 3: Implement subprocess runner**

Tool executable names/paths are supplied by CLI options (`--clang`, `--ld`, `--nm`) with defaults `clang`, `ld.lld`, and `nm`. Missing tools and nonzero exits become `WorkspaceError`. No command uses a shell and the framework never downloads a toolchain.

- [x] **Step 4: Enforce emitted-image constraints**

Empty output, output larger than `max_size`, missing hook symbols, hook destinations outside the emitted image, and linker-produced BSS are rejected.

- [x] **Step 5: Real local compiler smoke check when tools exist**

A throwaway function was compiled with Clang 17, LLD 17, and GNU `nm`, linked at `0x0221A000`, emitted a 24-byte ARM flat binary, and exposed the expected symbol. No compiled game-derived binary was committed.

- [x] **Step 6: Commit**

Compiler/linker bridge and tests are committed on the feature branch.

---

### Task 4: Transactional workspace application and BLZ-safe ARM images

**Files:**
- Create: `src/bakugan_ds/source_apply.py`
- Create: `tests/unit/test_source_apply.py`

- [x] **Step 1: Write overlay transaction tests**

Synthetic coverage requires the target runtime SHA guard, exact placement, all hook guards before mutation, no payload/hook overlap, no hook-hook overlap, and no missing/out-of-image hook symbols.

- [x] **Step 2: Write compressed ARM transaction tests**

Synthetic BLZ tests cover exact-size successful re-encoding when sufficient representable slack exists and explicit fail-closed behavior when an edit cannot fit the exact stored size. Exact B6RE ARM9 verification uses the repository's proven `0x8000` passthrough geometry rather than assuming the reference stream's `0x4000` passthrough is reproducible by the deterministic encoder.

- [x] **Step 3: Implement atomic application**

The complete mutated runtime image is built in memory, all hooks/overlaps are validated, the stored representation is encoded, then the target and report are published through temporary files. If report publication fails after target replacement, original target bytes are restored.

- [x] **Step 4: Emit deterministic report**

`manifests/source-patch-<manifest-stem>.json` includes profile/target, runtime placement, emitted size/hash, source hashes, normalized tool commands, original/final runtime hashes, original/final stored hashes, storage geometry, and hook before/after data.

- [x] **Step 5: Commit**

Transactional application and report implementation are committed on the feature branch.

---

### Task 5: CLI, documentation, and exact-profile integration

**Files:**
- Create: `src/bakugan_ds/source_patch_cli.py`
- Modify: `src/bakugan_ds/cli.py`
- Create: `tests/unit/test_source_patch_cli.py`
- Create: `docs/source-patching.md`
- Create: `tests/integration/test_source_patch_reference.py`

- [x] **Step 1: Write failing CLI tests**

Command:

```text
bakugan-ds source-patch build WORKSPACE MANIFEST \
  [--profile PROFILE] [--clang PATH] [--ld PATH] [--nm PATH]
```

Dispatch and explicit tool overrides are covered.

- [x] **Step 2: Wire the CLI**

The command loads the exact profile, validates workspace/profile agreement, compiles, applies, and prints the deterministic report path.

- [x] **Step 3: Add exact B6RE read-only mapping integration**

`tests/integration/test_source_patch_reference.py` covers exact Overlay 7 runtime mapping and ARM9 BLZ decode/exact-size re-encode when `BAKUGAN_DS_ROM` is supplied. Independent mounted-ROM verification also confirms the exact B6RE mapping and runtime-safe ARM9 encoding.

- [x] **Step 4: Document workflow and boundaries**

`docs/source-patching.md` documents the manifest, explicit code-space requirement, ARM/Thumb state rule, no-BSS rule, whole-runtime hash guard, exact-size BLZ handling, B6RE ARM9 `0x8000` re-encode geometry, and authoritative rebuild path.

- [x] **Step 5: Run full verification**

The PR gate has reached compileall, Ruff, strict mypy, full pytest, and `git diff --check`. Exact mounted-ROM verification independently exercises the B6RE ARM9/overlay evidence that is environment-gated in hosted CI.

- [x] **Step 6: Commit**

CLI, exact-profile integration, and permanent documentation are committed on the feature branch.

---

### Task 6: Final PR review and merge gate

- [x] Fetch/review the complete PR diff for unsafe path handling, subprocess construction, runtime/ROM address confusion, compression assumptions, transactional behavior, instruction-state transitions, and overclaimed evidence.
- [x] Fix important findings and add regressions, including exact B6RE BLZ geometry, emitted-symbol bounds, and ARM/Thumb interworking rejection.
- [ ] Run exact-head CI after the final documentation synchronization.
- [ ] Confirm fresh exact mounted-ROM evidence against the final contract.
- [ ] Mark PR #47 ready only after the final head SHA has passed the complete gate.
- [ ] Merge and verify `main` CI before declaring completion.
