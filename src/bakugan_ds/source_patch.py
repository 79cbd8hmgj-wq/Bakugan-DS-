from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.workspace.paths import safe_relative_path

_SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_VALID_MODES = frozenset({"arm", "thumb"})
_VALID_SOURCE_SUFFIXES = frozenset({".c", ".s"})
_U32_MAX = 0xFFFFFFFF


@dataclass(frozen=True)
class SourceHook:
    hook_id: str
    runtime_address: int
    expected: bytes
    symbol: str
    link: bool
    mode: str


@dataclass(frozen=True)
class SourcePatchManifest:
    format_version: int
    profile_id: str
    target: str
    runtime_address: int
    max_size: int
    mode: str
    expected_runtime_sha256: str
    sources: tuple[str, ...]
    definitions: tuple[tuple[str, int], ...]
    hooks: tuple[SourceHook, ...]


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkspaceError(f"{label} must be an integer")
    return value


def _require_u32(value: object, label: str) -> int:
    result = _require_integer(value, label)
    if not 0 <= result <= _U32_MAX:
        raise WorkspaceError(f"{label} must fit unsigned 32-bit")
    return result


def _require_positive(value: object, label: str) -> int:
    result = _require_integer(value, label)
    if result <= 0:
        raise WorkspaceError(f"{label} must be positive")
    return result


def _require_hash(value: object, label: str) -> str:
    result = str(value).lower()
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise WorkspaceError(f"{label} must be a 64-character SHA-256 value")
    return result


def _require_mode(value: object, label: str) -> str:
    result = str(value).lower()
    if result not in _VALID_MODES:
        raise WorkspaceError(f"{label} mode must be arm or thumb")
    return result


def _require_symbol(value: object, label: str) -> str:
    result = str(value)
    if not _SYMBOL_RE.fullmatch(result):
        raise WorkspaceError(f"{label} symbol is invalid: {result!r}")
    return result


def _require_aligned(address: int, mode: str, label: str) -> None:
    alignment = 4 if mode == "arm" else 2
    if address % alignment:
        mode_label = "ARM" if mode == "arm" else "Thumb"
        raise WorkspaceError(f"{label} must be {mode_label} aligned")


def _require_target(value: object) -> str:
    target = str(value)
    if target in {"arm9", "arm7"}:
        return target
    if target.startswith("overlay:"):
        suffix = target.split(":", 1)[1]
        try:
            overlay_id = int(suffix)
        except ValueError as exc:
            raise WorkspaceError(f"source patch target is invalid: {target!r}") from exc
        if overlay_id < 0 or suffix != str(overlay_id):
            raise WorkspaceError(f"source patch target is invalid: {target!r}")
        return target
    raise WorkspaceError(f"source patch target is unsupported: {target!r}")


def _decode_expected(value: object, label: str) -> bytes:
    text = str(value)
    if not text or len(text) % 2:
        raise WorkspaceError(f"{label} expected bytes must be nonempty even-length hexadecimal")
    try:
        result = bytes.fromhex(text)
    except ValueError as exc:
        raise WorkspaceError(f"{label} expected bytes are not valid hexadecimal") from exc
    if not result:
        raise WorkspaceError(f"{label} expected bytes must be nonempty")
    return result


def _load_sources(value: object) -> tuple[str, ...]:
    raw_sources = _require_array(value, "sources")
    if not raw_sources:
        raise WorkspaceError("sources must be a nonempty array")
    sources: list[str] = []
    seen: set[str] = set()
    for index, raw_source in enumerate(raw_sources):
        if not isinstance(raw_source, str):
            raise WorkspaceError(f"sources[{index}] must be a string")
        try:
            safe_path = safe_relative_path(raw_source)
        except ValueError as exc:
            raise WorkspaceError(f"unsafe path in sources[{index}]: {raw_source!r}") from exc
        normalized = safe_path.as_posix()
        if normalized in seen:
            raise WorkspaceError(f"duplicate source path: {normalized}")
        suffix = Path(normalized).suffix.lower()
        if suffix not in _VALID_SOURCE_SUFFIXES:
            raise WorkspaceError(f"unsupported source suffix for {normalized}: {suffix or '<none>'}")
        seen.add(normalized)
        sources.append(normalized)
    return tuple(sources)


