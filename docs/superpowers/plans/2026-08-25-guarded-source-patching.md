# Guarded ARM Source Patching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile explicitly approved ARMv5TE C/ASM source into a bounded ARM9/ARM7/overlay runtime region, generate guarded ARM/Thumb hooks, and atomically update an extracted Bakugan workspace without bypassing existing profile, compression, or rebuild controls.

**Architecture:** `source_patch.py` owns manifest validation, component/runtime mapping, branch encoding, deterministic external-tool commands, symbol parsing, and transactional workspace mutation. `source_patch_cli.py` exposes the workflow. Overlay files use the existing decoded workspace representation directly. BLZ-compressed ARM images are decoded, patched by runtime address, and deterministically recompressed to the exact original stored size before being written back. The existing `bakugan-ds rebuild` command remains the only ROM builder.

**Tech Stack:** Python 3.11, existing workspace/profile/BLZ modules, `clang --target=arm-none-eabi`, `ld.lld`, a user-selectable `nm`, argparse, pytest.

**Spec:** `docs/superpowers/specs/2026-08-25-nitro-assets-source-patching-design.md`

## Global Constraints

- No source address, code cave, overlay growth, or symbol address is guessed.
- The manifest must name the exact profile, target, runtime placement, byte budget, instruction mode, source paths, and pre-mutation runtime-image SHA-256.
- Hook sites require exact expected bytes.
- Source paths are relative to the manifest directory and path traversal is rejected.
- Subprocesses are argument arrays with `shell=False` semantics.
- Toolchains are never downloaded by the framework.
- C/ASM output must be freestanding and contain no BSS in this first bridge version.
- Output must fit the existing target runtime allocation. Overlay growth is not implicit; an already approved/expanded workspace may be targeted, but this command never invents new overlay geometry.
- ARM9/ARM7 compression must round-trip through the repository's strict BLZ implementation when applicable.
- All writes and reports are transactional.

---

### Task 1: Source-patch manifest and runtime target mapping

**Files:**
- Create: `src/bakugan_ds/source_patch.py`
- Create: `tests/unit/test_source_patch.py`

**Interfaces:**
- Consumes: `WorkspaceManifest`, `WorkspaceLayout`, `RomProfile`, strict BLZ helpers.
- Produces: `SourcePatchManifest`, `SourceTarget`, `load_source_patch_manifest()`, `resolve_source_target()`.

- [ ] **Step 1: Write failing manifest validation tests**

Cover a valid overlay manifest plus failures for wrong format version, unsupported profile, path traversal, duplicate source paths, unsupported target/mode, invalid SHA-256, zero/negative byte budget, unaligned placement, duplicate hook IDs, and malformed expected hook bytes.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/unit/test_source_patch.py -v`

Expected: missing `bakugan_ds.source_patch`.

- [ ] **Step 3: Implement immutable manifest models and strict JSON loader**

Initial manifest shape:

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

Hook mode may be `arm` or `thumb` independently of emitted-code mode, but a hook destination must match the emitted symbol's instruction-state convention: ARM symbols use even addresses; Thumb destinations are emitted with bit 0 cleared in the ELF map and encoded using Thumb branch rules.

- [ ] **Step 4: Implement target resolution**

For overlays, derive runtime base/size from `WorkspaceManifest.overlays` and read `modified/overlays/overlay_NNN.bin`.

For ARM9/ARM7, derive runtime base from `RomProfile.expected`. If the stored component is valid BLZ, derive passthrough geometry from `parse_blz_footer()`, decode it with `decompress_blz()`, and expose the decoded runtime image. If it is not BLZ, use the stored bytes directly.

Reject placement or hooks outside the decoded/runtime image. Reject any `runtime_address + max_size` beyond the existing allocation.

- [ ] **Step 5: Run focused tests and commit**

Commit: `feat: add guarded source patch manifest model`

---

### Task 2: ARM and Thumb hook encoding

**Files:**
- Modify: `src/bakugan_ds/source_patch.py`
- Modify: `tests/unit/test_source_patch.py`

- [ ] **Step 1: Write exact branch-vector tests**

ARM hooks reuse the repository's already-tested ARM branch encoder. Add source-patch byte-level tests for B and BL, forward/backward range, alignment, and out-of-range rejection.

Implement Thumb-1 unconditional B (16-bit, ±2 KiB) and BL (two 16-bit halfwords, ±4 MiB) for ARMv5T. Test exact little-endian bytes, forward/backward targets, halfword alignment, and range boundaries.

- [ ] **Step 2: Implement `encode_hook()`**

Return replacement bytes whose length must exactly equal the hook's `expected` byte length. Fail closed if the selected branch encoding does not fit that guard length.

- [ ] **Step 3: Run focused tests and commit**

Commit: `feat: add guarded ARM and Thumb hooks`

---

### Task 3: Deterministic external ARMv5TE compilation

**Files:**
- Modify: `src/bakugan_ds/source_patch.py`
- Modify: `tests/unit/test_source_patch.py`

**Interfaces:**
- Produces: deterministic tool commands, temporary linker script, emitted image, parsed symbols, source/tool hashes for the report.

- [ ] **Step 1: Write command-construction tests**

Require argument-array commands equivalent to:

```text
clang --target=arm-none-eabi -mcpu=arm946e-s -marm|-mthumb \
  -ffreestanding -fno-builtin -fno-stack-protector \
  -fno-unwind-tables -fno-asynchronous-unwind-tables -c SOURCE -o OBJECT
