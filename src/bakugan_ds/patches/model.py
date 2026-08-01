from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from bakugan_ds.errors import WorkspaceError


@dataclass(frozen=True)
class BinaryPatch:
    patch_id: str
    target: str
    offset: int
    expected: bytes
    replacement: bytes
    rationale: str


@dataclass(frozen=True)
class PatchSet:
    format_version: int
    profile_id: str
    patches: tuple[BinaryPatch, ...]


def _decode_hex(value: object, label: str) -> bytes:
    text = str(value)
    if len(text) == 0 or len(text) % 2 != 0:
        raise WorkspaceError(f"{label} must contain a nonempty even-length hex string")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise WorkspaceError(f"{label} is not valid hexadecimal") from exc


def load_patch_set(path: Path) -> PatchSet:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"cannot load patch file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WorkspaceError("patch document must be a JSON object")
    try:
        format_version = int(payload["format_version"])
        profile_id = str(payload["profile_id"])
        raw_patches = payload["patches"]
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"invalid patch document field: {exc}") from exc
    if format_version != 1:
        raise WorkspaceError(f"unsupported patch format version: {format_version}")
    if not isinstance(raw_patches, list) or not raw_patches:
        raise WorkspaceError("patches must be a nonempty array")

    patches: list[BinaryPatch] = []
    seen_ids: set[str] = set()
    for index, value in enumerate(raw_patches):
        if not isinstance(value, dict):
            raise WorkspaceError(f"patches[{index}] must be an object")
        try:
            patch_id = str(value["id"])
            patch_type = str(value["type"])
            target = str(value["target"])
            offset = int(value["offset"])
            expected = _decode_hex(value["expected"], f"patches[{index}].expected")
            replacement = _decode_hex(value["replacement"], f"patches[{index}].replacement")
            rationale = str(value.get("rationale", ""))
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid patches[{index}] field: {exc}") from exc
        if not patch_id or patch_id in seen_ids:
            raise WorkspaceError(f"duplicate or empty patch ID: {patch_id!r}")
        if patch_type != "binary_replace":
            raise WorkspaceError(f"unsupported patch type: {patch_type}")
        if offset < 0:
            raise WorkspaceError(f"patch {patch_id} offset must be nonnegative")
        if len(expected) != len(replacement):
            raise WorkspaceError(f"patch {patch_id} expected and replacement must be the same length")
        seen_ids.add(patch_id)
        patches.append(
            BinaryPatch(
                patch_id=patch_id,
                target=target,
                offset=offset,
                expected=expected,
                replacement=replacement,
                rationale=rationale,
            )
        )
    return PatchSet(format_version=format_version, profile_id=profile_id, patches=tuple(patches))
