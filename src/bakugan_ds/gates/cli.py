from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.context import context_report, load_context_fields
from bakugan_ds.gates.discovery import load_discovery_artifact
from bakugan_ds.gates.io import load_json_object, write_evidence
from bakugan_ds.gates.legacy import (
    LegacyGateRecord,
    export_legacy_table,
    legacy_spec_from_dict,
    parse_legacy_table,
)
from bakugan_ds.gates.model import LegacyGateTableSpec
from bakugan_ds.gates.readiness_report import generate_readiness_report
from bakugan_ds.gates.record import parse_trailer
from bakugan_ds.gates.runtime_image import (
    load_runtime_arm9,
    load_workspace_arm9,
    map_runtime_region,
)
from bakugan_ds.workspace.manifest import load_workspace_manifest
from bakugan_ds.workspace.model import WorkspaceLayout

SUPPORTED_PROFILE_ID = "b6re_rev0"


def _add_gate_commands(subparsers: Any) -> None:
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="validate and print legacy Gate table metadata",
    )
    inspect_parser.add_argument("workspace", type=Path)
    inspect_parser.add_argument("--runtime-arm9", type=Path, required=True)
    inspect_parser.add_argument("--metadata", type=Path, required=True)

    export_parser = subparsers.add_parser(
        "export-legacy",
        help="write the complete legacy Gate table to a local ignored report",
    )
    export_parser.add_argument("workspace", type=Path)
    export_parser.add_argument("output", type=Path)
    export_parser.add_argument("--runtime-arm9", type=Path, required=True)
    export_parser.add_argument("--metadata", type=Path, required=True)

    context_parser = subparsers.add_parser(
        "report-context",
        help="write confirmed Gate battle-context evidence",
    )
    context_parser.add_argument("workspace", type=Path)
    context_parser.add_argument("output", type=Path)
    context_parser.add_argument("--evidence", type=Path, required=True)

    artifact_parser = subparsers.add_parser(
        "validate-artifact",
        help="validate one normalized Gate discovery artifact",
    )
    artifact_parser.add_argument("artifact", type=Path)

    trailer_parser = subparsers.add_parser(
        "validate-trailer",
        help="validate one complete Gate System 2.0 G2DT trailer",
    )
    trailer_parser.add_argument("trailer", type=Path)

    readiness_parser = subparsers.add_parser(
        "readiness",
        help="generate the fail-closed Milestone 6C readiness report",
    )
    readiness_parser.add_argument("--requirements", type=Path, required=True)
    readiness_parser.add_argument("--evidence-dir", type=Path, required=True)
    readiness_parser.add_argument("--output", type=Path, required=True)


def build_gate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bakugan-ds gate")
    _add_gate_commands(parser.add_subparsers(dest="gate_command", required=True))
    return parser


def add_gate_parser(subparsers: Any) -> None:
    gate_parser = subparsers.add_parser("gate", help="analyze Gate Card runtime data")
    _add_gate_commands(gate_parser.add_subparsers(dest="gate_command", required=True))


def validate_workspace_profile(workspace: Path) -> WorkspaceLayout:
    layout = WorkspaceLayout.from_root(workspace)
    manifest = load_workspace_manifest(layout.manifests / "workspace.json")
    if manifest.profile_id != SUPPORTED_PROFILE_ID:
        raise WorkspaceError(
            f"unsupported Gate workspace profile: expected {SUPPORTED_PROFILE_ID}, "
            f"got {manifest.profile_id}"
        )
    return layout


def _repository_root(start: Path) -> Path | None:
    resolved = start.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def ensure_local_output(path: Path) -> Path:
    output = path.expanduser().resolve()
    repository = _repository_root(Path.cwd())
    if repository is None or not output.is_relative_to(repository):
        return output
    allowed_roots = (
        repository / "work",
        repository / "reports",
        repository / "analysis/generated",
        repository / "references/generated",
    )
    if not any(output.is_relative_to(root) for root in allowed_roots):
        raise WorkspaceError(
            f"refusing to write complete Gate data to source-controlled path: {output}"
        )
    return output


def _load_verified_legacy(
    arguments: argparse.Namespace,
) -> tuple[dict[str, object], LegacyGateTableSpec, tuple[LegacyGateRecord, ...]]:
    validate_workspace_profile(arguments.workspace)
    payload = load_json_object(arguments.metadata)
    spec = legacy_spec_from_dict(payload)
    runtime_image = load_runtime_arm9(arguments.runtime_arm9)
    workspace_image = load_workspace_arm9(arguments.workspace)
    map_runtime_region(
        runtime_image,
        workspace_image,
        spec.runtime_address,
        spec.table_size,
    )
    records = parse_legacy_table(runtime_image, spec)
    return payload, spec, records


def _artifact_summary(path: Path) -> dict[str, object]:
    artifact = load_discovery_artifact(path)
    return {
        "checks": [check.name for check in artifact.checks],
        "domain": artifact.domain,
        "fields": [field.name for field in artifact.fields],
        "unresolved": list(artifact.unresolved),
        "valid": True,
    }


def _trailer_summary(path: Path) -> dict[str, object]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise WorkspaceError(f"cannot read Gate trailer {path}: {exc}") from exc
    header, records = parse_trailer(data)
    return {
        "first_card_id": header.first_card_id,
        "header_size": header.header_size,
        "payload_crc32": f"0x{header.payload_crc32:08X}",
        "payload_size": header.payload_size,
        "record_count": len(records),
        "record_size": header.record_size,
        "valid": True,
        "version": header.version,
    }


def run_gate_command(arguments: argparse.Namespace) -> int:
    if arguments.gate_command == "inspect":
        payload, _, _ = _load_verified_legacy(arguments)
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0
    if arguments.gate_command == "export-legacy":
        _, spec, records = _load_verified_legacy(arguments)
        output = ensure_local_output(arguments.output)
        export_legacy_table(output, records, spec)
        print(f"Wrote local legacy Gate export: {output}")
        return 0
    if arguments.gate_command == "report-context":
        validate_workspace_profile(arguments.workspace)
        output = ensure_local_output(arguments.output)
        fields = load_context_fields(arguments.evidence)
        write_evidence(output, context_report(fields))
        print(f"Wrote confirmed Gate battle-context report: {output}")
        return 0
    if arguments.gate_command == "validate-artifact":
        sys.stdout.write(
            json.dumps(
                _artifact_summary(arguments.artifact),
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return 0
    if arguments.gate_command == "validate-trailer":
        sys.stdout.write(
            json.dumps(
                _trailer_summary(arguments.trailer),
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return 0
    if arguments.gate_command == "readiness":
        report = generate_readiness_report(
            arguments.requirements,
            arguments.evidence_dir,
        )
        write_evidence(arguments.output, report.to_dict())
        print(f"Wrote Gate readiness report: {arguments.output.resolve()}")
        return 0 if report.ready_for_milestone_6c else 4
    raise WorkspaceError(f"unknown Gate command: {arguments.gate_command}")
