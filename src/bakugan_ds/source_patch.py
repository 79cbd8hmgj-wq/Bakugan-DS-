from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path

from bakugan_ds.compression.blz import decompress_blz, is_blz, parse_blz_footer
from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.arm32 import encode_branch
from bakugan_ds.profile import RomProfile
from bakugan_ds.workspace.manifest import load_workspace_manifest, sha256_bytes
from bakugan_ds.workspace.model import WorkspaceLayout
from bakugan_ds.workspace.paths import safe_relative_path

_SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_VALID_MODES = frozenset({"arm", "thumb"})
_VALID_SOURCE_SUFFIXES = frozenset({".c", ".s"})
_U32_MAX = 0xFFFFFFFF
_B6RE_ARM9_STORED_SIZE = 448_192
_B6RE_ARM9_REENCODE_PASSTHROUGH = 0x8000


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


@dataclass(frozen=True)
class SourceTarget:
    target: str
    path: Path
    runtime_base: int
    runtime_image: bytes
    placement_offset: int
    storage_encoding: str
    stored_size: int
    passthrough_length: int | None

    @property
    def runtime_size(self) -> int:
        return len(self.runtime_image)


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
            display_suffix = suffix or "<none>"
            raise WorkspaceError(
                f"unsupported source suffix for {normalized}: {display_suffix}"
            )
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
    definitions = _load_definitions(payload.get("definitions"))
    hooks = _load_hooks(payload.get("hooks"))
    for hook in hooks:
        if hook.mode != mode:
            raise WorkspaceError(
                f"hook {hook.hook_id!r} mode {hook.mode!r} differs from source patch mode "
                f"{mode!r}; an interworking veneer is required"
            )

    return SourcePatchManifest(
        format_version=format_version,
        profile_id=profile_id,
        target=target,
        runtime_address=runtime_address,
        max_size=max_size,
        mode=mode,
        expected_runtime_sha256=expected_runtime_sha256,
        sources=sources,
        definitions=definitions,
        hooks=hooks,
    )


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise WorkspaceError(f"cannot read {label}: {path}") from exc


def _resolve_overlay_target(
    layout: WorkspaceLayout,
    workspace_manifest_path: Path,
    manifest: SourcePatchManifest,
) -> tuple[Path, int, bytes, str, int | None]:
    workspace_manifest = load_workspace_manifest(workspace_manifest_path)
    overlay_id = int(manifest.target.split(":", 1)[1])
    overlay = next(
        (entry for entry in workspace_manifest.overlays if entry.overlay_id == overlay_id),
        None,
    )
    if overlay is None:
        raise WorkspaceError(f"workspace does not contain overlay {overlay_id}")
    path = layout.modified_overlays / f"overlay_{overlay_id:03d}.bin"
    runtime_image = _read_bytes(path, f"modified overlay {overlay_id}")
    if len(runtime_image) != overlay.decoded_size:
        raise WorkspaceError(
            f"modified overlay {overlay_id} size mismatch: "
            f"expected {overlay.decoded_size}, got {len(runtime_image)}"
        )
    return path, overlay.ram_address, runtime_image, "decoded-overlay", None


def _blz_reencode_passthrough(
    profile: RomProfile,
    kind: str,
    original_passthrough: int,
) -> int:
    # This exact B6RE ARM9 geometry is already covered by the repository's
    # runtime-safe ARM9 BLZ regression: 0x8000 passthrough, 448192 stored bytes.
    if (
        profile.id == "b6re_rev0"
        and kind == "arm9"
        and profile.expected.arm9_size == _B6RE_ARM9_STORED_SIZE
    ):
        return _B6RE_ARM9_REENCODE_PASSTHROUGH
    return original_passthrough


def _resolve_arm_target(
    layout: WorkspaceLayout,
    manifest: SourcePatchManifest,
    profile: RomProfile,
) -> tuple[Path, int, bytes, str, int | None]:
    is_arm9 = manifest.target == "arm9"
    kind = "arm9" if is_arm9 else "arm7"
    path = layout.modified / f"{kind}.bin"
    stored = _read_bytes(path, f"modified {kind.upper()}")
    expected_size = profile.expected.arm9_size if is_arm9 else profile.expected.arm7_size
    runtime_base = (
        profile.expected.arm9_ram_address if is_arm9 else profile.expected.arm7_ram_address
    )
    if len(stored) != expected_size:
        raise WorkspaceError(
            f"modified {kind.upper()} stored size mismatch: "
            f"expected {expected_size}, got {len(stored)}"
        )
    if is_blz(stored):
        footer = parse_blz_footer(stored)
        original_passthrough = len(stored) - footer.compressed_length
        runtime_image = decompress_blz(stored)
        passthrough_length = _blz_reencode_passthrough(
            profile,
            kind,
            original_passthrough,
        )
        if not 0 <= passthrough_length < len(runtime_image):
            raise WorkspaceError(
                f"BLZ re-encode passthrough {passthrough_length} is outside decoded {kind.upper()}"
            )
        return path, runtime_base, runtime_image, "blz", passthrough_length
    return path, runtime_base, stored, "raw-arm", None


