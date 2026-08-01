# Bakugan DS Milestone 3 Rebuild and Guarded Patching Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development. Implement each task test-first and verify against the exact `B6RE` ROM.

**Goal:** Rebuild a valid Nintendo DS ROM from a Milestone 2 workspace, preserve exact bytes for a no-change build, safely repack changed FAT payloads, restore LZ10 compression for changed resources, support uncompressed changed overlays, and apply source-controlled guarded binary patches.

**Architecture:** The original ROM remains the source for all non-workspace regions. A workspace validator verifies the ROM identity, manifests, immutable original hashes, decoded reference hashes, and modified inputs. If nothing changed, the source ROM is copied exactly. If changes exist, payloads are rebuilt deterministically, all FAT-backed files are repacked in original physical order on 0x200-byte boundaries, FAT ranges are updated, and changed overlay compression flags are cleared when the decoded overlay is stored uncompressed.

**Tech Stack:** Python 3.11+, standard library, existing NDS parsers and workspace models, pytest.

## Global Constraints

- Only the exact `b6re_rev0` ROM may be rebuilt.
- No ROM or extracted binary may be committed.
- Rebuild writes to a temporary sibling and atomically installs the final output.
- A no-change rebuild must be byte-identical to the source ROM.
- Original workspace files and hashes must be validated before any build.
- ARM9 and ARM7 replacements must remain exactly their declared sizes.
- Changed LZ10 resources are deterministically recompressed; unchanged resources reuse exact original raw bytes.
- Changed overlays must remain exactly `ram_size` bytes and are stored uncompressed with overlay flags and compressed-size metadata cleared.
- Every guarded binary replacement must verify expected bytes before writing.
- FAT payloads are repacked in original physical order and aligned to 0x200 bytes.
- Output must remain within the original 128 MB ROM capacity.

---

### Task 1: LZ10 Encoder

**Files:**
- Modify: `src/bakugan_ds/compression/lz10.py`
- Modify: `src/bakugan_ds/compression/__init__.py`
- Create: `tests/unit/test_lz10_compress.py`

- [ ] Write tests for empty-input rejection, literal-only encoding, deterministic output, boundary flag groups, and round-trip decoding.
- [ ] Implement `compress_lz10(data: bytes) -> bytes` using deterministic literal groups.
- [ ] Require decompressed length to fit the 24-bit LZ10 header.
- [ ] Commit `feat: encode deterministic LZ10 resources`.

### Task 2: Workspace Loading and Integrity Validation

**Files:**
- Modify: `src/bakugan_ds/workspace/manifest.py`
- Create: `src/bakugan_ds/workspace/validate.py`
- Modify: `src/bakugan_ds/workspace/__init__.py`
- Create: `tests/unit/test_workspace_validate.py`

- [ ] Load `workspace.json` into typed manifest models with strict format-version and field validation.
- [ ] Verify source ROM SHA-256 and size.
- [ ] Verify ARM9, ARM7, every original raw file, every original decoded file, and every original overlay against manifest hashes.
- [ ] Verify all modified files exist and classify changed components by decoded SHA-256.
- [ ] Reject missing, extra mapping, unsafe path, tampered original, and incorrect source-ROM inputs.
- [ ] Commit `feat: validate extracted workspaces for rebuilding`.

### Task 3: Deterministic Rebuild Service

**Files:**
- Create: `src/bakugan_ds/workspace/rebuild.py`
- Create: `tests/unit/test_rebuild.py`

**Interfaces:**
- `RebuildOptions(output: Path, force: bool = False)`
- `BuildChange`
- `BuildReport`
- `rebuild_rom(source_rom, profile, workspace, options) -> BuildReport`

- [ ] Write synthetic tests proving an unchanged workspace yields an exact source copy.
- [ ] Write tests for changed plain files, changed LZ10 files, changed overlays, ARM9 edits, size violations, output refusal, staging cleanup, and ROM-capacity overflow.
- [ ] Reuse original raw bytes for unchanged payloads.
- [ ] LZ10-compress changed resources originally marked `lz10`.
- [ ] Store changed overlays uncompressed and clear the overlay table reserved word.
- [ ] Repack every FAT payload in original physical order starting at the original first named-file data address, aligned to `0x200`.
- [ ] Update every FAT start/end pair and changed overlay metadata.
- [ ] Keep the original ROM size and preserve all non-payload regions.
- [ ] Reparse the output before atomic installation and emit a deterministic JSON build report.
- [ ] Commit `feat: rebuild deterministic Nintendo DS ROMs`.

