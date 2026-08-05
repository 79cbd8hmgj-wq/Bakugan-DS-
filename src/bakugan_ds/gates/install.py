from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from bakugan_ds.compression.blz import (
    compress_blz,
    decompress_blz,
    is_blz,
    parse_blz_footer,
)
from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    load_authoring_document,
    load_milestone_6d_authoring_document,
)
from bakugan_ds.gates.loader import (
    ARM9_DECODED_SHA256,
    CACHE_ADDRESS,
    CACHE_SIZE,
    EXPANDED_OVERLAY_SIZE,
    REFERENCE_FILE_ID,
    REFERENCE_OVERLAY_SHA256,
    REFERENCE_OVERLAY_SIZE,
    REFERENCE_RAW_SHA256,
    REFERENCE_RAW_SIZE,
    append_validated_trailer,
    build_expanded_overlay,
)
from bakugan_ds.gates.record import build_trailer
from bakugan_ds.gates.runtime_module import RuntimeModule, build_milestone_6c_module
from bakugan_ds.gates.runtime_module_6d import build_milestone_6d_module
from bakugan_ds.patches.model import load_patch_set
from bakugan_ds.workspace.manifest import load_workspace_manifest, sha256_bytes
from bakugan_ds.workspace.model import WorkspaceLayout
from bakugan_ds.workspace.overrides import (
    BuildOverrides,
    OverlayLayoutOverride,
    RawNitroFsOverride,
)

SUPPORTED_PROFILE_ID = "b6re_rev0"
CORE_PATCHED_OVERLAY_SHA256 = "7e310ef95fcc3304870b98d11046ed453b1dc2d270f42a438af161b603437f2e"
DEFAULT_READINESS_PATH = Path("analysis/gates/milestone-6c-readiness.json")
DEFAULT_PATCH_PATH = Path("patches/gate-system2-milestone-6c-hooks.json")
CORE_PATCH_PATH = Path("patches/core-g-compression-400.json")
INSTALL_REPORT_NAME = "gate-system2-milestone-6c-install.json"
MILESTONE_6D_INSTALL_REPORT_NAME = "gate-system2-milestone-6d-install.json"
ARENA_LOW_OFFSET = 0x6264
ARENA_LOW_EXPECTED = bytes.fromhex("20bc2802")
ARENA_LOW_REPLACEMENT = bytes.fromhex("603c2902")
ARM9_REENCODE_PASSTHROUGH = 0x8000


