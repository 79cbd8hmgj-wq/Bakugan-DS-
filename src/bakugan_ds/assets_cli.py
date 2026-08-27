from __future__ import annotations

import argparse
from pathlib import Path

from nds_disassembly_toolkit.assets_cli import add_assets_parser as _add_assets_parser
from nds_disassembly_toolkit.assets_cli import run_assets_command


def add_assets_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    *,
    default_profile: Path,
) -> None:
    _add_assets_parser(
        subparsers,
        default_profile=default_profile,
        supported_by_default=True,
    )


__all__ = ["add_assets_parser", "run_assets_command"]
