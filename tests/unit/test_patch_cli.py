from pathlib import Path
from types import SimpleNamespace

import pytest
from nds_disassembly_toolkit import cli as toolkit_cli

from bakugan_ds import cli
from bakugan_ds.errors import WorkspaceError


def test_parser_accepts_patch_command(tmp_path: Path) -> None:
    arguments = cli.build_parser().parse_args(
        ["patch", str(tmp_path / "workspace"), str(tmp_path / "balance.json")]
    )

    assert arguments.command == "patch"
    assert arguments.workspace == tmp_path / "workspace"
    assert arguments.patch_file == tmp_path / "balance.json"


def test_patch_cli_prints_success_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    patch_file = tmp_path / "balance.json"
    report = SimpleNamespace(applied=(1, 2, 3))
    monkeypatch.setattr(
        toolkit_cli,
        "apply_patch_set",
        lambda workspace, patch_path: report,
    )

    result = cli.main(["patch", str(workspace), str(patch_file)])

    assert result == 0
    text = capsys.readouterr().out
    assert "3 patches" in text
    assert str((workspace / "manifests/patch-balance.json").resolve()) in text


def test_patch_cli_reports_stale_guard(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        toolkit_cli,
        "apply_patch_set",
        lambda workspace, patch_path: (_ for _ in ()).throw(
            WorkspaceError("expected bytes did not match")
        ),
    )

    result = cli.main(["patch", str(tmp_path / "work"), str(tmp_path / "p.json")])

    assert result == 4
    assert "expected bytes" in capsys.readouterr().err