### Task 4: Guarded Patch Model

**Files:**
- Create: `src/bakugan_ds/patches/__init__.py`
- Create: `src/bakugan_ds/patches/model.py`
- Create: `src/bakugan_ds/patches/apply.py`
- Create: `tests/unit/test_patches.py`

**Patch schema:**

```json
{
  "format_version": 1,
  "profile_id": "b6re_rev0",
  "patches": [
    {
      "id": "example",
      "type": "binary_replace",
      "target": "overlay:7",
      "offset": 4096,
      "expected": "00112233",
      "replacement": "44556677",
      "rationale": "Documented behavior change"
    }
  ]
}
```

- [ ] Support targets `arm9`, `arm7`, `overlay:<id>`, and `nitrofs:<path>`.
- [ ] Reject unknown targets, unsafe paths, duplicate patch IDs, malformed hex, unequal lengths, out-of-bounds writes, profile mismatch, and stale expected bytes.
- [ ] Apply all replacements in memory first; write atomically only after every guard succeeds.
- [ ] Emit an application report with before/after component hashes.
- [ ] Commit `feat: apply guarded binary patches`.

### Task 5: CLI Commands and Documentation

**Files:**
- Modify: `src/bakugan_ds/cli.py`
- Modify: `README.md`
- Create: `docs/rebuild-and-patching.md`
- Create: `tests/unit/test_rebuild_cli.py`
- Create: `tests/unit/test_patch_cli.py`

**Commands:**

```bash
bakugan-ds rebuild ROM WORKSPACE OUTPUT [--profile PATH] [--force]
bakugan-ds patch WORKSPACE PATCH.json
```

- [ ] Preserve existing `inspect` and `extract` behavior.
- [ ] Print concise success summaries with changed count, output hash, and report path.
- [ ] Document exact-copy no-change behavior, changed-build repacking, overlay uncompressed fallback, and patch guard semantics.
- [ ] Commit `feat: add rebuild and patch CLI commands`.

### Task 6: Exact-ROM Integration Verification

**Files:**
- Create: `tests/integration/test_rebuild_reference_rom.py`
- Modify: `analysis/overlays.yaml` only if newly verified metadata requires it.

- [ ] Extract the exact ROM and rebuild without modifications.
- [ ] Assert output bytes and SHA-256 exactly equal the source ROM.
- [ ] Modify one LZ10-decoded NitroFS resource, rebuild, re-extract, and assert the decoded modification survives.
- [ ] Modify one byte in overlay 7, rebuild, assert its FAT range is `467360` bytes, overlay flags are `0`, and re-extraction returns the modified decoded overlay.
- [ ] Verify rebuilt ROM structure, counts, file mappings, and all unchanged decoded hashes.
- [ ] Run full tests, Python compilation, Git whitespace check, and tracked-binary hygiene check.
- [ ] Commit `test: verify exact and modified ROM rebuilds`.

---

## Final Verification

```bash
BAKUGAN_DS_ROM="/absolute/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds" python -m pytest -v
python -m compileall -q src tests
git diff --check
git ls-files | grep -E '\.(nds|sav|bin)$' && exit 1 || true

rm -rf /tmp/bakugan-m3-work /tmp/bakugan-m3-output.nds
bakugan-ds extract "$BAKUGAN_DS_ROM" /tmp/bakugan-m3-work
bakugan-ds rebuild "$BAKUGAN_DS_ROM" /tmp/bakugan-m3-work /tmp/bakugan-m3-output.nds
cmp "$BAKUGAN_DS_ROM" /tmp/bakugan-m3-output.nds
```

Expected: the complete suite passes, the no-change ROM is byte-identical, guarded patches fail closed on stale bytes, modified overlays rebuild uncompressed with corrected metadata, and no copyrighted binary is tracked.
