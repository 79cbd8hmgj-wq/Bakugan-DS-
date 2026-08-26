from __future__ import annotations

from pathlib import Path

import pytest

from bakugan_ds.disassembly import find_module_params, overlay_layout_report
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.nds.overlays import parse_arm9_overlays


@pytest.mark.integration
def test_b6re_module_params_define_overlay_slot_boundary(reference_rom: Path) -> None:
    rom = reference_rom.read_bytes()
    header = NdsHeader.from_bytes(rom)
    arm9 = rom[header.arm9_offset : header.arm9_offset + header.arm9_size]

    params = find_module_params(arm9, base_address=header.arm9_ram_address)

    assert params is not None
    assert params.offset == 0xBA0
    assert params.address == 0x02000BA0
    assert params.compressed_static_end == 0x0206D6C0
    assert params.static_bss_end == 0x02219440

    overlays = parse_arm9_overlays(rom, header)
    report = overlay_layout_report(overlays, static_end=params.static_bss_end)

    assert report["after_static"] == list(range(9))
    assert report["shared_start_groups"] == [
        {"ram_address": 0x02219440, "overlay_ids": list(range(9))}
    ]
    assert report["load_relations"] == []
