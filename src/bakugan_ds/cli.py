from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from bakugan_ds.errors import BakuganDSError, ProfileError, RomFormatError, UnsupportedRomError
from bakugan_ds.gates.cli import add_gate_parser, run_gate_command
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.patches.apply import apply_patch_set
from bakugan_ds.profile import load_profile
from bakugan_ds.workspace.extract import ExtractionOptions, extract_workspace
from bakugan_ds.workspace.rebuild import RebuildOptions, rebuild_rom

DEFAULT_PROFILE = Path("config/b6re_rev0.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bakugan-ds")
    subparsers = parser.add_subparsers(dest="command")

    inspect_parser = subparsers.add_parser("inspect", help="inspect Nintendo DS ROM structures")
    inspect_parser.add_argument("rom", type=Path)
    inspect_parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    inspect_parser.add_argument("--output", type=Path)
    inspect_parser.add_argument(
        "--allow-unsupported",
        action="store_true",
        help="parse a ROM that does not match the selected profile",
    )

    extract_parser = subparsers.add_parser(
        "extract", help="extract a deterministic editable ROM workspace"
    )
    extract_parser.add_argument("rom", type=Path)
    extract_parser.add_argument("workspace", type=Path)
    extract_parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    extract_parser.add_argument("--force", action="store_true")

    rebuild_parser = subparsers.add_parser(
        "rebuild", help="rebuild a Nintendo DS ROM from an extracted workspace"
    )
    rebuild_parser.add_argument("rom", type=Path)
    rebuild_parser.add_argument("workspace", type=Path)
    rebuild_parser.add_argument("output", type=Path)
    rebuild_parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    rebuild_parser.add_argument("--force", action="store_true")

    patch_parser = subparsers.add_parser(
        "patch", help="apply guarded binary replacements to a workspace"
    )
    patch_parser.add_argument("workspace", type=Path)
    patch_parser.add_argument("patch_file", type=Path)

    add_gate_parser(subparsers)
    return parser


def _write_report(report: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(report)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(report, encoding="utf-8")
    temporary.replace(output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_usage(sys.stderr)
        return 2
    try:
        if arguments.command == "gate":
            return run_gate_command(arguments)
        if arguments.command == "inspect":
            profile = load_profile(arguments.profile)
            inspection = inspect_rom(
                arguments.rom,
                profile,
                require_supported=not arguments.allow_unsupported,
            )
            _write_report(inspection.to_json(), arguments.output)
            return 0
        if arguments.command == "extract":
            profile = load_profile(arguments.profile)
            workspace = arguments.workspace.expanduser().resolve()
            manifest = extract_workspace(
                arguments.rom,
                profile,
                ExtractionOptions(workspace=workspace, force=arguments.force),
            )
            print(
                f"Extracted workspace {workspace} "
                f"({len(manifest.files)} files, {len(manifest.overlays)} overlays); "
                f"manifest: {workspace / 'manifests/workspace.json'}"
            )
            return 0
        if arguments.command == "rebuild":
            profile = load_profile(arguments.profile)
            output = arguments.output.expanduser().resolve()
            report = rebuild_rom(
                arguments.rom,
                profile,
                arguments.workspace,
                RebuildOptions(output=output, force=arguments.force),
            )
            report_path = output.with_suffix(output.suffix + ".build.json")
            print(
                f"Rebuilt ROM {output} ({len(report.changes)} changes, "
                f"sha256 {report.output_sha256}); report: {report_path}"
            )
            return 0
        if arguments.command == "patch":
            workspace = arguments.workspace.expanduser().resolve()
            patch_file = arguments.patch_file.expanduser().resolve()
            report = apply_patch_set(workspace, patch_file)
            report_path = workspace / "manifests" / f"patch-{patch_file.stem}.json"
            print(
                f"Applied {len(report.applied)} patches to {workspace}; report: {report_path}"
            )
            return 0
    except UnsupportedRomError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (ProfileError, RomFormatError) as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 5
    except BakuganDSError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    parser.print_usage(sys.stderr)
    return 2
