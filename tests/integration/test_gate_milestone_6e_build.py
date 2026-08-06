from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from bakugan_ds.compression.blz import decompress_blz
from bakugan_ds.gates.authoring import approved_juggernoid_record
from bakugan_ds.gates.install import (
    ARENA_LOW_EXPECTED,
    ARENA_LOW_OFFSET,
    ARENA_LOW_REPLACEMENT,
    install_milestone_6d,
    install_milestone_6e,
)
from bakugan_ds.gates.record import TRAILER_SIZE, parse_trailer
from bakugan_ds.gates.runtime_module_6d import build_milestone_6d_module
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import RomProfile
from bakugan_ds.workspace.manifest import WorkspaceManifest, sha256_bytes
from bakugan_ds.workspace.rebuild import RebuildOptions, rebuild_rom

AUTHORING = Path("config/gates/milestone-6e-system2-v1.json")
MILESTONE_6D_AUTHORING = Path("config/gates/milestone-6d-system2-v1.json")
CORE_PATCH = Path("patches/core-g-compression-400.json")
SOURCE_ROM_SHA256 = "7b8f0ac330d3bff7cf2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b"
REBUILT_ROM_SHA256 = "fbddc21f08dc26d71ac540e57c2dfef0013fc0e5093ebc19cbed151ff52a68aa"
BUILD_REPORT_SHA256 = "47f4f5e1078849f44c79ad2c6a7afa72db32a83615a2c7333c6d0f33c96a927f"
MODULE_SHA256 = "8fa90c244d3710479e94903e099f9dbbe71b5ce8d86c52603383d2e4f42e7a1c"
OVERLAY_SHA256 = "748574da0d20ceb99b4ea48f848cab62b1139e5c4398f9d95a29adbc6dce5121"
RAW_CARRIER_SHA256 = "18e1ec4c56a52c4126c67bd20cb073b23b9da81deb0477089ab6469490179c6f"
STORED_ARM9_SHA256 = "95494c52cb94c85f7209ddf00fd37b6289fdecd6ad855f734132b3f840236f8"


def _payload(data: bytes, inspection, file_id: int) -> bytes:
    entry = inspection.fat[file_id]
    return data[entry.start : entry.end]


@pytest.mark.integration
def test_exact_milestone_6e_install_and_rebuild_are_deterministic(
    reference_rom: Path,
    reference_profile: RomProfile,
    reference_workspace: tuple[Path, WorkspaceManifest],
    tmp_path: Path,
) -> None:
    source_workspace, _manifest = reference_workspace
    workspace = tmp_path / "workspace"
    shutil.copytree(source_workspace, workspace, copy_function=shutil.copyfile)
    install = install_milestone_6e(workspace, AUTHORING)
    assert install.no_op is False
    assert install.module_sha256 == MODULE_SHA256
    assert install_milestone_6e(workspace, AUTHORING).no_op is True

    first = tmp_path / "milestone-6e-a.nds"
    second = tmp_path / "milestone-6e-b.nds"
    first_report = rebuild_rom(reference_rom, reference_profile, workspace, RebuildOptions(first))
    second_report = rebuild_rom(reference_rom, reference_profile, workspace, RebuildOptions(second))

    upgraded_workspace = tmp_path / "milestone-6d-workspace"
    shutil.copytree(source_workspace, upgraded_workspace, copy_function=os.link)
    install_milestone_6d(upgraded_workspace, MILESTONE_6D_AUTHORING)
    upgraded = install_milestone_6e(upgraded_workspace, AUTHORING)
    assert upgraded.no_op is False
    third = tmp_path / "milestone-6e-from-6d.nds"
    third_report = rebuild_rom(
        reference_rom,
        reference_profile,
        upgraded_workspace,
        RebuildOptions(third),
    )

    source = reference_rom.read_bytes()
    first_data = first.read_bytes()
    second_data = second.read_bytes()
    third_data = third.read_bytes()

    assert sha256_bytes(source) == SOURCE_ROM_SHA256
    assert first_data == second_data == third_data
    assert len(first_data) == len(source) == 134_217_728
    assert first_report.output_sha256 == second_report.output_sha256
    assert first_report.output_sha256 == third_report.output_sha256 == REBUILT_ROM_SHA256
    assert sha256_bytes(first.with_suffix(".nds.build.json").read_bytes()) == BUILD_REPORT_SHA256
    assert first.with_suffix(".nds.build.json").read_bytes() == second.with_suffix(
        ".nds.build.json"
    ).read_bytes()
    assert [(change.kind, change.identifier) for change in first_report.changes] == [
        ("arm9", "arm9"),
        ("nitrofs_raw", "font/mes_CardName.mes"),
        ("overlay", "7"),
    ]

    original = inspect_rom(reference_rom, reference_profile, require_supported=True)
    rebuilt = inspect_rom(first, reference_profile, require_supported=False)
    assert rebuilt.layout_mismatches == ()
    changed_ids = {7, 2762}
    for old, new in zip(original.fat, rebuilt.fat, strict=True):
        if old.file_id not in changed_ids:
            assert source[old.start : old.end] == first_data[new.start : new.end]

    carrier = _payload(first_data, rebuilt, 2762)
    assert len(carrier) == 6992
    assert sha256_bytes(carrier) == RAW_CARRIER_SHA256
    _header, records = parse_trailer(carrier[-TRAILER_SIZE:])
    assert len(records) == 103
    assert records[18] == approved_juggernoid_record()
    assert all(record.archetype != 0 for record in records)

    overlay_entry = next(item for item in rebuilt.arm9_overlays if item.overlay_id == 7)
    overlay = _payload(first_data, rebuilt, overlay_entry.file_id)
    module = build_milestone_6d_module()
    assert overlay_entry.ram_size == 0x7A7E0
    assert overlay_entry.bss_size == 0x40
    assert sha256_bytes(overlay) == OVERLAY_SHA256
    assert module.sha256 == MODULE_SHA256
    assert overlay[0x727E0:0x7A7E0] == module.image
    for hook in module.hook_replacements:
        assert overlay[hook.component_offset : hook.component_offset + len(hook.replacement)] == (
            hook.replacement
        )

    core_patch = json.loads(CORE_PATCH.read_text(encoding="utf-8"))
    for patch in core_patch["patches"]:
        replacement = bytes.fromhex(patch["replacement"])
        offset = patch["offset"]
        assert overlay[offset : offset + len(replacement)] == replacement

    original_arm9 = source[
        original.header.arm9_offset : original.header.arm9_offset + original.header.arm9_size
    ]
    rebuilt_arm9 = first_data[
        rebuilt.header.arm9_offset : rebuilt.header.arm9_offset + rebuilt.header.arm9_size
    ]
    assert sha256_bytes(rebuilt_arm9) == STORED_ARM9_SHA256
    old_decoded = decompress_blz(original_arm9)
    new_decoded = decompress_blz(rebuilt_arm9)
    assert old_decoded[ARENA_LOW_OFFSET : ARENA_LOW_OFFSET + 4] == ARENA_LOW_EXPECTED
    assert new_decoded[ARENA_LOW_OFFSET : ARENA_LOW_OFFSET + 4] == ARENA_LOW_REPLACEMENT
    assert old_decoded[:ARENA_LOW_OFFSET] == new_decoded[:ARENA_LOW_OFFSET]
    assert old_decoded[ARENA_LOW_OFFSET + 4 :] == new_decoded[ARENA_LOW_OFFSET + 4 :]
