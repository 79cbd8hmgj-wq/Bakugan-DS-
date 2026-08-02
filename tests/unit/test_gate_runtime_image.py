from __future__ import annotations

from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.runtime_image import (
    load_runtime_arm9,
    load_workspace_arm9,
    map_runtime_region,
    runtime_slice,
)


def test_runtime_mapping_requires_exact_same_region(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime.bin"
    workspace_path = tmp_path / "workspace.bin"
    runtime_path.write_bytes(b"abcdefgh")
    workspace_path.write_bytes(b"abcdefgh")

    mapping = map_runtime_region(
        load_runtime_arm9(runtime_path),
        load_runtime_arm9(workspace_path),
        0x02000002,
        4,
    )

    assert mapping.runtime_offset == mapping.decoded_offset == 2
    assert mapping.mapping_kind == "direct"
    assert mapping.directly_patchable is True


def test_runtime_slice_rejects_range_past_end(tmp_path: Path) -> None:
    path = tmp_path / "runtime.bin"
    path.write_bytes(b"abcdefgh")
    image = load_runtime_arm9(path)

    with pytest.raises(WorkspaceError, match="outside arm9"):
        runtime_slice(image, 0x02000006, 4)


def test_mapping_rejects_mismatched_exact_region(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime.bin"
    workspace_path = tmp_path / "workspace.bin"
    runtime_path.write_bytes(b"abXXefgh")
    workspace_path.write_bytes(b"abYYefgh")

    with pytest.raises(WorkspaceError, match="does not match"):
        map_runtime_region(
            load_runtime_arm9(runtime_path),
            load_runtime_arm9(workspace_path),
            0x02000002,
            2,
        )


def test_workspace_arm9_uses_original_image_and_hashes(tmp_path: Path) -> None:
    arm9 = tmp_path / "workspace" / "original" / "arm9.bin"
    arm9.parent.mkdir(parents=True)
    arm9.write_bytes(b"abcdefgh")

    image = load_workspace_arm9(tmp_path / "workspace")

    assert image.component.path == arm9.resolve()
    assert image.component.data == b"abcdefgh"
    assert image.source_encoding == "none"
    assert image.sha256 == image.stored_sha256


def test_load_runtime_arm9_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="cannot read runtime ARM9"):
        load_runtime_arm9(tmp_path / "missing.bin")


def test_compressed_workspace_mapping_is_not_directly_patchable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    arm9 = tmp_path / "workspace" / "original" / "arm9.bin"
    arm9.parent.mkdir(parents=True)
    arm9.write_bytes(b"compressed")
    monkeypatch.setattr("bakugan_ds.gates.runtime_image.is_blz", lambda data: True)
    monkeypatch.setattr(
        "bakugan_ds.gates.runtime_image.decompress_blz",
        lambda data: b"abcdefgh",
    )
    runtime_path = tmp_path / "runtime.bin"
    runtime_path.write_bytes(b"abcdefgh")

    mapping = map_runtime_region(
        load_runtime_arm9(runtime_path),
        load_workspace_arm9(tmp_path / "workspace"),
        0x02000000,
        4,
    )

    assert mapping.mapping_kind == "decoded"
    assert mapping.directly_patchable is False
    assert mapping.stored_sha256 != mapping.decoded_sha256
