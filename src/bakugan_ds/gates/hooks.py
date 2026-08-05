from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence

CORE_G_PROTECTED_RANGES = (
    range(0x23C18, 0x23C1C),
    range(0x23CB0, 0x23CF8),
    range(0x23D78, 0x23D7C),
)
_HEX_DIGITS = frozenset("0123456789abcdef")


class HookPurpose(StrEnum):
    GATE_BONUS = "gate_bonus"
    BATTLE_TYPE_SELECTOR = "battle_type_selector"
    CONTEXT_ACCESS = "context_access"
    EXPANDED_DATA_LOOKUP = "expanded_data_lookup"


@dataclass(frozen=True)
class HookSite:
    purpose: HookPurpose
    component: str
    address: int
    component_offset: int
    instruction_length: int
    expected_bytes_sha256: str
    calling_convention: str
    live_registers: tuple[str, ...]
    stack_assumptions: str
    overwritten_behavior: str
    return_address: int
    code_space_strategy: str
    core_g_compatible: bool
    rollback: str
    confidence: Confidence
    evidence: str

    def validate(self) -> None:
        if not isinstance(self.purpose, HookPurpose):
            raise WorkspaceError("hook purpose is invalid")
        if not self.component.strip():
            raise WorkspaceError("hook component must be nonempty")
        if self.address < 0 or self.component_offset < 0 or self.return_address < 0:
            raise WorkspaceError("hook addresses and offsets must be nonnegative")
        if self.instruction_length <= 0 or self.instruction_length % 4:
            raise WorkspaceError("hook instruction length must be a positive multiple of four")
        digest = self.expected_bytes_sha256
        if len(digest) != 64 or any(character not in _HEX_DIGITS for character in digest):
            raise WorkspaceError("hook expected bytes must use a lowercase SHA-256 value")
        for label, value in (
            ("calling convention", self.calling_convention),
            ("stack assumptions", self.stack_assumptions),
            ("overwritten behavior", self.overwritten_behavior),
            ("code-space strategy", self.code_space_strategy),
            ("rollback", self.rollback),
            ("evidence", self.evidence),
        ):
            if not value.strip():
                raise WorkspaceError(f"hook {label} must be nonempty")
        if not self.live_registers or any(not value.strip() for value in self.live_registers):
            raise WorkspaceError("hook live registers must be nonempty")
        if type(self.core_g_compatible) is not bool or not self.core_g_compatible:
            raise WorkspaceError("hook must explicitly preserve core-G compatibility")
        if self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError("hook boundary must be confirmed")


def _overlaps(first_start: int, first_length: int, second: range) -> bool:
    first_end = first_start + first_length
    return first_start < second.stop and second.start < first_end


def validate_hook_sites(sites: tuple[HookSite, ...]) -> None:
    by_purpose: dict[HookPurpose, HookSite] = {}
    occupied: list[tuple[str, int, int, HookPurpose]] = []
    for site in sites:
        site.validate()
        if site.purpose in by_purpose:
            raise WorkspaceError(f"duplicate hook purpose: {site.purpose}")
        by_purpose[site.purpose] = site
        if site.component == "overlay_0007":
            for protected in CORE_G_PROTECTED_RANGES:
                if _overlaps(site.component_offset, site.instruction_length, protected):
                    raise WorkspaceError(
                        f"hook {site.purpose} overlaps protected core-G range "
                        f"0x{protected.start:X}:0x{protected.stop:X}"
                    )
        for component, start, end, purpose in occupied:
            if (
                site.component == component
                and site.component_offset < end
                and start < (site.component_offset + site.instruction_length)
            ):
                raise WorkspaceError(f"hook {site.purpose} overlaps hook {purpose}")
        occupied.append(
            (
                site.component,
                site.component_offset,
                site.component_offset + site.instruction_length,
                site.purpose,
            )
        )

    missing = sorted(set(HookPurpose) - by_purpose.keys(), key=str)
    if missing:
        raise WorkspaceError(
            "missing hook purposes: " + ", ".join(str(purpose) for purpose in missing)
        )


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise WorkspaceError(f"{label} must be a boolean")
    return value


def _parse_integer(value: object, label: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value, 0)
        raise ValueError
    except ValueError as exc:
        raise WorkspaceError(f"{label} must be an integer") from exc


def normalize_hook_capture(payload: dict[str, object]) -> tuple[HookSite, ...]:
    raw_sites = _require_array(payload.get("sites"), "sites")
    sites: list[HookSite] = []
    for index, raw in enumerate(raw_sites):
        item = _require_object(raw, f"sites[{index}]")
        try:
            site = HookSite(
                purpose=HookPurpose(str(item["purpose"])),
                component=str(item["component"]),
                address=_parse_integer(item["address"], f"sites[{index}].address"),
                component_offset=_parse_integer(
                    item["component_offset"], f"sites[{index}].component_offset"
                ),
                instruction_length=_parse_integer(
                    item["instruction_length"], f"sites[{index}].instruction_length"
                ),
                expected_bytes_sha256=str(item["expected_bytes_sha256"]),
                calling_convention=str(item["calling_convention"]),
                live_registers=tuple(
                    str(value)
                    for value in _require_array(
                        item["live_registers"], f"sites[{index}].live_registers"
                    )
                ),
                stack_assumptions=str(item["stack_assumptions"]),
                overwritten_behavior=str(item["overwritten_behavior"]),
                return_address=_parse_integer(
                    item["return_address"], f"sites[{index}].return_address"
                ),
                code_space_strategy=str(item["code_space_strategy"]),
                core_g_compatible=_require_bool(
                    item["core_g_compatible"], f"sites[{index}].core_g_compatible"
                ),
                rollback=str(item["rollback"]),
                confidence=Confidence(str(item["confidence"])),
                evidence=str(item["evidence"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid sites[{index}]: {exc}") from exc
        sites.append(site)
    result = tuple(sorted(sites, key=lambda site: str(site.purpose)))
    validate_hook_sites(result)
    return result


# Exact displaced bytes for the four approved Milestone 6C hook boundaries.
HOOK_SOURCE_BYTES: dict[HookPurpose, bytes] = {
    HookPurpose.GATE_BONUS: bytes.fromhex(
        "1910d5e5b400d6e1011ea0e1211ea0e161a2f8eb0a10a0e3900101e0b211c5e1"
    ),
    HookPurpose.CONTEXT_ACCESS: bytes.fromhex("010082e0be00c5e1"),
    HookPurpose.BATTLE_TYPE_SELECTOR: bytes.fromhex("151400eb"),
    HookPurpose.EXPANDED_DATA_LOOKUP: bytes.fromhex("08402de9"),
}


def validate_hook_source_bytes(purpose: HookPurpose, expected_sha256: str) -> bytes:
    if not isinstance(purpose, HookPurpose):
        raise WorkspaceError("hook source purpose is invalid")
    data = HOOK_SOURCE_BYTES[purpose]
    import hashlib

    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise WorkspaceError(f"hook source bytes for {purpose} do not match committed SHA-256")
    return data
