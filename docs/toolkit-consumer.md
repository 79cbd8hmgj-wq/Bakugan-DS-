# Standalone NDS Toolkit Consumer Boundary

Bakugan DS consumes reusable Nintendo DS infrastructure from the standalone [`NDS-Disassembly-Toolkit`](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit) instead of maintaining independent generic implementations.

## Dependency policy

`pyproject.toml` pins the executable toolkit dependency to an exact Git commit so Bakugan builds do not silently change when toolkit code advances.

Current executable toolkit pin:

```text
f60bb6e1a6eca5a2e4f020419c8718b7029bdcde
```

Toolkit documentation may advance independently of this code pin when no executable behavior changes. The Phase 5H documentation handoff is present on toolkit `main` at/after `c8eae0f1bbb2e9d9c6f2bbe2f6d1949277418d9e`.

## Ownership boundary

The standalone toolkit owns reusable Nintendo DS mechanics, including:

- NDS header, FAT, FNT/NitroFS, and overlay parsing;
- LZ10 and BLZ compression support;
- generic ROM inspection and optional exact-profile validation;
- deterministic workspace extraction, validation, and rebuilding;
- generic disassembly and ARM/Thumb static-analysis infrastructure;
- Nitro asset inventory/classification;
- guarded fixed-length binary patching;
- generic source compilation, branch encoding, guarded source-patch application, rollback, and reporting;
- reusable CLI parser/runner helpers for the operations above.

Bakugan DS owns game-specific knowledge and policy, including:

- the exact B6RE revision-0 ROM profile and reference hash;
- Bakugan addresses, symbols, discoveries, and reverse-engineering evidence;
- strict-by-default B6RE policy for write operations;
- the read-only unsupported-ROM exception exposed only where explicitly intended;
- the B6RE ARM9 `blz_passthrough_length=32768` source-patch rule;
- Bakugan-specific patch/source manifests, placements, expected bytes, and runtime hashes;
- Gate-system rules, runtime state, installation policy, and gameplay logic.

## Compatibility strategy

Several `bakugan_ds` import paths intentionally remain as thin compatibility or policy adapters. They preserve existing Bakugan APIs while delegating Nintendo DS mechanics to the standalone toolkit.

A remaining adapter is valid when it does one of these jobs:

1. preserves a stable Bakugan import/API path while re-exporting toolkit behavior; or
2. enforces a documented Bakugan/B6RE policy before delegating to the toolkit.

It must not contain a second independent implementation of a reusable Nintendo DS subsystem.

Examples of intentional Bakugan policy adapters include:

- rejecting unprofiled Bakugan binary patch sets/workspaces;
- enforcing patch/workspace profile equality;
- requiring the B6RE override profile ID;
- requiring B6RE ARM9 source patches to declare `blz_passthrough_length=32768`;
- requiring profiled inspection before Bakugan asset inventory.

## CLI boundary

Bakugan's top-level CLI registers and dispatches toolkit-owned generic commands, then adds Bakugan-owned command groups such as Gate-system operations.

For ROM commands, Bakugan supplies its B6RE profile and strict support policy. `inspect` may expose an explicit read-only `--allow-unsupported` path; write operations such as `extract` and `rebuild` do not.

The guarded binary `patch` parser/runner is toolkit-owned. Bakugan's profile policy remains enforced by its patch-model/application adapters.

## Documentation boundary

Generic workflow documentation now lives in the standalone toolkit:

- workspace/rebuild;
- disassembly/static analysis;
- Nitro asset inventory;
- guarded binary patching;
- guarded ARM/Thumb source patching.

Bakugan's corresponding documents are B6RE-specific addenda and evidence records rather than copies of the generic toolkit manuals.

Bakugan-specific Gate/runtime/static-analysis documentation remains entirely in this repository.
