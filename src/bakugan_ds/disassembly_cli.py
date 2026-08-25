from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

from bakugan_ds.disassembly import (
    disassemble_binary,
    find_module_params,
    overlay_layout_report,
    render_labelled_bytes,
    unified_disassembly_diff,
)
from bakugan_ds.errors import BakuganDSError
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.profile import load_profile


def _auto_int(value: str) -> int:
    return int(value, 0)


def _write_text(text: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(text)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(output)


def add_disassembly_parser(subparsers: Any, *, default_profile: Path) -> None:
    parser = subparsers.add_parser(
        "disasm",
        help="prepare and compare Nintendo DS executable components",
    )
    commands = parser.add_subparsers(dest="disasm_command")

    module_parser = commands.add_parser(
        "module-params",
        help="locate and decode Nitro ARM9 module parameters",
    )
    module_parser.add_argument("binary", type=Path)
    module_parser.add_argument("--base-address", type=_auto_int, default=0)
    module_parser.add_argument("--output", type=Path)

    overlay_parser = commands.add_parser(
        "overlay-map",
        help="report overlay placement and load relationships",
    )
    overlay_parser.add_argument("rom", type=Path)
    overlay_parser.add_argument("--profile", type=Path, default=default_profile)
    overlay_parser.add_argument("--output", type=Path)
    overlay_parser.add_argument(
        "--allow-unsupported",
        action="store_true",
        help="parse a non-profile ROM read-only",
    )

    labels_parser = commands.add_parser(
        "labels",
        help="emit labelled assembly byte blocks from a flat binary",
    )
    labels_parser.add_argument("binary", type=Path)
    labels_parser.add_argument("offsets", type=Path)
    labels_parser.add_argument("--vma", type=_auto_int, required=True)
    labels_parser.add_argument("--output", type=Path)

    diff_parser = commands.add_parser(
        "diff",
        help="unified objdump diff between two flat DS executable components",
    )
    diff_parser.add_argument("reference", type=Path)
    diff_parser.add_argument("candidate", type=Path)
    diff_parser.add_argument("--vma", type=_auto_int, required=True)
    diff_parser.add_argument("--start", type=_auto_int)
    diff_parser.add_argument("--end", type=_auto_int)
    diff_parser.add_argument("--thumb", action="store_true")
    diff_parser.add_argument("--processor", default="armv5te")
    diff_parser.add_argument("--objdump", default="arm-none-eabi-objdump")
    diff_parser.add_argument("--output", type=Path)


def _run_module_params(arguments: argparse.Namespace) -> int:
    data = arguments.binary.read_bytes()
    params = find_module_params(data, base_address=arguments.base_address)
    if params is None:
        raise BakuganDSError("Nitro module-parameter block was not found")
    _write_text(json.dumps(asdict(params), indent=2, sort_keys=True) + "\n", arguments.output)
    return 0


def _run_overlay_map(arguments: argparse.Namespace) -> int:
    profile = load_profile(arguments.profile)
    inspection = inspect_rom(
        arguments.rom,
        profile,
        require_supported=not arguments.allow_unsupported,
    )
    rom = arguments.rom.read_bytes()
    arm9_start = inspection.header.arm9_offset
    arm9_end = arm9_start + inspection.header.arm9_size
    params = find_module_params(
        rom[arm9_start:arm9_end],
        base_address=inspection.header.arm9_ram_address,
    )
    static_end = None if params is None else params.static_bss_end
    payload = {
        "source": str(arguments.rom),
        "profile_id": inspection.profile_id,
        "supported": inspection.supported,
        "module_params": None if params is None else asdict(params),
        "arm9": overlay_layout_report(inspection.arm9_overlays, static_end=static_end),
        "arm7": overlay_layout_report(inspection.arm7_overlays),
    }
    _write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", arguments.output)
    return 0


def _run_labels(arguments: argparse.Namespace) -> int:
    labels = tuple(int(value, 0) for value in arguments.offsets.read_text(encoding="utf-8").split())
    rendered = render_labelled_bytes(
        arguments.binary.read_bytes(),
        labels=labels,
        base_address=arguments.vma,
    )
    _write_text(rendered, arguments.output)
    return 0


def _run_diff(arguments: argparse.Namespace) -> int:
    common = {
        "base_address": arguments.vma,
        "start_address": arguments.start,
        "stop_address": arguments.end,
        "thumb": arguments.thumb,
        "processor": arguments.processor,
        "executable": arguments.objdump,
    }
    reference = disassemble_binary(arguments.reference, **common)
    candidate = disassemble_binary(arguments.candidate, **common)
    diff = unified_disassembly_diff(
        reference,
        candidate,
        reference_name=str(arguments.reference),
        candidate_name=str(arguments.candidate),
    )
    _write_text(diff, arguments.output)
    return 0


def run_disassembly_command(arguments: argparse.Namespace) -> int:
    if arguments.disasm_command == "module-params":
        return _run_module_params(arguments)
    if arguments.disasm_command == "overlay-map":
        return _run_overlay_map(arguments)
    if arguments.disasm_command == "labels":
        return _run_labels(arguments)
    if arguments.disasm_command == "diff":
        return _run_diff(arguments)
    raise BakuganDSError("a disasm subcommand is required")
