from pathlib import Path

from bakugan_ds.analysis import cli


def test_cli_requires_command(capsys) -> None:
    assert cli.main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_parse_hex_addresses() -> None:
    args = cli.build_parser().parse_args(
        [
            "scan",
            "--arm9",
            "a.bin",
            "--overlay7",
            "b.bin",
            "--reference",
            "r.json",
            "--output",
            "o.json",
            "--overlay7-base",
            "0x02219440",
        ]
    )
    assert args.overlay7 == Path("b.bin")
    assert args.overlay7_base == 0x02219440
