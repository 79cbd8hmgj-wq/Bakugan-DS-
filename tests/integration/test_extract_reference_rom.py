import os
from pathlib import Path

import pytest

from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import load_profile
from bakugan_ds.workspace.manifest import sha256_bytes
from bakugan_ds.workspace.extract import ExtractionOptions, extract_workspace


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
def test_reference_rom_extracts_deterministically(reference_rom: Path, tmp_path: Path) -> None:
    profile = load_profile(Path("config/b6re_rev0.json"))
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    inspection = inspect_rom(reference_rom, profile, require_supported=True)
    rom_data = reference_rom.read_bytes()
    first = extract_workspace(reference_rom, profile, ExtractionOptions(first_root))
    second = extract_workspace(reference_rom, profile, ExtractionOptions(second_root))

    assert len(first.files) == 10996
    assert sum(item.compression == "lz10" for item in first.files) == 8476
    assert len(first.overlays) == 9
    assert all(item.compression == "blz" for item in first.overlays)
    overlay_7 = next(item for item in first.overlays if item.overlay_id == 7)
    assert overlay_7.raw_size == 255740
    assert overlay_7.decoded_size == 467360
    assert (first_root / "original/decoded/overlays/overlay_007.bin").stat().st_size == 467360
    assert (first_root / "modified/overlays/overlay_007.bin").stat().st_size == 467360
    assert first.to_json() == second.to_json()
    for overlay in first.overlays:
        fat_entry = inspection.fat[overlay.file_id]
        direct = rom_data[fat_entry.start : fat_entry.end]
        assert overlay.raw_sha256 == sha256_bytes(direct)
        assert (
            first_root / "original/raw/overlays" / f"overlay_{overlay.overlay_id:03d}.bin"
        ).read_bytes() == direct
    for name in ("workspace.json", "files.json", "overlays.json"):
        assert (first_root / "manifests" / name).read_bytes() == (
            second_root / "manifests" / name
        ).read_bytes()
