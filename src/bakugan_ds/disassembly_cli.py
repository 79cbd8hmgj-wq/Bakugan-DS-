from __future__ import annotations

from pathlib import Path
from typing import Any

from nds_disassembly_toolkit.disassembly_cli import (
    add_disassembly_parser as _add_disassembly_parser,
    run_disassembly_command,
)


def add_disassembly_parser(subparsers: Any, *, default_profile: Path) -> None:
    _add_disassembly_parser(
        subparsers,
        default_profile=default_profile,
        supported_by_default=True,
    )


__all__ = ["add_disassembly_parser", "run_disassembly_command"]
