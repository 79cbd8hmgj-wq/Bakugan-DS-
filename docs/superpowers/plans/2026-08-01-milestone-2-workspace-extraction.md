# Bakugan DS Milestone 2 Workspace Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic extraction command that validates the supported ROM, writes immutable original data and editable modified data into a structured workspace, decodes all LZ10 NitroFS resources, decodes all BLZ-compressed ARM9 overlays, and records exact hashes and layout metadata in manifests.

**Architecture:** Reuse the Milestone 1 inspection models as the single source of ROM structure. Compression support is isolated in pure functions. Workspace creation writes into a temporary sibling directory and atomically renames it only after every file, hash, manifest, and count validates. Raw ROM payloads remain preserved under `original/raw`, while decoded canonical data is copied into both `original/decoded` and `modified`.

**Tech Stack:** Python 3.11+, standard library only, pytest, existing typed dataclasses and CLI.

## Global Constraints

- Supported ROM identity remains exactly `b6re_rev0`.
- No ROM, extracted game data, workspaces, reports, `.bin`, `.nds`, or `.sav` files may be committed.
- Extraction must fail closed on unsupported ROMs.
- Existing target workspace must not be overwritten unless `--force` is explicitly supplied.
- `original/` must never be modified after successful extraction.
- Every emitted file must have a SHA-256 entry in a deterministic manifest.
- Path traversal, absolute FNT paths, duplicate output paths, and writes outside the workspace must be rejected.
- LZ10 detection is exact: byte `0x10` followed by a three-byte little-endian decompressed size.
- The reference ROM has 11,005 FAT entries, 10,996 FNT-named files, 8,476 LZ10 resources, and 9 BLZ-compressed ARM9 overlays.
- Overlay raw payload IDs are FAT file IDs `0` through `8`.
- Overlay 7 raw size is `255740`; decoded size is `467360`.

---

### Task 1: Workspace Models, Path Safety, and Deterministic Manifests

**Files:**
- Create: `src/bakugan_ds/workspace/__init__.py`
- Create: `src/bakugan_ds/workspace/model.py`
- Create: `src/bakugan_ds/workspace/paths.py`
- Create: `src/bakugan_ds/workspace/manifest.py`
- Create: `tests/unit/test_workspace_model.py`

**Interfaces:**
- `WorkspaceLayout.from_root(root: Path) -> WorkspaceLayout`
- `safe_relative_path(value: str) -> PurePosixPath`
- `sha256_bytes(data: bytes) -> str`
- `write_json_atomic(path: Path, payload: object) -> None`
- Frozen manifest dataclasses: `ExtractedFile`, `ExtractedOverlay`, `WorkspaceManifest`
- `WorkspaceManifest.to_dict() -> dict[str, object]`
- `WorkspaceManifest.to_json() -> str`

- [ ] Write failing tests for rejecting `../`, absolute paths, backslashes, empty components, and duplicate normalized paths.
- [ ] Write failing tests asserting every `WorkspaceLayout` path is rooted under the requested workspace.
- [ ] Write failing tests proving manifest JSON is sorted, stable, newline-terminated, and round-trippable.
- [ ] Implement frozen dataclasses and exact field names used by later tasks:
  - file: `file_id`, `path`, `raw_size`, `decoded_size`, `compression`, `raw_sha256`, `decoded_sha256`
  - overlay: `overlay_id`, `file_id`, `ram_address`, `ram_size`, `bss_size`, `raw_size`, `decoded_size`, `raw_sha256`, `decoded_sha256`, `compression`
  - workspace: `format_version`, `profile_id`, `rom_sha256`, `rom_size`, `arm9_sha256`, `arm7_sha256`, `files`, `overlays`
- [ ] Implement atomic JSON writes using a sibling `.tmp` file and `Path.replace`.
- [ ] Verify unit tests and commit `feat: add deterministic workspace manifests`.

---

### Task 2: Nintendo LZ10 Decoder

**Files:**
- Create: `src/bakugan_ds/compression/__init__.py`
- Create: `src/bakugan_ds/compression/lz10.py`
- Create: `tests/unit/test_lz10.py`

