# Milestone 6D Core Balance Framework Verification

## Scope

This document records deterministic host, exact-build, emitted-module, and live-runtime acceptance for Milestone 6D on profile `b6re_rev0`.

Milestone 6D generalizes the deterministic Gate Card System 2.0 calculation framework while keeping **only Gate ID 19, Juggernoid, live**. The remaining 102 records are canonical legacy passthroughs. Full-roster conversion remains Milestone 6E.

## Exact local inputs

```text
Reference ROM SHA-256:
7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b

Reference ROM size:
134217728 bytes

Reference decoded overlay 7 SHA-256:
82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1

Reference runtime-decoded ARM9 SHA-256:
7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e
```

These user-owned inputs remain local and are not committed.

## Deterministic install and rebuild

Two independent exact workspaces produced byte-identical install manifests, authoring output, expanded overlays, patched ARM9 images, manifests, and rebuilt ROMs.

```text
G2DT trailer SHA-256:
c67d3bad47ad318ea782a938fc3412a6244509e96b0d2fb75e3bf8424c9fe72b

Installed carrier size:
6992 bytes

Installed carrier SHA-256:
6961673e91f0ced7afa299d371ba54d73b3e64ab75c79e14224e59c56003b634

Generated module size:
32768 bytes

Generated module SHA-256:
8fa90c244d3710479e94903e099f9dbbe71b5ce8d86c52603383d2e4f42e7a1c

Expanded overlay 7 size:
501728 bytes

Expanded overlay 7 SHA-256:
748574da0d20ceb99b4ea48f848cab62b1139e5c4398f9d95a29adbc6dce5121

Patched stored ARM9 SHA-256:
95494b52cb94c85f7209ddf00fd37b6289fdecd6ad855f7344132b3f840236f8

Rebuilt ROM SHA-256:
519edbd5f4e17db3513cff0451109036ad411b44f1f2fd8f8e635fb68d0ffc7c
```

The rebuilt ROM remains 134,217,728 bytes. The build changes only ARM9, raw NitroFS carrier file ID 2762, and overlay 7. Unrelated FAT payloads remain byte-identical. The protected core-G instruction ranges remain unchanged.

## Runtime-module geometry

```text
Module: 0x0228BC20–0x02293C20
Cache:  0x02293C20–0x02293C60
Arena:  starts at 0x02293C60
```

The generated image remains exactly `0x8000` bytes and contains the generic condition, target, effect, Gate calculation, and battle-selector dispatchers. Six guarded overlay hooks and one guarded decoded-ARM9 arena-boundary replacement are installed transactionally.

## Emitted-module parity

The exact generated ARM32 module was executed in the repository interpreter. The focused module file contains 31 tests covering:

- all supported condition IDs plus unknown-ID rejection;
- all target modes plus unknown-ID rejection;
- signed add/subtract effects, drawbacks, overflow controls, and unknown-ID rejection;
- preserved Milestone 6C Juggernoid vectors;
- generic Control reward and drawback dispatch;
- negative percentage, attribute, and target components;
- confirmed landing-result conditions and missing-context fallback;
- signed total clamping and fixed module geometry.

These are controlled executions of the exact emitted module. They are **not** represented as 31 naturally occurring emulator battles.

## Live DeSmuME acceptance

The same rebuilt ROM ran in the validated DeSmuME 0.9.14 Linux x86_64 GDB bundle.

The live run confirmed:

- title/tutorial navigation and responsive input;
- the Juggernoid Gate Card appearing in the tutorial path;
- the generated 32 KiB module present at `0x0228BC20` with the expected SHA-256;
- an unrelated Gate 21 selected into cache as a valid canonical legacy passthrough;
- tutorial continuation through the supported path;
- return to a responsive surrounding tutorial/arena state;
- all 64 cache bytes zero after completion.

The exact emitted controls, rather than a naturally forced emulator vector, prove Juggernoid arithmetic and weighted-selector compatibility. The Gate 21 no-weighted-RNG claim likewise comes from the exact emitted unrelated-Gate control; the live capture proves that the canonical passthrough record was selected and remained compatible.

A post-exit roster read retained the Serpenoid raw G value `19`, corresponding to displayed `190 G`. No battery-save file was created by this run. Exact interpreter write-set controls confirm that Ability state, activation counters, and history bytes are not modified by Milestone 6D.

## Verified implementation and runtime-evidence head

This is the exact local source head after Task 13 and before the documentation-only Task 14 commit:

```text
88c9424c4303b03af65a5857c1958e8de777ad7f
```

## Verification counts

```text
Host suite:
679 passed, 41 expected environment-gated skips, 0 failed

Focused exact/runtime suite:
44 passed, 0 failed

Python compilation:
passed

Ruff:
unavailable in the local runtime; required in GitHub CI

Strict mypy:
unavailable in the local runtime; required in GitHub CI

Whitespace validation:
passed
```

## Evidence boundary

Committed evidence contains normalized values, commands, contracts, and hashes only. ROMs, rebuilt ROMs, frames, states, battery saves, selected live memory, and debugger output remain local.

This milestone does not convert the complete roster and does not implement Ability manipulation, fatigue, history penalties, AI evaluation, presentation changes, save changes, or arena-dependent conditions.
