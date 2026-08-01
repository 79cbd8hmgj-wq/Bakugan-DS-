from pathlib import Path

import pytest

from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import RomProfile
from bakugan_ds.workspace.extract import ExtractionOptions, extract_workspace
from bakugan_ds.workspace.manifest import WorkspaceManifest, sha256_bytes


@pytest.mark.integration
def test_reference_rom_extracts_deterministically(
    reference_rom: Path,
    reference_profile: RomProfile,
    reference_workspace: tuple[Path, WorkspaceManifest],
    tmp_path: Path,
) -> None:
    first_root, first = reference_workspace
    second_root = tmp_path / "second"

    inspection = inspect_rom(reference_rom, reference_profile, require_supported=True)
    rom_data = reference_rom.read_bytes()
    second = extract_workspace(
        reference_rom,
        reference_profile,
        ExtractionOptions(second_root),
    )

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
