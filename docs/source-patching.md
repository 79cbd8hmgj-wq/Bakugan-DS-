# B6RE Source-Patch Addendum

Generic ARMv5TE compilation, manifest validation, runtime addressing, branch encoding, guard checks, rollback, BLZ handling, and reporting are documented by the standalone [NDS Disassembly Toolkit source-patching guide](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit/blob/main/docs/source-patching.md).

This document records only the Bakugan-specific policy and verified B6RE geometry layered on that toolkit bridge.

## Bakugan command

```text
bakugan-ds source-patch build WORKSPACE MANIFEST \
  [--profile PROFILE] [--clang PATH] [--ld PATH] [--nm PATH]
```

Bakugan defaults `--profile` to:

```text
config/b6re_rev0.json
```

The compiler/linker/nm execution and source-patch application are toolkit-owned. Bakugan validates its additional manifest policy before delegation.

## B6RE profile binding

Bakugan source-patch manifests are expected to identify the exact supported workspace/profile rather than operating as generic unbound manifests.

Current profile ID:

```json
"profile_id": "b6re_rev0"
```

The manifest's profile binding, workspace identity, runtime target hash, placement, hook bytes, and symbol addresses together form the fail-closed evidence boundary for a source modification.

## B6RE ARM9 BLZ geometry

For the exact B6RE ARM9 target, Bakugan requires the source-patch manifest to declare:

```json
"blz_passthrough_length": 32768
```

That is `0x8000` bytes.

This is a Bakugan policy rule, not a generic toolkit default. The toolkit supports other validated passthrough lengths for other BLZ ARM targets and can retain observed geometry when no override is supplied.

The B6RE value differs from the reference stream's `0x4000` passthrough because the deterministic re-encoder otherwise produces storage slack that the BLZ footer cannot represent while preserving the exact stored size. The `0x8000` geometry is the proven safe B6RE re-encode configuration used by the regression suite.

Bakugan rejects a `b6re_rev0` ARM9 source-patch manifest that omits this value or declares a different one.

## Placement and hook evidence

The toolkit deliberately does not discover code caves or decide where Bakugan gameplay code may be inserted. Every committed Bakugan source-patch manifest must therefore be backed by game-specific evidence for:

- the exact target component;
- approved runtime placement and byte budget;
- complete decoded-runtime SHA-256 guard;
- known external symbol addresses;
- hook addresses and expected instruction bytes;
- ARM/Thumb mode;
- the semantic reason the placement and hook are valid for B6RE.

Those addresses and hashes belong in Bakugan manifests/evidence, not in the generic toolkit.

## Rebuild boundary

A successful source patch mutates the extracted workspace and writes its report under:

```text
WORKSPACE/manifests/source-patch-<manifest-stem>.json
```

The final ROM must still be produced through Bakugan's strict-profile rebuild path:

```text
bakugan-ds rebuild REFERENCE.nds WORKSPACE output.nds
```

No source-patch command is allowed to weaken Bakugan's exact-ROM rebuild policy.

## Ownership boundary

`bakugan_ds.source_apply`, `bakugan_ds.source_compile`, and `bakugan_ds.source_patch` may preserve compatibility names or B6RE policy adapters, but compilation, target resolution, branch encoding, BLZ storage mechanics, stale-write protection, rollback, and report generation remain toolkit-owned.
