from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.inspection import RomInspection, inspect_rom
from bakugan_ds.profile import RomProfile, sha256_file
from bakugan_ds.workspace.manifest import WorkspaceManifest, load_workspace_manifest, sha256_bytes
from bakugan_ds.workspace.model import WorkspaceLayout
from bakugan_ds.workspace.paths import safe_relative_path


@dataclass(frozen=True)
class WorkspaceChange:
    kind: str
    identifier: str
    original_sha256: str
    modified_sha256: str


@dataclass(frozen=True)
class ValidatedWorkspace:
    layout: WorkspaceLayout
    manifest: WorkspaceManifest
    inspection: RomInspection
    changes: tuple[WorkspaceChange, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.changes)


def _read_verified(path: Path, size: int, digest: str, label: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise WorkspaceError(f"missing {label}: {path}") from exc
    if len(data) != size:
        raise WorkspaceError(f"{label} size mismatch: expected {size}, got {len(data)}")
    actual = sha256_bytes(data)
    if actual != digest:
        raise WorkspaceError(f"{label} SHA-256 mismatch: expected {digest}, got {actual}")
    return data


def _scan_relative_files(root: Path) -> set[str]:
    if not root.is_dir():
        raise WorkspaceError(f"missing modified directory: {root}")
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def validate_workspace(
    source_rom: Path,
    profile: RomProfile,
    workspace: Path,
) -> ValidatedWorkspace:
    layout = WorkspaceLayout.from_root(workspace)
    manifest = load_workspace_manifest(layout.manifests / "workspace.json")
    if manifest.profile_id != profile.id:
        raise WorkspaceError(
            f"workspace profile mismatch: expected {profile.id}, got {manifest.profile_id}"
        )
    try:
        source_size = source_rom.stat().st_size
        source_hash = sha256_file(source_rom)
    except OSError as exc:
        raise WorkspaceError(f"cannot read source ROM {source_rom}: {exc}") from exc
    if source_size != manifest.rom_size or source_hash != manifest.rom_sha256:
        raise WorkspaceError(
            "source ROM does not match workspace manifest: "
            f"expected {manifest.rom_size} bytes/{manifest.rom_sha256}, "
            f"got {source_size} bytes/{source_hash}"
        )

    inspection = inspect_rom(source_rom, profile, require_supported=True)
    source_paths = {item.file_id: item.path for item in inspection.fnt.files}
    manifest_paths = {item.file_id: item.path for item in manifest.files}
    if source_paths != manifest_paths:
        raise WorkspaceError("workspace file mapping does not match source ROM FNT")
    source_overlays = {
        item.overlay_id: item.file_id
        for item in (*inspection.arm9_overlays, *inspection.arm7_overlays)
    }
    manifest_overlays = {item.overlay_id: item.file_id for item in manifest.overlays}
    if source_overlays != manifest_overlays:
        raise WorkspaceError("workspace overlay mapping does not match source ROM")

    _read_verified(
        layout.original / "arm9.bin",
        inspection.header.arm9_size,
        manifest.arm9_sha256,
        "original ARM9",
    )
    _read_verified(
        layout.original / "arm7.bin",
        inspection.header.arm7_size,
        manifest.arm7_sha256,
        "original ARM7",
    )

    changes: list[WorkspaceChange] = []
    for name, expected_size, original_hash in (
        ("arm9", inspection.header.arm9_size, manifest.arm9_sha256),
        ("arm7", inspection.header.arm7_size, manifest.arm7_sha256),
    ):
        path = layout.modified / f"{name}.bin"
        try:
            modified = path.read_bytes()
        except OSError as exc:
            raise WorkspaceError(f"missing modified {name.upper()}: {path}") from exc
        if len(modified) != expected_size:
            raise WorkspaceError(
                f"modified {name.upper()} size mismatch: expected {expected_size}, got {len(modified)}"
            )
        modified_hash = sha256_bytes(modified)
        if modified_hash != original_hash:
            changes.append(WorkspaceChange(name, name, original_hash, modified_hash))

    expected_modified_files: set[str] = set()
    for entry in manifest.files:
        relative = safe_relative_path(entry.path)
        relative_path = Path(*relative.parts)
        _read_verified(
            layout.original_raw_nitrofs / relative_path,
            entry.raw_size,
            entry.raw_sha256,
            f"original raw NitroFS file {entry.path}",
        )
        _read_verified(
            layout.original_decoded_nitrofs / relative_path,
            entry.decoded_size,
            entry.decoded_sha256,
            f"original decoded NitroFS file {entry.path}",
        )
        modified_path = layout.modified_nitrofs / relative_path
        try:
            modified = modified_path.read_bytes()
        except OSError as exc:
            raise WorkspaceError(f"missing modified NitroFS file: {entry.path}") from exc
        modified_hash = sha256_bytes(modified)
        if modified_hash != entry.decoded_sha256:
            changes.append(
                WorkspaceChange("nitrofs", entry.path, entry.decoded_sha256, modified_hash)
            )
        expected_modified_files.add(relative.as_posix())
    actual_modified_files = _scan_relative_files(layout.modified_nitrofs)
    extra_files = sorted(actual_modified_files - expected_modified_files)
    missing_files = sorted(expected_modified_files - actual_modified_files)
    if extra_files:
        raise WorkspaceError(f"unmanifested modified NitroFS files: {extra_files}")
    if missing_files:
        raise WorkspaceError(f"missing modified NitroFS files: {missing_files}")

    expected_overlay_files: set[str] = set()
    for entry in manifest.overlays:
        filename = f"overlay_{entry.overlay_id:03d}.bin"
        _read_verified(
            layout.original_raw_overlays / filename,
            entry.raw_size,
            entry.raw_sha256,
            f"original raw overlay {entry.overlay_id}",
        )
        _read_verified(
            layout.original_decoded_overlays / filename,
            entry.decoded_size,
            entry.decoded_sha256,
            f"original decoded overlay {entry.overlay_id}",
        )
        modified_path = layout.modified_overlays / filename
        try:
            modified = modified_path.read_bytes()
        except OSError as exc:
            raise WorkspaceError(f"missing modified overlay {entry.overlay_id}: {modified_path}") from exc
        if len(modified) != entry.ram_size:
            raise WorkspaceError(
                f"modified overlay {entry.overlay_id} size mismatch: "
                f"expected {entry.ram_size}, got {len(modified)}"
            )
        modified_hash = sha256_bytes(modified)
        if modified_hash != entry.decoded_sha256:
            changes.append(
                WorkspaceChange(
                    "overlay",
                    str(entry.overlay_id),
                    entry.decoded_sha256,
                    modified_hash,
                )
            )
        expected_overlay_files.add(filename)
    actual_overlay_files = _scan_relative_files(layout.modified_overlays)
    extra_overlays = sorted(actual_overlay_files - expected_overlay_files)
    missing_overlays = sorted(expected_overlay_files - actual_overlay_files)
    if extra_overlays:
        raise WorkspaceError(f"unmanifested modified overlays: {extra_overlays}")
    if missing_overlays:
        raise WorkspaceError(f"missing modified overlays: {missing_overlays}")

    order = {"arm9": 0, "arm7": 1, "nitrofs": 2, "overlay": 3}
    return ValidatedWorkspace(
        layout=layout,
        manifest=manifest,
        inspection=inspection,
        changes=tuple(sorted(changes, key=lambda item: (order[item.kind], item.identifier))),
    )
