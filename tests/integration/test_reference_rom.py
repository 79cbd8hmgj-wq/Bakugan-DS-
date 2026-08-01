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
    assert inspection.header.fnt_offset == 0x0FFC00
    assert inspection.header.fnt_size == 212348
    assert inspection.header.fat_offset == 0x133A00
    assert inspection.header.fat_size == 88040
    assert inspection.header.arm9_overlay_offset == 0x71800
    assert inspection.header.arm9_overlay_size == 288
    assert len(inspection.fat) == 11005
    assert len(inspection.fnt.files) == 10996
    assert len(inspection.fnt.directories) == 95
    assert len(inspection.arm9_overlays) == 9
    assert len(inspection.arm7_overlays) == 0
    assert inspection.layout_mismatches == ()

    overlay_7 = next(item for item in inspection.arm9_overlays if item.overlay_id == 7)
    assert overlay_7.file_id == 7
    assert overlay_7.ram_address == 0x02219440
    assert overlay_7.ram_size == 467360
    assert overlay_7.bss_size == 1600
    assert overlay_7.compressed_size == 255740
