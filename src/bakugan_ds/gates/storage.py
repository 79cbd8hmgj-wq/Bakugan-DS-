from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import WorkspaceError

REQUIRED_STORAGE_CANDIDATES = frozenset(
    {
        "nitrofs",
        "expanded_executable_overlay",
        "dedicated_overlay",
        "hybrid",
    }
)


@dataclass(frozen=True)
class StorageCandidate:
    name: str
    scope: str
    confirmed_requirements: tuple[str, ...]
    unresolved_requirements: tuple[str, ...]
    risks: tuple[str, ...]
    viable: bool

    def validate(self) -> None:
        if self.name not in REQUIRED_STORAGE_CANDIDATES:
            raise WorkspaceError(f"unknown storage candidate: {self.name}")
        if not self.scope.strip():
            raise WorkspaceError(f"storage candidate {self.name} requires a scope")
        if not self.confirmed_requirements:
            raise WorkspaceError(
                f"storage candidate {self.name} requires confirmed requirements"
            )
        if any(not value.strip() for value in self.confirmed_requirements):
            raise WorkspaceError(
                f"storage candidate {self.name} has an empty confirmed requirement"
            )
        if any(not value.strip() for value in self.unresolved_requirements):
            raise WorkspaceError(
                f"storage candidate {self.name} has an empty unresolved requirement"
            )
        if not self.risks or any(not value.strip() for value in self.risks):
            raise WorkspaceError(f"storage candidate {self.name} requires bounded risks")
        if self.viable and self.unresolved_requirements:
            raise WorkspaceError(
                f"viable storage candidate {self.name} still has unresolved requirements"
            )
        if not self.viable and not self.unresolved_requirements:
            raise WorkspaceError(
                f"non-viable storage candidate {self.name} must state unresolved requirements"
            )


@dataclass(frozen=True)
class StorageDecision:
    primary: str
    fallback: str
    candidates: tuple[StorageCandidate, ...]
    evidence: tuple[str, ...]


def validate_storage_decision(decision: StorageDecision) -> None:
    if decision.primary == decision.fallback:
        raise WorkspaceError("storage primary and fallback must be distinct")
    if not decision.evidence or any(not item.strip() for item in decision.evidence):
        raise WorkspaceError("storage decision requires nonempty evidence")

    by_name: dict[str, StorageCandidate] = {}
    for storage_candidate in decision.candidates:
        storage_candidate.validate()
        if storage_candidate.name in by_name:
            raise WorkspaceError(f"duplicate storage candidate: {storage_candidate.name}")
        by_name[storage_candidate.name] = storage_candidate

    missing = sorted(REQUIRED_STORAGE_CANDIDATES - by_name.keys())
    if missing:
        raise WorkspaceError(f"missing storage candidates: {', '.join(missing)}")
    extra = sorted(by_name.keys() - REQUIRED_STORAGE_CANDIDATES)
    if extra:
        raise WorkspaceError(f"unknown storage candidates: {', '.join(extra)}")

    for role, name in (("primary", decision.primary), ("fallback", decision.fallback)):
        selected_candidate = by_name.get(name)
        if selected_candidate is None:
            raise WorkspaceError(f"storage {role} references unknown candidate: {name}")
        if not selected_candidate.viable:
            raise WorkspaceError(f"storage {role} candidate {name} is not viable")


def append_lz10_trailer(
    original_raw: bytes,
    trailer: bytes,
    *,
    maximum_size: int,
) -> bytes:
    from bakugan_ds.compression.lz10 import lz10_declared_size
    from bakugan_ds.errors import RomFormatError

    if maximum_size <= 0:
        raise WorkspaceError("trailer maximum size must be positive")
    if not trailer:
        raise WorkspaceError("trailer must be nonempty")
    if len(trailer) > maximum_size:
        raise WorkspaceError(
            f"trailer size {len(trailer)} exceeds maximum {maximum_size}"
        )
    try:
        lz10_declared_size(original_raw)
    except RomFormatError as exc:
        raise WorkspaceError(f"carrier payload is not valid LZ10: {exc}") from exc
    return original_raw + trailer


def extract_lz10_trailer(
    raw_with_trailer: bytes,
    trailer_size: int,
    expected_magic: bytes,
) -> bytes:
    if trailer_size <= 0 or trailer_size > len(raw_with_trailer):
        raise WorkspaceError("trailer size is outside carrier payload")
    if not expected_magic:
        raise WorkspaceError("trailer magic must be nonempty")
    trailer = raw_with_trailer[-trailer_size:]
    if not trailer.startswith(expected_magic):
        raise WorkspaceError("trailer magic does not match")
    return trailer


