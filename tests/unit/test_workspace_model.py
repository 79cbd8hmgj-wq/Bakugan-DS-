import json
from pathlib import Path, PurePosixPath

import pytest

from bakugan_ds.workspace.manifest import (
    ExtractedFile,
    ExtractedOverlay,
    WorkspaceManifest,
    sha256_bytes,
    write_json_atomic,
)
from bakugan_ds.workspace.model import WorkspaceLayout
from bakugan_ds.workspace.paths import ensure_unique_relative_paths, safe_relative_path


@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "../evil.bin", "/absolute.bin", "Game/../evil.bin", "Game\\evil.bin"],
)
def test_safe_relative_path_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(ValueError):
        safe_relative_path(value)


def test_safe_relative_path_preserves_posix_path() -> None:
    assert safe_relative_path("Game/Bakugan/data.bin") == PurePosixPath(
        "Game/Bakugan/data.bin"
    )


def test_unique_paths_reject_duplicates_after_normalization() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ensure_unique_relative_paths(["Game/a.bin", "Game/a.bin"])


def test_workspace_layout_stays_under_root(tmp_path: Path) -> None:
    layout = WorkspaceLayout.from_root(tmp_path / "workspace")

    for path in layout.all_directories():
        assert path == layout.root or layout.root in path.parents
    assert layout.original_raw_nitrofs == layout.root / "original/raw/nitrofs"
    assert layout.modified_overlays == layout.root / "modified/overlays"


def test_manifest_json_is_deterministic() -> None:
    manifest = WorkspaceManifest(
        format_version=1,
        profile_id="b6re_rev0",
        rom_sha256="a" * 64,
        rom_size=128,
        arm9_sha256="b" * 64,
        arm7_sha256="c" * 64,
        files=(
            ExtractedFile(9, "z.bin", 3, 3, "none", "d" * 64, "d" * 64),
            ExtractedFile(10, "a.bin", 4, 8, "lz10", "e" * 64, "f" * 64),
        ),
        overlays=(
            ExtractedOverlay(
                0,
                0,
                0x02219440,
                10,
                2,
                8,
                10,
                "1" * 64,
                "2" * 64,
                "blz",
            ),
        ),
    )

    first = manifest.to_json()
    second = manifest.to_json()
    payload = json.loads(first)

    assert first == second
    assert first.endswith("\n")
    assert payload["files"][0]["file_id"] == 9
    assert payload["overlays"][0]["overlay_id"] == 0


def test_write_json_atomic_replaces_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("old", encoding="utf-8")

    write_json_atomic(path, {"value": 2})

    assert json.loads(path.read_text(encoding="utf-8")) == {"value": 2}
    assert not path.with_suffix(".json.tmp").exists()


def test_sha256_bytes_is_stable() -> None:
    assert sha256_bytes(b"Bakugan") == sha256_bytes(b"Bakugan")
    assert sha256_bytes(b"Bakugan") != sha256_bytes(b"bakugan")
