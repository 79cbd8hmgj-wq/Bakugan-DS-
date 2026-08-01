# Bakugan DS Milestone 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested Python command-line foundation that validates the supported Bakugan DS ROM, parses its Nintendo DS header, FAT, FNT, and ARM9 overlay table, and emits deterministic inspection reports.

**Architecture:** A small typed Python package will separate immutable ROM-profile validation from Nintendo DS structure parsing. Each parser consumes bytes plus explicit offsets and returns frozen dataclasses. The CLI will compose those parsers into a single inspection report while local-ROM integration tests remain optional and never commit copyrighted data.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `dataclasses`, `hashlib`, `json`, `pathlib`, `struct`), `pytest`, `ruff`, `mypy`.

## Global Constraints

- Initial supported ROM: `Bakugan: Battle Brawlers`, USA revision 0.
- Internal title: `BAKUGAN W`.
- Game code: `B6RE`.
- Maker code: `52`.
- Revision: `0`.
- ROM size: `134217728` bytes.
- SHA-256: `7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b`.
- The repository must not contain the ROM, extracted copyrighted assets, or rebuilt ROM images.
- Inspection-only parsing may report unsupported ROMs, but any future write path must fail closed on profile mismatch.
- All offsets and lengths must be bounds-checked before slicing.
- All public parser results must use typed frozen dataclasses.
- No guessed function, table, or gameplay behavior may be labeled confirmed.
- Python source must pass `ruff check`, `ruff format --check`, `mypy`, and `pytest`.

---

## File Map

The plan creates the following files:

```text
README.md                              Project purpose, legal boundary, setup, CLI usage
.gitignore                             Ignore ROMs, workspaces, reports, caches, virtualenvs
pyproject.toml                         Package metadata, CLI entry point, pytest/ruff/mypy config
config/b6re_rev0.json                  Exact supported-ROM identity and expected layout
src/bakugan_ds/__init__.py             Package version export
src/bakugan_ds/__main__.py             `python -m bakugan_ds` entry point
src/bakugan_ds/cli.py                  CLI argument parsing and command dispatch
src/bakugan_ds/errors.py               Domain exception hierarchy
src/bakugan_ds/profile.py              ROM profile loading, hashing, and identity validation
src/bakugan_ds/inspection.py           Composition of parsers into deterministic report models
src/bakugan_ds/nds/__init__.py         NDS parser exports
src/bakugan_ds/nds/header.py           Nintendo DS header parser
src/bakugan_ds/nds/fat.py              File Allocation Table parser
src/bakugan_ds/nds/fnt.py              File Name Table parser and path reconstruction
src/bakugan_ds/nds/overlays.py         ARM9/ARM7 overlay table parser
src/bakugan_ds/util.py                 Shared bounds checks and little-endian readers
analysis/memory-map.yaml               Verified executable and overlay load-address baseline
analysis/overlays.yaml                 Verified overlay metadata baseline
analysis/symbols/.gitkeep              Reserved symbol output directory
analysis/functions/.gitkeep            Reserved function documentation directory
docs/rom-map.md                        Human-readable verified ROM structure
docs/reverse-engineering-workflow.md   Confidence labels and runtime/static evidence rules
tests/conftest.py                      Shared synthetic ROM builders
tests/unit/test_profile.py             Profile loading and identity validation tests
tests/unit/test_header.py              Header parser tests
tests/unit/test_fat.py                 FAT parser tests
tests/unit/test_fnt.py                 FNT traversal tests
tests/unit/test_overlays.py            Overlay parser tests
tests/unit/test_inspection.py          Report composition and deterministic JSON tests
tests/unit/test_cli.py                 CLI exit-code and output tests
tests/integration/test_reference_rom.py Optional exact-ROM integration tests
```

---

### Task 1: Project Scaffold and Domain Errors

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/bakugan_ds/__init__.py`
- Create: `src/bakugan_ds/__main__.py`
- Create: `src/bakugan_ds/errors.py`
- Create: `tests/unit/test_package.py`

**Interfaces:**
- Produces: `bakugan_ds.__version__: str`
- Produces: `BakuganDSError`, `RomFormatError`, `UnsupportedRomError`, `BoundsError`, `ProfileError`
- Produces: console script `bakugan-ds = bakugan_ds.cli:main`

- [ ] **Step 1: Write the package smoke test**

Create `tests/unit/test_package.py`:

```python
from bakugan_ds import __version__
from bakugan_ds.errors import BakuganDSError, BoundsError, RomFormatError


def test_package_exports_version() -> None:
    assert __version__ == "0.1.0"


def test_domain_errors_share_common_base() -> None:
    assert issubclass(BoundsError, RomFormatError)
    assert issubclass(RomFormatError, BakuganDSError)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_package.py -v
```

Expected: collection fails because `bakugan_ds` does not exist.

- [ ] **Step 3: Create the package configuration**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "bakugan-ds"
version = "0.1.0"
description = "Reproducible inspection and modding tools for Bakugan: Battle Brawlers on Nintendo DS"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Bakugan DS contributors" }]
dependencies = []

[project.optional-dependencies]
dev = [
  "mypy>=1.11",
  "pytest>=8.3",
  "ruff>=0.6",
]

[project.scripts]
bakugan-ds = "bakugan_ds.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/bakugan_ds"]

[tool.pytest.ini_options]
addopts = "-ra"
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.11"
strict = true
packages = ["bakugan_ds"]
```

Create `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
dist/
build/
*.egg-info/

*.nds
*.sav
work/
reports/
*.bin
```

- [ ] **Step 4: Create the package and exception hierarchy**

Create `src/bakugan_ds/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/bakugan_ds/errors.py`:

```python
class BakuganDSError(Exception):
    """Base exception for expected tool failures."""


class ProfileError(BakuganDSError):
    """Raised when a ROM profile is malformed or incomplete."""


class UnsupportedRomError(BakuganDSError):
    """Raised when a ROM does not match the selected supported profile."""


class RomFormatError(BakuganDSError):
    """Raised when Nintendo DS structures are malformed."""


class BoundsError(RomFormatError):
    """Raised when a structure points outside the available ROM bytes."""
```

Create `src/bakugan_ds/__main__.py`:

```python
from bakugan_ds.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Create a temporary `src/bakugan_ds/cli.py` that will be replaced in Task 7:

```python
def main() -> int:
    return 0
```

- [ ] **Step 5: Create the README baseline**

Create `README.md` with these exact sections and substance:

```markdown
# Bakugan DS

Reproducible inspection and modding tools for the USA revision 0 release of
**Bakugan: Battle Brawlers** on Nintendo DS.

## Legal boundary

This repository contains code, documentation, hashes, schemas, and minimal
synthetic test fixtures. It does not contain ROM images, extracted game assets,
or rebuilt game images. Users must provide their own legally obtained ROM.

## Supported ROM

- Internal title: `BAKUGAN W`
- Game code: `B6RE`
- Revision: `0`
- SHA-256: `7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b`

## Development setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
```

## Current scope

Milestone 1 validates the supported ROM and parses its NDS header, FAT, FNT,
and overlay tables. Extraction, rebuilding, and gameplay patches follow in
later milestones.
```

- [ ] **Step 6: Install and run the smoke test**

Run:

```bash
python -m pip install -e '.[dev]'
python -m pytest tests/unit/test_package.py -v
```

Expected: 2 tests pass.

- [ ] **Step 7: Run static checks**

Run:

```bash
ruff check .
ruff format --check .
mypy src
```

Expected: all commands exit 0.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .gitignore README.md src tests/unit/test_package.py
git commit -m "chore: initialize Bakugan DS Python tooling"
```

---

### Task 2: ROM Profile Loading and Exact Identity Validation

**Files:**
- Create: `config/b6re_rev0.json`
- Create: `src/bakugan_ds/profile.py`
- Create: `tests/unit/test_profile.py`

**Interfaces:**
- Produces: `LayoutExpectations`
- Produces: `RomProfile`
- Produces: `RomIdentity`
- Produces: `load_profile(path: Path) -> RomProfile`
- Produces: `sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str`
- Produces: `read_rom_identity(path: Path) -> RomIdentity`
- Produces: `validate_rom(path: Path, profile: RomProfile) -> RomIdentity`

- [ ] **Step 1: Write profile and validation tests**

Create `tests/unit/test_profile.py`:

```python
import hashlib
import json
from pathlib import Path

import pytest

from bakugan_ds.errors import ProfileError, UnsupportedRomError
from bakugan_ds.profile import load_profile, read_rom_identity, sha256_file, validate_rom


def make_identity_rom(path: Path, *, size: int = 0x200) -> bytes:
    data = bytearray(size)
    data[0x00:0x0C] = b"BAKUGAN W\x00\x00\x00"
    data[0x0C:0x10] = b"B6RE"
    data[0x10:0x12] = b"52"
    data[0x1E] = 0
    path.write_bytes(data)
    return bytes(data)


