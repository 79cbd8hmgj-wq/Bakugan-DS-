from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.io import load_json_object
from bakugan_ds.gates.legacy import export_legacy_table, legacy_spec_from_dict, parse_legacy_table
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
):
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
        raise WorkspaceError(
            "Gate battle-context reporting is unavailable until Task 8 evidence is confirmed"
        )
    raise WorkspaceError(f"unknown Gate command: {arguments.gate_command}")