def _load_definitions(value: object) -> tuple[tuple[str, int], ...]:
    if value is None:
        return ()
    payload = _require_object(value, "definitions")
    definitions: list[tuple[str, int]] = []
    for raw_name, raw_address in payload.items():
        name = _require_symbol(raw_name, "definition")
        address = _require_u32(raw_address, f"definition {name}")
        definitions.append((name, address))
    return tuple(sorted(definitions))


def _load_hooks(value: object) -> tuple[SourceHook, ...]:
    if value is None:
        return ()
    raw_hooks = _require_array(value, "hooks")
    hooks: list[SourceHook] = []
    seen_ids: set[str] = set()
    for index, raw_hook in enumerate(raw_hooks):
        hook = _require_object(raw_hook, f"hooks[{index}]")
        try:
            hook_id = str(hook["id"])
            runtime_address = _require_u32(
                hook["runtime_address"], f"hooks[{index}].runtime_address"
            )
            expected = _decode_expected(hook["expected"], f"hooks[{index}]")
            symbol = _require_symbol(hook["symbol"], f"hooks[{index}]")
            mode = _require_mode(hook["mode"], f"hooks[{index}]")
            link_value = hook["link"]
        except KeyError as exc:
            raise WorkspaceError(f"hooks[{index}] is missing field: {exc.args[0]}") from exc
        if not hook_id or hook_id in seen_ids:
            raise WorkspaceError(f"duplicate hook ID: {hook_id!r}")
        if type(link_value) is not bool:
            raise WorkspaceError(f"hooks[{index}].link must be boolean")
        _require_aligned(runtime_address, mode, f"hooks[{index}].runtime_address")
        seen_ids.add(hook_id)
        hooks.append(
            SourceHook(
                hook_id=hook_id,
                runtime_address=runtime_address,
                expected=expected,
                symbol=symbol,
                link=link_value,
                mode=mode,
            )
        )
    return tuple(hooks)


def load_source_patch_manifest(path: Path) -> SourcePatchManifest:
    try:
        payload = _require_object(
            json.loads(path.read_text(encoding="utf-8")),
            "source patch manifest",
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"cannot load source patch manifest {path}: {exc}") from exc

    try:
        format_version = _require_integer(payload["format_version"], "format_version")
        profile_id = str(payload["profile_id"])
        target = _require_target(payload["target"])
        runtime_address = _require_u32(payload["runtime_address"], "runtime_address")
        max_size = _require_positive(payload["max_size"], "max_size")
        mode = _require_mode(payload["mode"], "source patch")
        expected_runtime_sha256 = _require_hash(
            payload["expected_runtime_sha256"],
            "expected_runtime_sha256",
        )
        sources = _load_sources(payload["sources"])
    except KeyError as exc:
        raise WorkspaceError(f"source patch manifest is missing field: {exc.args[0]}") from exc

    if format_version != 1:
        raise WorkspaceError(f"unsupported source patch format version: {format_version}")
    if not profile_id:
        raise WorkspaceError("profile_id must be nonempty")
    _require_aligned(runtime_address, mode, "runtime_address")
    if runtime_address + max_size > _U32_MAX + 1:
        raise WorkspaceError("runtime_address plus max_size exceeds unsigned 32-bit address space")

    return SourcePatchManifest(
        format_version=format_version,
        profile_id=profile_id,
        target=target,
        runtime_address=runtime_address,
        max_size=max_size,
        mode=mode,
        expected_runtime_sha256=expected_runtime_sha256,
        sources=sources,
        definitions=_load_definitions(payload.get("definitions")),
        hooks=_load_hooks(payload.get("hooks")),
    )
