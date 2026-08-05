from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    build_milestone_6d_balance_report,
    load_authoring_document,
    load_gate_roster_authoring_document,
    load_milestone_6d_authoring_document,
    validate_milestone_6d_roster,
    write_milestone_6d_balance_report,
)
from bakugan_ds.gates.context import context_report, load_context_fields
from bakugan_ds.gates.discovery import load_discovery_artifact
from bakugan_ds.gates.install import install_milestone_6c, install_milestone_6d
from bakugan_ds.gates.io import load_json_object, write_evidence
from bakugan_ds.gates.legacy import (
    LegacyGateRecord,
    export_legacy_table,
    legacy_spec_from_dict,
    parse_legacy_table,
)
from bakugan_ds.gates.model import LegacyGateTableSpec
from bakugan_ds.gates.readiness_report import generate_readiness_report
from bakugan_ds.gates.record import build_trailer, parse_trailer
from bakugan_ds.gates.roster_analysis import write_roster_analysis
from bakugan_ds.gates.roster_metadata import load_gate_roster_metadata
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

    build_trailer_parser = subparsers.add_parser(
        "build-trailer",
        help="build the approved Milestone 6C G2DT trailer",
    )
    build_trailer_parser.add_argument("authoring", type=Path)
    build_trailer_parser.add_argument("output", type=Path)

    install_parser = subparsers.add_parser(
        "install-milestone-6c",
        help="install the approved Milestone 6C Gate System 2.0 prototype",
    )
    install_parser.add_argument("workspace", type=Path)
    install_parser.add_argument(
        "--authoring",
        type=Path,
        default=Path("config/gates/milestone-6c-system2-v1.json"),
    )
    install_parser.add_argument("--dry-run", action="store_true")

    install_6d_parser = subparsers.add_parser(
        "install-milestone-6d",
        help="install the deterministic Milestone 6D Gate balance framework",
    )
    install_6d_parser.add_argument("workspace", type=Path)
    install_6d_parser.add_argument(
        "--authoring",
        type=Path,
        default=Path("config/gates/milestone-6d-system2-v1.json"),
    )
    install_6d_parser.add_argument("--dry-run", action="store_true")

    validate_6d_parser = subparsers.add_parser(
        "validate-milestone-6d",
        help="validate the deterministic Milestone 6D Gate balance authoring roster",
    )
    validate_6d_parser.add_argument("authoring", type=Path)

    report_6d_parser = subparsers.add_parser(
        "report-milestone-6d",
        help="write the deterministic Milestone 6D Gate balance report",
    )
    report_6d_parser.add_argument("authoring", type=Path)
    report_6d_parser.add_argument("output", type=Path)

    report_6e_parser = subparsers.add_parser(
        "report-milestone-6e-roster",
        help="write the deterministic Milestone 6E whole-roster analysis",
    )
    report_6e_parser.add_argument("authoring", type=Path)
    report_6e_parser.add_argument("output", type=Path)
    report_6e_parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("config/gates/milestone-6e-roster-metadata.json"),
    )

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