**Interfaces:**
- `is_lz10(data: bytes | bytearray | memoryview) -> bool`
- `lz10_declared_size(data) -> int`
- `decompress_lz10(data) -> bytes`

- [ ] Write failing tests for a literal-only stream, a back-reference stream, overlapping back-reference copies, truncated headers, truncated flag groups, invalid displacement, and declared-size mismatch.
- [ ] Implement strict LZ10 decoding:
  - header byte `0x10`
  - decompressed size in bytes 1–3, little-endian
  - flags consumed MSB-first
  - compressed pair: length `(high_nibble + 3)`, displacement `low_12_bits + 1`
  - stop exactly at declared output size
  - tolerate unused padding bytes after the final token but reject missing input
- [ ] Export APIs from `compression/__init__.py`.
- [ ] Verify unit tests and commit `feat: decode Nintendo LZ10 resources`.

---

### Task 3: Nintendo DS BLZ Overlay Decoder

**Files:**
- Create: `src/bakugan_ds/compression/blz.py`
- Create: `tests/unit/test_blz.py`

**Interfaces:**
- `BlzFooter(compressed_length: int, header_length: int, added_length: int)`
- `parse_blz_footer(data) -> BlzFooter`
- `is_blz(data) -> bool`
- `decompress_blz(data) -> bytes`

- [ ] Write failing tests for footer parsing using the verified overlay 7 trailer `fc e6 03 0b a4 3a 03 00`.
- [ ] Write synthetic backwards-compression fixtures covering literals, references, overlap, invalid header length, compressed length larger than payload, invalid displacement, and truncated control groups.
- [ ] Implement strict backward decoding from the footer:
  - compressed length is the low 24 bits of the first footer word
  - header length is the high byte of that word
  - added length is the final little-endian word
  - final decoded length is `len(data) + added_length`
  - source cursor begins at `len(data) - header_length`
  - destination cursor begins at decoded length
  - flags are consumed MSB-first while moving backward
- [ ] Preserve the uncompressed prefix before the encoded tail.
- [ ] Verify the decoder against all nine exact-ROM overlay payloads in an optional integration test: decoded sizes equal each overlay table `ram_size`.
- [ ] Commit `feat: decode compressed ARM overlays`.

---

### Task 4: Transactional Workspace Extraction Service

**Files:**
- Create: `src/bakugan_ds/workspace/extract.py`
- Create: `tests/unit/test_extract_workspace.py`
- Create: `tests/integration/test_extract_reference_rom.py`

**Interfaces:**
- `ExtractionOptions(workspace: Path, force: bool = False)`
- `extract_workspace(rom_path: Path, profile: RomProfile, options: ExtractionOptions) -> WorkspaceManifest`

**Required layout:**

```text
workspace/
├── original/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── raw/
│   │   ├── overlays/overlay_000.bin ... overlay_008.bin
│   │   └── nitrofs/<FNT path>
│   └── decoded/
│       ├── overlays/overlay_000.bin ... overlay_008.bin
│       └── nitrofs/<FNT path>
├── modified/
│   ├── arm9.bin
│   ├── arm7.bin
│   ├── overlays/overlay_000.bin ... overlay_008.bin
│   └── nitrofs/<FNT path>
└── manifests/
    ├── workspace.json
    ├── files.json
    └── overlays.json
```

- [ ] Write failing tests for existing-target refusal, `--force` replacement, staging-directory cleanup after failure, and path traversal rejection.
- [ ] Write a synthetic-ROM extraction test proving raw bytes, decoded bytes, modified copies, and manifest hashes agree.
- [ ] Implement extraction from a single `inspect_rom(..., require_supported=True)` result.
- [ ] Extract ARM9 and ARM7 directly from header ranges.
- [ ] For each FNT-named FAT entry:
  - write exact payload to `original/raw/nitrofs`
  - if LZ10, decode into `original/decoded/nitrofs`; otherwise copy raw bytes
  - copy canonical decoded bytes into `modified/nitrofs`