SYSTEM2_STORAGE_DECISION = StorageDecision(
    primary="hybrid",
    fallback="nitrofs",
    candidates=(
        StorageCandidate(
            name="nitrofs",
            scope="full_roster_fallback",
            confirmed_requirements=(
                (
                    "Use a 4,152-byte G2DT trailer appended after the existing raw "
                    "LZ10 stream of font/mes_CardName.mes."
                ),
                (
                    "Native LZ10 decoding remains byte-identical because decoding "
                    "stops at the 6,524-byte declared output size."
                ),
                (
                    "Read one 32-byte header and one 40-byte selected record into a "
                    "72-byte stack buffer during battle construction."
                ),
                (
                    "Reject missing magic, unsupported version, bad record geometry, "
                    "invalid card ID, or checksum failure and use legacy behavior."
                ),
                (
                    "Rebuild by appending the exact trailer to the original raw file "
                    "payload before deterministic FAT repacking."
                ),
            ),
            unresolved_requirements=(),
            risks=(
                "Repeated raw NitroFS reads are slower than a battle-local cache.",
                (
                    "The fallback is suitable for the first prototype but should not "
                    "perform file I/O in frame-critical loops."
                ),
            ),
            viable=True,
        ),
        StorageCandidate(
            name="expanded_executable_overlay",
            scope="not_selected",
            confirmed_requirements=(
                (
                    "The decoded ARM9 contains 72 zero Gate-table bytes for global "
                    "IDs 201 through 212."
                ),
                (
                    "Overlay 7 is fixed at 467,360 decoded bytes and the current "
                    "rebuilder rejects overlay growth."
                ),
            ),
            unresolved_requirements=(
                "No safe full-roster code/data region is confirmed.",
                (
                    "The ARM9 runtime image is BLZ-compressed and the repository has "
                    "no deterministic BLZ recompressor."
                ),
                "Seventy-two bytes cannot hold the full System 2.0 roster and dispatcher data.",
            ),
            risks=(
                "Repurposing apparently zero executable data could corrupt another card subsystem.",
                "In-place hooks would become card-specific and defeat the data-driven design.",
            ),
            viable=False,
        ),
        StorageCandidate(
            name="dedicated_overlay",
            scope="not_selected",
            confirmed_requirements=(
                "The ROM has nine ARM9 overlays and all use load address 0x02219440.",
                "The current rebuild verifies that overlay counts remain unchanged.",
            ),
            unresolved_requirements=(
                "No loader route or overlay-table slot exists for a tenth overlay.",
                "Load/unload coordination with battle overlay 7 is not confirmed.",
                "Address-space ownership and relocation support are unresolved.",
            ),
            risks=(
                "A new overlay can collide with the active battle overlay.",
                "Overlay-table and FNT/FAT expansion would broaden the framework substantially.",
            ),
            viable=False,
        ),
        StorageCandidate(
            name="hybrid",
            scope="full_roster_primary",
            confirmed_requirements=(
                "Store the same 4,152-byte raw LZ10 trailer used by the NitroFS fallback.",
                (
                    "Preserve the original 0x640-byte overlay-7 BSS as zero-backed "
                    "writable bytes inside the expanded payload."
                ),
                (
                    "Append a guarded 0x8000-byte System 2.0 code region at "
                    "0x0228BC20 through 0x02293C20."
                ),
                (
                    "Set overlay-7 ram_size to 0x7A7E0 and reserve a new 0x40-byte "
                    "BSS cache at 0x02293C20 through 0x02293C60."
                ),
                (
                    "Move the ARM9 battle-arena low boundary from 0x0228BC20 to "
                    "0x02293C60 atomically with the overlay metadata changes."
                ),
                (
                    "The arena high boundary is 0x023E0000, leaving 1,360,800 bytes "
                    "after code and cache reservation."
                ),
                (
                    "Zero the cache on overlay load and reset its valid flag when the "
                    "battle object completes."
                ),
                "Reject malformed trailers and preserve the original Gate path.",
            ),
            unresolved_requirements=(),
            risks=(
                "Milestone 6B must add guarded overlay growth and overlay-metadata patch support.",
                "Every hook must tolerate an invalid cache and fall back to legacy behavior.",
            ),
            viable=True,
        ),
    ),
    evidence=(
        (
            "font/mes_CardName.mes is file ID 2762, raw size 2,840, decoded "
            "size 6,524, with 213 indexed names."
        ),
        (
            "The raw LZ10 stream reaches its declared output after 2,838 bytes and "
            "already has two ignored trailing zero bytes."
        ),
        (
            "Global IDs 1 through 103 are Gate Cards, so 103 fixed 40-byte records "
            "plus a 32-byte header require 4,152 bytes."
        ),
        (
            "ARM9 function 0x020061D8 returns 0x0228BC20 as the overlay-7 arena low "
            "boundary and 0x023E0000 as the main arena high boundary."
        ),
        (
            "Overlay-7 ram_size is 0x721A0 and BSS is 0x640; the hybrid layout changes "
            "them to 0x7A7E0 and 0x40 while preserving original BSS addresses."
        ),
    ),
)
