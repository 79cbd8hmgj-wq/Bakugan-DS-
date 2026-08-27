# B6RE Workspace Addendum

Generic workspace extraction, directory roles, manifest semantics, transaction rules, compression representation, and rebuild behavior are documented by the standalone [NDS Disassembly Toolkit workspace guide](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit/blob/main/docs/workspace-and-rebuild.md).

This document records only Bakugan-specific policy/evidence layered on that toolkit workflow.

## Supported workspace profile

Bakugan's canonical supported ROM is profile:

```text
b6re_rev0
```

`bakugan-ds extract` supplies that profile automatically and requires the ROM to match it exactly. Unlike the generic toolkit CLI, Bakugan does not expose an unsupported-ROM escape hatch for extraction.

```bash
bakugan-ds extract "/path/to/Bakugan - Battle Brawlers.nds" work/bakugan
```

Use `--force` only to replace an existing workspace after the complete replacement staging tree has been created successfully.

## B6RE workspace expectations

The resulting directory structure is the generic toolkit workspace layout:

```text
workspace/
├── original/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── raw/{overlays,nitrofs}/
│   └── decoded/{overlays,nitrofs}/
├── modified/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── overlays/
│   └── nitrofs/
└── manifests/{workspace,files,overlays}.json
```

For the supported B6RE ROM this workspace is large (roughly 300 MB) because it intentionally keeps exact stored bytes, decoded references, and editable copies separately.

The workspace manifest records `profile_id: "b6re_rev0"`. Bakugan policy adapters rely on that identity for guarded binary/source patch workflows and reject missing or incompatible profile binding where the game workflow requires it.

## Ownership boundary

Do not add generic extraction, validation, compression, or workspace-format logic here. Those mechanics belong in `NDS-Disassembly-Toolkit`.

Bakugan should contain only B6RE-specific profile requirements, exact-ROM evidence, game-specific overrides, patches, and runtime discoveries that consume the generic workspace.
