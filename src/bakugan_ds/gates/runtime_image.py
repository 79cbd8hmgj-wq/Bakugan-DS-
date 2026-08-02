from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bakugan_ds.analysis.model import Component
from bakugan_ds.compression.blz import decompress_blz, is_blz
from bakugan_ds.errors import WorkspaceError
from bakugan_ds.workspace.manifest import sha256_bytes
from bakugan_ds.workspace.model import WorkspaceLayout

ARM9_BASE_ADDRESS = 0x02000000


@dataclass(frozen=True)
class RuntimeImage:
    component: Component
    sha256: str
    source_encoding: str
    stored_sha256: str | None = None
    stored_size: int | None = None


@dataclass(frozen=True)
class RuntimeStoredMapping:
    runtime_address: int
    runtime_offset: int
    workspace_component: str
    decoded_offset: int
    mapping_kind: str
    decoded_sha256: str
    stored_sha256: str
    directly_patchable: bool


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise WorkspaceError(f"cannot read {label} {path}: {exc}") from exc


def load_runtime_arm9(path: Path, base_address: int = ARM9_BASE_ADDRESS) -> RuntimeImage:
    resolved = path.expanduser().resolve()
    data = _read_bytes(resolved, "runtime ARM9")
    digest = sha256_bytes(data)
    return RuntimeImage(
        component=Component("arm9", resolved, base_address, data),
        sha256=digest,
        source_encoding="none",
        stored_sha256=digest,
        stored_size=len(data),
    )


def load_workspace_arm9(workspace: Path, base_address: int = ARM9_BASE_ADDRESS) -> RuntimeImage:
    layout = WorkspaceLayout.from_root(workspace)
    stored_path = layout.original / "arm9.bin"
    stored = _read_bytes(stored_path, "workspace ARM9")
    if is_blz(stored):
        try:
            decoded = decompress_blz(stored)
        except Exception as exc:
            raise WorkspaceError(f"cannot decompress workspace ARM9 {stored_path}: {exc}") from exc
        source_encoding = "blz"
    else:
        decoded = stored
        source_encoding = "none"
    return RuntimeImage(
        component=Component("arm9", stored_path.resolve(), base_address, decoded),
        sha256=sha256_bytes(decoded),
        source_encoding=source_encoding,
        stored_sha256=sha256_bytes(stored),
        stored_size=len(stored),
    )


def runtime_slice(image: RuntimeImage, address: int, length: int) -> bytes:
    if length <= 0:
        raise WorkspaceError("runtime slice length must be positive")
    try:
        offset = image.component.offset_for_address(address)
    except ValueError as exc:
        raise WorkspaceError(str(exc)) from exc
    end = offset + length
    if end > len(image.component.data):
        raise WorkspaceError(
            f"address range 0x{address:X}:0x{address + length:X} is outside "
            f"{image.component.name}"
        )
    return image.component.data[offset:end]


def map_runtime_region(
    runtime_image: RuntimeImage,
    workspace_image: RuntimeImage,
    address: int,
    length: int,
) -> RuntimeStoredMapping:
    runtime_data = runtime_slice(runtime_image, address, length)
    workspace_data = runtime_slice(workspace_image, address, length)
    if runtime_data != workspace_data:
        raise WorkspaceError(
            f"runtime ARM9 region at 0x{address:X} does not match workspace ARM9"
        )
    runtime_offset = address - runtime_image.component.base_address
    decoded_offset = address - workspace_image.component.base_address
    directly_patchable = (
        workspace_image.source_encoding == "none" and runtime_offset == decoded_offset
    )
    stored_sha256 = workspace_image.stored_sha256 or workspace_image.sha256
    return RuntimeStoredMapping(
        runtime_address=address,
        runtime_offset=runtime_offset,
        workspace_component=workspace_image.component.name,
        decoded_offset=decoded_offset,
        mapping_kind="direct" if directly_patchable else "decoded",
        decoded_sha256=workspace_image.sha256,
        stored_sha256=stored_sha256,
        directly_patchable=directly_patchable,
    )
