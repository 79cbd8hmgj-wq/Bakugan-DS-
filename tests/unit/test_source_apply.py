from __future__ import annotations

from pathlib import Path

import pytest

from bakugan_ds.compression.blz import compress_blz, decompress_blz, is_blz, parse_blz_footer
from bakugan_ds.errors import WorkspaceError
from bakugan_ds.source_apply import build_patched_runtime, encode_target_storage
from bakugan_ds.source_compile import CompiledSource
from bakugan_ds.source_patch import SourceHook, SourcePatchManifest, SourceTarget


def _manifest(
    *,
    hooks: tuple[SourceHook, ...] = (),
    mode: str = "arm",
) -> SourcePatchManifest:
    return SourcePatchManifest(
        format_version=1,
        profile_id="b6re_rev0",
        target="overlay:7",
        runtime_address=0x0221A000,
        max_size=0x20,
        mode=mode,
        expected_runtime_sha256="0" * 64,
        sources=("src/injected.c",),
        definitions=(),
        hooks=hooks,
    )


def _target(runtime: bytes, *, encoding: str = "decoded-overlay") -> SourceTarget:
    return SourceTarget(
        target="overlay:7",
        path=Path("overlay_007.bin"),
        runtime_base=0x02219000,
        runtime_image=runtime,
        placement_offset=0x1000,
        storage_encoding=encoding,
        stored_size=len(runtime),
        passthrough_length=None,
    )


def _compiled(image: bytes, symbols: tuple[tuple[str, int], ...] = ()) -> CompiledSource:
    return CompiledSource(
        image=image,
        symbols=symbols,
        source_hashes=(("src/injected.c", "1" * 64),),
        commands=(("clang", "..."),),
    )


def test_build_patched_runtime_places_image_without_touching_unused_budget() -> None:
    runtime = b"\xAA" * 0x1100

    patched, hooks = build_patched_runtime(
        _target(runtime),
        _manifest(),
        _compiled(b"\x01\x02\x03\x04"),
    )

    assert patched[0x1000:0x1004] == b"\x01\x02\x03\x04"
    assert patched[0x1004:0x1020] == b"\xAA" * 0x1C
    assert hooks == ()


def test_build_patched_runtime_checks_all_hook_guards_before_mutation() -> None:
    runtime = bytearray(b"\x00" * 0x1100)
    runtime[0x40:0x44] = bytes.fromhex("000000ea")
    hook = SourceHook(
        hook_id="entry",
        runtime_address=0x02219040,
        expected=bytes.fromhex("ffffffff"),
        symbol="entry",
        link=True,
        mode="arm",
    )

    with pytest.raises(WorkspaceError, match="guard mismatch"):
        build_patched_runtime(
            _target(bytes(runtime)),
            _manifest(hooks=(hook,)),
            _compiled(b"\x01\x02\x03\x04", (("entry", 0x0221A000),)),
        )

    assert bytes(runtime)[0x1000:0x1004] == b"\x00" * 4


def test_build_patched_runtime_rejects_missing_hook_symbol() -> None:
    hook = SourceHook(
        hook_id="entry",
        runtime_address=0x02219040,
        expected=b"\x00" * 4,
        symbol="missing",
        link=True,
        mode="arm",
    )

    with pytest.raises(WorkspaceError, match="missing symbol"):
        build_patched_runtime(
            _target(b"\x00" * 0x1100),
            _manifest(hooks=(hook,)),
            _compiled(b"\x00" * 4),
        )


def test_build_patched_runtime_rejects_hook_symbol_outside_emitted_image() -> None:
    hook = SourceHook(
        hook_id="entry",
        runtime_address=0x02219040,
        expected=b"\x00" * 4,
        symbol="entry",
        link=True,
        mode="arm",
    )

    with pytest.raises(WorkspaceError, match="resolves outside emitted image"):
        build_patched_runtime(
            _target(b"\x00" * 0x1100),
            _manifest(hooks=(hook,)),
            _compiled(b"\x00" * 4, (("entry", 0x02065BF4),)),
        )


def test_thumb_hook_canonicalizes_elf_thumb_function_symbol_bit() -> None:
    hook = SourceHook(
        hook_id="thumb_entry",
        runtime_address=0x02219040,
        expected=b"\x00" * 4,
        symbol="thumb_entry",
        link=True,
        mode="thumb",
    )

    patched, hooks = build_patched_runtime(
        _target(b"\x00" * 0x1100),
        _manifest(hooks=(hook,), mode="thumb"),
        _compiled(b"\x00" * 4, (("thumb_entry", 0x0221A001),)),
    )

    assert patched[0x40:0x44] != b"\x00" * 4
    assert hooks[0].destination == 0x0221A000


