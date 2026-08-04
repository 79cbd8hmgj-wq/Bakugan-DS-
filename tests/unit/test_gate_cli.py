from __future__ import annotations

import json
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


def test_build_trailer_command_writes_exact_repeatable_binary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    authoring = Path("config/gates/milestone-6c-system2-v1.json")
    first = tmp_path / "first.g2dt"
    second = tmp_path / "second.g2dt"

    for output in (first, second):
        arguments = Namespace(
            gate_command="build-trailer",
            authoring=authoring,
            output=output,
        )
        assert gate_cli.run_gate_command(arguments) == 0

    assert first.read_bytes() == second.read_bytes()
    assert len(first.read_bytes()) == 4152
    printed = capsys.readouterr().out
    assert "record_count=103" in printed
    assert "size=4152" in printed
    assert "sha256=" in printed
    assert "payload_crc32=0x" in printed


def test_gate_parser_accepts_build_trailer_command() -> None:
    parser = gate_cli.build_gate_parser()
    arguments = parser.parse_args(
        [
            "build-trailer",
            "config/gates/milestone-6c-system2-v1.json",
            "work/system2.g2dt",
        ]
    )
    assert arguments.gate_command == "build-trailer"


def test_gate_parser_and_runner_support_milestone_6c_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from types import SimpleNamespace

    parser = gate_cli.build_gate_parser()
    arguments = parser.parse_args(
        [
            "install-milestone-6c",
            str(tmp_path / "workspace"),
            "--authoring",
            "config/gates/milestone-6c-system2-v1.json",
            "--dry-run",
        ]
    )
    assert arguments.gate_command == "install-milestone-6c"
    calls: list[tuple[Path, Path, bool]] = []

    def fake_install(workspace: Path, authoring: Path, *, dry_run: bool):
        calls.append((workspace, authoring, dry_run))
        return SimpleNamespace(
            trailer_sha256="a" * 64,
            module_sha256="b" * 64,
            raw_carrier_size=6992,
            overlay_size=501728,
            cache_range=(0x02293C20, 0x02293C60),
            binary_patches=tuple(range(7)),
            no_op=False,
            dry_run=True,
        )

    monkeypatch.setattr(gate_cli, "install_milestone_6c", fake_install)
    assert gate_cli.run_gate_command(arguments) == 0
    assert calls == [
        (
            tmp_path / "workspace",
            Path("config/gates/milestone-6c-system2-v1.json"),
            True,
        )
    ]
    output = capsys.readouterr().out
    assert "raw_size=6992" in output
    assert "overlay_size=501728" in output
    assert "cache=0x02293C20-0x02293C60" in output
    assert "patches=7" in output
