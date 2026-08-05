from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bakugan_ds.compression.blz import compress_blz
from bakugan_ds.gates.runtime_module import build_milestone_6c_module
from bakugan_ds.workspace.manifest import (
    ExtractedFile,
    ExtractedOverlay,
    WorkspaceManifest,
)
from bakugan_ds.workspace.model import WorkspaceLayout

AUTHORING = Path("config/gates/milestone-6c-system2-v1.json")
AUTHORING_6D = Path("config/gates/milestone-6d-system2-v1.json")
EXPECTED_PATCH_IDS = {
    "gate-system2-gate-bonus-hook",
    "gate-system2-context-access-hook",
    "gate-system2-battle-type-selector-hook",
    "gate-system2-expanded-data-lookup-hook",
    "gate-system2-cache-load-hook",
    "gate-system2-cache-clear-hook",
    "gate-system2-arena-low",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _synthetic_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from bakugan_ds.patches.model import load_patch_set

    root = tmp_path / "workspace"
    layout = WorkspaceLayout.from_root(root)
    for directory in layout.all_directories():
        directory.mkdir(parents=True, exist_ok=True)

    carrier = b"\x10\x7c\x19\x00" + b"\0" * (2840 - 4)
    carrier_path = Path("font/mes_CardName.mes")
    raw_path = layout.original_raw_nitrofs / carrier_path
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(carrier)
    (layout.modified_nitrofs / carrier_path).parent.mkdir(parents=True, exist_ok=True)
    (layout.modified_nitrofs / carrier_path).write_bytes(b"decoded-placeholder")

    module = build_milestone_6c_module()
    original_overlay = bytearray(0x721A0)
    core_patch = load_patch_set(Path("patches/core-g-compression-400.json"))
    for patch in core_patch.patches:
        start = patch.offset
        original_overlay[start : start + len(patch.expected)] = patch.expected
    for hook in module.hook_replacements:
        original_overlay[hook.component_offset : hook.component_offset + len(hook.expected)] = (
            hook.expected
        )
    patched_overlay = bytearray(original_overlay)
    for patch in core_patch.patches:
        start = patch.offset
        assert patched_overlay[start : start + len(patch.expected)] == patch.expected
        patched_overlay[start : start + len(patch.replacement)] = patch.replacement
    original_overlay_bytes = bytes(original_overlay)
    patched_overlay_bytes = bytes(patched_overlay)
    (layout.original_decoded_overlays / "overlay_007.bin").write_bytes(original_overlay_bytes)
    (layout.modified_overlays / "overlay_007.bin").write_bytes(patched_overlay_bytes)

    decoded_arm9 = bytearray(0x7000)
    decoded_arm9[0x6264:0x6268] = bytes.fromhex("20bc2802")
    synthetic_passthrough = 0x6800
    minimal = compress_blz(
        decoded_arm9,
        passthrough_length=synthetic_passthrough,
    )
    stored_arm9 = compress_blz(
        decoded_arm9,
        passthrough_length=synthetic_passthrough,
        target_size=len(minimal) + 64,
    )
    (layout.original / "arm9.bin").write_bytes(stored_arm9)
    (layout.modified / "arm9.bin").write_bytes(stored_arm9)
    (layout.original / "arm7.bin").write_bytes(b"arm7")
    (layout.modified / "arm7.bin").write_bytes(b"arm7")

    manifest = WorkspaceManifest(
        format_version=1,
        profile_id="b6re_rev0",
        rom_sha256="0" * 64,
        rom_size=1,
        arm9_sha256=_sha(stored_arm9),
        arm7_sha256=_sha(b"arm7"),
        files=(
            ExtractedFile(
                file_id=2762,
                path=carrier_path.as_posix(),
                raw_size=len(carrier),
                decoded_size=len(b"decoded-placeholder"),
                compression="lz10",
                raw_sha256=_sha(carrier),
                decoded_sha256=_sha(b"decoded-placeholder"),
            ),
        ),
        overlays=(
            ExtractedOverlay(
                overlay_id=7,
                file_id=7,
                ram_address=0x02219440,
                ram_size=0x721A0,
                bss_size=0x640,
                raw_size=1,
                decoded_size=0x721A0,
                raw_sha256="1" * 64,
                decoded_sha256=_sha(original_overlay_bytes),
                compression="blz",
            ),
        ),
    )
    (layout.manifests / "workspace.json").write_text(manifest.to_json(), encoding="utf-8")
    readiness = tmp_path / "readiness.json"
    readiness.write_text(
        json.dumps(
            {
                "ready_for_milestone_6c": True,
                "deferred": ["arena_id"],
                "failures": [],
            }
        ),
        encoding="utf-8",
    )

    import bakugan_ds.gates.install as install

    monkeypatch.setattr(install, "REFERENCE_RAW_SHA256", _sha(carrier))
    monkeypatch.setattr(
        install,
        "REFERENCE_OVERLAY_SHA256",
        _sha(original_overlay_bytes),
    )
    monkeypatch.setattr(
        install,
        "CORE_PATCHED_OVERLAY_SHA256",
        _sha(patched_overlay_bytes),
    )
    monkeypatch.setattr(
        install,
        "ARM9_DECODED_SHA256",
        _sha(bytes(decoded_arm9)),
    )
    monkeypatch.setattr(
        install,
        "ARM9_REENCODE_PASSTHROUGH",
        synthetic_passthrough,
    )
    monkeypatch.setattr(install, "DEFAULT_READINESS_PATH", readiness)
    return root


def test_install_report_declares_every_atomic_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.gates.install import install_milestone_6c

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    report = install_milestone_6c(workspace, AUTHORING, dry_run=True)

    assert report.profile_id == "b6re_rev0"
    assert report.raw_override.file_id == 2762
    assert report.overlay_override.overlay_id == 7
    assert {patch.patch_id for patch in report.binary_patches} == EXPECTED_PATCH_IDS
    assert report.dry_run is True
    assert report.no_op is False
    assert report.cache_range == (0x02293C20, 0x02293C60)


def test_install_is_transactional_and_identical_reinstall_is_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.gates.install import install_milestone_6c

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    first = install_milestone_6c(workspace, AUTHORING)
    second = install_milestone_6c(workspace, AUTHORING)
    assert first.no_op is False
    assert second.no_op is True
    assert first.trailer_sha256 == second.trailer_sha256
    assert first.module_sha256 == second.module_sha256


def test_install_failure_leaves_workspace_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.errors import WorkspaceError
    from bakugan_ds.gates.install import install_milestone_6c

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    layout = WorkspaceLayout.from_root(workspace)
    before = (layout.modified / "arm9.bin").read_bytes()
    carrier = layout.original_raw_nitrofs / "font/mes_CardName.mes"
    carrier.write_bytes(carrier.read_bytes()[:-1] + b"X")

    with pytest.raises(WorkspaceError, match="carrier"):
        install_milestone_6c(workspace, AUTHORING)
    assert (layout.modified / "arm9.bin").read_bytes() == before
    assert not layout.build_overrides.exists()


def test_dry_run_rejects_non_core_g_overlay_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.errors import WorkspaceError
    from bakugan_ds.gates.install import install_milestone_6c

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    layout = WorkspaceLayout.from_root(workspace)
    original = (layout.original_decoded_overlays / "overlay_007.bin").read_bytes()
    (layout.modified_overlays / "overlay_007.bin").write_bytes(original)
    with pytest.raises(WorkspaceError, match="core-G baseline"):
        install_milestone_6c(workspace, AUTHORING, dry_run=True)


def test_install_rejects_wrong_workspace_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.errors import WorkspaceError
    from bakugan_ds.gates.install import install_milestone_6c

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    manifest_path = workspace / "manifests/workspace.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["profile_id"] = "other"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WorkspaceError, match="only b6re_rev0"):
        install_milestone_6c(workspace, AUTHORING, dry_run=True)


def test_install_rejects_partial_prior_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.errors import WorkspaceError
    from bakugan_ds.gates.install import install_milestone_6c

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    layout = WorkspaceLayout.from_root(workspace)
    layout.build_overrides.write_text("{}", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="preexisting divergent"):
        install_milestone_6c(workspace, AUTHORING)


def test_milestone_6d_install_is_transactional_and_reinstall_is_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.gates.install import install_milestone_6d

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    first = install_milestone_6d(workspace, AUTHORING_6D)
    second = install_milestone_6d(workspace, AUTHORING_6D)
    assert first.no_op is False
    assert second.no_op is True
    assert first.module_sha256 == second.module_sha256
    assert (workspace / "manifests/gate-system2-milestone-6d-install.json").exists()



def test_milestone_6d_accepts_pristine_extracted_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.gates.install import install_milestone_6d

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    layout = WorkspaceLayout.from_root(workspace)
    pristine = (layout.original_decoded_overlays / "overlay_007.bin").read_bytes()
    (layout.modified_overlays / "overlay_007.bin").write_bytes(pristine)

    report = install_milestone_6d(workspace, AUTHORING_6D)

    assert report.no_op is False
    assert report.dry_run is False
    assert (workspace / "manifests/gate-system2-milestone-6d-install.json").exists()

def test_milestone_6d_accepts_verified_milestone_6c_upgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.gates.install import install_milestone_6c, install_milestone_6d

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    install_milestone_6c(workspace, AUTHORING)
    upgraded = install_milestone_6d(workspace, AUTHORING_6D)
    assert upgraded.no_op is False
    assert (workspace / "manifests/gate-system2-milestone-6c-install.json").exists()
    assert (workspace / "manifests/gate-system2-milestone-6d-install.json").exists()


def test_milestone_6d_rejects_divergent_verified_upgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bakugan_ds.errors import WorkspaceError
    from bakugan_ds.gates.install import install_milestone_6c, install_milestone_6d

    workspace = _synthetic_workspace(tmp_path, monkeypatch)
    install_milestone_6c(workspace, AUTHORING)
    overlay = workspace / "modified/overlays/overlay_007.bin"
    overlay.write_bytes(overlay.read_bytes()[:-1] + b"X")
    with pytest.raises(WorkspaceError, match="prior Gate overlay"):
        install_milestone_6d(workspace, AUTHORING_6D)
