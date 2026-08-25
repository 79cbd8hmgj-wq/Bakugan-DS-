from __future__ import annotations

import argparse
from pathlib import Path

from bakugan_ds.errors import BakuganDSError
from bakugan_ds.profile import load_profile
from bakugan_ds.source_apply import apply_source_patch
from bakugan_ds.source_compile import SourceToolchain


def add_source_patch_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    *,
    default_profile: Path,
) -> None:
    source_parser = subparsers.add_parser(
        "source-patch",
        help="compile and apply guarded ARM source patches to a workspace",
    )
    source_subparsers = source_parser.add_subparsers(dest="source_patch_command")
    build_parser = source_subparsers.add_parser(
        "build",
        help="compile source and apply it to an extracted workspace",
    )
    build_parser.add_argument("workspace", type=Path)
    build_parser.add_argument("manifest", type=Path)
    build_parser.add_argument("--profile", type=Path, default=default_profile)
    build_parser.add_argument("--clang", default="clang")
    build_parser.add_argument("--ld", default="ld.lld")
    build_parser.add_argument("--nm", default="nm")


def run_source_patch_command(arguments: argparse.Namespace) -> int:
    if arguments.source_patch_command != "build":
        raise BakuganDSError("a source-patch subcommand is required")
    workspace = arguments.workspace.expanduser().resolve()
    manifest = arguments.manifest.expanduser().resolve()
    profile = load_profile(arguments.profile)
    toolchain = SourceToolchain(
        clang=arguments.clang,
        ld=arguments.ld,
        nm=arguments.nm,
    )
    report = apply_source_patch(
        workspace,
        manifest,
        profile,
        toolchain=toolchain,
    )
    report_path = workspace / "manifests" / f"source-patch-{manifest.stem}.json"
    print(
        f"Applied source patch {manifest.name} to {report.target} "
        f"({report.compiled_size} compiled bytes); report: {report_path}"
    )
    return 0