def _validate_runtime_ranges(target: SourceTarget, manifest: SourcePatchManifest) -> None:
    runtime_end = target.runtime_base + target.runtime_size
    placement_end = manifest.runtime_address + manifest.max_size
    if manifest.runtime_address < target.runtime_base or placement_end > runtime_end:
        raise WorkspaceError(
            f"source patch placement range 0x{manifest.runtime_address:08X}-"
            f"0x{placement_end:08X} is outside {manifest.target} runtime image "
            f"0x{target.runtime_base:08X}-0x{runtime_end:08X}"
        )
    for hook in manifest.hooks:
        hook_end = hook.runtime_address + len(hook.expected)
        if hook.runtime_address < target.runtime_base or hook_end > runtime_end:
            raise WorkspaceError(
                f"hook {hook.hook_id!r} is outside {manifest.target} runtime image"
            )


def resolve_source_target(
    workspace: Path,
    manifest: SourcePatchManifest,
    profile: RomProfile,
) -> SourceTarget:
    layout = WorkspaceLayout.from_root(workspace)
    workspace_manifest_path = layout.manifests / "workspace.json"
    workspace_manifest = load_workspace_manifest(workspace_manifest_path)
    if manifest.profile_id != profile.id:
        raise WorkspaceError(
            "source patch profile mismatch: "
            f"manifest {manifest.profile_id!r}, profile {profile.id!r}"
        )
    if workspace_manifest.profile_id != profile.id:
        raise WorkspaceError(
            f"workspace profile mismatch: workspace {workspace_manifest.profile_id!r}, "
            f"profile {profile.id!r}"
        )

    if manifest.target.startswith("overlay:"):
        path, runtime_base, runtime_image, encoding, passthrough_length = _resolve_overlay_target(
            layout,
            workspace_manifest_path,
            manifest,
        )
    else:
        path, runtime_base, runtime_image, encoding, passthrough_length = _resolve_arm_target(
            layout,
            manifest,
            profile,
        )

    runtime_hash = sha256_bytes(runtime_image)
    if runtime_hash != manifest.expected_runtime_sha256:
        raise WorkspaceError(
            f"{manifest.target} runtime SHA-256 mismatch: "
            f"expected {manifest.expected_runtime_sha256}, got {runtime_hash}"
        )

    target = SourceTarget(
        target=manifest.target,
        path=path,
        runtime_base=runtime_base,
        runtime_image=runtime_image,
        placement_offset=manifest.runtime_address - runtime_base,
        storage_encoding=encoding,
        stored_size=path.stat().st_size,
        passthrough_length=passthrough_length,
    )
    _validate_runtime_ranges(target, manifest)
    return target


def _encode_thumb_branch(source_address: int, target_address: int, *, link: bool) -> bytes:
    if source_address % 2 or target_address % 2:
        raise WorkspaceError("Thumb branch source and target must be halfword aligned")
    displacement = target_address - (source_address + 4)
    if displacement % 2:
        raise WorkspaceError("Thumb branch displacement must be halfword aligned")

    if link:
        if not -4_194_304 <= displacement <= 4_194_302:
            raise WorkspaceError("Thumb BL target is outside signed 23-bit branch range")
        high = 0xF000 | ((displacement >> 12) & 0x7FF)
        low = 0xF800 | ((displacement >> 1) & 0x7FF)
        return struct.pack("<HH", high, low)

    if not -2_048 <= displacement <= 2_046:
        raise WorkspaceError("Thumb B target is outside signed 12-bit branch range")
    instruction = 0xE000 | ((displacement >> 1) & 0x7FF)
    return struct.pack("<H", instruction)


def encode_hook(hook: SourceHook, destination: int) -> bytes:
    if hook.mode == "arm":
        word = encode_branch(
            hook.runtime_address,
            destination,
            link=hook.link,
        )
        encoded = struct.pack("<I", word)
    elif hook.mode == "thumb":
        encoded = _encode_thumb_branch(
            hook.runtime_address,
            destination,
            link=hook.link,
        )
    else:
        raise WorkspaceError(f"hook {hook.hook_id!r} has unsupported mode: {hook.mode!r}")

    if len(encoded) != len(hook.expected):
        raise WorkspaceError(
            f"hook {hook.hook_id!r} guard length {len(hook.expected)} cannot hold "
            f"{len(encoded)}-byte {hook.mode.upper()} branch encoding"
        )
    return encoded
