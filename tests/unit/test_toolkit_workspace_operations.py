from pathlib import Path
from typing import Any

import pytest

from bakugan_ds.profile import load_profile
from bakugan_ds.workspace.extract import ExtractionOptions, extract_workspace
from bakugan_ds.workspace.rebuild import RebuildOptions, rebuild_rom
from bakugan_ds.workspace.validate import validate_workspace


def test_extract_workspace_preserves_bakugan_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    profile = load_profile(Path("config/b6re_rev0.json"))
    rom = tmp_path / "game.nds"
    options = ExtractionOptions(tmp_path / "workspace")
    sentinel = object()
    calls: list[tuple[object, ...]] = []

    def fake_extract(
        rom_path: Path,
        received_options: ExtractionOptions,
        *,
        profile: object,
        require_supported: bool,
    ) -> Any:
        calls.append((rom_path, received_options, profile, require_supported))
        return sentinel

    monkeypatch.setattr("bakugan_ds.workspace.extract._toolkit_extract_workspace", fake_extract)

    result = extract_workspace(rom, profile, options)

    assert result is sentinel
    assert calls == [(rom, options, profile, True)]


def test_validate_workspace_preserves_bakugan_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    profile = load_profile(Path("config/b6re_rev0.json"))
    rom = tmp_path / "game.nds"
    workspace = tmp_path / "workspace"
    sentinel = object()
    calls: list[tuple[object, ...]] = []

    def fake_validate(
        source_rom: Path,
        received_workspace: Path,
        *,
        profile: object,
        require_supported: bool,
    ) -> Any:
        calls.append((source_rom, received_workspace, profile, require_supported))
        return sentinel

    monkeypatch.setattr("bakugan_ds.workspace.validate._toolkit_validate_workspace", fake_validate)

    result = validate_workspace(rom, profile, workspace)

    assert result is sentinel
    assert calls == [(rom, workspace, profile, True)]


def test_rebuild_rom_preserves_bakugan_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    profile = load_profile(Path("config/b6re_rev0.json"))
    rom = tmp_path / "game.nds"
    workspace = tmp_path / "workspace"
    options = RebuildOptions(tmp_path / "rebuilt.nds")
    sentinel = object()
    calls: list[tuple[object, ...]] = []

    def fake_rebuild(
        source_rom: Path,
        received_workspace: Path,
        received_options: RebuildOptions,
        *,
        profile: object,
        require_supported: bool,
    ) -> Any:
        calls.append((source_rom, received_workspace, received_options, profile, require_supported))
        return sentinel

    monkeypatch.setattr("bakugan_ds.workspace.rebuild._toolkit_rebuild_rom", fake_rebuild)

    result = rebuild_rom(rom, profile, workspace, options)

    assert result is sentinel
    assert calls == [(rom, workspace, options, profile, True)]
