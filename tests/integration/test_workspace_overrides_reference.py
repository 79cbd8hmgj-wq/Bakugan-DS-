from __future__ import annotations

import shutil
from pathlib import Path

from bakugan_ds.nds.fat import parse_fat
from bakugan_ds.nds.fnt import parse_fnt
from bakugan_ds.nds.header import NdsHeader
from bakugan_ds.nds.overlays import parse_arm9_overlays
from bakugan_ds.profile import RomProfile
from bakugan_ds.workspace.manifest import WorkspaceManifest, sha256_bytes
from bakugan_ds.workspace.model import WorkspaceLayout
from bakugan_ds.workspace.overrides import (
    BuildOverrides,
    OverlayLayoutOverride,
    RawNitroFsOverride,
    write_build_overrides,
)
from bakugan_ds.workspace.rebuild import RebuildOptions, rebuild_rom


def test_reference_raw_and_overlay_overrides_preserve_unrelated_payloads(
    reference_rom: Path,
    reference_profile: RomProfile,
    reference_workspace: tuple[Path, WorkspaceManifest],
    tmp_path: Path,
) -> None:
    source_workspace, manifest = reference_workspace
    workspace = tmp_path / "workspace"
    shutil.copytree(source_workspace, workspace, copy_function=shutil.copyfile)
    layout = WorkspaceLayout.from_root(workspace)

    carrier = next(item for item in manifest.files if item.file_id == 2762)
    carrier_relative = Path(*carrier.path.split("/"))
    original_raw = (layout.original_raw_nitrofs / carrier_relative).read_bytes()
    replacement_raw = original_raw + b"TEST"
    raw_output = layout.modified_raw_nitrofs / carrier_relative
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_bytes(replacement_raw)

    overlay_manifest = next(item for item in manifest.overlays if item.overlay_id == 7)
    overlay_path = layout.modified_overlays / "overlay_007.bin"
    original_overlay = overlay_path.read_bytes()
    replacement_overlay = original_overlay + (b"\0" * 0x640) + (b"\0" * 0x8000)
    assert len(replacement_overlay) == 0x7A7E0
    overlay_path.write_bytes(replacement_overlay)

    write_build_overrides(
        layout.build_overrides,
        BuildOverrides(
            1,
            "b6re_rev0",
            (
                RawNitroFsOverride(
                    carrier.file_id,
                    carrier.path,
                    len(original_raw),
                    sha256_bytes(original_raw),
                    len(replacement_raw),
                    sha256_bytes(replacement_raw),
                ),
            ),
            (
                OverlayLayoutOverride(
                    7,
                    overlay_manifest.ram_size,
                    overlay_manifest.bss_size,
                    len(replacement_overlay),
                    0x40,
                    0,
                ),
            ),
        ),
    )

    output = tmp_path / "overridden.nds"
    rebuild_rom(
        reference_rom,
        reference_profile,
        workspace,
        RebuildOptions(output),
    )

    source = reference_rom.read_bytes()
    rebuilt = output.read_bytes()
    source_header = NdsHeader.from_bytes(source)
    rebuilt_header = NdsHeader.from_bytes(rebuilt)
    source_fat = parse_fat(source, source_header)
    rebuilt_fat = parse_fat(rebuilt, rebuilt_header)
    assert len(rebuilt_fat) == len(source_fat)
    assert parse_fnt(rebuilt, rebuilt_header, len(rebuilt_fat)) == parse_fnt(
        source, source_header, len(source_fat)
    )
    overlays = {item.overlay_id: item for item in parse_arm9_overlays(rebuilt, rebuilt_header)}
    assert overlays[7].ram_size == 0x7A7E0
    assert overlays[7].bss_size == 0x40
    assert overlays[7].flags == 0

    changed_ids = {2762, overlay_manifest.file_id}
    for original_entry, rebuilt_entry in zip(source_fat, rebuilt_fat, strict=True):
        if original_entry.file_id in changed_ids:
            continue
        assert source[original_entry.start : original_entry.end] == rebuilt[
            rebuilt_entry.start : rebuilt_entry.end
        ]
    assert rebuilt[rebuilt_fat[2762].start : rebuilt_fat[2762].end] == replacement_raw
    assert rebuilt[
        rebuilt_fat[overlay_manifest.file_id].start : rebuilt_fat[overlay_manifest.file_id].end
    ] == replacement_overlay
