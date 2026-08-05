from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.workspace.model import WorkspaceLayout
from bakugan_ds.workspace.overrides import (
    BuildOverrides,
    OverlayLayoutOverride,
    RawNitroFsOverride,
    load_build_overrides,
    write_build_overrides,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def test_workspace_layout_exposes_raw_override_directory(tmp_path: Path) -> None:
    layout = WorkspaceLayout.from_root(tmp_path / "work")
    assert layout.modified_raw_nitrofs == tmp_path / "work/modified/raw/nitrofs"
    assert layout.build_overrides == tmp_path / "work/manifests/build-overrides.json"


def test_overlay_override_requires_exact_original_geometry() -> None:
    override = OverlayLayoutOverride(
        overlay_id=7,
        expected_ram_size=0x721A0,
        expected_bss_size=0x640,
        replacement_ram_size=0x7A7E0,
        replacement_bss_size=0x40,
        replacement_flags=0,
    )
    override.validate()


def test_build_overrides_round_trip_deterministically(tmp_path: Path) -> None:
    raw = RawNitroFsOverride(
        file_id=2762,
        path="font/mes_CardName.mes",
        expected_size=2840,
        expected_sha256=DIGEST_A,
        replacement_size=6992,
        replacement_sha256=DIGEST_B,
    )
    overlay = OverlayLayoutOverride(
        overlay_id=7,
        expected_ram_size=0x721A0,
        expected_bss_size=0x640,
        replacement_ram_size=0x7A7E0,
        replacement_bss_size=0x40,
        replacement_flags=0,
    )
    overrides = BuildOverrides(1, "b6re_rev0", (raw,), (overlay,))
    path = tmp_path / "build-overrides.json"

    write_build_overrides(path, overrides)

    assert load_build_overrides(path) == overrides
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert load_build_overrides(tmp_path / "missing.json") is None


def test_build_overrides_rejects_duplicate_raw_ids() -> None:
    first = RawNitroFsOverride(1, "a.bin", 1, DIGEST_A, 2, DIGEST_B)
    second = RawNitroFsOverride(1, "b.bin", 1, DIGEST_A, 2, DIGEST_B)
    overrides = BuildOverrides(1, "b6re_rev0", (first, second), ())

    with pytest.raises(WorkspaceError, match="duplicate raw override file ID"):
        overrides.validate()


def test_raw_override_rejects_unchanged_replacement() -> None:
    override = RawNitroFsOverride(1, "a.bin", 1, DIGEST_A, 1, DIGEST_A)

    with pytest.raises(WorkspaceError, match="must change"):
        override.validate()


def test_overlay_override_rejects_nonzero_flags() -> None:
    override = OverlayLayoutOverride(7, 1, 2, 3, 4, 1)

    with pytest.raises(WorkspaceError, match="flags"):
        override.validate()


def test_load_build_overrides_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "build-overrides.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(WorkspaceError, match="cannot load build overrides"):
        load_build_overrides(path)


def test_write_build_overrides_is_transactional_on_validation_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "build-overrides.json"
    path.write_text("preserved\n", encoding="utf-8")
    invalid = BuildOverrides(
        1,
        "wrong-profile",
        (),
        (),
    )

    with pytest.raises(WorkspaceError, match="profile"):
        write_build_overrides(path, invalid)

    assert path.read_text(encoding="utf-8") == "preserved\n"
