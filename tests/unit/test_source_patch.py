from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bakugan_ds.compression.blz import compress_blz
from bakugan_ds.errors import WorkspaceError
from bakugan_ds.profile import LayoutExpectations, RomProfile
from bakugan_ds.source_patch import load_source_patch_manifest, resolve_source_target
from bakugan_ds.workspace.manifest import (
    ExtractedOverlay,
    WorkspaceManifest,
    sha256_bytes,
    write_json_atomic,
)
from bakugan_ds.workspace.model import WorkspaceLayout

TARGET_HASH = hashlib.sha256(b"target").hexdigest()
OVERLAY_BASE = 0x02219440


def _manifest_payload() -> dict[str, object]:
    return {
        "format_version": 1,
        "profile_id": "b6re_rev0",
        "target": "overlay:7",
        "runtime_address": 0x0221A000,
        "max_size": 0x100,
        "mode": "arm",
        "expected_runtime_sha256": TARGET_HASH,
        "sources": ["src/injected.c"],
        "definitions": {"known_helper": 0x02065BF4},
        "hooks": [
            {
                "id": "call_injected",
                "runtime_address": 0x0221B000,
                "expected": "000000ea",
                "symbol": "injected_entry",
                "link": True,
                "mode": "arm",
            }
        ],
    }


def _write_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "source-patch.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _profile(*, arm9_size: int = 0x1000) -> RomProfile:
    return RomProfile(
        id="b6re_rev0",
        sha256="0" * 64,
        size=1,
        title="BAKUGAN",
        game_code="B6RE",
        maker_code="20",
        revision=0,
        expected=LayoutExpectations(
            arm9_offset=0x4000,
            arm9_ram_address=0x02000000,
            arm9_size=arm9_size,
            arm7_offset=0,
            arm7_ram_address=0x02380000,
            arm7_size=0x200,
            fnt_offset=0,
            fnt_size=0,
            fat_offset=0,
            fat_size=0,
            arm9_overlay_offset=0,
            arm9_overlay_size=0,
            arm7_overlay_offset=0,
            arm7_overlay_size=0,
            nitrofs_file_count=0,
            directory_count=0,
            arm9_overlay_count=1,
            arm7_overlay_count=0,
        ),
    )


def _write_workspace(
    tmp_path: Path,
    *,
    overlay_data: bytes,
    arm9_data: bytes = b"\x00" * 0x1000,
    arm7_data: bytes = b"\x00" * 0x200,
) -> Path:
    root = tmp_path / "workspace"
    layout = WorkspaceLayout.from_root(root)
    for directory in layout.all_directories():
        directory.mkdir(parents=True, exist_ok=True)
    (layout.modified / "arm9.bin").write_bytes(arm9_data)
    (layout.modified / "arm7.bin").write_bytes(arm7_data)
    (layout.modified_overlays / "overlay_007.bin").write_bytes(overlay_data)
    manifest = WorkspaceManifest(
        format_version=1,
        profile_id="b6re_rev0",
        rom_sha256="0" * 64,
        rom_size=1,
        arm9_sha256=sha256_bytes(arm9_data),
        arm7_sha256=sha256_bytes(arm7_data),
        files=(),
        overlays=(
            ExtractedOverlay(
                overlay_id=7,
                file_id=7,
                ram_address=OVERLAY_BASE,
                ram_size=len(overlay_data),
                bss_size=0x100,
                raw_size=len(overlay_data),
                decoded_size=len(overlay_data),
                raw_sha256=sha256_bytes(overlay_data),
                decoded_sha256=sha256_bytes(overlay_data),
                compression="none",
            ),
        ),
    )
    write_json_atomic(layout.manifests / "workspace.json", manifest.to_dict())
    return root


