# Milestone 6B Verification Record

## Result

Milestone 6B complete-system discovery is ready for Milestone 6C.

```text
ready_for_milestone_6c = true
deferred = ["arena_id"]
failures = []
```

The generated report is `analysis/gates/milestone-6c-readiness.json`. It is derived from the requirement manifest and normalized evidence artifacts; it is not hand-authored.

## Runtime scenario coverage

| Scenario | Evidence/result |
|---|---|
| Normal player battle | Gate owner, combatants, compressed core G, Gate contribution, target total, battle-type path, result, capture, removal, and responsive exit confirmed. |
| AI path | Participant-owned AI identity and AI shot-planner path confirmed; difficulty is consumed directly by the AI parameter builder. |
| Tutorial/scripted path | Tutorial setup, forced Gate-slot states, scripted scores, guided throw retry, skip/result path, and responsive story return documented without treating script-seeded state as ordinary lifecycle state. |
| Ability used | Two natural activations consumed the exact selected slot, changed available count `3 -> 2`, reached terminal state 20, and continued normally. |
| Ability unused | Selector returned `0xFF` when no slot was available and activation was bypassed. |
| Score/capture update | Winner score `+0xEE` increments before the separate six-byte capture ledger and `+0xF4` count. Victory threshold is three. |
| Repeated round/Gate transition | Battle-object destruction ends round-local pointer validity; session/participant construction provides authoritative reset; arena transfer and removal are separate. |
| Landing outcomes | Natural result codes 1, 2, and 3 were observed; 1 precedes `GATE CARD WON!`, 2 produced an unopposed Stand, and 3 produced a contested Gate battle. |
| Difficulty controls | Natural Easy `0` and reversible Normal `1` reached the same AI consumer and produced different derived output. Hard remains intentionally unlabelled because locked. |
| Valid trailer | Exact carrier read and CRC-valid `G2DT` parsing populate the 64-byte cache for selected Gate ID 21. |
| Malformed trailer | Missing, truncated, short-read, invalid geometry, and CRC failure paths leave the cache invalid and preserve legacy behavior. |
| Cache lifecycle | Cache remains intact during battle and all 64 bytes clear at battle completion. |

## Commands

```bash
python -m compileall -q src tests tools
python -m pytest -v
BAKUGAN_DS_ROM="$BAKUGAN_DS_ROM" \
BAKUGAN_DS_RUNTIME_ARM9="$BAKUGAN_DS_RUNTIME_ARM9" \
BAKUGAN_DS_OVERLAY1="$BAKUGAN_DS_OVERLAY1" \
BAKUGAN_DS_OVERLAY7="$BAKUGAN_DS_OVERLAY7" \
python -m pytest -m integration -v
bakugan-ds gate readiness \
  --requirements analysis/gates/milestone-6b-requirements.json \
  --evidence-dir analysis/gates \
  --output analysis/gates/milestone-6c-readiness.json
git diff --check main...HEAD
```

## Test results

Task 9 local verification:

```text
373 passed
31 expected environment-gated skips
0 failed
```

The final handoff suite produced 377 passes with 31 expected environment-gated skips. The direct Gate exact-ROM/runtime subset produced 24 passes after correcting three stale graphic evidence hashes. Exact-head GitHub CI is the authoritative compilation, Ruff, strict mypy, full-test, and whitespace record.

## Deterministic rebuild proof

Two rebuilds from the same exact ROM and unchanged workspace produced byte-identical ROMs and byte-identical build reports:

```text
ROM A SHA-256:          7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b
ROM B SHA-256:          7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b
Build report SHA-256:   f95eda0d5a7b3d81e3c9bde6e26797b27f725059289c1454a74b24937283c991
Reported changes:       0
```

The no-change rebuild is byte-identical to the supported input ROM. Loader/layout changes remain separately guarded by exact-overlay Task 11 tests and are not silently introduced by documentation or discovery tooling.

## Binary boundaries

- Exact supported ROM SHA-256: `7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b`.
- Exact decoded overlay-7 SHA-256: `82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1`.
- Exact decoded overlay-1 SHA-256: `65c807a92bce03d6e6d7d053c8c8c6c933d27de02089a39deca231f207cd139a`.
- Original overlay-7 BSS remains `0x640` bytes.
- System 2.0 module reservation and cache do not repurpose original participant, battle, arena, padding, or save bytes.
- No live System 2.0 Gate bonus, condition, field effect, AI behavior change, battle probability change, or roster rebalance is enabled by Milestone 6B.

## Limitations

- `arena_id` remains the sole deferred context field.
- Hard difficulty value `2` is executable-accepted but is not semantically promoted from the locked profile.
- Landing codes `0` and `4` remain numeric rather than receiving unsupported universal labels.
- Runtime instrumentation and reversible controls are evidence only; raw logs, screenshots, saves, states, RAM dumps, ROMs, and extracted copyrighted tables are not committed.
