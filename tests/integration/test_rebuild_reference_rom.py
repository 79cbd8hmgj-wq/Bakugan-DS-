from pathlib import Path

import pytest

from bakugan_ds.compression.lz10 import decompress_lz10
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import RomProfile, sha256_file
from bakugan_ds.workspace.manifest import WorkspaceManifest
from bakugan_ds.workspace.rebuild import RebuildOptions, rebuild_rom


def assert_unchanged_raw_payloads(
    source: bytes,
    source_inspection,
    output: bytes,
    output_inspection,
    changed_file_ids: set[int],
) -> None:
    assert len(source_inspection.fat) == len(output_inspection.fat)
    for source_entry, output_entry in zip(source_inspection.fat, output_inspection.fat, strict=True):
        assert source_entry.file_id == output_entry.file_id
        if source_entry.file_id in changed_file_ids:
            continue
        assert source[source_entry.start : source_entry.end] == output[
            output_entry.start : output_entry.end
        ]


@pytest.mark.integration
def test_reference_rom_rebuilds_exact_and_modified_variants(
    reference_rom: Path,
    reference_profile: RomProfile,
    reference_workspace: tuple[Path, WorkspaceManifest],
    tmp_path: Path,
) -> None:
    profile = reference_profile
    workspace, manifest = reference_workspace
    source = reference_rom.read_bytes()
    source_inspection = inspect_rom(reference_rom, profile, require_supported=True)

    exact_output = tmp_path / "exact.nds"
    exact_report = rebuild_rom(
        reference_rom,
        profile,
        workspace,
        RebuildOptions(exact_output),
    )
    assert exact_report.exact_copy is True
    assert exact_report.changes == ()
    assert exact_output.read_bytes() == source
    assert sha256_file(exact_output) == profile.sha256

    lz_entry = next(
        item
        for item in manifest.files
        if item.path == "Game/Gimmick/SetData/SetData_00_03.bin"
    )
    assert lz_entry.compression == "lz10"
    lz_modified = workspace / "modified/nitrofs" / lz_entry.path
    lz_modified.write_bytes(bytes.fromhex("01000000"))
    lz_output = tmp_path / "lz-modified.nds"
    lz_report = rebuild_rom(
        reference_rom,
        profile,
        workspace,
        RebuildOptions(lz_output),
    )
    assert [(item.kind, item.identifier, item.encoding) for item in lz_report.changes] == [
        ("nitrofs", lz_entry.path, "lz10")
    ]
    lz_data = lz_output.read_bytes()
    lz_inspection = inspect_rom(lz_output, profile, require_supported=False)
    assert lz_inspection.layout_mismatches == ()
    rebuilt_lz_fat = lz_inspection.fat[lz_entry.file_id]
    rebuilt_lz_raw = lz_data[rebuilt_lz_fat.start : rebuilt_lz_fat.end]
    assert decompress_lz10(rebuilt_lz_raw) == bytes.fromhex("01000000")
    assert_unchanged_raw_payloads(
        source,
        source_inspection,
        lz_data,
        lz_inspection,
        {lz_entry.file_id},
    )

    original_lz = workspace / "original/decoded/nitrofs" / lz_entry.path
    lz_modified.write_bytes(original_lz.read_bytes())
    overlay_entry = next(item for item in manifest.overlays if item.overlay_id == 7)
    overlay_path = workspace / "modified/overlays/overlay_007.bin"
    overlay_modified = bytearray(overlay_path.read_bytes())
    overlay_modified[0] ^= 0x01
    overlay_path.write_bytes(overlay_modified)
    overlay_output = tmp_path / "overlay-modified.nds"
    overlay_report = rebuild_rom(
        reference_rom,
        profile,
        workspace,
        RebuildOptions(overlay_output),
    )
    assert [(item.kind, item.identifier, item.encoding) for item in overlay_report.changes] == [
        ("overlay", "7", "uncompressed-overlay")
    ]
    overlay_data = overlay_output.read_bytes()
    overlay_inspection = inspect_rom(overlay_output, profile, require_supported=False)
    assert overlay_inspection.layout_mismatches == ()
    rebuilt_overlay = next(item for item in overlay_inspection.arm9_overlays if item.overlay_id == 7)
    rebuilt_overlay_fat = overlay_inspection.fat[rebuilt_overlay.file_id]
    assert rebuilt_overlay.flags == 0
    assert rebuilt_overlay.compressed_size == 0
    assert rebuilt_overlay_fat.size == overlay_entry.ram_size == 467360
    assert overlay_data[rebuilt_overlay_fat.start : rebuilt_overlay_fat.end] == bytes(
        overlay_modified
    )
    assert_unchanged_raw_payloads(
        source,
        source_inspection,
        overlay_data,
        overlay_inspection,
        {overlay_entry.file_id},
    )