def test_load_source_patch_manifest_normalizes_valid_payload(tmp_path: Path) -> None:
    manifest = load_source_patch_manifest(_write_manifest(tmp_path, _manifest_payload()))

    assert manifest.profile_id == "b6re_rev0"
    assert manifest.target == "overlay:7"
    assert manifest.runtime_address == 0x0221A000
    assert manifest.max_size == 0x100
    assert manifest.mode == "arm"
    assert manifest.expected_runtime_sha256 == TARGET_HASH
    assert manifest.sources == ("src/injected.c",)
    assert manifest.definitions == (("known_helper", 0x02065BF4),)
    assert manifest.hooks[0].expected == bytes.fromhex("000000ea")
    assert manifest.hooks[0].link is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("format_version", 2, "source patch format version"),
        ("profile_id", "", "profile_id"),
        ("target", "overlay:x", "target"),
        ("target", "nitrofs:file.bin", "target"),
        ("runtime_address", -1, "runtime_address"),
        ("runtime_address", 0x0221A002, "ARM aligned"),
        ("max_size", 0, "max_size"),
        ("mode", "mips", "mode"),
        ("expected_runtime_sha256", "bad", "SHA-256"),
    ],
)
def test_manifest_rejects_invalid_top_level_fields(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    payload = _manifest_payload()
    payload[field] = value

    with pytest.raises(WorkspaceError, match=message):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_source_path_traversal(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["sources"] = ["../escape.c"]

    with pytest.raises(WorkspaceError, match="unsafe path"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_duplicate_sources(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["sources"] = ["src/injected.c", "src/injected.c"]

    with pytest.raises(WorkspaceError, match="duplicate source"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_invalid_source_suffix(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["sources"] = ["src/injected.txt"]

    with pytest.raises(WorkspaceError, match="source suffix"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_invalid_definition_symbol(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["definitions"] = {"not-a-symbol": 0x02000000}

    with pytest.raises(WorkspaceError, match="definition symbol"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_duplicate_hook_ids(tmp_path: Path) -> None:
    payload = _manifest_payload()
    hook = dict(payload["hooks"][0])  # type: ignore[index]
    payload["hooks"] = [hook, hook]

    with pytest.raises(WorkspaceError, match="duplicate hook ID"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_malformed_hook_expected_bytes(tmp_path: Path) -> None:
    payload = _manifest_payload()
    hook = dict(payload["hooks"][0])  # type: ignore[index]
    hook["expected"] = "abc"
    payload["hooks"] = [hook]

    with pytest.raises(WorkspaceError, match="expected"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_non_boolean_hook_link(tmp_path: Path) -> None:
    payload = _manifest_payload()
    hook = dict(payload["hooks"][0])  # type: ignore[index]
    hook["link"] = 1
    payload["hooks"] = [hook]

    with pytest.raises(WorkspaceError, match="link"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_thumb_manifest_requires_halfword_alignment(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["mode"] = "thumb"
    payload["runtime_address"] = 0x0221A001

    with pytest.raises(WorkspaceError, match="Thumb aligned"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_resolve_overlay_target_maps_runtime_image_and_offsets(tmp_path: Path) -> None:
    overlay_data = bytes(index & 0xFF for index in range(0x3000))
    workspace = _write_workspace(tmp_path, overlay_data=overlay_data)
    payload = _manifest_payload()
    payload["expected_runtime_sha256"] = sha256_bytes(overlay_data)
    manifest = load_source_patch_manifest(_write_manifest(tmp_path, payload))

    target = resolve_source_target(workspace, manifest, _profile())

    assert target.runtime_base == OVERLAY_BASE
    assert target.runtime_image == overlay_data
    assert target.placement_offset == 0xBC0
    assert target.storage_encoding == "decoded-overlay"
    assert target.passthrough_length is None


def test_resolve_target_rejects_runtime_hash_mismatch(tmp_path: Path) -> None:
    workspace = _write_workspace(tmp_path, overlay_data=b"\x00" * 0x3000)
    manifest = load_source_patch_manifest(_write_manifest(tmp_path, _manifest_payload()))

    with pytest.raises(WorkspaceError, match="runtime SHA-256"):
        resolve_source_target(workspace, manifest, _profile())


def test_resolve_target_rejects_placement_outside_component(tmp_path: Path) -> None:
    overlay_data = b"\x00" * 0x1000
    workspace = _write_workspace(tmp_path, overlay_data=overlay_data)
    payload = _manifest_payload()
    payload["runtime_address"] = OVERLAY_BASE + 0xF80
    payload["max_size"] = 0x100
    payload["hooks"] = []
    payload["expected_runtime_sha256"] = sha256_bytes(overlay_data)
    manifest = load_source_patch_manifest(_write_manifest(tmp_path, payload))

    with pytest.raises(WorkspaceError, match="placement range"):
        resolve_source_target(workspace, manifest, _profile())


def test_resolve_target_rejects_hook_outside_component(tmp_path: Path) -> None:
    overlay_data = b"\x00" * 0x1000
    workspace = _write_workspace(tmp_path, overlay_data=overlay_data)
    payload = _manifest_payload()
    payload["runtime_address"] = OVERLAY_BASE
    payload["max_size"] = 0x100
    payload["expected_runtime_sha256"] = sha256_bytes(overlay_data)
    hook = dict(payload["hooks"][0])  # type: ignore[index]
    hook["runtime_address"] = OVERLAY_BASE + 0x1000
    payload["hooks"] = [hook]
    manifest = load_source_patch_manifest(_write_manifest(tmp_path, payload))

    with pytest.raises(WorkspaceError, match=r"hook.*outside"):
        resolve_source_target(workspace, manifest, _profile())


def test_resolve_blz_arm9_exposes_decoded_runtime_image(tmp_path: Path) -> None:
    decoded = (b"ARM9" * 0x800) + (b"\x00" * 0x1000)
    stored = compress_blz(decoded)
    workspace = _write_workspace(
        tmp_path,
        overlay_data=b"\x00" * 0x3000,
        arm9_data=stored,
    )
    payload = _manifest_payload()
    payload["target"] = "arm9"
    payload["runtime_address"] = 0x02000100
    payload["max_size"] = 0x80
    payload["hooks"] = []
    payload["expected_runtime_sha256"] = sha256_bytes(decoded)
    manifest = load_source_patch_manifest(_write_manifest(tmp_path, payload))

    target = resolve_source_target(
        workspace,
        manifest,
        _profile(arm9_size=len(stored)),
    )

    assert target.runtime_base == 0x02000000
    assert target.runtime_image == decoded
    assert target.placement_offset == 0x100
    assert target.storage_encoding == "blz"
    assert target.passthrough_length is not None
    assert target.stored_size == len(stored)