def test_arm_hook_rejects_thumb_marked_elf_symbol() -> None:
    hook = SourceHook(
        hook_id="entry",
        runtime_address=0x02219040,
        expected=b"\x00" * 4,
        symbol="entry",
        link=True,
        mode="arm",
    )

    with pytest.raises(WorkspaceError, match="Thumb-state symbol"):
        build_patched_runtime(
            _target(b"\x00" * 0x1100),
            _manifest(hooks=(hook,)),
            _compiled(b"\x00" * 4, (("entry", 0x0221A001),)),
        )


def test_build_patched_runtime_rejects_hook_overlap_with_injected_code() -> None:
    hook = SourceHook(
        hook_id="overlap",
        runtime_address=0x0221A000,
        expected=b"\x00" * 4,
        symbol="entry",
        link=True,
        mode="arm",
    )

    with pytest.raises(WorkspaceError, match="overlaps injected code"):
        build_patched_runtime(
            _target(b"\x00" * 0x1100),
            _manifest(hooks=(hook,)),
            _compiled(b"\x00" * 8, (("entry", 0x0221A000),)),
        )


def test_build_patched_runtime_rejects_overlapping_hooks() -> None:
    first = SourceHook(
        hook_id="first",
        runtime_address=0x02219040,
        expected=b"\x00" * 4,
        symbol="entry",
        link=True,
        mode="arm",
    )
    second = SourceHook(
        hook_id="second",
        runtime_address=0x02219040,
        expected=b"\x00" * 4,
        symbol="entry",
        link=True,
        mode="arm",
    )

    with pytest.raises(WorkspaceError, match="hook ranges overlap"):
        build_patched_runtime(
            _target(b"\x00" * 0x1100),
            _manifest(hooks=(first, second)),
            _compiled(b"\x00" * 4, (("entry", 0x0221A000),)),
        )


def test_encode_target_storage_keeps_decoded_overlay_bytes() -> None:
    runtime = b"\x12" * 0x1100
    target = _target(runtime)

    assert encode_target_storage(target, runtime) == runtime


def test_encode_target_storage_keeps_raw_arm_exact_size() -> None:
    runtime = b"\x34" * 0x1100
    target = _target(runtime, encoding="raw-arm")

    assert encode_target_storage(target, runtime) == runtime


def test_encode_target_storage_recompresses_blz_to_original_size() -> None:
    decoded = (b"ABCD" * 0x200) + (b"\x00" * 0x1000)
    minimal = compress_blz(decoded)
    stored = compress_blz(decoded, target_size=len(minimal) + 32)
    footer = parse_blz_footer(stored)
    target = SourceTarget(
        target="arm9",
        path=Path("arm9.bin"),
        runtime_base=0x02000000,
        runtime_image=decoded,
        placement_offset=0,
        storage_encoding="blz",
        stored_size=len(stored),
        passthrough_length=len(stored) - footer.compressed_length,
    )
    patched = bytearray(decoded)
    patched[0] ^= 1

    encoded = encode_target_storage(target, bytes(patched))

    assert len(encoded) == len(stored)
    assert is_blz(encoded)
    assert decompress_blz(encoded) == bytes(patched)


def test_encode_target_storage_fails_closed_without_blz_size_slack() -> None:
    decoded = (b"ABCD" * 0x200) + (b"\x00" * 0x1000)
    stored = compress_blz(decoded)
    footer = parse_blz_footer(stored)
    target = SourceTarget(
        target="arm9",
        path=Path("arm9.bin"),
        runtime_base=0x02000000,
        runtime_image=decoded,
        placement_offset=0,
        storage_encoding="blz",
        stored_size=len(stored),
        passthrough_length=len(stored) - footer.compressed_length,
    )
    patched = bytearray(decoded)
    patched[0] ^= 1

    with pytest.raises(WorkspaceError, match="exact stored size"):
        encode_target_storage(target, bytes(patched))


def test_encode_target_storage_rejects_runtime_length_change() -> None:
    target = _target(b"\x00" * 0x1100)

    with pytest.raises(WorkspaceError, match="runtime size"):
        encode_target_storage(target, b"\x00" * 0x10FF)
