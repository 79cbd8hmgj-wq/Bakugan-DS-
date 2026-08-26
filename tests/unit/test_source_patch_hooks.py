from __future__ import annotations

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.source_patch import SourceHook, encode_hook


def _hook(*, mode: str, link: bool, expected: bytes, address: int) -> SourceHook:
    return SourceHook(
        hook_id="test_hook",
        runtime_address=address,
        expected=expected,
        symbol="entry",
        link=link,
        mode=mode,
    )


def test_arm_b_encodes_exact_little_endian_word() -> None:
    hook = _hook(mode="arm", link=False, expected=b"\x00" * 4, address=0x0221B000)

    assert encode_hook(hook, 0x0221A000) == bytes.fromhex("fefbffea")


def test_arm_bl_encodes_exact_little_endian_word() -> None:
    hook = _hook(mode="arm", link=True, expected=b"\x00" * 4, address=0x0221B000)

    assert encode_hook(hook, 0x0221A000) == bytes.fromhex("fefbffeb")


def test_thumb_b_encodes_forward_and_backward_vectors() -> None:
    forward = _hook(mode="thumb", link=False, expected=b"\x00" * 2, address=0x1000)
    backward = _hook(mode="thumb", link=False, expected=b"\x00" * 2, address=0x1100)

    assert encode_hook(forward, 0x1100) == bytes.fromhex("7ee0")
    assert encode_hook(backward, 0x1000) == bytes.fromhex("7ee7")


def test_thumb_bl_encodes_forward_and_backward_vectors() -> None:
    forward = _hook(mode="thumb", link=True, expected=b"\x00" * 4, address=0x1000)
    backward = _hook(mode="thumb", link=True, expected=b"\x00" * 4, address=0x1100)

    assert encode_hook(forward, 0x1100) == bytes.fromhex("00f07ef8")
    assert encode_hook(backward, 0x1000) == bytes.fromhex("fff77eff")


def test_thumb_b_accepts_exact_range_boundaries() -> None:
    hook = _hook(mode="thumb", link=False, expected=b"\x00" * 2, address=0x2000)

    assert len(encode_hook(hook, 0x2004 - 2048)) == 2
    assert len(encode_hook(hook, 0x2004 + 2046)) == 2


def test_thumb_bl_accepts_exact_range_boundaries() -> None:
    hook = _hook(mode="thumb", link=True, expected=b"\x00" * 4, address=0x00800000)

    assert len(encode_hook(hook, 0x00800004 - 4_194_304)) == 4
    assert len(encode_hook(hook, 0x00800004 + 4_194_302)) == 4


@pytest.mark.parametrize(
    ("mode", "link", "source", "destination"),
    [
        ("thumb", False, 0x2000, 0x2004 + 2048),
        ("thumb", False, 0x2000, 0x2004 - 2050),
        ("thumb", True, 0x00800000, 0x00800004 + 4_194_304),
        ("thumb", True, 0x00800000, 0x00800004 - 4_194_306),
    ],
)
def test_thumb_hook_rejects_out_of_range_branch(
    mode: str,
    link: bool,
    source: int,
    destination: int,
) -> None:
    expected = b"\x00" * (4 if link else 2)
    hook = _hook(mode=mode, link=link, expected=expected, address=source)

    with pytest.raises(WorkspaceError, match="range"):
        encode_hook(hook, destination)


def test_hook_rejects_unaligned_destination() -> None:
    hook = _hook(mode="thumb", link=False, expected=b"\x00" * 2, address=0x1000)

    with pytest.raises(WorkspaceError, match="aligned"):
        encode_hook(hook, 0x1101)


def test_hook_rejects_guard_length_that_cannot_hold_encoding() -> None:
    hook = _hook(mode="arm", link=True, expected=b"\x00" * 2, address=0x0221B000)

    with pytest.raises(WorkspaceError, match="guard length"):
        encode_hook(hook, 0x0221A000)
