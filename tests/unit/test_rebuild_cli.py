from pathlib import Path
from types import SimpleNamespace

import pytest

from bakugan_ds import cli
from bakugan_ds.errors import WorkspaceError


def test_parser_accepts_rebuild_command(tmp_path: Path) -> None:
    arguments = cli.build_parser().parse_args(
        [
            "rebuild",
            "game.nds",
            str(tmp_path / "workspace"),
            str(tmp_path / "out.nds"),
            "--force",
        ]
    )

    assert arguments.command == "rebuild"
    assert arguments.rom == Path("game.nds")
    assert arguments.workspace == tmp_path / "workspace"
    assert arguments.output == tmp_path / "out.nds"
    assert arguments.force is True


def test_rebuild_cli_prints_success_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output = tmp_path / "out.nds"
    report = SimpleNamespace(changes=(1, 2), output_sha256="a" * 64, exact_copy=False)
    monkeypatch.setattr(cli, "load_profile", lambda path: object())
    monkeypatch.setattr(cli, "rebuild_rom", lambda rom, profile, workspace, options: report)

    result = cli.main(["rebuild", "game.nds", str(tmp_path / "work"), str(output)])

    assert result == 0
    text = capsys.readouterr().out
    assert "2 changes" in text
    assert "a" * 64 in text
    assert str(output.with_suffix(".nds.build.json").resolve()) in text


def test_rebuild_cli_reports_workspace_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli, "load_profile", lambda path: object())
    monkeypatch.setattr(
        cli,
        "rebuild_rom",
        lambda rom, profile, workspace, options: (_ for _ in ()).throw(
            WorkspaceError("output already exists")
        ),
    )

    result = cli.main(
        ["rebuild", "game.nds", str(tmp_path / "work"), str(tmp_path / "out.nds")]
    )

    assert result == 4
    assert "already exists" in capsys.readouterr().err
