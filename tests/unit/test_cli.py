from pathlib import Path

import pytest

from bakugan_ds import cli


def test_cli_requires_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_cli_reports_missing_rom(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    result = cli.main(["inspect", str(tmp_path / "missing.nds")])
    assert result == 5
    assert "missing.nds" in capsys.readouterr().err


def test_cli_writes_report_from_mocked_inspection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    rom_path = tmp_path / "game.nds"
    rom_path.write_bytes(b"x")
    output_path = tmp_path / "report.json"

    class FakeInspection:
        def to_json(self) -> str:
            return '{"supported": true}\n'

    monkeypatch.setattr(cli, "load_profile", lambda path: object())
    monkeypatch.setattr(
        cli,
        "inspect_rom",
        lambda path, profile, require_supported: FakeInspection(),
    )

    result = cli.main(
        [
            "inspect",
            str(rom_path),
            "--profile",
            "config/b6re_rev0.json",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert output_path.read_text(encoding="utf-8") == '{"supported": true}\n'


def test_gate_export_dispatches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = []
    monkeypatch.setattr(cli, "run_gate_command", lambda args: calls.append(args) or 0)

    result = cli.main(
        [
            "gate",
            "export-legacy",
            str(tmp_path / "workspace"),
            str(tmp_path / "output.json"),
            "--runtime-arm9",
            str(tmp_path / "runtime.bin"),
            "--metadata",
            "analysis/gates/legacy-table-metadata.json",
        ]
    )

    assert result == 0
    assert calls[0].gate_command == "export-legacy"
