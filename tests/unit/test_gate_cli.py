from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates import cli as gate_cli


def test_gate_parser_defines_all_analysis_commands() -> None:
    parser = gate_cli.build_gate_parser()
    cases = (
        (
            "inspect",
            [
                "inspect",
                "workspace",
                "--runtime-arm9",
                "runtime.bin",
                "--metadata",
                "metadata.json",
            ],
        ),
        (
            "export-legacy",
            [
                "export-legacy",
                "workspace",
                "output.json",
                "--runtime-arm9",
                "runtime.bin",
                "--metadata",
                "metadata.json",
            ],
        ),
        (
            "report-context",
            [
                "report-context",
                "workspace",
                "output.json",
                "--evidence",
                "context.json",
            ],
        ),
    )
    for expected, arguments in cases:
        assert parser.parse_args(arguments).gate_command == expected


def test_export_rejects_source_controlled_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    monkeypatch.chdir(root)
    with pytest.raises(WorkspaceError, match="source-controlled path"):
        gate_cli.ensure_local_output(root / "analysis/gates/full-table.json")
    gate_cli.ensure_local_output(root / "work/reports/gates/full-table.json")


def test_report_context_fails_until_task_8(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate_cli, "validate_workspace_profile", lambda workspace: None)
    arguments = Namespace(
        gate_command="report-context",
        workspace=Path("w"),
        output=Path("o"),
        evidence=Path("e"),
    )
    with pytest.raises(WorkspaceError, match="Task 8"):
        gate_cli.run_gate_command(arguments)
