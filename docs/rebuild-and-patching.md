# B6RE Rebuild and Binary-Patch Addendum

Generic workspace rebuilding and guarded binary patching are owned by the standalone toolkit:

- [Workspace extraction and rebuild](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit/blob/main/docs/workspace-and-rebuild.md)
- [Guarded binary patching](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit/blob/main/docs/binary-patching.md)

This document records the stricter Bakugan/B6RE policy and exact reference evidence.

## Strict rebuild policy

`bakugan-ds rebuild` automatically uses the exact `b6re_rev0` profile. There is no `--allow-unsupported` path for rebuilds.

```bash
bakugan-ds rebuild "/path/to/Bakugan - Battle Brawlers.nds" \
  work/bakugan \
  output/Bakugan-modded.nds
```

A workspace with no edits must rebuild to a byte-identical copy of the supported ROM:

```text
SHA-256: 7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b
```

The build report is written as `<output>.build.json`.

## B6RE changed-overlay evidence

The generic rebuilder stores a changed overlay as its decoded/uncompressed payload unless an explicit validated overlay-layout override supplies replacement metadata.

For B6RE overlay 7, the established reference geometry is:

```text
load address: 0x02219440
RAM payload size: 467360 bytes
```

Without an explicit alternate approved layout, an edited overlay 7 build must therefore retain that decoded payload size and clear compression metadata so the Nintendo DS loader does not attempt BLZ decompression.

Any future overlay expansion or layout replacement must be backed by separate B6RE evidence and an explicit validated override; it is not inferred by the generic rebuilder.

## Bakugan binary-patch policy

Bakugan patch files use the toolkit's guarded fixed-length binary replacement schema, but Bakugan adds two policy requirements before delegating application:

1. the patch set must contain a nonempty `profile_id`;
2. the patch profile must exactly match the workspace manifest profile.

For current committed Bakugan patches that profile is:

```json
"profile_id": "b6re_rev0"
```

A stale expected byte guard, profile mismatch, invalid target, or other patch-domain failure is surfaced through Bakugan's top-level CLI as a write failure rather than being relaxed.

Patch reports remain under:

```text
WORKSPACE/manifests/patch-<patch-file-stem>.json
```

## Ownership boundary

The toolkit owns target resolution, guard validation, fixed-length mutation, reporting, workspace validation, deterministic rebuild, FAT repacking, and compression mechanics.

Bakugan owns the exact B6RE profile, patch documents, expected bytes, rationale, B6RE overlay/layout evidence, and the decision that unsupported ROMs are never accepted for write workflows.
