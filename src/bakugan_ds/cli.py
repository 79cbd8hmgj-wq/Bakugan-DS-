from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from nds_disassembly_toolkit.cli import (
    add_patch_parser,
    add_rom_parsers,
    run_patch_command,
    run_rom_command,
)

from bakugan_ds.assets_cli import add_assets_parser, run_assets_command
from bakugan_ds.disassembly_cli import add_disassembly_parser, run_disassembly_command
from bakugan_ds.errors import BakuganDSError, ProfileError, RomFormatError, UnsupportedRomError
from bakugan_ds.gates.cli import add_gate_parser, run_gate_command
from bakugan_ds.source_patch_cli import add_source_patch_parser, run_source_patch_command

DEFAULT_PROFILE = Path("config/b6re_rev0.json")
_ROM_COMMANDS = frozenset({"inspect", "extract", "rebuild"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bakugan-ds")
    subparsers = parser.add_subparsers(dest="command")

    add_rom_parsers(
        subparsers,
        default_profile=DEFAULT_PROFILE,
        supported_by_default=True,
        allow_unsupported_commands={"inspect"},
    )
    add_patch_parser(subparsers)
    add_assets_parser(subparsers, default_profile=DEFAULT_PROFILE)
    add_disassembly_parser(subparsers, default_profile=DEFAULT_PROFILE)
    add_source_patch_parser(subparsers, default_profile=DEFAULT_PROFILE)
    add_gate_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_usage(sys.stderr)
        return 2
    try:
        if arguments.command == "assets":
            return run_assets_command(arguments)
        if arguments.command == "disasm":
            return run_disassembly_command(arguments)
        if arguments.command == "source-patch":
            return run_source_patch_command(arguments)
        if arguments.command == "gate":
            return run_gate_command(arguments)
        if arguments.command in _ROM_COMMANDS:
            return run_rom_command(arguments)
        if arguments.command == "patch":
            return run_patch_command(arguments)
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
