# Standalone NDS Toolkit Consumer Boundary

Bakugan DS consumes reusable Nintendo DS infrastructure from the standalone
[`NDS-Disassembly-Toolkit`](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit)
instead of maintaining independent copies of that infrastructure.

## Dependency policy

`pyproject.toml` pins the toolkit to an exact Git commit. Toolkit upgrades are
intentional repository changes so Bakugan builds do not silently change when
the toolkit advances.

Current Phase 5 pin:

```text
530b58f592b2bca385d9a3e868be0015278b4dc7
```

## Ownership boundary

The standalone toolkit owns reusable Nintendo DS mechanics, including:

- NDS header, FAT, FNT, and overlay parsing;
- LZ10 and BLZ compression support;
- generic ROM inspection, extraction, rebuilding, and validation;
- generic disassembly and ARM/Thumb analysis infrastructure;
- generic source compilation and guarded patch application.

Bakugan DS owns game-specific knowledge and policy, including:

- supported Bakugan ROM profiles and exact-binary fixtures;
- Bakugan addresses, symbols, discoveries, and reverse-engineering evidence;
- Gate-system rules, runtime state, installation policy, and gameplay logic;
- Bakugan-specific patch manifests and authoring data.

## Compatibility strategy

Phase 5 removes duplicated implementations incrementally. Existing
`bakugan_ds` import paths may remain temporarily as thin compatibility modules
that re-export toolkit implementations. This lets game-specific code and tests
continue using stable imports while making the standalone toolkit the source of
truth.

A compatibility module must not add Bakugan policy to a generic toolkit API.
When a generic API is insufficient, improve the standalone toolkit first and
then update the Bakugan consumer pin.

## Migration order

1. Generic errors, NDS structure parsers, and compression primitives.
2. Workspace models, validation, extraction, and rebuild infrastructure.
3. Generic source-patch compilation/application infrastructure.
4. Generic inspection, disassembly, and analysis helpers.
5. Remove compatibility modules once Bakugan code imports the toolkit directly.

Bakugan-specific `gates` implementation remains outside these migration slices.
