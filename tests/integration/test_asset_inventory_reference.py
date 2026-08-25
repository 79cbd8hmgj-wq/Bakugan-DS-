from __future__ import annotations

from pathlib import Path

import pytest

from bakugan_ds.assets import inventory_assets
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import RomProfile


@pytest.mark.integration
def test_exact_b6re_nitro_asset_inventory(
    reference_rom: Path,
    reference_profile: RomProfile,
) -> None:
    inspection = inspect_rom(reference_rom, reference_profile, require_supported=True)
    inventory = inventory_assets(reference_rom.read_bytes(), inspection)
    payload = inventory.to_dict()

    assert payload["supported"] is True
    assert payload["counts"] == {
        "scanned_files": 10_996,
        "reported_files": 2_575,
        "recognized_assets": 2_575,
        "unknown_files": 8_421,
        "signed_mismatches": 0,
    }
    assert payload["formats"] == {
        "NSBMD": 678,
        "NSBTX": 587,
        "NTFP": 982,
        "NTFT": 327,
        "SDAT": 1,
    }
    assert payload["compressions"] == {"lz10": 2_574, "raw": 1}
