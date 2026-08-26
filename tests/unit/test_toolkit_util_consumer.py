import nds_disassembly_toolkit.util as toolkit_util

import bakugan_ds.util as bakugan_util


def test_binary_utilities_are_toolkit_owned() -> None:
    for name in ("require_range", "read_u16_le", "read_u32_le"):
        assert getattr(bakugan_util, name) is getattr(toolkit_util, name)


def test_buffer_alias_matches_toolkit() -> None:
    assert bakugan_util.Buffer == toolkit_util.Buffer
