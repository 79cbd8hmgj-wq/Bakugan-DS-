from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from bakugan_ds.errors import BakuganDSError, ProfileError, RomFormatError, UnsupportedRomError
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import load_profile

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
        if arguments.command == "inspect":
            profile = load_profile(arguments.profile)
            inspection = inspect_rom(
                arguments.rom,
                profile,
                require_supported=not arguments.allow_unsupported,
            )
            _write_report(inspection.to_json(), arguments.output)
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