- [ ] For each ARM9/ARM7 overlay:
  - write exact FAT payload under `original/raw/overlays`
  - BLZ-decode when footer metadata is valid; otherwise retain raw bytes only when raw size already equals `ram_size`
  - require decoded length to equal overlay `ram_size`
  - write decoded bytes to `original/decoded/overlays` and `modified/overlays`
- [ ] Generate deterministic manifests ordered by file ID and overlay ID.
- [ ] Make `original/` read-only after successful extraction using platform permission bits while documenting that permissions are advisory.
- [ ] Exact-ROM integration assertions:
  - 10,996 file manifest records
  - 8,476 records with `compression == "lz10"`
  - 9 overlay records with `compression == "blz"`
  - overlay 7 decoded size `467360`
  - repeated extraction produces byte-identical manifests
- [ ] Commit `feat: extract deterministic ROM workspaces`.

---

### Task 5: CLI `extract` Command

**Files:**
- Modify: `src/bakugan_ds/cli.py`
- Modify: `README.md`
- Create: `tests/unit/test_extract_cli.py`

**Command:**

```bash
bakugan-ds extract ROM WORKSPACE [--profile PATH] [--force]
```

- [ ] Write failing tests for argument parsing, success output, existing-workspace exit behavior, and filesystem errors.
- [ ] Add `extract` without changing `inspect` behavior or exit codes.
- [ ] Print one concise success line containing workspace path, file count, overlay count, and manifest path.
- [ ] Use the same unsupported-ROM, malformed-ROM, and filesystem exit-code mapping as `inspect`.
- [ ] Document workspace size expectations and the exact directory layout in README.
- [ ] Commit `feat: add workspace extraction CLI`.

---

### Task 6: Reference-ROM Verification and Analysis Handoff

**Files:**
- Create: `docs/workspace-format.md`
- Create: `docs/overlay-analysis-handoff.md`
- Modify: `analysis/overlays.yaml`
- Modify: `tests/integration/test_extract_reference_rom.py`

- [ ] Run extraction twice into separate temporary directories and compare every manifest hash.
- [ ] Verify raw overlay hashes match FAT payload hashes from direct ROM slicing.
- [ ] Verify every decoded overlay size equals declared `ram_size`.
- [ ] Record overlay 7 analysis handoff:
  - raw source file: `original/raw/overlays/overlay_007.bin`
  - decoded analysis file: `original/decoded/overlays/overlay_007.bin`
  - load address: `0x02219440`
  - decoded size: `467360`
  - BSS begins at `0x0228B5E0` and spans `1600` bytes
  - component-relative offsets are computed from `0x02219440`
- [ ] Document that overlapping overlay addresses require separate disassembler programs or overlay-specific memory maps.
- [ ] Run full pytest suite with `BAKUGAN_DS_ROM` set, Python compileall, `git diff --check`, and tracked-binary hygiene checks.
- [ ] Commit `docs: define extracted workspace and overlay handoff`.

---

## Final Milestone 2 Verification

```bash
BAKUGAN_DS_ROM="/absolute/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds" python -m pytest -v
python -m compileall -q src tests
git diff --check
git ls-files | grep -E '\.(nds|sav|bin)$' && exit 1 || true
rm -rf /tmp/bakugan-work-a /tmp/bakugan-work-b
bakugan-ds extract "$BAKUGAN_DS_ROM" /tmp/bakugan-work-a
bakugan-ds extract "$BAKUGAN_DS_ROM" /tmp/bakugan-work-b
cmp /tmp/bakugan-work-a/manifests/workspace.json /tmp/bakugan-work-b/manifests/workspace.json
cmp /tmp/bakugan-work-a/manifests/files.json /tmp/bakugan-work-b/manifests/files.json
cmp /tmp/bakugan-work-a/manifests/overlays.json /tmp/bakugan-work-b/manifests/overlays.json
```

Expected results:

- all tests pass;
- no copyrighted binary is tracked;
- both extraction runs produce identical manifests;
- workspace contains 10,996 canonical NitroFS files and 9 decoded overlays;
- overlay 7 is ready for static analysis at runtime address `0x02219440`.
