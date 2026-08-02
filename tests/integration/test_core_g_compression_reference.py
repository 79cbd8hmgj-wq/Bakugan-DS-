from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.patches.apply import apply_patch_set
from bakugan_ds.profile import RomProfile
from bakugan_ds.workspace.extract import ExtractionOptions, extract_workspace
from bakugan_ds.workspace.rebuild import RebuildOptions, rebuild_rom

PATCH_PATH = Path("patches/core-g-compression-400.json")
OVERLAY_SHA256 = "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"
OVERLAY_SIZE = 467360


def assert_unchanged_raw_payloads(
    source: bytes,
    source_inspection,
    output: bytes,
    output_inspection,
    changed_file_ids: set[int],
) -> None:
    assert len(source_inspection.fat) == len(output_inspection.fat)
    for source_entry, output_entry in zip(
        source_inspection.fat, output_inspection.fat, strict=True
    ):
        assert source_entry.file_id == output_entry.file_id
        if source_entry.file_id in changed_file_ids:
            continue
        assert source[source_entry.start : source_entry.end] == output[
            output_entry.start : output_entry.end
        ]


def clone_patch_target(source_workspace: Path, destination: Path) -> Path:
    (destination / "manifests").mkdir(parents=True)
    (destination / "modified/overlays").mkdir(parents=True)
    (destination / "manifests/workspace.json").write_bytes(
        (source_workspace / "manifests/workspace.json").read_bytes()
    )
    (destination / "modified/overlays/overlay_007.bin").write_bytes(
        (source_workspace / "modified/overlays/overlay_007.bin").read_bytes()
    )
    return destination


@pytest.mark.integration
def test_core_g_compression_patch_is_atomic_and_rebuilds_exact_overlay(
    reference_rom: Path,
    reference_profile: RomProfile,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    manifest = extract_workspace(
        reference_rom, reference_profile, ExtractionOptions(workspace)
    )
    overlay_entry = next(item for item in manifest.overlays if item.overlay_id == 7)
    overlay_path = workspace / "modified/overlays/overlay_007.bin"
    before = overlay_path.read_bytes()
    assert len(before) == OVERLAY_SIZE == overlay_entry.ram_size
    assert hashlib.sha256(before).hexdigest() == OVERLAY_SHA256

    patch_payload = json.loads(PATCH_PATH.read_text(encoding="utf-8"))
    expected_ranges = []
    for item in patch_payload["patches"]:
        start = item["offset"]
        expected = bytes.fromhex(item["expected"])
        assert before[start : start + len(expected)] == expected
        expected_ranges.append(range(start, start + len(expected)))

    stale_workspace = clone_patch_target(workspace, tmp_path / "stale-workspace")
    stale_overlay = stale_workspace / "modified/overlays/overlay_007.bin"
    stale_before = bytearray(stale_overlay.read_bytes())
    stale_before[patch_payload["patches"][1]["offset"]] ^= 0x01
    stale_overlay.write_bytes(stale_before)
    with pytest.raises(WorkspaceError, match="expected bytes"):
        apply_patch_set(stale_workspace, PATCH_PATH)
    assert stale_overlay.read_bytes() == bytes(stale_before)
    assert not (
        stale_workspace / "manifests/patch-core-g-compression-400.json"
    ).exists()

    report = apply_patch_set(workspace, PATCH_PATH)
    after = overlay_path.read_bytes()
    assert len(after) == len(before) == OVERLAY_SIZE
    assert [item.patch_id for item in report.applied] == [
        "preload-core-compression-constant",
        "compress-both-core-g-inputs",
        "restore-gate-scale-constant",
    ]

    changed = {
        index
        for index, pair in enumerate(zip(before, after, strict=True))
        if pair[0] != pair[1]
    }
    allowed = {index for declared in expected_ranges for index in declared}
    assert changed
    assert changed <= allowed
    for item in patch_payload["patches"]:
        start = item["offset"]
        replacement = bytes.fromhex(item["replacement"])
        assert after[start : start + len(replacement)] == replacement

    output = tmp_path / "core-g-compression.nds"
    build_report = rebuild_rom(
        reference_rom,
        reference_profile,
        workspace,
        RebuildOptions(output),
    )
    assert [
        (item.kind, item.identifier, item.encoding) for item in build_report.changes
    ] == [("overlay", "7", "uncompressed-overlay")]

    source = reference_rom.read_bytes()
    output_data = output.read_bytes()
    source_inspection = inspect_rom(
        reference_rom, reference_profile, require_supported=True
    )
    output_inspection = inspect_rom(
        output, reference_profile, require_supported=False
    )
    assert len(output_data) == len(source) == 134217728
    assert output_inspection.layout_mismatches == ()

    rebuilt_overlay = next(
        item for item in output_inspection.arm9_overlays if item.overlay_id == 7
    )
    rebuilt_fat = output_inspection.fat[rebuilt_overlay.file_id]
    assert rebuilt_overlay.ram_address == 0x02219440
    assert rebuilt_overlay.ram_size == OVERLAY_SIZE
    assert rebuilt_overlay.bss_size == overlay_entry.bss_size
    assert rebuilt_overlay.flags == 0
    assert rebuilt_overlay.compressed_size == 0
    assert rebuilt_fat.size == OVERLAY_SIZE
    assert output_data[rebuilt_fat.start : rebuilt_fat.end] == after
    assert_unchanged_raw_payloads(
        source,
        source_inspection,
        output_data,
        output_inspection,
        {overlay_entry.file_id},
    )
