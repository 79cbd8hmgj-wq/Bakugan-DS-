from __future__ import annotations

from argparse import Namespace
import json
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


def test_report_context_writes_included_and_excluded_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gate_cli, "validate_workspace_profile", lambda workspace: None)
    evidence = tmp_path / "context.json"
    evidence.write_text(
        """{
          "fields": [
            {
              "name": "gate_bonus_g",
              "width_bits": 16,
              "signed": false,
              "owner_structure": "record",
              "access": "+0x12",
              "lifetime": "gate",
              "initialization": "constructor",
              "reset": "record discarded",
              "safe_for_hook": true,
              "confidence": "confirmed",
              "evidence": "confirmed field",
              "exclusion_reason": ""
            },
            {
              "name": "gate_owner",
              "width_bits": 8,
              "signed": false,
              "owner_structure": "candidate",
              "access": "+0x18",
              "lifetime": "gate",
              "initialization": "candidate constructor",
              "reset": "candidate reset",
              "safe_for_hook": false,
              "confidence": "candidate",
              "evidence": "candidate field",
              "exclusion_reason": "not canonical"
            }
          ]
        }""",
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    arguments = Namespace(
        gate_command="report-context",
        workspace=Path("w"),
        output=output,
        evidence=evidence,
    )

    assert gate_cli.run_gate_command(arguments) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [item["name"] for item in payload["included"]] == ["gate_bonus_g"]
    assert [item["name"] for item in payload["excluded"]] == ["gate_owner"]