```

The linker uses `ld.lld --entry=0` and a generated script beginning exactly at the approved runtime placement. It keeps `.text*`, `.rodata*`, and `.data*`, rejects nonzero `.bss`, and discards ARM unwind/comment/note sections. One link emits ELF for symbols; a second deterministic link with `--oformat=binary` emits the flat image.

- [ ] **Step 2: Add definition/symbol-map tests**

Definitions become explicit linker `--defsym=name=0xADDRESS` arguments after validating symbol names and unsigned 32-bit addresses. Parse `nm -n --defined-only` without depending on host architecture support beyond ELF symbol-table reading.

- [ ] **Step 3: Implement subprocess runner**

Tool executable names/paths are supplied by CLI options (`--clang`, `--ld`, `--nm`) with defaults `clang`, `ld.lld`, and `nm`. Missing tools and nonzero exits become `WorkspaceError` with captured diagnostic text. No command uses a shell.

- [ ] **Step 4: Enforce emitted-image constraints**

Reject empty output, output larger than `max_size`, missing hook symbols, symbols outside the emitted region, or linker-produced BSS.

- [ ] **Step 5: Real local compiler smoke check when tools exist**

The mounted environment currently has Clang 17, LLD 17, and GNU `nm`; use a throwaway one-function source to prove ARM ELF + flat binary generation. This smoke result is supporting evidence, not a committed binary fixture.

- [ ] **Step 6: Commit**

Commit: `feat: compile bounded ARMv5TE source patches`

---

### Task 4: Transactional workspace application and BLZ-safe ARM images

**Files:**
- Modify: `src/bakugan_ds/source_patch.py`
- Modify: `tests/unit/test_source_patch.py`

- [ ] **Step 1: Write overlay transaction tests**

Given a synthetic workspace, assert the target runtime SHA must match, the emitted payload is written at the exact placement, hooks are applied only after expected-byte checks, overlapping payload/hook ranges are rejected, and any failure leaves the workspace unchanged.

- [ ] **Step 2: Write compressed ARM transaction tests**

Construct a deterministic BLZ image, patch its decoded runtime bytes, recompress using the original passthrough length and exact stored target size, and assert `decompress_blz()` returns the intended patched runtime image. Reject edits that cannot recompress safely to the existing stored size.

- [ ] **Step 3: Implement atomic application**

Build the full mutated runtime image in memory first, validate every hook and overlap, then encode the stored representation and atomically replace the single target file. No partial writes.

- [ ] **Step 4: Emit deterministic report**

Write `manifests/source-patch-<manifest-stem>.json` only after the target succeeds. Include manifest/profile/target, original and final runtime hashes, stored hashes, placement, emitted size/hash, source hashes, tool commands, symbols used by hooks, hook before/after bytes, and compression/re-encode metadata.

- [ ] **Step 5: Commit**

Commit: `feat: apply source patches transactionally`

---

### Task 5: CLI, documentation, and exact-profile integration

**Files:**
- Create: `src/bakugan_ds/source_patch_cli.py`
- Modify: `src/bakugan_ds/cli.py`
- Create: `tests/unit/test_source_patch_cli.py`
- Create: `docs/source-patching.md`
- Create: `tests/integration/test_source_patch_reference.py`

- [ ] **Step 1: Write failing CLI tests**

Command:

```text
bakugan-ds source-patch build WORKSPACE MANIFEST \
  [--profile PROFILE] [--clang PATH] [--ld PATH] [--nm PATH]
```

Assert dispatch, default profile, tool overrides, and normal domain-error behavior.

- [ ] **Step 2: Wire the CLI**

The command loads the exact profile, validates workspace/profile agreement, compiles, applies, and prints the deterministic report path/hash summary.

- [ ] **Step 3: Add exact B6RE read-only mapping integration**

With `BAKUGAN_DS_ROM` set, extract a temporary exact workspace and assert Overlay 7 runtime mapping and ARM9 BLZ decode/re-encode geometry resolve as expected. The test must not commit game bytes or source-derived binary output.

- [ ] **Step 4: Document workflow and boundaries**

Document example manifest, explicit code-space requirement, ARM/Thumb rules, no-BSS rule, exact-hash guards, compressed ARM handling, and that `bakugan-ds rebuild` remains authoritative.

- [ ] **Step 5: Run full verification**

Run compilation, Ruff, strict mypy, full pytest, and `git diff --check`; run exact-reference integration with the mounted B6RE ROM where possible.

- [ ] **Step 6: Commit**

Commit: `docs: finalize guarded source patch workflow`

---

### Task 6: Final PR review and merge gate

- [ ] Fetch/review the complete PR diff for unsafe path handling, subprocess construction, runtime/ROM address confusion, compression assumptions, transactional behavior, and overclaimed evidence.
- [ ] Fix all important findings and add regressions.
- [ ] Run exact-head CI.
- [ ] Keep PR #47 draft until all checks are green.
- [ ] Mark ready and merge only after the head SHA has passed the complete gate.
