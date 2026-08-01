from dataclasses import replace
import json
from pathlib import Path

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
        fnt_offset=0x0FFC00,
        fnt_size=212348,
        fat_offset=0x133A00,
        fat_size=16,
        arm9_overlay_offset=0x071800,
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
        arm9_overlays=(OverlayEntry(7, 0x02219440, 467360, 1600, 0, 0, 70, 0),),
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
    broken = replace(
        inspection,
        fnt=FntTree(
            directories=inspection.fnt.directories,
            files=(FntFile(0, "a.bin"),),
        ),
    )

    with pytest.raises(ValueError, match="FAT file IDs missing from FNT"):
        broken.to_dict()


def test_inspection_allows_unnamed_overlay_fat_entries() -> None:
    inspection = make_inspection()
    overlay_backed = replace(
        inspection,
        fnt=FntTree(
            directories=inspection.fnt.directories,
            files=(FntFile(0, "a.bin"),),
        ),
        arm9_overlays=(OverlayEntry(7, 0x02219440, 467360, 1600, 0, 0, 1, 0),),
    )

    payload = overlay_backed.to_dict()

    assert payload["files"][1]["path"] is None
    assert payload["files"][1]["overlay_ids"] == [7]
