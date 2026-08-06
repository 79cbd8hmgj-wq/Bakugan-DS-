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
MILESTONE_6E_INSTALL_REPORT_NAME = "gate-system2-milestone-6e-install.json"
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
        raise WorkspaceError(f"cannot load install patch contract: {path}") from exc
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
                replacement=_decode_hex(raw["replacement"], f"patches[{index}].replacement"),
                rationale=str(raw["rationale"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid install patches[{index}]: {exc}") from exc
        patch.validate()
        if patch.patch_id in ids:
            raise WorkspaceError(f"duplicate install patch ID: {patch.patch_id}")
        ids.add(patch.patch_id)
        patches.append(patch)
    return tuple(patches)


def _generated_install_patches(
    path: Path,
    module: RuntimeModule,
) -> tuple[InstallPatch, ...]:
    stored = _load_install_patches(path)
    hooks_by_offset = {hook.component_offset: hook for hook in module.hook_replacements}
    generated: list[InstallPatch] = []
    for patch in stored:
        if patch.target != "overlay:7":
            generated.append(patch)
            continue
        hook = hooks_by_offset.get(patch.offset)
        if hook is None:
            raise WorkspaceError(
                f"install patch contract contains unknown overlay offset: {patch.offset}"
            )
        if patch.expected != hook.expected:
            raise WorkspaceError(
                f"install patch expected bytes differ from generated hook: {patch.patch_id}"
            )
        generated.append(replace(patch, replacement=hook.replacement))
    if {patch.offset for patch in generated if patch.target == "overlay:7"} != set(
        hooks_by_offset
    ):
        raise WorkspaceError("install patch contract omits a generated overlay hook")
    return tuple(generated)


def _apply_core_patch(original_overlay: bytes) -> bytes:
    buffer = bytearray(original_overlay)
    patch_set = load_patch_set(CORE_PATCH_PATH)
    for patch in patch_set.patches:
        if patch.target != "overlay:7":
            raise WorkspaceError("core-G patch contains a non-overlay-7 target")
        end = patch.offset + len(patch.expected)
        if bytes(buffer[patch.offset : end]) != patch.expected:
            raise WorkspaceError("core-G patch expected bytes do not match overlay 7")
        buffer[patch.offset : end] = patch.replacement
    result = bytes(buffer)
    if sha256_bytes(result) != CORE_PATCHED_OVERLAY_SHA256:
        raise WorkspaceError("core-G patched overlay SHA-256 does not match")
    return result


def _validate_patch_contract(
    patches: tuple[InstallPatch, ...],
    module: RuntimeModule,
) -> None:
    expected_overlay = {
        (hook.component_offset, hook.expected, hook.replacement)
        for hook in module.hook_replacements
    }
    actual_overlay = {
        (patch.offset, patch.expected, patch.replacement)
        for patch in patches
        if patch.target == "overlay:7"
    }
    if actual_overlay != expected_overlay:
        raise WorkspaceError("install patch contract does not match generated hooks")
    arena = [patch for patch in patches if patch.target == "arm9-decoded"]
    if len(arena) != 1:
        raise WorkspaceError("install patch contract requires one decoded ARM9 patch")
    patch = arena[0]
    if (
        patch.offset,
        patch.expected,
        patch.replacement,
    ) != (ARENA_LOW_OFFSET, ARENA_LOW_EXPECTED, ARENA_LOW_REPLACEMENT):
        raise WorkspaceError("decoded ARM9 arena-low patch does not match")


def _patch_overlay(core_overlay: bytes, patches: tuple[InstallPatch, ...]) -> bytes:
    buffer = bytearray(core_overlay)
    for patch in patches:
        if patch.target != "overlay:7":
            continue
        end = patch.offset + len(patch.expected)
        if bytes(buffer[patch.offset : end]) != patch.expected:
            raise WorkspaceError(f"stale overlay hook: {patch.patch_id}")
        buffer[patch.offset : end] = patch.replacement
    return bytes(buffer)


def _patch_arm9(stored: bytes, expected_decoded_hash: str) -> bytes:
    if not is_blz(stored):
        raise WorkspaceError("workspace ARM9 is not BLZ-compressed")
    decoded = bytearray(decompress_blz(stored))
    if sha256_bytes(bytes(decoded)) != expected_decoded_hash:
        raise WorkspaceError("decoded ARM9 SHA-256 does not match")
    if decoded[ARENA_LOW_OFFSET : ARENA_LOW_OFFSET + 4] != ARENA_LOW_EXPECTED:
        raise WorkspaceError("decoded ARM9 arena-low expected bytes do not match")
    decoded[ARENA_LOW_OFFSET : ARENA_LOW_OFFSET + 4] = ARENA_LOW_REPLACEMENT
    footer = parse_blz_footer(stored)
    original_passthrough = len(stored) - footer.compressed_length
    if original_passthrough > ARM9_REENCODE_PASSTHROUGH:
        raise WorkspaceError("original ARM9 passthrough exceeds re-encode boundary")
    return compress_blz(
        decoded,
        passthrough_length=ARM9_REENCODE_PASSTHROUGH,
        target_size=len(stored),
    )


def _prepare_install(
    workspace: Path,
    authoring_path: Path,
    *,
    readiness_path: Path,
    dry_run: bool,
    milestone_6d: bool = False,
    report_name: str | None = None,
) -> _PreparedInstall:
    layout = WorkspaceLayout.from_root(workspace)
    manifest = load_workspace_manifest(layout.manifests / "workspace.json")
    if manifest.profile_id != SUPPORTED_PROFILE_ID:
        raise WorkspaceError("Milestone 6C installer supports only b6re_rev0")
    _load_readiness(readiness_path)

    records = (
        load_milestone_6d_authoring_document(authoring_path)
        if milestone_6d
        else load_authoring_document(authoring_path)
    )
    trailer = build_trailer(records)
    module = build_milestone_6d_module() if milestone_6d else build_milestone_6c_module()
    patches = _generated_install_patches(DEFAULT_PATCH_PATH, module)
    _validate_patch_contract(patches, module)

    carrier_entry = next(
        (entry for entry in manifest.files if entry.file_id == REFERENCE_FILE_ID),
        None,
    )
    if carrier_entry is None:
        raise WorkspaceError("workspace does not contain Gate carrier file ID 2762")
    carrier_path = Path(*carrier_entry.path.split("/"))
    original_carrier = _read(
        layout.original_raw_nitrofs / carrier_path,
        "original Gate carrier",
    )
    if len(original_carrier) != REFERENCE_RAW_SIZE:
        raise WorkspaceError("Gate carrier size does not match")
    if sha256_bytes(original_carrier) != REFERENCE_RAW_SHA256:
        raise WorkspaceError("Gate carrier SHA-256 does not match")
    raw_with_trailer = append_validated_trailer(
        original_carrier,
        trailer,
        expected_raw_sha256=REFERENCE_RAW_SHA256,
    )

    original_overlay = _read(
        layout.original_decoded_overlays / "overlay_007.bin",
        "original decoded overlay 7",
    )
    if len(original_overlay) != REFERENCE_OVERLAY_SIZE:
        raise WorkspaceError("original overlay 7 size does not match")
    if sha256_bytes(original_overlay) != REFERENCE_OVERLAY_SHA256:
        raise WorkspaceError("original overlay 7 SHA-256 does not match")
    core_overlay = _apply_core_patch(original_overlay)
    hooked_overlay = _patch_overlay(core_overlay, patches)
    expanded_overlay = build_expanded_overlay(hooked_overlay, module.image)

    original_arm9 = _read(layout.original / "arm9.bin", "original ARM9")
    if sha256_bytes(original_arm9) != manifest.arm9_sha256:
        raise WorkspaceError("original ARM9 SHA-256 does not match manifest")
    patched_arm9 = _patch_arm9(original_arm9, ARM9_DECODED_SHA256)

    raw_override = RawNitroFsOverride(
        file_id=REFERENCE_FILE_ID,
        path=carrier_entry.path,
        expected_size=len(original_carrier),
        expected_sha256=sha256_bytes(original_carrier),
        replacement_size=len(raw_with_trailer),
        replacement_sha256=sha256_bytes(raw_with_trailer),
    )
    overlay_entry = next(
        (entry for entry in manifest.overlays if entry.overlay_id == 7),
        None,
    )
    if overlay_entry is None:
        raise WorkspaceError("workspace does not contain overlay 7")
    overlay_override = OverlayLayoutOverride(
        overlay_id=7,
        expected_ram_size=overlay_entry.ram_size,
        expected_bss_size=overlay_entry.bss_size,
        replacement_ram_size=EXPANDED_OVERLAY_SIZE,
        replacement_bss_size=CACHE_SIZE,
        replacement_flags=0,
    )
    overrides = BuildOverrides(
        format_version=1,
        profile_id=SUPPORTED_PROFILE_ID,
        raw_nitrofs=(raw_override,),
        overlays=(overlay_override,),
    )
    overrides.validate()
    override_bytes = (json.dumps(overrides.to_dict(), indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )

    report = InstallReport(
        format_version=1,
        profile_id=SUPPORTED_PROFILE_ID,
        trailer_sha256=sha256_bytes(trailer),
        module_sha256=module.sha256,
        raw_carrier_size=len(raw_with_trailer),
        overlay_size=len(expanded_overlay),
        cache_range=(CACHE_ADDRESS, CACHE_ADDRESS + CACHE_SIZE),
        raw_override=raw_override,
        overlay_override=overlay_override,
        binary_patches=patches,
        arm9_sha256=sha256_bytes(patched_arm9),
        overlay_sha256=sha256_bytes(expanded_overlay),
        dry_run=dry_run,
        no_op=False,
    )
    return _PreparedInstall(
        report=report,
        raw_path=layout.modified_raw_nitrofs / carrier_path,
        raw_bytes=raw_with_trailer,
        overlay_path=layout.modified_overlays / "overlay_007.bin",
        overlay_bytes=expanded_overlay,
        arm9_path=layout.modified / "arm9.bin",
        arm9_bytes=patched_arm9,
        override_path=layout.build_overrides,
        override_bytes=override_bytes,
        report_path=layout.manifests
        / (
            report_name
            or (
                MILESTONE_6D_INSTALL_REPORT_NAME
                if milestone_6d
                else INSTALL_REPORT_NAME
            )
        ),
    )


def _matches(path: Path, expected: bytes) -> bool:
    try:
        return path.read_bytes() == expected
    except OSError:
        return False


def _write_transaction(targets: tuple[tuple[Path, bytes], ...]) -> None:
    snapshots: dict[Path, bytes | None] = {}
    temporaries: dict[Path, Path] = {}
    try:
        for path, data in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            snapshots[path] = path.read_bytes() if path.exists() else None
            handle = tempfile.NamedTemporaryFile(  # noqa: SIM115
                prefix=f".{path.name}.tmp-",
                dir=path.parent,
                delete=False,
            )
            temporary = Path(handle.name)
            with handle:
                handle.write(data)
                handle.flush()
            temporaries[path] = temporary
        for path, _data in targets:
            temporaries[path].replace(path)
    except Exception:
        for temporary in temporaries.values():
            temporary.unlink(missing_ok=True)
        for path, previous in snapshots.items():
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous)
        raise


def _load_prior_report(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"cannot load prior Gate install report: {path}") from exc
    if not isinstance(payload, dict):
        raise WorkspaceError("prior Gate install report must be an object")
    return payload


def _validate_prior_install(
    prepared: _PreparedInstall,
    prior_report_path: Path,
) -> None:
    payload = _load_prior_report(prior_report_path)
    raw_override = payload.get("raw_override")
    if not isinstance(raw_override, dict):
        raise WorkspaceError("prior Gate install report lacks raw override data")
    expected_raw = raw_override.get("replacement_sha256")
    expected_overlay = payload.get("overlay_sha256")
    expected_arm9 = payload.get("arm9_sha256")
    if not all(isinstance(value, str) and len(value) == 64 for value in (
        expected_raw,
        expected_overlay,
        expected_arm9,
    )):
        raise WorkspaceError("prior Gate install report hashes are invalid")
    if sha256_bytes(_read(prepared.raw_path, "prior Gate carrier")) != expected_raw:
        raise WorkspaceError("prior Gate carrier differs from its install report")
    if sha256_bytes(_read(prepared.overlay_path, "prior Gate overlay")) != expected_overlay:
        raise WorkspaceError("prior Gate overlay differs from its install report")
    if sha256_bytes(_read(prepared.arm9_path, "prior Gate ARM9")) != expected_arm9:
        raise WorkspaceError("prior Gate ARM9 differs from its install report")


def _install_prepared(
    workspace: Path,
    prepared: _PreparedInstall,
    *,
    milestone_label: str,
    allow_prior_report: Path | None = None,
    allow_pristine_extracted: bool = False,
) -> InstallReport:
    marker_exists = prepared.report_path.exists()
    expected_targets = (
        (prepared.raw_path, prepared.raw_bytes),
        (prepared.overlay_path, prepared.overlay_bytes),
        (prepared.arm9_path, prepared.arm9_bytes),
        (prepared.override_path, prepared.override_bytes),
    )
    if marker_exists:
        if not all(_matches(path, data) for path, data in expected_targets):
            raise WorkspaceError(f"existing {milestone_label} install is partial or divergent")
        return replace(prepared.report, dry_run=prepared.report.dry_run, no_op=True)

    prior_validated = False
    if allow_prior_report is not None and allow_prior_report.exists():
        _validate_prior_install(prepared, allow_prior_report)
        prior_validated = True

    if not prior_validated and (prepared.raw_path.exists() or prepared.override_path.exists()):
        raise WorkspaceError(f"preexisting divergent {milestone_label} override outputs")

    layout = WorkspaceLayout.from_root(workspace)
    if not prior_validated:
        current_overlay = _read(prepared.overlay_path, "modified overlay 7")
        current_overlay_sha256 = sha256_bytes(current_overlay)
        approved_baselines = {CORE_PATCHED_OVERLAY_SHA256}
        if allow_pristine_extracted:
            approved_baselines.add(REFERENCE_OVERLAY_SHA256)
        if current_overlay_sha256 not in approved_baselines:
            raise WorkspaceError(
                "modified overlay 7 is not an approved pristine or core-G baseline"
            )
        current_arm9 = _read(prepared.arm9_path, "modified ARM9")
        original_arm9 = _read(layout.original / "arm9.bin", "original ARM9")
        if current_arm9 != original_arm9:
            raise WorkspaceError("modified ARM9 has divergent preexisting changes")
    if prepared.report.dry_run:
        return prepared.report

    installed_report = replace(prepared.report, dry_run=False, no_op=False)
    targets = (
        *expected_targets,
        (prepared.report_path, installed_report.to_json().encode("utf-8")),
    )
    _write_transaction(targets)
    return installed_report


def install_milestone_6c(
    workspace: Path,
    authoring_path: Path,
    *,
    dry_run: bool = False,
    readiness_path: Path | None = None,
) -> InstallReport:
    resolved_workspace = workspace.expanduser().resolve()
    prepared = _prepare_install(
        resolved_workspace,
        authoring_path.expanduser().resolve(),
        readiness_path=(readiness_path or DEFAULT_READINESS_PATH).expanduser().resolve(),
        dry_run=dry_run,
    )
    return _install_prepared(
        resolved_workspace,
        prepared,
        milestone_label="Milestone 6C",
    )


def install_milestone_6d(
    workspace: Path,
    authoring_path: Path,
    *,
    dry_run: bool = False,
    readiness_path: Path | None = None,
) -> InstallReport:
    resolved_workspace = workspace.expanduser().resolve()
    prepared = _prepare_install(
        resolved_workspace,
        authoring_path.expanduser().resolve(),
        readiness_path=(readiness_path or DEFAULT_READINESS_PATH).expanduser().resolve(),
        dry_run=dry_run,
        milestone_6d=True,
    )
    layout = WorkspaceLayout.from_root(resolved_workspace)
    return _install_prepared(
        resolved_workspace,
        prepared,
        milestone_label="Milestone 6D",
        allow_prior_report=layout.manifests / INSTALL_REPORT_NAME,
        allow_pristine_extracted=True,
    )


def install_milestone_6e(
    workspace: Path,
    authoring_path: Path,
    *,
    dry_run: bool = False,
    readiness_path: Path | None = None,
) -> InstallReport:
    """Install the approved complete 103-card Milestone 6E roster transactionally."""
    resolved_workspace = workspace.expanduser().resolve()
    prepared = _prepare_install(
        resolved_workspace,
        authoring_path.expanduser().resolve(),
        readiness_path=(readiness_path or DEFAULT_READINESS_PATH).expanduser().resolve(),
        dry_run=dry_run,
        milestone_6d=True,
        report_name=MILESTONE_6E_INSTALL_REPORT_NAME,
    )
    layout = WorkspaceLayout.from_root(resolved_workspace)
    return _install_prepared(
        resolved_workspace,
        prepared,
        milestone_label="Milestone 6E",
        allow_prior_report=layout.manifests / MILESTONE_6D_INSTALL_REPORT_NAME,
        allow_pristine_extracted=True,
    )
