from __future__ import annotations

from pathlib import Path

import pytest

from bakugan_ds.compression.blz import compress_blz, decompress_blz, is_blz
from bakugan_ds.profile import RomProfile
from bakugan_ds.source_apply import encode_target_storage
from bakugan_ds.source_patch import SourcePatchManifest, resolve_source_target
from bakugan_ds.workspace.manifest import WorkspaceManifest, sha256_bytes
from bakugan_ds.workspace.model import WorkspaceLayout


def _manifest(
    *,
    target: str,
    runtime_address: int,
    max_size: int,
    runtime_image: bytes,
) -> SourcePatchManifest:
    return SourcePatchManifest(
        format_version=1,
        profile_id="b6re_rev0",
        target=target,
        runtime_address=runtime_address,
        max_size=max_size,
        mode="arm",
        expected_runtime_sha256=sha256_bytes(runtime_image),
        sources=("src/injected.c",),
        definitions=(),
        hooks=(),
    )


@pytest.mark.integration
def test_exact_b6re_overlay7_source_patch_mapping(
    reference_workspace: tuple[Path, WorkspaceManifest],
    reference_profile: RomProfile,
) -> None:
    workspace, workspace_manifest = reference_workspace
    overlay = next(item for item in workspace_manifest.overlays if item.overlay_id == 7)
    layout = WorkspaceLayout.from_root(workspace)
    runtime_image = (layout.modified_overlays / "overlay_007.bin").read_bytes()

    manifest = _manifest(
        target="overlay:7",
        runtime_address=overlay.ram_address + 0x100,
        max_size=0x20,
        runtime_image=runtime_image,
    )
    target = resolve_source_target(workspace, manifest, reference_profile)

    assert overlay.ram_address == 0x02219440
    assert overlay.decoded_size == 467_360
    assert target.runtime_base == overlay.ram_address
    assert target.runtime_image == runtime_image
    assert target.placement_offset == 0x100
    assert target.storage_encoding == "decoded-overlay"


@pytest.mark.integration
def test_exact_b6re_arm9_blz_mapping_and_exact_size_reencode(
    reference_workspace: tuple[Path, WorkspaceManifest],
    reference_profile: RomProfile,
) -> None:
    workspace, _workspace_manifest = reference_workspace
    layout = WorkspaceLayout.from_root(workspace)
    stored = (layout.modified / "arm9.bin").read_bytes()

    assert len(stored) == reference_profile.expected.arm9_size
    assert is_blz(stored)
    runtime_image = decompress_blz(stored)
    manifest = _manifest(
        target="arm9",
        runtime_address=reference_profile.expected.arm9_ram_address,
        max_size=0x20,
        runtime_image=runtime_image,
    )
    target = resolve_source_target(workspace, manifest, reference_profile)

    assert target.runtime_base == 0x02000000
    assert target.storage_encoding == "blz"
    assert target.stored_size == len(stored)
    assert target.passthrough_length is not None
    encoded = encode_target_storage(target, runtime_image)
    assert len(encoded) == len(stored)
    assert decompress_blz(encoded) == runtime_image
    assert compress_blz(
        runtime_image,
        passthrough_length=target.passthrough_length,
        target_size=target.stored_size,
    ) == encoded
