from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from bakugan_ds.analysis.model import Component
from bakugan_ds.analysis.references import import_reference_catalog, load_reference_catalog
from bakugan_ds.analysis.report import analyze_components, write_report


def _parse_address(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid address: {value}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m bakugan_ds.analysis")
    subparsers = parser.add_subparsers(dest="command")

    importer = subparsers.add_parser("import-reference")
    importer.add_argument("--bakugan-csv", type=Path, required=True)
    importer.add_argument("--gate-csv", type=Path, required=True)
    importer.add_argument("--ability-csv", type=Path, required=True)
    importer.add_argument("--output", type=Path, required=True)

    scanner = subparsers.add_parser("scan")
    scanner.add_argument("--arm9", type=Path, required=True)
    scanner.add_argument("--overlay7", type=Path, required=True)
    scanner.add_argument("--reference", type=Path, required=True)
    scanner.add_argument("--output", type=Path, required=True)
    scanner.add_argument("--arm9-base", type=_parse_address, default=0x02000000)
    scanner.add_argument("--overlay7-base", type=_parse_address, default=0x02219440)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_usage(sys.stderr)
        return 2
    try:
        if arguments.command == "import-reference":
            catalog = import_reference_catalog(
                bakugan_csv=arguments.bakugan_csv,
                gate_csv=arguments.gate_csv,
                ability_csv=arguments.ability_csv,
                output=arguments.output,
            )
            print(
                f"Imported {len(catalog['bakugan'])} Bakugan, "
                f"{len(catalog['gate_cards'])} Gate Cards, and "
                f"{len(catalog['ability_cards'])} Ability Cards"
            )
            return 0
        if arguments.command == "scan":
            components = (
                Component("arm9", arguments.arm9, arguments.arm9_base, arguments.arm9.read_bytes()),
                Component(
                    "overlay_0007",
                    arguments.overlay7,
                    arguments.overlay7_base,
                    arguments.overlay7.read_bytes(),
                ),
            )
            report = analyze_components(components, load_reference_catalog(arguments.reference))
            write_report(arguments.output, report)
            print(
                f"Wrote {arguments.output} with {len(report['keyword_strings'])} keyword strings, "
                f"{len(report['numeric_matches'])} numeric matches, and "
                f"{len(report['symbol_candidates'])} symbol candidates"
            )
            return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 4
    return 2
