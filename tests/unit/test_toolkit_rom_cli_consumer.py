from pathlib import Path

import pytest
from nds_disassembly_toolkit import cli as toolkit_cli

from bakugan_ds import cli


def test_rom_cli_runner_is_toolkit_owned() -> None:
    assert cli.run_rom_command is toolkit_cli.run_rom_command


def test_bakugan_rom_parser_keeps_strict_policy(tmp_path: Path) -> None:
    parser = cli.build_parser()

    inspect_args = parser.parse_args(["inspect", "game.nds"])
    assert inspect_args.profile == cli.DEFAULT_PROFILE
    assert inspect_args.require_supported is True

    unsupported_args = parser.parse_args(["inspect", "game.nds", "--allow-unsupported"])
    assert unsupported_args.require_supported is False

    extract_args = parser.parse_args(["extract", "game.nds", str(tmp_path / "work")])
    assert extract_args.profile == cli.DEFAULT_PROFILE
    assert extract_args.require_supported is True

    rebuild_args = parser.parse_args(
        ["rebuild", "game.nds", str(tmp_path / "work"), str(tmp_path / "out.nds")]
    )
    assert rebuild_args.profile == cli.DEFAULT_PROFILE
    assert rebuild_args.require_supported is True

    with pytest.raises(SystemExit):
        parser.parse_args(
            ["extract", "game.nds", str(tmp_path / "work"), "--allow-unsupported"]
        )