def test_load_profile_reads_exact_values(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "id": "test",
                "sha256": "0" * 64,
                "size": 512,
                "title": "BAKUGAN W",
                "game_code": "B6RE",
                "maker_code": "52",
                "revision": 0,
                "expected": {
                    "arm9_offset": 16384,
                    "arm9_ram_address": 33554432,
                    "arm9_size": 448192,
                    "arm7_offset": 887296,
                    "arm7_ram_address": 37224448,
                    "arm7_size": 160048,
                    "fnt_offset": 1047808,
                    "fnt_size": 212348,
                    "fat_offset": 1260032,
                    "fat_size": 88040,
                    "nitrofs_file_count": 11005,
                    "directory_count": 95,
                    "arm9_overlay_count": 9,
                    "arm7_overlay_count": 0
                }
            }
        ),
        encoding="utf-8",
    )

    profile = load_profile(profile_path)

    assert profile.id == "test"
    assert profile.game_code == "B6RE"
    assert profile.expected.nitrofs_file_count == 11005


def test_load_profile_rejects_bad_sha_length(tmp_path: Path) -> None:
    profile_path = tmp_path / "bad.json"
    profile_path.write_text(
        json.dumps(
            {
                "id": "bad",
                "sha256": "abc",
                "size": 512,
                "title": "BAKUGAN W",
                "game_code": "B6RE",
                "maker_code": "52",
                "revision": 0,
                "expected": {}
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProfileError, match="sha256"):
        load_profile(profile_path)


def test_read_rom_identity_reads_header_fields_and_hash(tmp_path: Path) -> None:
    rom_path = tmp_path / "test.nds"
    data = make_identity_rom(rom_path)

    identity = read_rom_identity(rom_path)

    assert identity.title == "BAKUGAN W"
    assert identity.game_code == "B6RE"
    assert identity.maker_code == "52"
    assert identity.revision == 0
    assert identity.size == len(data)
    assert identity.sha256 == hashlib.sha256(data).hexdigest()


def test_validate_rom_rejects_hash_mismatch(tmp_path: Path) -> None:
    rom_path = tmp_path / "test.nds"
    make_identity_rom(rom_path)
    profile_path = Path("config/b6re_rev0.json")
    profile = load_profile(profile_path)

    with pytest.raises(UnsupportedRomError, match="size"):
        validate_rom(rom_path, profile)


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"Bakugan" * 1000)

    assert sha256_file(path, chunk_size=17) == hashlib.sha256(path.read_bytes()).hexdigest()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_profile.py -v
```

Expected: collection fails because `bakugan_ds.profile` does not exist.

- [ ] **Step 3: Create the exact reference profile**

Create `config/b6re_rev0.json`:

```json
{
  "id": "b6re_rev0",
  "sha256": "7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b",
  "size": 134217728,
  "title": "BAKUGAN W",
  "game_code": "B6RE",
  "maker_code": "52",
  "revision": 0,
  "expected": {
    "arm9_offset": 16384,
    "arm9_ram_address": 33554432,
    "arm9_size": 448192,
    "arm7_offset": 887296,
    "arm7_ram_address": 37224448,
    "arm7_size": 160048,
    "fnt_offset": 1047808,
    "fnt_size": 212348,
    "fat_offset": 1260032,
    "fat_size": 88040,
    "nitrofs_file_count": 11005,
    "directory_count": 95,
    "arm9_overlay_count": 9,
    "arm7_overlay_count": 0
  }
}
```

- [ ] **Step 4: Implement typed profile models and validation**

Create `src/bakugan_ds/profile.py` with these models and behavior:

```python
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import Path
from typing import Any

from bakugan_ds.errors import ProfileError, UnsupportedRomError


@dataclass(frozen=True)
class LayoutExpectations:
    arm9_offset: int
    arm9_ram_address: int
    arm9_size: int
    arm7_offset: int
    arm7_ram_address: int
    arm7_size: int
    fnt_offset: int
    fnt_size: int
    fat_offset: int
    fat_size: int
    nitrofs_file_count: int
    directory_count: int
    arm9_overlay_count: int
    arm7_overlay_count: int


@dataclass(frozen=True)
class RomProfile:
    id: str
    sha256: str
    size: int
    title: str
    game_code: str
    maker_code: str
    revision: int
    expected: LayoutExpectations


@dataclass(frozen=True)
class RomIdentity:
    title: str
    game_code: str
    maker_code: str
    revision: int
    size: int
    sha256: str


def _require_mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError(f"{name} must be an object")
    return value


def _decode_ascii(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="strict").rstrip()


def load_profile(path: Path) -> RomProfile:
    try:
        payload = _require_mapping(json.loads(path.read_text(encoding="utf-8")), "profile")
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"cannot load profile {path}: {exc}") from exc

    expected_payload = _require_mapping(payload.get("expected"), "expected")
    expected_names = {field.name for field in fields(LayoutExpectations)}
    missing_expected = sorted(expected_names - expected_payload.keys())
    if missing_expected:
        raise ProfileError(f"expected is missing fields: {', '.join(missing_expected)}")

    try:
        profile = RomProfile(
            id=str(payload["id"]),
            sha256=str(payload["sha256"]).lower(),
            size=int(payload["size"]),
            title=str(payload["title"]),
            game_code=str(payload["game_code"]),
            maker_code=str(payload["maker_code"]),
            revision=int(payload["revision"]),
            expected=LayoutExpectations(
                **{name: int(expected_payload[name]) for name in expected_names}
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProfileError(f"invalid profile field: {exc}") from exc

    if len(profile.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in profile.sha256):
        raise ProfileError("sha256 must be 64 lowercase hexadecimal characters")
    if len(profile.game_code) != 4:
        raise ProfileError("game_code must contain exactly 4 characters")
    if len(profile.maker_code) != 2:
        raise ProfileError("maker_code must contain exactly 2 characters")
    if not 0 <= profile.revision <= 255:
        raise ProfileError("revision must fit in one byte")
    return profile


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def read_rom_identity(path: Path) -> RomIdentity:
    size = path.stat().st_size
    with path.open("rb") as handle:
        header = handle.read(0x20)
    if len(header) < 0x20:
        raise UnsupportedRomError(f"ROM is too small for an NDS header: {len(header)} bytes")
    return RomIdentity(
        title=_decode_ascii(header[0x00:0x0C]),
        game_code=_decode_ascii(header[0x0C:0x10]),
        maker_code=_decode_ascii(header[0x10:0x12]),
        revision=header[0x1E],
        size=size,
        sha256=sha256_file(path),
    )


def validate_rom(path: Path, profile: RomProfile) -> RomIdentity:
    identity = read_rom_identity(path)
    comparisons = {
        "title": (identity.title, profile.title),
        "game code": (identity.game_code, profile.game_code),
        "maker code": (identity.maker_code, profile.maker_code),
        "revision": (identity.revision, profile.revision),
        "size": (identity.size, profile.size),
        "sha256": (identity.sha256, profile.sha256),
    }
    for label, (actual, expected) in comparisons.items():
        if actual != expected:
            raise UnsupportedRomError(
                f"unsupported ROM: {label} mismatch; expected {expected!r}, got {actual!r}"
            )
    return identity
```

- [ ] **Step 5: Run the profile tests**

Run:

```bash
python -m pytest tests/unit/test_profile.py -v
```

Expected: 5 tests pass.

- [ ] **Step 6: Run static checks**

Run:

```bash
ruff check src tests
ruff format --check src tests
mypy src
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add config/b6re_rev0.json src/bakugan_ds/profile.py tests/unit/test_profile.py
git commit -m "feat: validate the supported Bakugan DS ROM"
```

---

### Task 3: Shared Binary Readers and Nintendo DS Header Parser

**Files:**
- Create: `src/bakugan_ds/util.py`
- Create: `src/bakugan_ds/nds/__init__.py`
- Create: `src/bakugan_ds/nds/header.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_header.py`

**Interfaces:**
- Produces: `require_range(data: bytes | bytearray | memoryview, offset: int, size: int, label: str) -> memoryview`
- Produces: `read_u16_le(data, offset, label) -> int`
- Produces: `read_u32_le(data, offset, label) -> int`
- Produces: `NdsHeader.from_bytes(data: bytes | bytearray | memoryview) -> NdsHeader`
- Produces: `NdsHeader.section_ranges() -> tuple[SectionRange, ...]`

- [ ] **Step 1: Write synthetic-header tests**

Create `tests/conftest.py`:

```python
from collections.abc import Callable
import struct

import pytest


@pytest.fixture
def make_nds_header() -> Callable[[], bytes]:
    def factory() -> bytes:
        data = bytearray(0x200)
        data[0x00:0x0C] = b"BAKUGAN W\x00\x00\x00"
        data[0x0C:0x10] = b"B6RE"
        data[0x10:0x12] = b"52"
        data[0x1E] = 0
        struct.pack_into("<III", data, 0x20, 0x4000, 0x02000000, 0x02000000)
        struct.pack_into("<I", data, 0x2C, 448192)
        struct.pack_into("<III", data, 0x30, 0x0D8A00, 0x02380000, 0x02380000)
        struct.pack_into("<I", data, 0x3C, 160048)
        struct.pack_into("<II", data, 0x40, 0x0FFD00, 212348)
        struct.pack_into("<II", data, 0x48, 0x133A00, 88040)
        struct.pack_into("<II", data, 0x50, 0x0EBD00, 9 * 32)
        struct.pack_into("<II", data, 0x58, 0, 0)
        struct.pack_into("<I", data, 0x80, 134217728)
        return bytes(data)

    return factory
```

Create `tests/unit/test_header.py`:

```python
from collections.abc import Callable

import pytest

from bakugan_ds.errors import BoundsError, RomFormatError
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.util import read_u16_le, read_u32_le, require_range


def test_require_range_returns_requested_slice() -> None:
    assert bytes(require_range(b"abcdef", 1, 3, "test")) == b"bcd"


def test_require_range_rejects_negative_offset() -> None:
    with pytest.raises(BoundsError, match="test"):
        require_range(b"abc", -1, 1, "test")


def test_integer_readers_use_little_endian() -> None:
    data = bytes.fromhex("341278563412")
    assert read_u16_le(data, 0, "u16") == 0x1234
    assert read_u32_le(data, 2, "u32") == 0x12345678


def test_header_parses_verified_layout(make_nds_header: Callable[[], bytes]) -> None:
    header = NdsHeader.from_bytes(make_nds_header())

    assert header.title == "BAKUGAN W"
    assert header.game_code == "B6RE"
    assert header.arm9_offset == 0x4000
    assert header.arm9_ram_address == 0x02000000
    assert header.arm9_size == 448192
    assert header.fnt_offset == 0x0FFD00
    assert header.fat_size == 88040
    assert header.arm9_overlay_size == 288
    assert header.arm7_overlay_size == 0


def test_header_rejects_truncated_data() -> None:
    with pytest.raises(BoundsError, match="NDS header"):
        NdsHeader.from_bytes(b"\x00" * 0x100)


def test_header_rejects_non_multiple_overlay_table_size(
    make_nds_header: Callable[[], bytes],
) -> None:
    data = bytearray(make_nds_header())
    data[0x54:0x58] = (33).to_bytes(4, "little")

    with pytest.raises(RomFormatError, match="overlay table size"):
        NdsHeader.from_bytes(data)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_header.py -v
```

Expected: collection fails because `bakugan_ds.nds.header` and `bakugan_ds.util` do not exist.

- [ ] **Step 3: Implement shared bounds-safe readers**

Create `src/bakugan_ds/util.py`:

```python
from __future__ import annotations

import struct
from typing import TypeAlias

from bakugan_ds.errors import BoundsError

Buffer: TypeAlias = bytes | bytearray | memoryview


def require_range(data: Buffer, offset: int, size: int, label: str) -> memoryview:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise BoundsError(
            f"{label} range 0x{offset:X}..0x{offset + size:X} exceeds buffer size 0x{len(data):X}"
        )
    return memoryview(data)[offset : offset + size]


def read_u16_le(data: Buffer, offset: int, label: str) -> int:
    return struct.unpack_from("<H", require_range(data, offset, 2, label))[0]


def read_u32_le(data: Buffer, offset: int, label: str) -> int:
    return struct.unpack_from("<I", require_range(data, offset, 4, label))[0]
```

- [ ] **Step 4: Implement the NDS header dataclasses and parser**

Create `src/bakugan_ds/nds/header.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import RomFormatError
from bakugan_ds.util import Buffer, read_u32_le, require_range


def _decode_ascii(raw: memoryview) -> str:
    return raw.tobytes().split(b"\x00", 1)[0].decode("ascii", errors="strict").rstrip()


@dataclass(frozen=True)
class SectionRange:
    name: str
    offset: int
    size: int

    @property
    def end(self) -> int:
        return self.offset + self.size


@dataclass(frozen=True)
class NdsHeader:
    title: str
    game_code: str
    maker_code: str
    revision: int
    arm9_offset: int
    arm9_entry_address: int
    arm9_ram_address: int
    arm9_size: int
    arm7_offset: int
    arm7_entry_address: int
    arm7_ram_address: int
    arm7_size: int
    fnt_offset: int
    fnt_size: int
    fat_offset: int
    fat_size: int
    arm9_overlay_offset: int
    arm9_overlay_size: int
    arm7_overlay_offset: int
    arm7_overlay_size: int
    rom_size_field: int

    @classmethod
    def from_bytes(cls, data: Buffer) -> "NdsHeader":
        header = require_range(data, 0, 0x200, "NDS header")
        result = cls(
            title=_decode_ascii(header[0x00:0x0C]),
            game_code=_decode_ascii(header[0x0C:0x10]),
            maker_code=_decode_ascii(header[0x10:0x12]),
            revision=header[0x1E],
            arm9_offset=read_u32_le(header, 0x20, "ARM9 ROM offset"),
            arm9_entry_address=read_u32_le(header, 0x24, "ARM9 entry address"),
            arm9_ram_address=read_u32_le(header, 0x28, "ARM9 RAM address"),
            arm9_size=read_u32_le(header, 0x2C, "ARM9 size"),
            arm7_offset=read_u32_le(header, 0x30, "ARM7 ROM offset"),
            arm7_entry_address=read_u32_le(header, 0x34, "ARM7 entry address"),
            arm7_ram_address=read_u32_le(header, 0x38, "ARM7 RAM address"),
            arm7_size=read_u32_le(header, 0x3C, "ARM7 size"),
            fnt_offset=read_u32_le(header, 0x40, "FNT offset"),
            fnt_size=read_u32_le(header, 0x44, "FNT size"),
            fat_offset=read_u32_le(header, 0x48, "FAT offset"),
            fat_size=read_u32_le(header, 0x4C, "FAT size"),
            arm9_overlay_offset=read_u32_le(header, 0x50, "ARM9 overlay offset"),
            arm9_overlay_size=read_u32_le(header, 0x54, "ARM9 overlay size"),
            arm7_overlay_offset=read_u32_le(header, 0x58, "ARM7 overlay offset"),
            arm7_overlay_size=read_u32_le(header, 0x5C, "ARM7 overlay size"),
            rom_size_field=read_u32_le(header, 0x80, "ROM size field"),
        )
        for label, size in (
            ("ARM9 overlay table size", result.arm9_overlay_size),
            ("ARM7 overlay table size", result.arm7_overlay_size),
        ):
            if size % 32 != 0:
                raise RomFormatError(f"{label} must be a multiple of 32, got {size}")
        return result

    def section_ranges(self) -> tuple[SectionRange, ...]:
        return (
            SectionRange("arm9", self.arm9_offset, self.arm9_size),
            SectionRange("arm7", self.arm7_offset, self.arm7_size),
            SectionRange("fnt", self.fnt_offset, self.fnt_size),
            SectionRange("fat", self.fat_offset, self.fat_size),
            SectionRange("arm9_overlays", self.arm9_overlay_offset, self.arm9_overlay_size),
            SectionRange("arm7_overlays", self.arm7_overlay_offset, self.arm7_overlay_size),
        )
```

Create `src/bakugan_ds/nds/__init__.py`:

```python
from bakugan_ds.nds.header import NdsHeader, SectionRange

__all__ = ["NdsHeader", "SectionRange"]
```

- [ ] **Step 5: Run the header tests**

Run:

```bash
python -m pytest tests/unit/test_header.py -v
```

Expected: 6 tests pass.

- [ ] **Step 6: Run all current tests and static checks**

Run:

```bash
python -m pytest -v
ruff check src tests
ruff format --check src tests
mypy src
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add src/bakugan_ds/util.py src/bakugan_ds/nds tests/conftest.py tests/unit/test_header.py
git commit -m "feat: parse Nintendo DS ROM headers"
```

---

### Task 4: File Allocation Table Parser

**Files:**
- Create: `src/bakugan_ds/nds/fat.py`
- Create: `tests/unit/test_fat.py`
- Modify: `src/bakugan_ds/nds/__init__.py`

**Interfaces:**
- Consumes: `NdsHeader`, `Buffer`, `read_u32_le`, `require_range`
- Produces: `FatEntry(file_id: int, start: int, end: int)`
- Produces: `FatEntry.size -> int`
- Produces: `parse_fat(data: Buffer, header: NdsHeader) -> tuple[FatEntry, ...]`

- [ ] **Step 1: Write FAT parser tests**

Create `tests/unit/test_fat.py`:

```python
from collections.abc import Callable
import struct

import pytest

from bakugan_ds.errors import BoundsError, RomFormatError
from bakugan_ds.nds.fat import parse_fat
from bakugan_ds.nds.header import NdsHeader


def build_rom_with_fat(make_nds_header: Callable[[], bytes], entries: list[tuple[int, int]]) -> bytes:
    header_bytes = bytearray(make_nds_header())
    fat_offset = 0x300
    fat_size = len(entries) * 8
    struct.pack_into("<II", header_bytes, 0x48, fat_offset, fat_size)
    rom = bytearray(0x1000)
    rom[:0x200] = header_bytes
    for index, (start, end) in enumerate(entries):
        struct.pack_into("<II", rom, fat_offset + index * 8, start, end)
    return bytes(rom)


def test_parse_fat_assigns_file_ids_and_sizes(make_nds_header: Callable[[], bytes]) -> None:
    rom = build_rom_with_fat(make_nds_header, [(0x500, 0x510), (0x600, 0x640)])
    header = NdsHeader.from_bytes(rom)

    entries = parse_fat(rom, header)

    assert [(entry.file_id, entry.start, entry.end, entry.size) for entry in entries] == [
        (0, 0x500, 0x510, 0x10),
        (1, 0x600, 0x640, 0x40),
    ]


def test_parse_fat_rejects_non_multiple_of_eight(make_nds_header: Callable[[], bytes]) -> None:
    rom = bytearray(build_rom_with_fat(make_nds_header, [(0x500, 0x510)]))
    rom[0x4C:0x50] = (9).to_bytes(4, "little")
    header = NdsHeader.from_bytes(rom)

    with pytest.raises(RomFormatError, match="multiple of 8"):
        parse_fat(rom, header)


def test_parse_fat_rejects_reversed_range(make_nds_header: Callable[[], bytes]) -> None:
    rom = build_rom_with_fat(make_nds_header, [(0x600, 0x500)])
    header = NdsHeader.from_bytes(rom)

    with pytest.raises(RomFormatError, match="file 0"):
        parse_fat(rom, header)


def test_parse_fat_rejects_file_outside_rom(make_nds_header: Callable[[], bytes]) -> None:
    rom = build_rom_with_fat(make_nds_header, [(0x500, 0x2000)])
    header = NdsHeader.from_bytes(rom)

    with pytest.raises(BoundsError, match="file 0"):
        parse_fat(rom, header)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_fat.py -v
```

Expected: collection fails because `bakugan_ds.nds.fat` does not exist.

- [ ] **Step 3: Implement the FAT parser**

Create `src/bakugan_ds/nds/fat.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import BoundsError, RomFormatError
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.util import Buffer, read_u32_le, require_range


@dataclass(frozen=True)
class FatEntry:
    file_id: int
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start


def parse_fat(data: Buffer, header: NdsHeader) -> tuple[FatEntry, ...]:
    if header.fat_size % 8 != 0:
        raise RomFormatError(f"FAT size must be a multiple of 8, got {header.fat_size}")
    table = require_range(data, header.fat_offset, header.fat_size, "FAT")
    entries: list[FatEntry] = []
    for file_id in range(header.fat_size // 8):
        offset = file_id * 8
        start = read_u32_le(table, offset, f"FAT file {file_id} start")
        end = read_u32_le(table, offset + 4, f"FAT file {file_id} end")
        if end < start:
            raise RomFormatError(
                f"FAT file {file_id} has reversed range 0x{start:X}..0x{end:X}"
            )
        if end > len(data):
            raise BoundsError(
                f"FAT file {file_id} ends at 0x{end:X}, beyond ROM size 0x{len(data):X}"
            )
        entries.append(FatEntry(file_id=file_id, start=start, end=end))
    return tuple(entries)
```

Update `src/bakugan_ds/nds/__init__.py`:

```python
from bakugan_ds.nds.fat import FatEntry, parse_fat
from bakugan_ds.nds.header import NdsHeader, SectionRange

__all__ = ["FatEntry", "NdsHeader", "SectionRange", "parse_fat"]
```

- [ ] **Step 4: Run the FAT tests**

Run:

```bash
python -m pytest tests/unit/test_fat.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/bakugan_ds/nds/fat.py src/bakugan_ds/nds/__init__.py tests/unit/test_fat.py
git commit -m "feat: parse Nintendo DS file allocation tables"
```

---

### Task 5: File Name Table Parser and Path Reconstruction

**Files:**
- Create: `src/bakugan_ds/nds/fnt.py`
- Create: `tests/unit/test_fnt.py`
- Modify: `src/bakugan_ds/nds/__init__.py`

**Interfaces:**
- Consumes: `NdsHeader`, `Buffer`, bounds-safe readers
- Produces: `FntDirectory(dir_id: int, parent_id: int, first_file_id: int, path: str)`
- Produces: `FntFile(file_id: int, path: str)`
- Produces: `FntTree(directories: tuple[FntDirectory, ...], files: tuple[FntFile, ...])`
- Produces: `FntTree.file_by_id() -> dict[int, FntFile]`
- Produces: `parse_fnt(data: Buffer, header: NdsHeader, fat_entry_count: int) -> FntTree`

- [ ] **Step 1: Write FNT traversal tests with a synthetic hierarchy**

Create `tests/unit/test_fnt.py`:

```python
from collections.abc import Callable
import struct

import pytest

from bakugan_ds.errors import RomFormatError
from bakugan_ds.nds.fnt import parse_fnt
from bakugan_ds.nds.header import NdsHeader


def build_rom_with_fnt(make_nds_header: Callable[[], bytes]) -> bytes:
    header_bytes = bytearray(make_nds_header())
    fnt_offset = 0x300

    # Directory table: root 0xF000 and child 0xF001.
    # Root subtable starts at 0x10, child subtable starts at 0x1E.
    fnt = bytearray()
    fnt.extend(struct.pack("<IHH", 0x10, 0, 2))
    fnt.extend(struct.pack("<IHH", 0x1E, 2, 0xF000))

    # Root: file 0 "root.bin", directory "Game" -> 0xF001, terminator.
    fnt.extend(bytes([8]) + b"root.bin")
    fnt.extend(bytes([0x80 | 4]) + b"Game" + struct.pack("<H", 0xF001))
    fnt.extend(b"\x00")

    # Child: files 2 and 3, then terminator.
    fnt.extend(bytes([8]) + b"data.bin")
    fnt.extend(bytes([7]) + b"map.bin")
    fnt.extend(b"\x00")

    struct.pack_into("<II", header_bytes, 0x40, fnt_offset, len(fnt))
    rom = bytearray(0x1000)
    rom[:0x200] = header_bytes
    rom[fnt_offset : fnt_offset + len(fnt)] = fnt
    return bytes(rom)


def test_parse_fnt_reconstructs_paths(make_nds_header: Callable[[], bytes]) -> None:
    rom = build_rom_with_fnt(make_nds_header)
    header = NdsHeader.from_bytes(rom)

    tree = parse_fnt(rom, header, fat_entry_count=4)

    assert [directory.path for directory in tree.directories] == ["", "Game"]
    assert [(file.file_id, file.path) for file in tree.files] == [
        (0, "root.bin"),
        (2, "Game/data.bin"),
        (3, "Game/map.bin"),
    ]


def test_parse_fnt_maps_files_by_id(make_nds_header: Callable[[], bytes]) -> None:
    rom = build_rom_with_fnt(make_nds_header)
    tree = parse_fnt(rom, NdsHeader.from_bytes(rom), fat_entry_count=4)

    assert tree.file_by_id()[3].path == "Game/map.bin"


def test_parse_fnt_rejects_file_id_beyond_fat(make_nds_header: Callable[[], bytes]) -> None:
    rom = build_rom_with_fnt(make_nds_header)

    with pytest.raises(RomFormatError, match="FAT contains only 3"):
        parse_fnt(rom, NdsHeader.from_bytes(rom), fat_entry_count=3)


def test_parse_fnt_rejects_invalid_child_directory_id(
    make_nds_header: Callable[[], bytes],
) -> None:
    rom = bytearray(build_rom_with_fnt(make_nds_header))
    # Child ID follows the four-byte name "Game" in the root subtable.
    child_id_offset = 0x300 + 0x10 + 1 + 8 + 1 + 4
    rom[child_id_offset : child_id_offset + 2] = (0xF00A).to_bytes(2, "little")

    with pytest.raises(RomFormatError, match="directory ID"):
        parse_fnt(rom, NdsHeader.from_bytes(rom), fat_entry_count=4)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_fnt.py -v
```

Expected: collection fails because `bakugan_ds.nds.fnt` does not exist.

- [ ] **Step 3: Implement directory records and recursive traversal**

Create `src/bakugan_ds/nds/fnt.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from bakugan_ds.errors import RomFormatError
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.util import Buffer, read_u16_le, read_u32_le, require_range

ROOT_DIRECTORY_ID = 0xF000


@dataclass(frozen=True)
class FntDirectory:
    dir_id: int
    parent_id: int
    first_file_id: int
    path: str


@dataclass(frozen=True)
class FntFile:
    file_id: int
    path: str


@dataclass(frozen=True)
class FntTree:
    directories: tuple[FntDirectory, ...]
    files: tuple[FntFile, ...]

    def file_by_id(self) -> dict[int, FntFile]:
        return {entry.file_id: entry for entry in self.files}


@dataclass(frozen=True)
class _DirectoryRecord:
    subtable_offset: int
    first_file_id: int
    parent_id: int


def _directory_index(dir_id: int, directory_count: int) -> int:
    if dir_id < ROOT_DIRECTORY_ID:
        raise RomFormatError(f"invalid FNT directory ID 0x{dir_id:04X}")
    index = dir_id - ROOT_DIRECTORY_ID
    if index >= directory_count:
        raise RomFormatError(
            f"FNT directory ID 0x{dir_id:04X} resolves to index {index}, "
            f"but only {directory_count} directories exist"
        )
    return index


def _join(parent: str, name: str) -> str:
    return str(PurePosixPath(parent, name)) if parent else name


def parse_fnt(data: Buffer, header: NdsHeader, fat_entry_count: int) -> FntTree:
    table = require_range(data, header.fnt_offset, header.fnt_size, "FNT")
    if len(table) < 8:
        raise RomFormatError("FNT is too small for the root directory record")

    directory_count = read_u16_le(table, 6, "FNT root directory count")
    if directory_count == 0:
        raise RomFormatError("FNT declares zero directories")
    require_range(table, 0, directory_count * 8, "FNT directory table")

    records = tuple(
        _DirectoryRecord(
            subtable_offset=read_u32_le(table, index * 8, f"FNT directory {index} subtable"),
            first_file_id=read_u16_le(table, index * 8 + 4, f"FNT directory {index} file ID"),
            parent_id=read_u16_le(table, index * 8 + 6, f"FNT directory {index} parent"),
        )
        for index in range(directory_count)
    )

    directories: list[FntDirectory] = []
    files: list[FntFile] = []
    visited: set[int] = set()

    def walk(dir_id: int, path: str) -> None:
        index = _directory_index(dir_id, directory_count)
        if dir_id in visited:
            raise RomFormatError(f"FNT directory cycle detected at 0x{dir_id:04X}")
        visited.add(dir_id)
        record = records[index]
        directories.append(
            FntDirectory(
                dir_id=dir_id,
                parent_id=record.parent_id,
                first_file_id=record.first_file_id,
                path=path,
            )
        )
        cursor = record.subtable_offset
        file_id = record.first_file_id
        while True:
            entry_type = require_range(table, cursor, 1, f"FNT directory 0x{dir_id:04X} entry")[0]
            cursor += 1
            if entry_type == 0:
                return
            name_length = entry_type & 0x7F
            if name_length == 0:
                raise RomFormatError(f"FNT directory 0x{dir_id:04X} has an empty name")
            name_bytes = require_range(table, cursor, name_length, "FNT entry name").tobytes()
            cursor += name_length
            try:
                name = name_bytes.decode("ascii")
            except UnicodeDecodeError as exc:
                raise RomFormatError(f"FNT name is not ASCII: {name_bytes!r}") from exc
            child_path = _join(path, name)
            if entry_type & 0x80:
                child_id = read_u16_le(table, cursor, "FNT child directory ID")
                cursor += 2
                _directory_index(child_id, directory_count)
                walk(child_id, child_path)
            else:
                if file_id >= fat_entry_count:
                    raise RomFormatError(
                        f"FNT references file ID {file_id}, but FAT contains only {fat_entry_count} entries"
                    )
                files.append(FntFile(file_id=file_id, path=child_path))
                file_id += 1

    walk(ROOT_DIRECTORY_ID, "")
    if len(visited) != directory_count:
        missing = sorted(set(range(directory_count)) - {item - ROOT_DIRECTORY_ID for item in visited})
        raise RomFormatError(f"FNT contains unreachable directory indexes: {missing}")
    return FntTree(
        directories=tuple(sorted(directories, key=lambda item: item.dir_id)),
        files=tuple(sorted(files, key=lambda item: item.file_id)),
    )
```

Update `src/bakugan_ds/nds/__init__.py` to export `FntDirectory`, `FntFile`, `FntTree`, and `parse_fnt`.

- [ ] **Step 4: Run the FNT tests**

Run:

```bash
python -m pytest tests/unit/test_fnt.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Run all parser tests**

Run:

```bash
python -m pytest tests/unit/test_header.py tests/unit/test_fat.py tests/unit/test_fnt.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/bakugan_ds/nds/fnt.py src/bakugan_ds/nds/__init__.py tests/unit/test_fnt.py
git commit -m "feat: reconstruct NitroFS paths from the FNT"
```

---

### Task 6: ARM9 and ARM7 Overlay Table Parser

**Files:**
- Create: `src/bakugan_ds/nds/overlays.py`
- Create: `tests/unit/test_overlays.py`
- Modify: `src/bakugan_ds/nds/__init__.py`

**Interfaces:**
- Consumes: `NdsHeader`, `Buffer`, bounds-safe readers
- Produces: `OverlayEntry`
- Produces: `OverlayEntry.ram_end -> int`
- Produces: `OverlayEntry.compressed_size -> int`
- Produces: `OverlayEntry.flags -> int`
- Produces: `parse_overlay_table(data, offset, size, table_name) -> tuple[OverlayEntry, ...]`
- Produces: `parse_arm9_overlays(data, header) -> tuple[OverlayEntry, ...]`
- Produces: `parse_arm7_overlays(data, header) -> tuple[OverlayEntry, ...]`

- [ ] **Step 1: Write overlay-table tests**

Create `tests/unit/test_overlays.py`:

```python
from collections.abc import Callable
import struct

import pytest

from bakugan_ds.errors import RomFormatError
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.nds.overlays import parse_arm7_overlays, parse_arm9_overlays


def build_rom_with_overlays(make_nds_header: Callable[[], bytes]) -> bytes:
    header_bytes = bytearray(make_nds_header())
    table_offset = 0x300
    table_size = 2 * 32
    struct.pack_into("<II", header_bytes, 0x50, table_offset, table_size)
    struct.pack_into("<II", header_bytes, 0x58, 0, 0)
    rom = bytearray(0x1000)
    rom[:0x200] = header_bytes

    entries = [
        (0, 0x0221A1C0, 1000, 64, 0x0221A200, 0x0221A220, 10, 0x010001F4),
        (7, 0x0221A1C0, 467360, 1600, 0x0228C000, 0x0228C040, 70, 0x0103E6FC),
    ]
    for index, values in enumerate(entries):
        struct.pack_into("<8I", rom, table_offset + index * 32, *values)
    return bytes(rom)


def test_parse_arm9_overlays_decodes_fields(make_nds_header: Callable[[], bytes]) -> None:
    rom = build_rom_with_overlays(make_nds_header)
    overlays = parse_arm9_overlays(rom, NdsHeader.from_bytes(rom))

    assert len(overlays) == 2
    assert overlays[1].overlay_id == 7
    assert overlays[1].ram_address == 0x0221A1C0
    assert overlays[1].ram_size == 467360
    assert overlays[1].bss_size == 1600
    assert overlays[1].file_id == 70
    assert overlays[1].compressed_size == 0x03E6FC
    assert overlays[1].flags == 1
    assert overlays[1].ram_end == 0x0221A1C0 + 467360 + 1600


def test_parse_arm7_overlays_handles_empty_table(make_nds_header: Callable[[], bytes]) -> None:
    rom = build_rom_with_overlays(make_nds_header)
    assert parse_arm7_overlays(rom, NdsHeader.from_bytes(rom)) == ()


def test_overlay_table_rejects_duplicate_ids(make_nds_header: Callable[[], bytes]) -> None:
    rom = bytearray(build_rom_with_overlays(make_nds_header))
    rom[0x300 + 32 : 0x300 + 36] = (0).to_bytes(4, "little")

    with pytest.raises(RomFormatError, match="duplicate"):
        parse_arm9_overlays(rom, NdsHeader.from_bytes(rom))


def test_overlay_table_rejects_static_init_outside_ram(
    make_nds_header: Callable[[], bytes],
) -> None:
    rom = bytearray(build_rom_with_overlays(make_nds_header))
    rom[0x300 + 16 : 0x300 + 20] = (0x03000000).to_bytes(4, "little")

    with pytest.raises(RomFormatError, match="static initializer"):
        parse_arm9_overlays(rom, NdsHeader.from_bytes(rom))
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_overlays.py -v
```

Expected: collection fails because `bakugan_ds.nds.overlays` does not exist.

- [ ] **Step 3: Implement overlay parsing and validation**

Create `src/bakugan_ds/nds/overlays.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import RomFormatError
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.util import Buffer, read_u32_le, require_range

OVERLAY_ENTRY_SIZE = 32


@dataclass(frozen=True)
class OverlayEntry:
    overlay_id: int
    ram_address: int
    ram_size: int
    bss_size: int
    static_init_start: int
    static_init_end: int
    file_id: int
    reserved: int

    @property
    def compressed_size(self) -> int:
        return self.reserved & 0x00FFFFFF

    @property
    def flags(self) -> int:
        return self.reserved >> 24

    @property
    def ram_end(self) -> int:
        return self.ram_address + self.ram_size + self.bss_size


def parse_overlay_table(
    data: Buffer,
    offset: int,
    size: int,
    table_name: str,
) -> tuple[OverlayEntry, ...]:
    if size == 0:
        return ()
    if size % OVERLAY_ENTRY_SIZE != 0:
        raise RomFormatError(
            f"{table_name} size must be a multiple of {OVERLAY_ENTRY_SIZE}, got {size}"
        )
    table = require_range(data, offset, size, table_name)
    entries: list[OverlayEntry] = []
    seen_ids: set[int] = set()
    for index in range(size // OVERLAY_ENTRY_SIZE):
        base = index * OVERLAY_ENTRY_SIZE
        values = tuple(
            read_u32_le(table, base + field * 4, f"{table_name} entry {index} field {field}")
            for field in range(8)
        )
        entry = OverlayEntry(*values)
        if entry.overlay_id in seen_ids:
            raise RomFormatError(f"{table_name} contains duplicate overlay ID {entry.overlay_id}")
        seen_ids.add(entry.overlay_id)
        executable_end = entry.ram_address + entry.ram_size
        if not (
            entry.static_init_start == 0
            and entry.static_init_end == 0
        ) and not (
            entry.ram_address <= entry.static_init_start <= entry.static_init_end <= executable_end
        ):
            raise RomFormatError(
                f"{table_name} overlay {entry.overlay_id} static initializer range "
                f"0x{entry.static_init_start:X}..0x{entry.static_init_end:X} "
                f"is outside executable RAM range 0x{entry.ram_address:X}..0x{executable_end:X}"
            )
        entries.append(entry)
    return tuple(entries)


def parse_arm9_overlays(data: Buffer, header: NdsHeader) -> tuple[OverlayEntry, ...]:
    return parse_overlay_table(
        data,
        header.arm9_overlay_offset,
        header.arm9_overlay_size,
        "ARM9 overlay table",
    )


def parse_arm7_overlays(data: Buffer, header: NdsHeader) -> tuple[OverlayEntry, ...]:
    return parse_overlay_table(
        data,
        header.arm7_overlay_offset,
        header.arm7_overlay_size,
        "ARM7 overlay table",
    )
```

Update `src/bakugan_ds/nds/__init__.py` to export `OverlayEntry`, `parse_arm9_overlays`, `parse_arm7_overlays`, and `parse_overlay_table`.

- [ ] **Step 4: Run the overlay tests**

Run:

```bash
python -m pytest tests/unit/test_overlays.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/bakugan_ds/nds/overlays.py src/bakugan_ds/nds/__init__.py tests/unit/test_overlays.py
git commit -m "feat: parse Nintendo DS overlay tables"
```

---

### Task 7: Inspection Model, Layout Verification, and Deterministic JSON

**Files:**
- Create: `src/bakugan_ds/inspection.py`
- Create: `tests/unit/test_inspection.py`

**Interfaces:**
- Consumes: `RomProfile`, `RomIdentity`, `NdsHeader`, FAT, FNT, overlay parsers
- Produces: `LayoutMismatch(field: str, actual: int, expected: int)`
- Produces: `RomInspection`
- Produces: `inspect_rom(path: Path, profile: RomProfile, require_supported: bool) -> RomInspection`
- Produces: `RomInspection.to_dict() -> dict[str, object]`
- Produces: `RomInspection.to_json() -> str`

- [ ] **Step 1: Write report-composition tests**

Create `tests/unit/test_inspection.py`:

```python
from pathlib import Path
import json

import pytest

from bakugan_ds.inspection import RomInspection
from bakugan_ds.nds.fat import FatEntry
from bakugan_ds.nds.fnt import FntDirectory, FntFile, FntTree
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.nds.overlays import OverlayEntry
from bakugan_ds.profile import RomIdentity


def make_inspection() -> RomInspection:
    header = NdsHeader(
        title="BAKUGAN W",
        game_code="B6RE",
        maker_code="52",
        revision=0,
        arm9_offset=0x4000,
        arm9_entry_address=0x02000000,
        arm9_ram_address=0x02000000,
        arm9_size=448192,
        arm7_offset=0x0D8A00,
        arm7_entry_address=0x02380000,
        arm7_ram_address=0x02380000,
        arm7_size=160048,
        fnt_offset=0x0FFD00,
        fnt_size=212348,
        fat_offset=0x133A00,
        fat_size=16,
        arm9_overlay_offset=0x0EBD00,
        arm9_overlay_size=32,
        arm7_overlay_offset=0,
        arm7_overlay_size=0,
        rom_size_field=134217728,
    )
    return RomInspection(
        source_path=Path("game.nds"),
        identity=RomIdentity("BAKUGAN W", "B6RE", "52", 0, 134217728, "a" * 64),
        profile_id="b6re_rev0",
        supported=True,
        header=header,
        fat=(FatEntry(0, 0x100, 0x110), FatEntry(1, 0x110, 0x130)),
        fnt=FntTree(
            directories=(FntDirectory(0xF000, 1, 0, ""),),
            files=(FntFile(0, "a.bin"), FntFile(1, "b.bin")),
        ),
        arm9_overlays=(OverlayEntry(7, 0x0221A1C0, 467360, 1600, 0, 0, 70, 0),),
        arm7_overlays=(),
        layout_mismatches=(),
    )


def test_inspection_json_is_deterministic_and_machine_readable() -> None:
    inspection = make_inspection()

    first = inspection.to_json()
    second = inspection.to_json()
    payload = json.loads(first)

    assert first == second
    assert payload["identity"]["game_code"] == "B6RE"
    assert payload["counts"] == {
        "arm7_overlays": 0,
        "arm9_overlays": 1,
        "directories": 1,
        "files": 2,
    }
    assert payload["files"][1]["path"] == "b.bin"


def test_inspection_rejects_unmapped_fat_entry() -> None:
    inspection = make_inspection()
    broken = RomInspection(
        **{
            **inspection.__dict__,
            "fnt": FntTree(
                directories=inspection.fnt.directories,
                files=(FntFile(0, "a.bin"),),
            ),
        }
    )

    with pytest.raises(ValueError, match="FAT file IDs missing from FNT"):
        broken.to_dict()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inspection.py -v
```

Expected: collection fails because `bakugan_ds.inspection` does not exist.

- [ ] **Step 3: Implement inspection composition**

Create `src/bakugan_ds/inspection.py` with these required behaviors:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from bakugan_ds.errors import UnsupportedRomError
from bakugan_ds.nds.fat import FatEntry, parse_fat
from bakugan_ds.nds.fnt import FntTree, parse_fnt
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.nds.overlays import OverlayEntry, parse_arm7_overlays, parse_arm9_overlays
from bakugan_ds.profile import RomIdentity, RomProfile, read_rom_identity, validate_rom


@dataclass(frozen=True)
class LayoutMismatch:
    field: str
    actual: int
    expected: int


@dataclass(frozen=True)
class RomInspection:
    source_path: Path
    identity: RomIdentity
    profile_id: str
    supported: bool
    header: NdsHeader
    fat: tuple[FatEntry, ...]
    fnt: FntTree
    arm9_overlays: tuple[OverlayEntry, ...]
    arm7_overlays: tuple[OverlayEntry, ...]
    layout_mismatches: tuple[LayoutMismatch, ...]

    def to_dict(self) -> dict[str, object]:
        path_by_id = self.fnt.file_by_id()
        missing = sorted(entry.file_id for entry in self.fat if entry.file_id not in path_by_id)
        if missing:
            raise ValueError(f"FAT file IDs missing from FNT: {missing}")
        return {
            "source": str(self.source_path),
            "profile_id": self.profile_id,
            "supported": self.supported,
            "identity": asdict(self.identity),
            "header": asdict(self.header),
            "counts": {
                "files": len(self.fat),
                "directories": len(self.fnt.directories),
                "arm9_overlays": len(self.arm9_overlays),
                "arm7_overlays": len(self.arm7_overlays),
            },
            "layout_mismatches": [asdict(item) for item in self.layout_mismatches],
            "files": [
                {
                    "file_id": entry.file_id,
                    "path": path_by_id[entry.file_id].path,
                    "start": entry.start,
                    "end": entry.end,
                    "size": entry.size,
                }
                for entry in self.fat
            ],
            "directories": [asdict(item) for item in self.fnt.directories],
            "arm9_overlays": [asdict(item) | {
                "compressed_size": item.compressed_size,
                "flags": item.flags,
                "ram_end": item.ram_end,
            } for item in self.arm9_overlays],
            "arm7_overlays": [asdict(item) | {
                "compressed_size": item.compressed_size,
                "flags": item.flags,
                "ram_end": item.ram_end,
            } for item in self.arm7_overlays],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def _layout_mismatches(header: NdsHeader, profile: RomProfile, *, file_count: int,
                       directory_count: int, arm9_overlay_count: int,
                       arm7_overlay_count: int) -> tuple[LayoutMismatch, ...]:
    actual = {
        "arm9_offset": header.arm9_offset,
        "arm9_ram_address": header.arm9_ram_address,
        "arm9_size": header.arm9_size,
        "arm7_offset": header.arm7_offset,
        "arm7_ram_address": header.arm7_ram_address,
        "arm7_size": header.arm7_size,
        "fnt_offset": header.fnt_offset,
        "fnt_size": header.fnt_size,
        "fat_offset": header.fat_offset,
        "fat_size": header.fat_size,
        "nitrofs_file_count": file_count,
        "directory_count": directory_count,
        "arm9_overlay_count": arm9_overlay_count,
        "arm7_overlay_count": arm7_overlay_count,
    }
    expected = asdict(profile.expected)
    return tuple(
        LayoutMismatch(field=name, actual=value, expected=expected[name])
        for name, value in sorted(actual.items())
        if value != expected[name]
    )


def inspect_rom(path: Path, profile: RomProfile, require_supported: bool) -> RomInspection:
    if require_supported:
        identity = validate_rom(path, profile)
        supported = True
    else:
        identity = read_rom_identity(path)
        try:
            validate_rom(path, profile)
        except UnsupportedRomError:
            supported = False
        else:
            supported = True

    data = path.read_bytes()
    header = NdsHeader.from_bytes(data)
    fat = parse_fat(data, header)
    fnt = parse_fnt(data, header, fat_entry_count=len(fat))
    arm9_overlays = parse_arm9_overlays(data, header)
    arm7_overlays = parse_arm7_overlays(data, header)
    mismatches = _layout_mismatches(
        header,
        profile,
        file_count=len(fat),
        directory_count=len(fnt.directories),
        arm9_overlay_count=len(arm9_overlays),
        arm7_overlay_count=len(arm7_overlays),
    )
    return RomInspection(
        source_path=path,
        identity=identity,
        profile_id=profile.id,
        supported=supported,
        header=header,
        fat=fat,
        fnt=fnt,
        arm9_overlays=arm9_overlays,
        arm7_overlays=arm7_overlays,
        layout_mismatches=mismatches,
    )
```

During implementation, format `_layout_mismatches` across lines so `ruff format` produces the canonical layout. Do not change any names or signatures shown above.

- [ ] **Step 4: Run report tests and correct the test construction**

Because `RomInspection` is frozen and slotted behavior is not guaranteed, replace the `broken` construction in the second test with `dataclasses.replace`:

```python
from dataclasses import replace

broken = replace(
    inspection,
    fnt=FntTree(
        directories=inspection.fnt.directories,
        files=(FntFile(0, "a.bin"),),
    ),
)
```

Run:

```bash
python -m pytest tests/unit/test_inspection.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/bakugan_ds/inspection.py tests/unit/test_inspection.py
git commit -m "feat: compose deterministic ROM inspection reports"
```

---

### Task 8: Command-Line Inspector and Exit Codes

**Files:**
- Replace: `src/bakugan_ds/cli.py`
- Create: `tests/unit/test_cli.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `load_profile`, `inspect_rom`
- Produces: `build_parser() -> argparse.ArgumentParser`
- Produces: `main(argv: Sequence[str] | None = None) -> int`
- CLI command: `bakugan-ds inspect ROM [--profile PATH] [--output PATH] [--allow-unsupported]`
- Exit codes: `0` success, `2` user/argument error, `3` unsupported ROM, `4` malformed ROM/profile, `5` filesystem error

- [ ] **Step 1: Write CLI tests**

Create `tests/unit/test_cli.py`:

```python
from pathlib import Path

import pytest

from bakugan_ds import cli


def test_cli_requires_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_cli_reports_missing_rom(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    result = cli.main(["inspect", str(tmp_path / "missing.nds")])

    assert result == 5
    assert "missing.nds" in capsys.readouterr().err


def test_cli_writes_report_from_mocked_inspection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    rom_path = tmp_path / "game.nds"
    rom_path.write_bytes(b"x")
    output_path = tmp_path / "report.json"

    class FakeInspection:
        def to_json(self) -> str:
            return '{"supported": true}\n'

    monkeypatch.setattr(cli, "load_profile", lambda path: object())
    monkeypatch.setattr(cli, "inspect_rom", lambda path, profile, require_supported: FakeInspection())

    result = cli.main([
        "inspect",
        str(rom_path),
        "--profile",
        "config/b6re_rev0.json",
        "--output",
        str(output_path),
    ])

    assert result == 0
    assert output_path.read_text(encoding="utf-8") == '{"supported": true}\n'
```

- [ ] **Step 2: Run tests to verify the temporary CLI fails**

Run:

```bash
python -m pytest tests/unit/test_cli.py -v
```

Expected: tests fail because the temporary CLI accepts no arguments and emits no errors.

- [ ] **Step 3: Implement the complete CLI**

Replace `src/bakugan_ds/cli.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from collections.abc import Sequence

from bakugan_ds.errors import BakuganDSError, ProfileError, RomFormatError, UnsupportedRomError
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import load_profile

DEFAULT_PROFILE = Path("config/b6re_rev0.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bakugan-ds")
    subparsers = parser.add_subparsers(dest="command")
    inspect_parser = subparsers.add_parser("inspect", help="inspect Nintendo DS ROM structures")
    inspect_parser.add_argument("rom", type=Path)
    inspect_parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    inspect_parser.add_argument("--output", type=Path)
    inspect_parser.add_argument(
        "--allow-unsupported",
        action="store_true",
        help="parse a ROM that does not match the selected profile",
    )
    return parser


def _write_report(report: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(report)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(report, encoding="utf-8")
    temporary.replace(output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_usage(sys.stderr)
        return 2
    try:
        if arguments.command == "inspect":
            profile = load_profile(arguments.profile)
            inspection = inspect_rom(
                arguments.rom,
                profile,
                require_supported=not arguments.allow_unsupported,
            )
            _write_report(inspection.to_json(), arguments.output)
            return 0
    except UnsupportedRomError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (ProfileError, RomFormatError) as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 5
    except BakuganDSError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    parser.error(f"unknown command: {arguments.command}")
    return 2
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
python -m pytest tests/unit/test_cli.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Add README CLI usage**

Append to `README.md`:

```markdown
## Inspect a ROM

```bash
bakugan-ds inspect "/path/to/Bakugan - Battle Brawlers.nds"
```

Write a deterministic JSON report:

```bash
bakugan-ds inspect "/path/to/game.nds" --output reports/rom.json
```

Inspection rejects any ROM that does not exactly match the supported profile.
`--allow-unsupported` permits read-only structural inspection and clearly marks
the report as unsupported; it must never be used by future write commands.
```

- [ ] **Step 6: Run the entire unit suite and static checks**

Run:

```bash
python -m pytest tests/unit -v
ruff check .
ruff format --check .
mypy src
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add src/bakugan_ds/cli.py tests/unit/test_cli.py README.md
git commit -m "feat: add the ROM inspection CLI"
```

---

### Task 9: Exact Reference-ROM Integration Test

**Files:**
- Create: `tests/integration/test_reference_rom.py`
- Modify: `pyproject.toml`
- Modify: `README.md`

**Interfaces:**
- Consumes: environment variable `BAKUGAN_DS_ROM`
- Verifies exact supported-ROM identity and verified layout values
- Produces no repository fixture or copyrighted output

- [ ] **Step 1: Register the integration marker**

Add to `[tool.pytest.ini_options]` in `pyproject.toml`:

```toml
markers = [
  "integration: requires a user-supplied reference ROM",
]
```

- [ ] **Step 2: Write the optional exact-ROM integration test**

Create `tests/integration/test_reference_rom.py`:

```python
import os
from pathlib import Path

import pytest

from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import load_profile


@pytest.fixture(scope="module")
def reference_rom() -> Path:
    value = os.environ.get("BAKUGAN_DS_ROM")
    if value is None:
        pytest.skip("set BAKUGAN_DS_ROM to run reference-ROM integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"BAKUGAN_DS_ROM does not point to a file: {path}")
    return path


@pytest.mark.integration
def test_reference_rom_matches_verified_structure(reference_rom: Path) -> None:
    profile = load_profile(Path("config/b6re_rev0.json"))
    inspection = inspect_rom(reference_rom, profile, require_supported=True)

    assert inspection.supported is True
    assert inspection.identity.sha256 == profile.sha256
    assert inspection.header.arm9_offset == 0x4000
    assert inspection.header.arm9_ram_address == 0x02000000
    assert inspection.header.arm9_size == 448192
    assert inspection.header.arm7_offset == 0x0D8A00
    assert inspection.header.arm7_ram_address == 0x02380000
    assert inspection.header.arm7_size == 160048
    assert inspection.header.fnt_offset == 0x0FFD00
    assert inspection.header.fnt_size == 212348
    assert inspection.header.fat_offset == 0x133A00
    assert inspection.header.fat_size == 88040
    assert len(inspection.fat) == 11005
    assert len(inspection.fnt.directories) == 95
    assert len(inspection.arm9_overlays) == 9
    assert len(inspection.arm7_overlays) == 0
    assert inspection.layout_mismatches == ()

    overlay_7 = next(item for item in inspection.arm9_overlays if item.overlay_id == 7)
    assert overlay_7.ram_address == 0x0221A1C0
    assert overlay_7.ram_size == 467360
    assert overlay_7.bss_size == 1600
    assert overlay_7.compressed_size == 255740
```

- [ ] **Step 3: Run the suite without a ROM**

Run:

```bash
python -m pytest -v
```

Expected: all unit tests pass and the integration test is skipped with the documented reason.

- [ ] **Step 4: Run the integration test with the local ROM**

Run:

```bash
BAKUGAN_DS_ROM="/absolute/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds" \
python -m pytest tests/integration/test_reference_rom.py -v
```

Expected: 1 test passes. If any verified number differs, stop and reconcile the ROM profile or parser; do not weaken the assertion.

- [ ] **Step 5: Generate and inspect a real report**

Run:

```bash
BAKUGAN_DS_ROM="/absolute/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds"
bakugan-ds inspect "$BAKUGAN_DS_ROM" --output reports/reference-rom.json
python -m json.tool reports/reference-rom.json >/dev/null
```

Expected:

- CLI exits 0.
- `reports/reference-rom.json` is valid JSON.
- `supported` is `true`.
- counts are `11005` files, `95` directories, `9` ARM9 overlays, `0` ARM7 overlays.
- `layout_mismatches` is empty.

- [ ] **Step 6: Document integration-test usage**

Append to `README.md`:

```markdown
## Reference-ROM integration test

The unit suite uses only synthetic fixtures. To test against the supported ROM
without copying it into the repository:

```bash
BAKUGAN_DS_ROM="/absolute/path/to/game.nds" python -m pytest -m integration -v
```

The ROM path and generated reports are ignored by Git.
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml README.md tests/integration/test_reference_rom.py
git commit -m "test: verify the exact Bakugan DS reference ROM"
```

---

### Task 10: Verified Analysis Baseline and Milestone Documentation

**Files:**
- Create: `analysis/memory-map.yaml`
- Create: `analysis/overlays.yaml`
- Create: `analysis/symbols/.gitkeep`
- Create: `analysis/functions/.gitkeep`
- Create: `docs/rom-map.md`
- Create: `docs/reverse-engineering-workflow.md`
- Create: `tests/unit/test_analysis_metadata.py`

**Interfaces:**
- Produces source-controlled verified metadata for later extraction and disassembler import tasks
- Confidence values are restricted to `confirmed`, `probable`, or `candidate`
- Milestone 1 uses only `confirmed` for header-derived facts

- [ ] **Step 1: Write metadata consistency tests**

Create `tests/unit/test_analysis_metadata.py` without adding a YAML dependency by checking the exact required text and JSON-compatible numeric values:

```python
from pathlib import Path


def test_memory_map_contains_verified_addresses() -> None:
    text = Path("analysis/memory-map.yaml").read_text(encoding="utf-8")
    for required in (
        "game_code: B6RE",
        "arm9_ram_address: 0x02000000",
        "arm7_ram_address: 0x02380000",
        "overlay_load_address: 0x0221A1C0",
        "confidence: confirmed",
    ):
        assert required in text


def test_overlay_metadata_records_all_nine_ids() -> None:
    text = Path("analysis/overlays.yaml").read_text(encoding="utf-8")
    for overlay_id in range(9):
        assert f"- overlay_id: {overlay_id}\n" in text
    assert "overlay_id: 7" in text
    assert "ram_size: 467360" in text
    assert "bss_size: 1600" in text
    assert "compressed_size: 255740" in text


def test_reverse_engineering_workflow_defines_confidence_levels() -> None:
    text = Path("docs/reverse-engineering-workflow.md").read_text(encoding="utf-8")
    assert "## Confirmed" in text
    assert "## Probable" in text
    assert "## Candidate" in text
    assert "runtime address" in text
    assert "component-relative offset" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_analysis_metadata.py -v
```

Expected: 3 tests fail because the metadata files do not exist.

- [ ] **Step 3: Create the memory map baseline**

Create `analysis/memory-map.yaml`:

```yaml
rom_profile: b6re_rev0
game_code: B6RE
revision: 0
confidence: confirmed
arm9:
  rom_offset: 0x00004000
  ram_address: 0x02000000
  size: 448192
arm7:
  rom_offset: 0x000D8A00
  ram_address: 0x02380000
  size: 160048
nitrofs:
  fnt_offset: 0x000FFD00
  fnt_size: 212348
  fat_offset: 0x00133A00
  fat_size: 88040
  file_count: 11005
  directory_count: 95
overlays:
  arm9_count: 9
  arm7_count: 0
  overlay_load_address: 0x0221A1C0
notes:
  - Header and table-derived values are confirmed by exact-ROM integration tests.
  - Overlay responsibilities are not confirmed by these values.
```

- [ ] **Step 4: Create overlay metadata from the real inspection report**

Run the CLI against the local ROM and extract the nine `arm9_overlays` records from `reports/reference-rom.json`. Create `analysis/overlays.yaml` with this schema for every overlay ID 0 through 8:

```yaml
rom_profile: b6re_rev0
confidence: confirmed
overlays:
  - overlay_id: 0
    file_id: <decimal value from report>
    ram_address: 0x0221A1C0
    ram_size: <decimal value from report>
    bss_size: <decimal value from report>
    static_init_start: <hex value from report>
    static_init_end: <hex value from report>
    compressed_size: <decimal value from report>
    flags: <decimal value from report>
```

For overlay 7, the committed record must contain:

```yaml
  - overlay_id: 7
    file_id: <exact decimal file ID from the generated report>
    ram_address: 0x0221A1C0
    ram_size: 467360
    bss_size: 1600
    static_init_start: <exact hex value from the generated report>
    static_init_end: <exact hex value from the generated report>
    compressed_size: 255740
    flags: <exact decimal flags value from the generated report>
```

Do not infer or fabricate the values represented above by angle brackets. Copy them from the deterministic report produced by the implemented parser. This is the only step in the plan that intentionally depends on exact values discovered from the user-supplied ROM rather than values already present in the approved specification.

- [ ] **Step 5: Create documentation directories and verified ROM map**

Create empty files:

```bash
mkdir -p analysis/symbols analysis/functions
: > analysis/symbols/.gitkeep
: > analysis/functions/.gitkeep
```

Create `docs/rom-map.md` with:

```markdown
# Verified ROM Map

## Supported image

- Profile: `b6re_rev0`
- Internal title: `BAKUGAN W`
- Game code: `B6RE`
- Revision: `0`
- Size: `134217728` bytes
- SHA-256: `7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b`

## Executables

| Component | ROM offset | RAM address | Size |
|---|---:|---:|---:|
| ARM9 | `0x00004000` | `0x02000000` | `448192` |
| ARM7 | `0x000D8A00` | `0x02380000` | `160048` |

## NitroFS

| Structure | ROM offset | Size |
|---|---:|---:|
| FNT | `0x000FFD00` | `212348` |
| FAT | `0x00133A00` | `88040` |

The FAT contains `11005` file records. The FNT contains `95` directories.

## Overlays

The ARM9 overlay table contains nine entries. The ARM7 overlay table is empty.
All nine ARM9 overlays declare the load address `0x0221A1C0`, so runtime
addresses must always be paired with an overlay ID and component-relative
offset.

Overlay 7 is the largest known executable overlay:

- RAM size: `467360` bytes
- BSS size: `1600` bytes
- compressed payload size: `255740` bytes

These facts do not establish that overlay 7 is the battle engine. That remains
a candidate hypothesis until runtime call paths and controlled patches verify it.
```

- [ ] **Step 6: Document evidence and confidence rules**

Create `docs/reverse-engineering-workflow.md`:

```markdown
# Reverse-Engineering Evidence Workflow

Every symbol, structure, and behavioral claim must include an overlay or
executable component, a runtime address, a component-relative offset, and one
of the confidence levels below.

## Confirmed

Use `confirmed` only when behavior is demonstrated by runtime observation,
a controlled reversible patch, an exact documented file format, or immutable
ROM metadata verified by tests.

## Probable

Use `probable` when static evidence is strong and multiple references agree,
but no controlled runtime demonstration has been completed.

## Candidate

Use `candidate` for search results, strings, call sites, data regions, or
hypotheses that are useful investigation leads but remain unverified.

## Address notation

ARM9 symbols record the runtime address and the relative offset from
`0x02000000`. Overlay symbols record the overlay ID, runtime address, and
component-relative offset from that overlay's declared load address. Because
all current ARM9 overlays share `0x0221A1C0`, a runtime address alone is
ambiguous and must never be used as a unique identifier.

## Promotion rule

A candidate may become probable after static cross-reference analysis. A
probable symbol becomes confirmed only after a controlled runtime observation
or patch demonstrates its behavior. Documentation must retain the evidence
used for promotion.
```

- [ ] **Step 7: Run metadata tests and full verification**

Run:

```bash
python -m pytest tests/unit/test_analysis_metadata.py -v
python -m pytest -v
ruff check .
ruff format --check .
mypy src
```

Expected: all unit tests pass; the reference-ROM integration test either passes when configured or skips cleanly.

- [ ] **Step 8: Manually verify Milestone 1 CLI output**

Run:

```bash
bakugan-ds --help
bakugan-ds inspect "$BAKUGAN_DS_ROM" --output reports/final-milestone-1.json
python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path("reports/final-milestone-1.json").read_text())
assert payload["supported"] is True
assert payload["counts"] == {
    "arm7_overlays": 0,
    "arm9_overlays": 9,
    "directories": 95,
    "files": 11005,
}
assert payload["layout_mismatches"] == []
print("Milestone 1 report verified")
PY
```

Expected: prints `Milestone 1 report verified`.

- [ ] **Step 9: Commit**

```bash
git add analysis docs/rom-map.md docs/reverse-engineering-workflow.md tests/unit/test_analysis_metadata.py
git commit -m "docs: record the verified Bakugan DS ROM map"
```

---

## Final Milestone 1 Verification

- [ ] Run the complete automated suite:

```bash
python -m pytest -v
ruff check .
ruff format --check .
mypy src
```

Expected: all available tests pass; integration tests skip only when `BAKUGAN_DS_ROM` is unset.

- [ ] Run the exact-ROM integration suite:

```bash
BAKUGAN_DS_ROM="/absolute/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds" \
python -m pytest -m integration -v
```

Expected: 1 integration test passes.

- [ ] Run a clean CLI inspection:

```bash
rm -rf reports
bakugan-ds inspect "$BAKUGAN_DS_ROM" --output reports/reference.json
python -m json.tool reports/reference.json >/dev/null
```

Expected: successful JSON validation and no temporary output file remains.

- [ ] Confirm repository hygiene:

```bash
git status --short
git ls-files | grep -E '\.(nds|sav|bin)$' && exit 1 || true
```

Expected: clean working tree and no ROM, save, or binary asset tracked.

- [ ] Create the milestone completion commit only if verification produced documentation corrections:

```bash
git add -A
git commit -m "chore: complete milestone 1 ROM inspection foundation"
```

Skip this commit when the working tree is already clean.

## Plan Self-Review

- **Spec coverage:** This plan covers Milestone 1 only: project initialization, exact profile validation, NDS header parsing, FAT parsing, FNT parsing, overlay parsing, deterministic inspection reports, CLI behavior, optional exact-ROM integration tests, and verified documentation. Compression, extraction, rebuilding, patches, and gameplay analysis remain in later plans.
- **Placeholder scan:** No implementation step contains `TBD`, `TODO`, or an instruction to invent behavior. The only values not copied into the plan are overlay-table fields that must be read from the exact deterministic report; the step explicitly prohibits guessing and defines the source and schema.
- **Type consistency:** Parser signatures and model names are consistent across tasks. `inspect_rom` consumes the exact outputs produced by Tasks 2–6. The CLI and integration tests call the same `load_profile` and `inspect_rom` interfaces.