@dataclass(frozen=True)
class InstallPatch:
    patch_id: str
    patch_type: str
    target: str
    offset: int
    expected: bytes
    replacement: bytes
    rationale: str

    def validate(self) -> None:
        if not self.patch_id.strip() or not self.target.strip() or not self.rationale.strip():
            raise WorkspaceError("install patch text fields must be nonempty")
        if self.patch_type not in {"binary_replace", "decoded_arm9_replace"}:
            raise WorkspaceError(f"unsupported install patch type: {self.patch_type}")
        if self.offset < 0:
            raise WorkspaceError("install patch offset must be nonnegative")
        if not self.expected or len(self.expected) != len(self.replacement):
            raise WorkspaceError("install patch byte geometry is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.patch_id,
            "type": self.patch_type,
            "target": self.target,
            "offset": self.offset,
            "length": len(self.expected),
            "expected_sha256": sha256_bytes(self.expected),
            "replacement_sha256": sha256_bytes(self.replacement),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class InstallReport:
    format_version: int
    profile_id: str
    trailer_sha256: str
    module_sha256: str
    raw_carrier_size: int
    overlay_size: int
    cache_range: tuple[int, int]
    raw_override: RawNitroFsOverride
    overlay_override: OverlayLayoutOverride
    binary_patches: tuple[InstallPatch, ...]
    arm9_sha256: str
    overlay_sha256: str
    dry_run: bool
    no_op: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "profile_id": self.profile_id,
            "trailer_sha256": self.trailer_sha256,
            "module_sha256": self.module_sha256,
            "raw_carrier_size": self.raw_carrier_size,
            "overlay_size": self.overlay_size,
            "cache_range": [f"0x{value:08X}" for value in self.cache_range],
            "raw_override": asdict(self.raw_override),
            "overlay_override": asdict(self.overlay_override),
            "binary_patches": [patch.to_dict() for patch in self.binary_patches],
            "arm9_sha256": self.arm9_sha256,
            "overlay_sha256": self.overlay_sha256,
            "dry_run": self.dry_run,
            "no_op": self.no_op,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class _PreparedInstall:
    report: InstallReport
    raw_path: Path
    raw_bytes: bytes
    overlay_path: Path
    overlay_bytes: bytes
    arm9_path: Path
    arm9_bytes: bytes
    override_path: Path
    override_bytes: bytes
    report_path: Path


def _read(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise WorkspaceError(f"cannot read {label}: {path}") from exc


def _load_readiness(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"cannot load Milestone 6C readiness: {path}") from exc
    if not isinstance(payload, dict):
        raise WorkspaceError("Milestone 6C readiness must be an object")
    if payload.get("ready_for_milestone_6c") is not True:
        raise WorkspaceError("Milestone 6C readiness is not approved")
    if payload.get("deferred") != ["arena_id"] or payload.get("failures") != []:
        raise WorkspaceError("Milestone 6C readiness boundary does not match")


def _decode_hex(value: object, label: str) -> bytes:
    try:
        result = bytes.fromhex(str(value))
    except ValueError as exc:
        raise WorkspaceError(f"{label} is not valid hexadecimal") from exc
    if not result:
        raise WorkspaceError(f"{label} must be nonempty")
    return result


def _load_install_patches(path: Path) -> tuple[InstallPatch, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"cannot load installl patch contract: {path}") from exc
if not isinstance(payload, dict):
        raise WorkspaceError("install patch contract must be an object")
    if payload.get("format_version") != 1 or payload.get("profile_id") != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("install patch contract profile or version mismatch")
    raw_patches = payload.get("patches")
    if not isinstance(raw_patches, list):
        raise WorkspaceError("install patch contract patches must be an array")
    patches: list[InstallPatch] = []
    ids: set[str] = set()
    for index, raw in enumerate(raw_patches):
        if not isinstance(raw, dict):
            raise WorkspaceError(f"install patches[{index}] must be an object")
        try:
            patch = InstallPatch(
                patch_id=str(raw["id"]),
                patch_type=str(raw["type"]),
                target=str(raw["target"]),
                offset=int(raw["offset"]),
                expected=_decode_hex(raw["expected"], f"patches[{index}].expected"),
                replacement=_decoe_hex(raw["replacement"], f"patches[{index}].replacement"),
                rationale=str(raw["rationale"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid install patches[{index}]: {exc}") from exc
        patch.validate()
        if patch.patch_id in ids:
            raise WorkspaceError(f"duplicate install patch id: {patch.patch_id}")
        ids.add(patch.patch_id)
        patches.append(patch)
    return tuple(patches)


def _generated_install_patches(
    path: Path,
    module: RuntimeModule,
) -> tuple[InstallPatch, ...]:
    stored = _load_install_patches(path)
    generated = module.hook_replacements
    if len(stored) != len(generated):
        raise WorkspaceError(stored Gate hook count does not match generated module)
    patches: list[InstallPatch] = []
    for patch, generated_bytes in zip(stored, generated, strict=True):
        patches.append(replace(patch, replacement=generated_bytes))
    return tuple(patches)


def _validate_patch_contract(
    patches: tuple[InstallPatch, ...],
    module: RuntimeModule,
) -> None:
    expected_ids = {
        "gate-system2-gate-bonus-hook",
        "gate-system2-context-store-hook",
        "gate-system2-selector-hook",
        "gate-system2-loader-hook",
        "gate-system2-result-clear-call",
        "gate-system2-result-clear-cutscene-call",
        "gate-system2-arena-low-bound",
    }
    if {patch.patch_id for patch in patches} != expected_ids:
        raise WorkspaceError("install patch contract must contain the exact seven guards)
    expected_replacements = iter(module.hook_replacements)
    for patch in patches:
        if patch.patch_id == "gate-system2-arena-low-bound":
            if patch.expected != ARENA_LOW_EXPECTED or patch.replacement != ARENA_LOW_REPLACEMENT:
                raise WorkspaceError("arena-low bound patch contract is not exact")
        else:
            expected_replacement = next(expected_replacements)
            if patch.replacement != expected_replacement:
                raise WorkspaceError(f"{patch.patch_id } replacement does not match generated module")


def _apply_patches(data: bytes, patches: tuple[InstallPatch, ...], *, target: str) -> bytes:
    output = bytearray(data)
    spans: list[tuple[int, int, str]] = []
    for patch in patches:
        if patch.target != target:
            continue
        end = patch.offset + len(patch.expected)
        if end > len(output):
            raise WorkspaceError(f"{patch.patch_id} exceeds {target}")
        for existing_start, existing_end, existing_id in spans:
            if not (end <= existing_start or patch.offset >= existing_end):
                raise WorkspaceError(f"{patch.patch_id} overlaps {existing_id}")
        actual = bytes(output[patch.offset:end])
        if actual != patch.expected:
            raise WorkspaceError(
                f"{patch.patch_id} stale bytes in {target} at 0x{patch.offset:X}"
            )
        output[patch.offset:end] = patch.replacement
        spans.append((patch.offset, end, patch.patch_id))
    return bytes(output)


def _overlay_layout_preconditions(workspace: Path) -> None:
    layout = WorkspaceLayout.from_root(workspace)
    manifest = load_workspace_manifest(layout.manifest)
    overlay = next((overlay for overlay in manifest.overlays if overlay.overlay_id == 7), None)
    if overlay is None:
        raise WorkspaceError("workspace manifest lacks overlay 7")
    if (
        overlay.ram_address != 0x02219440
        or overlay.ram_size != REFERENCE_OVERLAY_SIZE
        or overlay.bss_size != 0x640
        or overlay.decoded_sha256 != REFERENCE_OVERLAY_SHA256
    ):
        raise WorkspaceError("workspace overlay 7 layout is not the supported b6re_rev0 build")

    target = nregay_table = manifest.header.arm9_overlay_offset + 7 * 32
    table_end = manifest.header.arm9_overlay_offset + manifest.header.arm9_overlay_size
    if target + 32 > table_end:
        raise WorkspaceError("overlay 7 table entry falls outside the ARM9 overlay table")
    if nregay_table < 0x200:
        raise WorkspaceError("overlay 7 table entry falls inside the NDC header")
    if nregay_table + 32 > manifest.header.rom_used_size:
        raise WorkspaceError("overlay 7 table entry exceeds the used ROM size")

    modified_overlay = _read(layout.modified_overlays / "overlay_007.bin", "modified overlay 7")
    if sha256_bytes(modified_overlay) != CORE_PATCHED_OVERLAY_SHA256:
        raise WorkspaceError(foverlay 7 is not the approved core-G baseline")
    original_arm9 = _read(layout.original / "arm9.bin", "original ARM9")
    if sha256_bytes(original_arm9) != ARM9_DECODED_SHA256:
        raise WorkspaceError("original ARM9 is not the supported b6re_rev0 build")

    entry = manifest.file_by_id(REFERENCE_FILE_ID)
    if entry.path != "font/mes_CardName.mes":
        raise WorkspaceError("file ID 2762 path does not match the approved carrier")
    raw = _read(layout.original_raw_nitrofs / entry.path, "original raw carrier")
    if len(raw) != REFERENCE_RAW_SIZE or sha256_bytes(raw) != REFERENCE_RAW_SHA256:
        raise WorkspaceError("original raw carrier does not match the supported build")

    if not is_blz(raw):
        raise WorkspaceError(foriginal raw carrier is not BLZ-encoded")

    return layout
