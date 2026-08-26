# Nitro Asset Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, read-only NitroFS asset inventory that distinguishes signature-confirmed Nitro formats from extension-only raw formats and validates the exact B6RE asset counts.

**Architecture:** Reuse the existing ROM inspection, FNT/FAT mapping, and strict LZ10 decoder. A focused `assets.py` module performs pure detection/report generation, while `assets_cli.py` owns argparse and output behavior. No workspace or ROM mutation is permitted.

**Tech Stack:** Python 3.11, existing `bakugan_ds` NDS parsers/profile/LZ10 modules, argparse, pytest.

**Spec:** `docs/superpowers/specs/2026-08-25-nitro-assets-source-patching-design.md`

## Global Constraints

- Read-only: no ROM or workspace writes except an explicitly requested JSON report path.
- Exact B6RE profile remains the supported write-grade reference; `--allow-unsupported` is inspection-only.
- Signed formats require decoded magic evidence.
- NTFT/NTFP remain extension-only evidence.
- Malformed LZ10 fails closed.
- Deterministic JSON and ordering are required.
- No upstream source is copied.

---

### Task 1: Asset detection model

**Files:**
- Create: `src/bakugan_ds/assets.py`
- Test: `tests/unit/test_assets.py`

**Interfaces:**
- Consumes: `RomInspection`, ROM bytes, `is_lz10()`, `decompress_lz10()`.
- Produces: `AssetRecord`, `AssetInventory`, `detect_asset()`, `inventory_assets()`.

- [ ] **Step 1: Write failing pure detection tests**

Cover raw `BMD0`, LZ10-wrapped `BTX0`, raw NTFT/NTFP extension evidence, localized `.nsbmd_d` normalization, a signed extension/signature mismatch, and unknown data.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `python -m pytest tests/unit/test_assets.py -v`

Expected: import/module failures because `bakugan_ds.assets` does not exist.

- [ ] **Step 3: Implement the minimal deterministic model**

Create immutable records with these stable fields:

```python
@dataclass(frozen=True)
class AssetRecord:
    file_id: int
    path: str
    raw_size: int
    decoded_size: int
    compression: str
    extension: str
    extension_format: str | None
    detected_format: str | None
    evidence: str
    decoded_magic: str
    extension_signature_match: bool | None
```

`detect_asset()` must decode LZ10 before signature inspection and must never claim NTFT/NTFP signature evidence.

- [ ] **Step 4: Add inventory summary and deterministic JSON tests**

Assert stable counts, record ordering, recognized-only default behavior, and `include_unknown=True` behavior.

- [ ] **Step 5: Run focused tests and commit**

Run: `python -m pytest tests/unit/test_assets.py -v`

Expected: PASS.

Commit: `feat: add Nitro asset detection model`

---

### Task 2: CLI integration

**Files:**
- Create: `src/bakugan_ds/assets_cli.py`
- Modify: `src/bakugan_ds/cli.py`
- Create: `tests/unit/test_assets_cli.py`

**Interfaces:**
- Consumes: `inventory_assets()` and existing `load_profile()` / `inspect_rom()`.
- Produces: `bakugan-ds assets inventory`.

- [ ] **Step 1: Write failing parser/dispatch tests**

Verify the command accepts ROM/profile/output/allow-unsupported/include-unknown and dispatches through `run_assets_command()`.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `python -m pytest tests/unit/test_assets_cli.py -v`

Expected: parser/dispatch failures.

- [ ] **Step 3: Implement CLI wiring**

The command loads the profile, calls `inspect_rom()`, reads the ROM once for payload bytes, builds the inventory, and writes deterministic JSON atomically when `--output` is supplied; otherwise it writes to stdout.

- [ ] **Step 4: Run focused tests and commit**

Run: `python -m pytest tests/unit/test_assets_cli.py tests/unit/test_cli.py -v`

Expected: PASS.

Commit: `feat: add asset inventory CLI`

---

### Task 3: Exact B6RE acceptance fixture and documentation

**Files:**
- Create: `tests/integration/test_asset_inventory_reference.py`
- Create: `docs/nitro-asset-inventory.md`

**Interfaces:**
- Consumes: `BAKUGAN_DS_ROM` environment variable and `inventory_assets()`.
- Produces: exact-ROM regression evidence and user workflow documentation.

- [ ] **Step 1: Write exact-ROM integration test**

The test must skip unless `BAKUGAN_DS_ROM` is set, then require exact profile validation and assert:

```text
named files = 10996
NSBMD = 678
NSBTX = 587
NTFT = 327
NTFP = 982
SDAT = 1
signed mismatches = 0
```

- [ ] **Step 2: Run the reference test against the mounted ROM**

Run: `BAKUGAN_DS_ROM='/mnt/data/Bakugan - Battle Brawlers (USA) (En,Fr).nds' python -m pytest tests/integration/test_asset_inventory_reference.py -v`

Expected: PASS.

- [ ] **Step 3: Document evidence semantics and commands**

Document why BMD0/BTX0/SDAT are signature-confirmed, why NTFT/NTFP are extension evidence, localized suffix normalization, and `--include-unknown`.

- [ ] **Step 4: Run repository verification**

Run: `python -m compileall -q src tests tools`

Run: `python -m ruff check src tests`

Run: `python -m mypy src/bakugan_ds`

Run: `python -m pytest -v`

Run: `git diff --check`

Expected: all checks PASS; environment-gated reference tests may skip when the variable is absent.

- [ ] **Step 5: Commit**

Commit: `test: verify exact Bakugan Nitro asset inventory`