def _write_binary_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(  # noqa: SIM115
        prefix=f".{path.name}.tmp-", dir=path.parent, delete=False
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(data)
            handle.flush()
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def run_gate_command(arguments: argparse.Namespace) -> int:
    if arguments.gate_command == "inspect":
        payload, _, _ = _load_verified_legacy(arguments)
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0
    if arguments.gate_command == "export-legacy":
        _, spec, legacy_records = _load_verified_legacy(arguments)
        output = ensure_local_output(arguments.output)
        export_legacy_table(output, legacy_records, spec)
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
    if arguments.gate_command == "build-trailer":
        gate_records = load_authoring_document(arguments.authoring)
        trailer = build_trailer(gate_records)
        output = ensure_local_output(arguments.output)
        _write_binary_atomic(output, trailer)
        header, _ = parse_trailer(trailer)
        digest = hashlib.sha256(trailer).hexdigest()
        print(
            f"Wrote Gate trailer: {output}; size={len(trailer)}; "
            f"sha256={digest}; record_count={header.record_count}; "
            f"payload_crc32=0x{header.payload_crc32:08X}"
        )
        return 0
    if arguments.gate_command == "install-milestone-6c":
        install_report = install_milestone_6c(
            arguments.workspace,
            arguments.authoring,
            dry_run=arguments.dry_run,
        )
        if install_report.no_op:
            install_state = "no-op"
        elif install_report.dry_run:
            install_state = "prepared"
        else:
            install_state = "complete"
        cache_start, cache_end = install_report.cache_range
        print(
            "Milestone 6C install "
            f"{install_state}; "
            f"trailer_sha256={install_report.trailer_sha256}; "
            f"module_sha256={install_report.module_sha256}; "
            f"raw_size={install_report.raw_carrier_size}; "
            f"overlay_size={install_report.overlay_size}; "
            f"cache=0x{cache_start:08X}-0x{cache_end:08X}; "
            f"patches={len(install_report.binary_patches)}"
        )
        return 0
    if arguments.gate_command == "install-milestone-6d":
        install_report = install_milestone_6d(
            arguments.workspace,
            arguments.authoring,
            dry_run=arguments.dry_run,
        )
        if install_report.no_op:
            install_state = "no-op"
        elif install_report.dry_run:
            install_state = "prepared"
        else:
            install_state = "complete"
        cache_start, cache_end = install_report.cache_range
        print(
            "Milestone 6D install "
            f"{install_state}; "
            f"trailer_sha256={install_report.trailer_sha256}; "
            f"module_sha256={install_report.module_sha256}; "
            f"raw_size={install_report.raw_carrier_size}; "
            f"overlay_size={install_report.overlay_size}; "
            f"cache=0x{cache_start:08X}-0x{cache_end:08X}; "
            f"patches={len(install_report.binary_patches)}"
        )
        return 0
    if arguments.gate_command == "validate-milestone-6d":
        gate_records = load_milestone_6d_authoring_document(arguments.authoring)
        report = build_milestone_6d_balance_report(gate_records)
        encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        balance_reports = validate_milestone_6d_roster(gate_records)
        net_budget = balance_reports[0].budget.net_budget
        print(
            "Milestone 6D authoring valid; "
            f"record_count={report['record_count']}; "
            f"live_card_ids={report['live_card_ids']}; "
            f"juggernoid_net_budget={net_budget}; "
            f"report_sha256={digest}"
        )
        return 0
    if arguments.gate_command == "report-milestone-6d":
        gate_records = load_milestone_6d_authoring_document(arguments.authoring)
        output = ensure_local_output(arguments.output)
        write_milestone_6d_balance_report(output, gate_records)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        print(f"Wrote Milestone 6D Gate balance report: {output}; sha256={digest}")
        return 0
    if arguments.gate_command == "report-milestone-6e-roster":
        gate_records = load_gate_roster_authoring_document(arguments.authoring)
        metadata = load_gate_roster_metadata(arguments.metadata)
        output = ensure_local_output(arguments.output)
        write_roster_analysis(output, gate_records, metadata)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        live_count = sum(record.archetype != 0 for record in gate_records)
        print(
            "Wrote Milestone 6E Gate roster analysis: "
            f"{output}; record_count={len(gate_records)}; "
            f"live_count={live_count}; sha256={digest}"
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
        readiness_report = generate_readiness_report(
            arguments.requirements,
            arguments.evidence_dir,
        )
        write_evidence(arguments.output, readiness_report.to_dict())
        print(f"Wrote Gate readiness report: {arguments.output.resolve()}")
        return 0 if readiness_report.ready_for_milestone_6c else 4
    raise WorkspaceError(f"unknown Gate command: {arguments.gate_command}")
