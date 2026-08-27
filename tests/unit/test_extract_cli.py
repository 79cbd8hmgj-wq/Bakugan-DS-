from pathlib import Path
from types import SimpleNamespace

import pytest
from nds_disassembly_toolkit import cli as toolkit_cli

from bakugan_ds import cli
from bakugan_ds.errors import WorkspaceError


def test_parser_accepts_extract_command(tmp_path: Path) -> None:
    arguments = cli.build_parser().parse_args(
        ["extract", "game.nds", str(tmp_path / "work"), "--force"]
    )

    assert arguments.command == "extract"
    assert arguments.rom == Path("game.nds")
    assert arguments.workspace == tmp_path / "work"
    assert arguments.force is True


def test_extract_cli_prints_success_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    rom_path = tmp_path / "game.nds"
    rom_path.write_bytes(b"x")
    workspace = tmp_path / "workspace"
    manifest = SimpleNamespace(files=(1, 2), overlays=(1,))
    monkeypatch.setattr(toolkit_cli, "load_profile", lambda path: object())
    monkeypatch.setattr(
        toolkit_cli,
        "extract_workspace",
        lambda rom, options, *, profile, require_supported: manifest,
    )

    result = cli.main(["extract", str(rom_path), str(workspace)])

    assert result == 0
    output = capsys.readouterr().out
    assert str(workspace.resolve()) in output
    assert "2 files" in output
    assert "1 overlays" in output
    assert "manifests/workspace.json" in output


def test_extract_cli_reports_existing_workspace(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    rom_path = tmp_path / "game.nds"
    rom_path.write_bytes(b"x")
    monkeypatch.setattr(toolkit_cli, "load_profile", lambda path: object())
    monkeypatch.setattr(
        toolkit_cli,
        "extract_workspace",
        lambda rom, options, *, profile, require_supported: (_ for _ in ()).throw(
            WorkspaceError("workspace already exists")
        ),
    )

    result = cli.main(["extract", str(rom_path), str(tmp_path / "workspace")])

    assert result == 4
    assert "already exists" in capsys.readouterr().err


def test_extract_cli_reports_filesystem_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    rom_path = tmp_path / "game.nds"
    rom_path.write_bytes(b"x")
    monkeypatch.setattr(toolkit_cli, "load_profile", lambda path: object())
    monkeypatch.setattr(
        toolkit_cli,
        "extract_workspace",
        lambda rom, options, *, profile, require_supported: (_ for _ in ()).throw(
            OSError("disk full")
        ),
    )

    result = cli.main(["extract", str(rom_path), str(tmp_path / "workspace")])

    assert result == 5
    assert "disk full" in capsys.readouterr().err
