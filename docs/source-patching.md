# Guarded ARM Source Patching

The source-patch bridge compiles small, explicitly approved ARMv5TE C/assembly payloads into an existing Bakugan DS runtime allocation and applies guarded branch hooks inside an extracted workspace.

It does **not** discover free space, grow overlays, download a compiler, guess symbols, or build a ROM directly. `bakugan-ds rebuild` remains the authoritative ROM builder.

## Command

```text
bakugan-ds source-patch build WORKSPACE MANIFEST \
  [--profile PROFILE] [--clang PATH] [--ld PATH] [--nm PATH]
```

Defaults:

```text
--profile config/b6re_rev0.json
--clang clang
--ld ld.lld
--nm nm
```

The tools are invoked as argument arrays. No shell is used.

## Manifest

Example:

```json
{
  "format_version": 1,
  "profile_id": "b6re_rev0",
  "target": "overlay:7",
  "runtime_address": 35758080,
  "max_size": 256,
  "mode": "arm",
  "expected_runtime_sha256": "64-character decoded-runtime SHA-256",
  "sources": ["src/injected.c"],
  "definitions": {
    "gate_lookup": 33971252
  },
  "hooks": [
    {
      "id": "call_injected",
      "runtime_address": 35899368,
      "expected": "000000ea",
      "symbol": "injected_entry",
      "link": true,
      "mode": "arm"
    }
  ]
}
```

Source paths are relative to the manifest directory. Absolute paths, path traversal, duplicate paths, and unsupported suffixes are rejected. The first bridge accepts `.c` and `.s` sources.

For the exact B6RE ARM9 target, the manifest must also declare the verified BLZ re-encode geometry explicitly:

```json
"blz_passthrough_length": 32768
```

Bakugan requires that exact value for `profile_id: "b6re_rev0"` with `target: "arm9"`. The generic toolkit supports other passthrough values for other ARM binaries; overlay targets cannot declare a BLZ passthrough override.

## Required evidence

A manifest must identify:

- the exact ROM profile;
- one target: `arm9`, `arm7`, or `overlay:N`;
- an already approved runtime placement;
- the maximum byte budget at that placement;
- ARM or Thumb output mode;
- the SHA-256 of the complete decoded runtime target before mutation;
- every source path;
- every externally known symbol address;
- every hook address, expected bytes, destination symbol, branch type, and hook instruction mode;
- the explicit `blz_passthrough_length` when targeting the exact B6RE ARM9.

The runtime-image SHA guard means a source patch cannot silently apply to a different binary state.

## Runtime addressing

Overlay workspace files are already stored decoded, so overlay runtime addresses map directly through the overlay RAM address recorded in `manifests/workspace.json`.

ARM9 and ARM7 use the RAM bases recorded in the workspace manifest, with the selected ROM profile available as a compatibility fallback for older workspaces. If a stored ARM component is BLZ compressed, the source-patch bridge decodes it before translating runtime addresses. Runtime addresses are never treated as offsets into compressed bytes.

BLZ targets are recompressed to the **exact original stored size** and must pass the toolkit's in-place decoder safety check. The exact B6RE ARM9 uses the already-proven `0x8000` (`32768`) re-encode passthrough geometry from the ARM9 BLZ regression suite; that geometry is now explicit manifest data instead of a hidden Bakugan source-code fallback. It is intentionally different from the reference stream's `0x4000` passthrough because the deterministic encoder otherwise produces too much size slack for the BLZ footer to represent. Other BLZ ARM targets may omit the field to retain their observed passthrough geometry. If the selected geometry cannot produce an exact-size safe stream, the patch fails closed.

## Compilation model

C/assembly is compiled for Nintendo DS ARM9-compatible ARMv5TE:

```text
clang --target=arm-none-eabi -mcpu=arm946e-s -marm|-mthumb \
  -ffreestanding -fno-builtin -fno-stack-protector \
  -fno-unwind-tables -fno-asynchronous-unwind-tables
```

The generated linker script:

- starts exactly at `runtime_address`;
- keeps `.text*`, `.rodata*`, and `.data*`;
- rejects nonzero `.bss`;
- discards unwind/comment/note metadata;
- asserts that the emitted image remains inside `max_size`.

Known game functions or data may be exposed only through explicit `definitions` addresses. These addresses are not inferred by the compiler bridge.

## Hooks

ARM hooks use ARM `B` or `BL` encoding. Thumb hooks support Thumb-1 unconditional `B` and `BL` within their architectural ranges. This first bridge does not synthesize interworking veneers, so every hook's mode must match the emitted source mode.

LLVM/ELF conventionally marks Thumb function symbols by setting bit 0 of the symbol value. The bridge recognizes that ABI state marker and clears bit 0 only when calculating the architectural Thumb branch address; an ARM hook rejects a Thumb-marked symbol.

Before mutation, every hook must satisfy all of the following:

- the hook lies inside the selected runtime component;
- its current bytes exactly equal `expected`;
- its guard length exactly fits the selected branch encoding;
- its destination symbol exists in the compiled ELF;
- the destination symbol resolves inside the emitted source image after instruction-state normalization;
- hook ranges do not overlap each other;
- hooks do not overlap the emitted payload.

All hook guards are checked before any runtime bytes are changed.

## Transaction and report

The complete patched runtime image and stored representation are built in memory first. The target is validated before and again after external compilation, and its stored bytes are compared again immediately before replacement to reject stale concurrent workspace writes. Only after compilation, hash validation, range checks, hook validation, compression validation, and final target revalidation succeed is the target replaced.

The command writes:

```text
WORKSPACE/manifests/source-patch-<manifest-stem>.json
```

The report records:

- profile and target;
- runtime placement;
- compiled size and SHA-256;
- source SHA-256 values;
- normalized compiler/linker/nm commands;
- original and final runtime hashes;
- original and final stored hashes;
- storage encoding, stored size, and BLZ re-encode passthrough length when applicable;
- each hook's address, symbol, destination, expected bytes, and emitted bytes.

If final report publication fails after the target replacement, the implementation restores the original target bytes before surfacing the error.

## Boundaries

This bridge deliberately does not provide automatic code-cave discovery or overlay expansion. A placement is valid only when prior reverse-engineering evidence has established that the range is safe for the intended target build.

The source-patch manifest is therefore an implementation artifact for already proven addresses, not a substitute for static/runtime reverse engineering.

After applying a source patch, rebuild through the normal exact-profile workflow:

```text
bakugan-ds rebuild REFERENCE.nds WORKSPACE output.nds
```
