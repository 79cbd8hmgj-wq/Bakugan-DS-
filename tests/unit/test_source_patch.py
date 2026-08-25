from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from bakugan_ds.source_patch import load_source_patch_manifest

from bakugan_ds.errors import WorkspaceError

TARGET_HASH = hashlib.sha256(b"target").hexdigest()


def _manifest_payload() -> dict[str, object]:
    return {
        "format_version": 1,
        "profile_id": "b6re_rev0",
        "target": "overlay:7",
        "runtime_address": 0x0221A000,
        "max_size": 0x100,
        "mode": "arm",
        "expected_runtime_sha256": TARGET_HASH,
        "sources": ["src/injected.c"],
        "definitions": {"known_helper": 0x02065BF4},
        "hooks": [
            {
                "id": "call_injected",
                "runtime_address": 0x0221B000,
                "expected": "000000ea",
                "symbol": "injected_entry",
                "link": True,
                "mode": "arm",
            }
        ],
    }


def _write_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "source-patch.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_source_patch_manifest_normalizes_valid_payload(tmp_path: Path) -> None:
    manifest = load_source_patch_manifest(_write_manifest(tmp_path, _manifest_payload()))

    assert manifest.profile_id == "b6re_rev0"
    assert manifest.target == "overlay:7"
    assert manifest.runtime_address == 0x0221A000
    assert manifest.max_size == 0x100
    assert manifest.mode == "arm"
    assert manifest.expected_runtime_sha256 == TARGET_HASH
    assert manifest.sources == ("src/injected.c",)
    assert manifest.definitions == (("known_helper", 0x02065BF4),)
    assert manifest.hooks[0].expected == bytes.fromhex("000000ea")
    assert manifest.hooks[0].link is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("format_version", 2, "source patch format version"),
        ("profile_id", "", "profile_id"),
        ("target", "overlay:x", "target"),
        ("target", "nitrofs:file.bin", "target"),
        ("runtime_address", -1, "runtime_address"),
        ("runtime_address", 0x0221A002, "ARM aligned"),
        ("max_size", 0, "max_size"),
        ("mode", "mips", "mode"),
        ("expected_runtime_sha256", "bad", "SHA-256"),
    ],
)
def test_manifest_rejects_invalid_top_level_fields(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    payload = _manifest_payload()
    payload[field] = value

    with pytest.raises(WorkspaceError, match=message):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_source_path_traversal(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["sources"] = ["../escape.c"]

    with pytest.raises(WorkspaceError, match="unsafe path"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_duplicate_sources(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["sources"] = ["src/injected.c", "src/injected.c"]

    with pytest.raises(WorkspaceError, match="duplicate source"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_invalid_source_suffix(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["sources"] = ["src/injected.txt"]

    with pytest.raises(WorkspaceError, match="source suffix"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_invalid_definition_symbol(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["definitions"] = {"not-a-symbol": 0x02000000}

    with pytest.raises(WorkspaceError, match="definition symbol"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_duplicate_hook_ids(tmp_path: Path) -> None:
    payload = _manifest_payload()
    hook = dict(payload["hooks"][0])  # type: ignore[index]
    payload["hooks"] = [hook, hook]

    with pytest.raises(WorkspaceError, match="duplicate hook ID"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_malformed_hook_expected_bytes(tmp_path: Path) -> None:
    payload = _manifest_payload()
    hook = dict(payload["hooks"][0])  # type: ignore[index]
    hook["expected"] = "abc"
    payload["hooks"] = [hook]

    with pytest.raises(WorkspaceError, match="expected"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_manifest_rejects_non_boolean_hook_link(tmp_path: Path) -> None:
    payload = _manifest_payload()
    hook = dict(payload["hooks"][0])  # type: ignore[index]
    hook["link"] = 1
    payload["hooks"] = [hook]

    with pytest.raises(WorkspaceError, match="link"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))


def test_thumb_manifest_requires_halfword_alignment(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["mode"] = "thumb"
    payload["runtime_address"] = 0x0221A001

    with pytest.raises(WorkspaceError, match="Thumb aligned"):
        load_source_patch_manifest(_write_manifest(tmp_path, payload))
